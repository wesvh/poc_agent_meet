"""Airflow DAG: ETL pipeline for aliados_dataset.csv → PostgreSQL.

Entry point: always triggered externally (EventBridge or Airflow REST API)
with conf = {"s3_key": "...", "s3_bucket": "..."}.
The DAG downloads the CSV from S3, processes it, and upserts into PostgreSQL.

Composition root: this file is the only place that imports concrete infrastructure
implementations (SqlAlchemyStoreRepo, etc.) and injects them into the application
layer functions (insert_staging, upsert_curated).
"""
from __future__ import annotations

import asyncio
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

log = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine safely inside Airflow tasks.

    Airflow (LocalExecutor) typically does NOT have a running event loop in the
    worker thread, so asyncio.run() works. This helper adds a fallback for
    environments where a loop is already running (e.g., testing, CeleryExecutor).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        try:
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        except ImportError:
            pass
    return asyncio.run(coro)


def _on_failure_callback(context):
    task_id = context.get("task_instance").task_id
    dag_id = context.get("dag").dag_id
    execution_date = context.get("execution_date")
    exception = context.get("exception")
    log.error(
        "[dag] Task FAILED | dag=%s task=%s execution_date=%s | error: %s",
        dag_id, task_id, execution_date, exception,
    )


default_args = {
    "owner": "rappi-handoff",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": _on_failure_callback,
}

with DAG(
    dag_id="etl_stores_csv",
    default_args=default_args,
    description="Load and normalize aliados_dataset.csv into PostgreSQL",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["etl", "stores"],
) as dag:

    def _archive_raw(**ctx) -> None:
        from src.config import Config
        from src.etl.extract import compute_file_hash, materialize_s3_object

        dag_conf = ctx["dag_run"].conf or {}
        s3_key = dag_conf.get("s3_key")
        s3_bucket = dag_conf.get("s3_bucket", Config.S3_RAW_BUCKET)

        if not s3_key:
            raise ValueError(
                "DAG conf must include 's3_key'. "
                "Trigger via ingest API (POST /upload) or EventBridge — not manually without a file."
            )

        path = _run_async(materialize_s3_object(s3_bucket, s3_key))
        file_hash = compute_file_hash(path)

        ctx["ti"].xcom_push(key="s3_key", value=s3_key)
        ctx["ti"].xcom_push(key="file_hash", value=file_hash)
        ctx["ti"].xcom_push(key="csv_path", value=path)
        log.info("Downloaded from S3: %s (hash=%s)", s3_key, file_hash)

    def _load_staging(**ctx) -> None:
        # Composition root: inject concrete ETL repo
        from src.etl.extract import read_csv_rows
        from src.etl.load import insert_staging
        from src.infrastructure.db.repositories import SqlAlchemyETLRepo

        ti = ctx["ti"]
        path = ti.xcom_pull(key="csv_path")
        s3_key = ti.xcom_pull(key="s3_key")
        file_hash = ti.xcom_pull(key="file_hash")

        rows = read_csv_rows(path)
        run_id = _run_async(insert_staging(rows, path, file_hash, s3_key, repo=SqlAlchemyETLRepo()))
        ti.xcom_push(key="etl_run_id", value=run_id)
        log.info("Staging loaded: %d rows, etl_run_id=%s", len(rows), run_id)

    def _transform_and_load(**ctx) -> None:
        # Composition root: inject concrete store, meeting, and ETL repos
        from src.etl.extract import read_csv_rows
        from src.etl.load import upsert_curated
        from src.etl.transform import transform_rows
        from src.etl.validate import check_business_rules
        from src.infrastructure.db.repositories import (
            SqlAlchemyETLRepo,
            SqlAlchemyMeetingRepo,
            SqlAlchemyStoreRepo,
        )

        ti = ctx["ti"]
        # NOTE: CSV is read again here instead of passing through XCom to avoid
        # XCom size limits for large datasets.
        path = ti.xcom_pull(key="csv_path")
        etl_run_id = ti.xcom_pull(key="etl_run_id")

        raw_rows = read_csv_rows(path)
        transformed = transform_rows(raw_rows, filename=Path(path).name)

        validated = []
        for row in transformed:
            biz_errors = check_business_rules(row)
            if biz_errors:
                row = row.with_additional_errors(biz_errors)
            validated.append(row)

        stats = _run_async(
            upsert_curated(
                validated,
                etl_run_id,
                store_repo=SqlAlchemyStoreRepo(),
                meeting_repo=SqlAlchemyMeetingRepo(),
                etl_repo=SqlAlchemyETLRepo(),
            )
        )
        schedule_candidates = [
            {
                "store_id": row.store_id,
                "scheduled_at": row.meeting.scheduled_at.isoformat(),
                "meeting_link": row.meeting.meeting_link,
            }
            for row in validated
            if row.data_quality_status != "invalid"
            and row.meeting
            and row.meeting.scheduled_at
            and row.meeting.meeting_link
        ]
        ti.xcom_push(key="schedule_candidates", value=schedule_candidates)
        log.info("ETL complete. stats=%s", stats)

    def _schedule_meetings(**ctx) -> None:
        from src.etl.meeting_scheduler import schedule_meeting_candidates

        ti = ctx["ti"]
        candidates = ti.xcom_pull(key="schedule_candidates", task_ids="transform_and_load") or []
        stats = _run_async(schedule_meeting_candidates(candidates))
        log.info("Meeting schedules ready. stats=%s", stats)

    def _cleanup_temp(**ctx) -> None:
        """Remove the temp dir created when materializing the S3 object."""
        ti = ctx["ti"]
        csv_path = ti.xcom_pull(key="csv_path", task_ids="archive_raw_to_s3")
        if csv_path:
            temp_dir = str(Path(csv_path).parent)
            if Path(temp_dir).exists() and "rappi-etl-" in temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
                log.info("Cleaned up temp dir: %s", temp_dir)

    archive_task = PythonOperator(task_id="archive_raw_to_s3", python_callable=_archive_raw)
    staging_task = PythonOperator(task_id="load_staging", python_callable=_load_staging)
    transform_task = PythonOperator(task_id="transform_and_load", python_callable=_transform_and_load)
    schedule_task = PythonOperator(task_id="schedule_meetings", python_callable=_schedule_meetings)
    cleanup_task = PythonOperator(
        task_id="cleanup_temp_files",
        python_callable=_cleanup_temp,
        trigger_rule="all_done",
    )

    archive_task >> staging_task >> transform_task >> schedule_task >> cleanup_task
