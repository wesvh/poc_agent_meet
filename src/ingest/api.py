"""Ingest service.

Behavior:
- accepts CSV uploads
- writes the raw file to S3
- relies on S3/EventBridge to trigger the ETL DAG
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from src.config import Config
from src.infrastructure.s3.storage import upload_bytes

log = logging.getLogger(__name__)

app = FastAPI(title="Handoff Ingest API", version="1.0.0")

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/upload", summary="Upload a CSV and trigger the ETL pipeline")
async def upload_csv(file: UploadFile = File(...)) -> JSONResponse:
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest_name = f"{Path(file.filename).stem}_{ts}.csv"
    s3_key = f"{Config.S3_RAW_PREFIX}/{datetime.now(timezone.utc).strftime('%Y/%m/%d/%H%M%S')}/{dest_name}"

    content = await file.read()
    await upload_bytes(content, Config.S3_RAW_BUCKET, s3_key, content_type="text/csv")
    log.info("Uploaded CSV to s3://%s/%s (%d bytes)", Config.S3_RAW_BUCKET, s3_key, len(content))
    return JSONResponse(
        status_code=202,
        content={
            "status": "uploaded",
            "file": dest_name,
            "bytes": len(content),
            "s3_bucket": Config.S3_RAW_BUCKET,
            "s3_key": s3_key,
            "trigger": "eventbridge",
        },
    )
