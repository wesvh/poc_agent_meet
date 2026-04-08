"""File storage port — abstract interface for object storage (S3, local, etc.)

Usage:
    from src.core.ports.storage import FileStorage

    async def archive(path: str, storage: FileStorage) -> str:
        await storage.upload(path, bucket="rappi-raw", key="raw/file.csv")
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class FileStorage(Protocol):
    """Persistence contract for binary object storage."""

    async def upload(self, local_path: str, bucket: str, key: str) -> None:
        """Upload a local file to object storage."""
        ...

    async def upload_bytes(
        self,
        content: bytes,
        bucket: str,
        key: str,
        content_type: str | None = None,
    ) -> None:
        """Upload raw bytes to object storage."""
        ...

    async def download(self, bucket: str, key: str, local_path: str) -> None:
        """Download an object to a local path."""
        ...

    async def ensure_bucket(self, bucket: str) -> None:
        """Create bucket if it does not exist (idempotent)."""
        ...

    async def enable_eventbridge_notifications(self, bucket: str) -> None:
        """Enable EventBridge notifications on a bucket."""
        ...
