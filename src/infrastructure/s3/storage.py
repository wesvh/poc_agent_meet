"""S3 / LocalStack object storage adapter.

Implements FileStorage protocol from src.core.ports.storage.
Also exposes the raw async helper functions used by extract.py.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import aioboto3

from src.config import Config

log = logging.getLogger(__name__)


@asynccontextmanager
async def _s3():
    session = aioboto3.Session()
    kwargs: dict = {"region_name": Config.AWS_REGION}
    if Config.AWS_ENDPOINT:
        kwargs["endpoint_url"] = Config.AWS_ENDPOINT
    async with session.client("s3", **kwargs) as client:
        yield client


# ── Low-level helpers (used by extract.py and S3FileStorage) ─────────────────

async def upload_file(local_path: str, bucket: str, key: str) -> None:
    size = os.path.getsize(local_path)
    log.info("[s3] Uploading '%s' (%d bytes) → s3://%s/%s", local_path, size, bucket, key)
    async with _s3() as s3:
        await s3.upload_file(local_path, bucket, key)
    log.debug("[s3] Upload complete: s3://%s/%s", bucket, key)


async def upload_bytes(content: bytes, bucket: str, key: str, content_type: str | None = None) -> None:
    extra_args: dict = {}
    if content_type:
        extra_args["ContentType"] = content_type
    log.info("[s3] Uploading %d bytes → s3://%s/%s", len(content), bucket, key)
    async with _s3() as s3:
        await s3.put_object(Bucket=bucket, Key=key, Body=content, **extra_args)
    log.debug("[s3] Upload complete: s3://%s/%s", bucket, key)


async def download_file(bucket: str, key: str, local_path: str) -> None:
    log.info("[s3] Downloading s3://%s/%s → '%s'", bucket, key, local_path)
    async with _s3() as s3:
        await s3.download_file(bucket, key, local_path)
    log.debug("[s3] Download complete: '%s'", local_path)


async def ensure_bucket(bucket: str) -> None:
    async with _s3() as s3:
        try:
            await s3.create_bucket(Bucket=bucket)
        except Exception as exc:
            err = str(exc)
            if "BucketAlreadyExists" not in err and "BucketAlreadyOwnedByYou" not in err:
                raise


async def enable_eventbridge_notifications(bucket: str) -> None:
    async with _s3() as s3:
        await s3.put_bucket_notification_configuration(
            Bucket=bucket,
            NotificationConfiguration={"EventBridgeConfiguration": {}},
        )


# ── FileStorage Protocol implementation ──────────────────────────────────────

class S3FileStorage:
    """Concrete FileStorage adapter backed by S3 / LocalStack.

    Inject this wherever a FileStorage port is required:
        storage = S3FileStorage()
        await storage.upload(local_path, bucket, key)
    """

    async def upload(self, local_path: str, bucket: str, key: str) -> None:
        await upload_file(local_path, bucket, key)

    async def upload_bytes(
        self,
        content: bytes,
        bucket: str,
        key: str,
        content_type: str | None = None,
    ) -> None:
        await upload_bytes(content, bucket, key, content_type)

    async def download(self, bucket: str, key: str, local_path: str) -> None:
        await download_file(bucket, key, local_path)

    async def ensure_bucket(self, bucket: str) -> None:
        await ensure_bucket(bucket)

    async def enable_eventbridge_notifications(self, bucket: str) -> None:
        await enable_eventbridge_notifications(bucket)
