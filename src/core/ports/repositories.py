"""Repository ports — abstract interfaces (Protocols) for all persistence operations.

These are the contracts that the application layer depends on.
Infrastructure adapters (SQLAlchemy, etc.) implement these Protocols.
The agent tools and ETL pipeline both import from here — never from infrastructure directly.

Usage:
    from src.core.ports import StoreRepository, MeetingRepository, ETLRunRepository

    async def my_use_case(store_repo: StoreRepository) -> None:
        await store_repo.upsert(row)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from src.schemas.etl import TransformedStoreRow, ValidationIssue


@runtime_checkable
class StoreRepository(Protocol):
    """Persistence contract for stores (aliados)."""

    async def upsert(self, row: TransformedStoreRow) -> None:
        """Insert or update a store from a transformed ETL row."""
        ...

    async def replace_payment_methods(self, store_id: str, methods: list[str]) -> None:
        """Replace all payment methods for a store atomically."""
        ...

    async def replace_schedule_days(self, store_id: str, days: list[str]) -> None:
        """Replace all schedule days for a store atomically."""
        ...


@runtime_checkable
class MeetingRepository(Protocol):
    """Persistence contract for meeting sessions."""

    async def upsert(self, store_id: str, scheduled_at: datetime | None, meeting_link: str | None) -> None:
        """Insert meeting if not already present (idempotent by store+time+link)."""
        ...

    async def find_pending(
        self,
        store_id: str,
        scheduled_at: datetime,
        meeting_link: str,
    ) -> Any | None:
        """Return the pending meeting matching the given criteria, or None."""
        ...


@runtime_checkable
class ETLRunRepository(Protocol):
    """Persistence contract for ETL run tracking and audit trail."""

    async def create_with_staging(
        self,
        filename: str,
        file_hash: str,
        s3_key: str | None,
        raw_rows: list[dict],
    ) -> str:
        """Create an ETL run record + insert all raw rows into staging. Returns run_id."""
        ...

    async def insert_errors(
        self,
        run_id: str,
        store_id: str,
        row_num: int,
        errors: list[ValidationIssue],
    ) -> None:
        """Persist field-level validation errors for a row."""
        ...

    async def mark_success(self, run_id: str, stats: dict) -> None:
        """Mark an ETL run as completed successfully with final stats."""
        ...

    async def mark_failed(self, run_id: str, stats: dict) -> None:
        """Mark an ETL run as failed with partial stats."""
        ...

    async def exists(self, run_id: str) -> bool:
        """Check if the given ETL run exists."""
        ...
