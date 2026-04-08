from __future__ import annotations

import csv
import hashlib
import logging
import os
import tempfile
from pathlib import Path

from src.infrastructure.s3.storage import download_file

log = logging.getLogger(__name__)


def compute_file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    digest = h.hexdigest()
    log.debug("[extract] SHA-256 of '%s': %s", path, digest)
    return digest


async def materialize_s3_object(bucket: str, key: str, filename: str | None = None) -> str:
    """Download an S3 object to a temp dir. Returns the local path."""
    suffix = Path(filename or key).suffix or ".csv"
    temp_dir = tempfile.mkdtemp(prefix="rappi-etl-")
    local_path = os.path.join(temp_dir, Path(filename or key).name or f"input{suffix}")
    log.info("[extract] Downloading s3://%s/%s → %s", bucket, key, local_path)
    await download_file(bucket, key, local_path)
    log.info("[extract] Download complete: %s", local_path)
    return local_path


def read_csv_rows(local_path: str) -> list[dict]:
    with open(local_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    log.info("[extract] Read %d rows from '%s'", len(rows), local_path)
    return rows
