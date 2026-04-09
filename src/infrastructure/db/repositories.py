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
    HandoffSession,
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

    async def get_by_id(self, store_id: str) -> dict | None:
        async with session_scope() as session:
            store = await session.get(Store, store_id)
            if store is None:
                return None
            data = {c.name: getattr(store, c.name) for c in Store.__table__.columns}
            # Attach payment methods
            methods_result = await session.execute(
                select(StorePaymentMethod.method).where(StorePaymentMethod.store_id == store_id)
            )
            data["payment_methods"] = [r[0] for r in methods_result]
            # Attach schedule days
            days_result = await session.execute(
                select(StoreScheduleDay.day).where(StoreScheduleDay.store_id == store_id)
            )
            data["schedule_days"] = [r[0] for r in days_result]
            # Serialize special types
            for key, val in data.items():
                if isinstance(val, (UUID,)):
                    data[key] = str(val)
                elif isinstance(val, datetime):
                    data[key] = val.isoformat()
                elif hasattr(val, "isoformat"):
                    data[key] = val.isoformat()
            return data

    async def update_field(self, store_id: str, field: str, value) -> None:
        allowed = {c.name for c in Store.__table__.columns} - {"store_id"}
        if field not in allowed:
            raise ValueError(f"Cannot update field '{field}' on stores")
        async with session_scope() as session:
            async with session.begin():
                store = await session.get(Store, store_id)
                if store is None:
                    raise ValueError(f"Store not found: {store_id}")
                setattr(store, field, value)


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

    async def get_pending_by_store_id(self, store_id: str) -> dict | None:
        async with session_scope() as session:
            meeting = await session.scalar(
                select(Meeting)
                .where(Meeting.store_id == store_id, Meeting.status == "pending")
                .order_by(Meeting.scheduled_at.asc())
                .limit(1)
            )
            if meeting is None:
                return None
            return {
                "id": str(meeting.id),
                "store_id": meeting.store_id,
                "scheduled_at": meeting.scheduled_at.isoformat() if meeting.scheduled_at else None,
                "meeting_link": meeting.meeting_link,
                "status": meeting.status,
            }

    async def update_status(self, meeting_id: str, status: str) -> None:
        async with session_scope() as session:
            async with session.begin():
                meeting = await session.get(Meeting, UUID(meeting_id))
                if meeting is None:
                    raise ValueError(f"Meeting not found: {meeting_id}")
                meeting.status = status
                meeting.updated_at = func.now()


class SqlAlchemyHandoffSessionRepo:
    """Implements HandoffSessionRepository using SQLAlchemy async sessions."""

    async def create(self, session_id: str, store_id: str, meeting_id: str | None) -> None:
        async with session_scope() as session:
            async with session.begin():
                hs = HandoffSession(
                    id=UUID(session_id),
                    store_id=store_id,
                    meeting_id=UUID(meeting_id) if meeting_id else None,
                )
                session.add(hs)
        log.info("[session-repo] Created handoff session %s for store %s", session_id, store_id)

    async def save_transcript(self, session_id: str, messages: list[dict]) -> None:
        async with session_scope() as session:
            async with session.begin():
                hs = await session.get(HandoffSession, UUID(session_id))
                if hs is None:
                    raise ValueError(f"Handoff session not found: {session_id}")
                hs.transcript = messages

    async def save_summary(self, session_id: str, summary: str) -> None:
        async with session_scope() as session:
            async with session.begin():
                hs = await session.get(HandoffSession, UUID(session_id))
                if hs is None:
                    raise ValueError(f"Handoff session not found: {session_id}")
                hs.summary = summary

    async def update_status(self, session_id: str, status: str) -> None:
        async with session_scope() as session:
            async with session.begin():
                hs = await session.get(HandoffSession, UUID(session_id))
                if hs is None:
                    raise ValueError(f"Handoff session not found: {session_id}")
                hs.status = status
                if status in ("completed", "abandoned"):
                    hs.ended_at = func.now()

    async def update_session_data(
        self,
        session_id: str,
        *,
        blocks_completed: dict | None = None,
        collected_data: dict | None = None,
        issues_detected: list[str] | None = None,
        commitments: list[str] | None = None,
        turn_count: int | None = None,
    ) -> None:
        async with session_scope() as session:
            async with session.begin():
                hs = await session.get(HandoffSession, UUID(session_id))
                if hs is None:
                    raise ValueError(f"Handoff session not found: {session_id}")
                if blocks_completed is not None:
                    hs.blocks_completed = blocks_completed
                if collected_data is not None:
                    hs.collected_data = collected_data
                if issues_detected is not None:
                    hs.issues_detected = issues_detected
                if commitments is not None:
                    hs.commitments = commitments
                if turn_count is not None:
                    hs.turn_count = turn_count

    async def get_by_store(self, store_id: str, limit: int = 5) -> list[dict]:
        async with session_scope() as session:
            result = await session.execute(
                select(HandoffSession)
                .where(HandoffSession.store_id == store_id)
                .order_by(HandoffSession.created_at.desc())
                .limit(limit)
            )
            sessions = result.scalars().all()
            return [
                {
                    "id": str(hs.id),
                    "status": hs.status,
                    "blocks_completed": hs.blocks_completed,
                    "issues_detected": hs.issues_detected,
                    "commitments": hs.commitments,
                    "summary": hs.summary,
                    "started_at": hs.started_at.isoformat() if hs.started_at else None,
                    "ended_at": hs.ended_at.isoformat() if hs.ended_at else None,
                    "turn_count": hs.turn_count,
                }
                for hs in sessions
            ]


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
