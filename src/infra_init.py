"""Infra init: creates S3 buckets and verifies DB connectivity."""
from __future__ import annotations

import asyncio
import logging
import sys

from sqlalchemy import func, select

from src.config import Config
from src.infrastructure.db.engine import session_scope
from src.infrastructure.db.orm import Store
from src.infrastructure.events.eventbridge import ensure_s3_to_airflow_rule
from src.infrastructure.s3.storage import enable_eventbridge_notifications, ensure_bucket

logging.basicConfig(level=logging.INFO, format="[infra-init] %(message)s")
log = logging.getLogger(__name__)


async def create_buckets() -> None:
    for bucket in [Config.S3_RAW_BUCKET, Config.S3_ARCHIVE_BUCKET]:
        await ensure_bucket(bucket)
        log.info("Bucket ready: %s", bucket)
    await enable_eventbridge_notifications(Config.S3_RAW_BUCKET)
    log.info("Bucket EventBridge notifications enabled: %s", Config.S3_RAW_BUCKET)
    await ensure_s3_to_airflow_rule()
    log.info("EventBridge -> Airflow rule ready for bucket: %s", Config.S3_RAW_BUCKET)


async def verify_db() -> None:
    async with session_scope() as session:
        count = await session.scalar(select(func.count()).select_from(Store))
    log.info("DB connection OK. stores.count=%d", count)


async def main() -> None:
    log.info("Starting infra init...")
    await create_buckets()
    await verify_db()
    log.info("Infra init complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        log.error("Infra init failed: %s", exc)
        sys.exit(1)
