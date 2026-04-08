"""SQLAlchemy concrete implementations of the repository ports.

These classes implement the Protocols defined in src.core.ports.repositories.
They own all SQLAlchemy-specific logic: ORM models, sessions, SQL statements.

Usage (composition root — DAG or API entry point):
    from src.infrastructure.db.repositories import SqlAlchemyStoreRepo, SqlAlchemyETLRepo, SqlAlchemyMeetingRepo

    store_repo = SqlAlchemyStoreRepo()
    etl_repo   = SqlAlchemyETLRepo()
    meeting_repo = SqlAlchemyMeetingRepo()
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select

from src.infrastructure.db.engine import session_scope
from src.infrastructure.db.orm import (
    ETLError,
    ETLRun,
    Meeting,
    StagingStoreRaw,
    Store,
    StorePaymentMethod,
    StoreScheduleDay,
)
from src.schemas.etl import TransformedStoreRow, ValidationIssue

log = logging.getLogger(__name__)


class SqlAlchemyStoreRepo:
    """Implements StoreRepository using SQLAlchemy async sessions."""

    async def upsert(self, row: TransformedStoreRow) -> None:
        async with session_scope() as session:
            async with session.begin():
                await session.execute(Store.upsert_stmt(row.store_values()))

    async def replace_payment_methods(self, store_id: str, methods: list[str]) -> None:
        async with session_scope() as session:
            async with session.begin():
                await session.execute(StorePaymentMethod.delete_for_store_stmt(store_id))
                if methods:
                    await session.execute(StorePaymentMethod.insert_many_stmt(store_id, methods))

    async def replace_schedule_days(self, store_id: str, days: list[str]) -> None:
        async with session_scope() as session:
            async with session.begin():
                await session.execute(StoreScheduleDay.delete_for_store_stmt(store_id))
                if days:
                    await session.execute(StoreScheduleDay.insert_many_stmt(store_id, days))


class SqlAlchemyMeetingRepo:
    """Implements MeetingRepository using SQLAlchemy async sessions."""

    async def upsert(
        self,
        store_id: str,
        scheduled_at: datetime | None,
        meeting_link: str | None,
    ) -> None:
        async with session_scope() as session:
            async with session.begin():
                await session.execute(
                    Meeting.upsert_stmt(
                        {
                            "store_id": store_id,
                            "scheduled_at": scheduled_at,
                            "meeting_link": meeting_link,
                        }
                    )
                )

    async def find_pending(
        self,
        store_id: str,
        scheduled_at: datetime,
        meeting_link: str,
    ) -> Meeting | None:
        async with session_scope() as session:
            return await session.scalar(
                select(Meeting).where(
                    Meeting.store_id == store_id,
                    Meeting.scheduled_at == scheduled_at,
                    Meeting.meeting_link == meeting_link,
                    Meeting.status == "pending",
                )
            )


class SqlAlchemyETLRepo:
    """Implements ETLRunRepository using SQLAlchemy async sessions."""

    async def create_with_staging(
        self,
        filename: str,
        file_hash: str,
        s3_key: str | None,
        raw_rows: list[dict],
    ) -> str:
        async with session_scope() as session:
            async with session.begin():
                etl_run = ETLRun(
                    source_file_name=Path(filename).name,
                    source_file_hash=file_hash,
                    s3_raw_key=s3_key,
                )
                session.add(etl_run)
                await session.flush()
                run_id = str(etl_run.id)

                session.add_all(
                    [
                        StagingStoreRaw(
                            etl_run_id=UUID(run_id),
                            source_file_name=Path(filename).name,
                            source_row_number=i + 1,
                            raw_data=row,
                        )
                        for i, row in enumerate(raw_rows)
                    ]
                )
        log.info("[etl-repo] Created ETL run %s with %d staging rows", run_id, len(raw_rows))
        return run_id

    async def insert_errors(
        self,
        run_id: str,
        store_id: str,
        row_num: int,
        errors: list[ValidationIssue],
    ) -> None:
        if not errors:
            return
        async with session_scope() as session:
            async with session.begin():
                session.add_all(
                    [
                        ETLError(
                            etl_run_id=UUID(run_id),
                            source_row_number=row_num,
                            store_id=store_id,
                            field_name=issue.field,
                            raw_value=issue.raw,
                            error_message=issue.msg,
                        )
                        for issue in errors
                    ]
                )

    async def mark_success(self, run_id: str, stats: dict) -> None:
        await self._finish(run_id, "success", stats)

    async def mark_failed(self, run_id: str, stats: dict) -> None:
        await self._finish(run_id, "failed", stats)

    async def exists(self, run_id: str) -> bool:
        async with session_scope() as session:
            result = await session.scalar(
                select(func.count()).select_from(ETLRun).where(ETLRun.id == UUID(run_id))
            )
            return bool(result)

    async def _finish(self, run_id: str, status: str, stats: dict) -> None:
        async with session_scope() as session:
            async with session.begin():
                etl_run = await session.get(ETLRun, UUID(run_id))
                if etl_run is None:
                    raise ValueError(f"ETL run not found: {run_id}")
                etl_run.status = status
                etl_run.finished_at = func.now()
                etl_run.rows_raw = stats.get("raw", 0)
                etl_run.rows_valid = stats.get("valid", 0)
                etl_run.rows_invalid = stats.get("invalid", 0)
                etl_run.rows_upserted = stats.get("upserted", 0)
