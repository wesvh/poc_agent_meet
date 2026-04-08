import os


def _int_env(name: str, default: str) -> int:
    value = os.getenv(name, default)
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Environment variable {name}={value!r} must be an integer") from None


class Config:
    # App database
    DB_HOST: str = os.getenv("APP_DB_HOST", "localhost")
    DB_PORT: int = _int_env("APP_DB_PORT", "5432")
    DB_NAME: str = os.getenv("APP_DB_NAME", "rappi_handoff")
    DB_USER: str = os.getenv("APP_DB_USER", "app")
    DB_PASSWORD: str = os.getenv("APP_DB_PASSWORD", "")

    # S3 / LocalStack
    AWS_ENDPOINT: str | None = os.getenv("LOCALSTACK_ENDPOINT")
    AWS_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    S3_RAW_BUCKET: str = os.getenv("S3_RAW_BUCKET", "rappi-handoff-raw")
    S3_ARCHIVE_BUCKET: str = os.getenv("S3_ARCHIVE_BUCKET", "rappi-handoff-archive")
    S3_RAW_PREFIX: str = os.getenv("S3_RAW_PREFIX", "raw")

    # Airflow API.
    # EventBridge uses this API as the ETL target.
    AIRFLOW_BASE_URL: str = os.getenv("AIRFLOW_BASE_URL", "http://airflow-webserver:8080")
    AIRFLOW_USERNAME: str = os.getenv("AIRFLOW_ADMIN_USERNAME", "airflow")
    AIRFLOW_PASSWORD: str = os.getenv("AIRFLOW_ADMIN_PASSWORD", "airflow")
    AIRFLOW_ETL_DAG_ID: str = os.getenv("AIRFLOW_ETL_DAG_ID", "etl_stores_csv")

    # EventBridge names for the event-driven ETL path.
    EVENTBRIDGE_CONNECTION_NAME: str = os.getenv("EVENTBRIDGE_CONNECTION_NAME", "rappi-airflow-basic-auth")
    EVENTBRIDGE_API_DESTINATION_NAME: str = os.getenv("EVENTBRIDGE_API_DESTINATION_NAME", "rappi-airflow-dag-trigger")
    EVENTBRIDGE_RULE_NAME: str = os.getenv("EVENTBRIDGE_RULE_NAME", "rappi-s3-object-created-csv")
    EVENTBRIDGE_TARGET_ID: str = os.getenv("EVENTBRIDGE_TARGET_ID", "airflow-dag-trigger")
    EVENTBRIDGE_INVOKE_ROLE_NAME: str = os.getenv("EVENTBRIDGE_INVOKE_ROLE_NAME", "rappi-eventbridge-invoke-airflow")
    EVENTBRIDGE_USE_INPUT_TRANSFORMER: bool = os.getenv("EVENTBRIDGE_USE_INPUT_TRANSFORMER", "1") == "1"
    EVENTBRIDGE_FILTER_CSV_SUFFIX: bool = os.getenv("EVENTBRIDGE_FILTER_CSV_SUFFIX", "1") == "1"

    # EventBridge Scheduler for future meeting sessions.
    MEETING_SCHEDULE_GROUP_NAME: str = os.getenv("MEETING_SCHEDULE_GROUP_NAME", "rappi-handoff-meetings")
    MEETING_SCHEDULE_ROLE_NAME: str = os.getenv("MEETING_SCHEDULE_ROLE_NAME", "rappi-scheduler-put-events")
    MEETING_SCHEDULE_PREFIX: str = os.getenv("MEETING_SCHEDULE_PREFIX", "rappi-meeting")
    MEETING_EVENT_SOURCE: str = os.getenv("MEETING_EVENT_SOURCE", "rappi.handoff.meeting")
    MEETING_EVENT_DETAIL_TYPE: str = os.getenv("MEETING_EVENT_DETAIL_TYPE", "MeetingDue")
    MEETING_EVENT_BUS_NAME: str = os.getenv("MEETING_EVENT_BUS_NAME", "default")
    MEETING_LEAD_MINUTES: int = _int_env("MEETING_LEAD_MINUTES", "5")
