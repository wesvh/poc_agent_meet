"""ETL load — application layer.

Orchestrates persistence of transformed ETL rows.
Depends only on repository Protocols (core.ports) — never on SQLAlchemy ORM directly.
Concrete implementations are injected by the entry point (DAG).
"""
from __future__ import annotations

import logging

from src.core.ports.repositories import ETLRunRepository, MeetingRepository, StoreRepository
from src.schemas.etl import TransformedStoreRow

log = logging.getLogger(__name__)


async def insert_staging(
    rows: list[dict],
    filename: str,
    file_hash: str,
    s3_key: str | None,
    *,
    repo: ETLRunRepository,
) -> str:
    """Create an ETL run record and persist all raw staging rows. Returns run_id."""
    run_id = await repo.create_with_staging(filename, file_hash, s3_key, rows)
    log.info("[load] Staging inserted: %d rows | etl_run_id=%s", len(rows), run_id)
    return run_id


async def upsert_curated(
    transformed_rows: list[TransformedStoreRow],
    etl_run_id: str,
    *,
    store_repo: StoreRepository,
    meeting_repo: MeetingRepository,
    etl_repo: ETLRunRepository,
) -> dict:
    """Upsert transformed rows into curated tables. Returns stats dict."""
    stats: dict = {
        "raw": len(transformed_rows),
        "valid": 0,
        "invalid": 0,
        "upserted": 0,
    }

    try:
        if not await etl_repo.exists(etl_run_id):
            raise ValueError(f"ETL run not found: {etl_run_id}")

        for row in transformed_rows:
            await _process_row(row, etl_run_id, stats, store_repo, meeting_repo, etl_repo)

        await etl_repo.mark_success(etl_run_id, stats)
        log.info("[load] Curated upsert complete | upserted=%d stats=%s", stats["upserted"], stats)

    except Exception:
        log.exception("[load] upsert_curated failed | etl_run_id=%s stats=%s", etl_run_id, stats)
        if await etl_repo.exists(etl_run_id):
            await etl_repo.mark_failed(etl_run_id, stats)
        raise

    return stats


async def _process_row(
    row: TransformedStoreRow,
    etl_run_id: str,
    stats: dict,
    store_repo: StoreRepository,
    meeting_repo: MeetingRepository,
    etl_repo: ETLRunRepository,
) -> None:
    if row.data_quality_status == "invalid":
        stats["invalid"] += 1
        await etl_repo.insert_errors(
            etl_run_id,
            row.store_id,
            row.source_row_number,
            row.validation_errors,
        )
    else:
        stats["valid"] += 1
        await store_repo.upsert(row)
        await store_repo.replace_payment_methods(row.store_id, row.payment_methods)
        await store_repo.replace_schedule_days(row.store_id, row.schedule_days)
        if row.meeting:
            await meeting_repo.upsert(
                row.store_id,
                row.meeting.scheduled_at,
                row.meeting.meeting_link,
            )
        stats["upserted"] += 1
