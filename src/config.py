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

    # Agent LLM (via LiteLLM)
    AGENT_ROUTER_MODEL: str = os.getenv("AGENT_ROUTER_MODEL", "openai/gpt-5.4-mini")
    AGENT_MODEL: str = os.getenv("AGENT_MODEL", "openai/gpt-5.4-nano")
    AGENT_CHEAP_MODEL: str = os.getenv("AGENT_CHEAP_MODEL", "openai/gpt-5.4-nano")
    AGENT_TEMPERATURE: float = float(os.getenv("AGENT_TEMPERATURE", "0.7"))
    AGENT_MAX_TOKENS: int = _int_env("AGENT_MAX_TOKENS", "2048")

    # Langfuse observability
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    # Voice (STT/TTS)
    # TTS_BACKEND: "kokoro" (local, default) | "openai" (LiteLLM/OpenAI TTS-1)
    TTS_BACKEND: str = os.getenv("TTS_BACKEND", "kokoro")
    TTS_MODEL: str = os.getenv("TTS_MODEL", "openai/tts-1")
    TTS_VOICE: str = os.getenv("TTS_VOICE", "nova")
    TTS_FORMAT: str = os.getenv("TTS_FORMAT", "mp3")
    # Kokoro TTS (used when TTS_BACKEND=kokoro)
    KOKORO_MODEL_PATH: str = os.getenv("KOKORO_MODEL_PATH", "/models/kokoro-v1.0.onnx")
    KOKORO_VOICES_PATH: str = os.getenv("KOKORO_VOICES_PATH", "/models/voices-v1.0.bin")
    KOKORO_VOICE: str = os.getenv("KOKORO_VOICE", "ef_dora")
    KOKORO_LANG: str = os.getenv("KOKORO_LANG", "es")
    STT_MODEL: str = os.getenv("STT_MODEL", "whisper-1")
    STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "es")

    # Recall.ai — Google Meet / Zoom bot integration
    RECALL_API_KEY: str = os.getenv("RECALL_API_KEY", "")
    RECALL_API_BASE_URL: str = os.getenv("RECALL_API_BASE_URL", "https://us-east-1.recall.ai")
    # Public URL of this server (required for Recall.ai webhooks and output-media page)
    # For local dev: use ngrok, e.g. https://abc123.ngrok.io
    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8002")
    # URL to share as screenshare when the bot joins a meeting.
    # Can be any public URL (e.g. https://www.google.com for PoC, or the Portal Partners mockup).
    # Leave empty to disable screenshare.
    SCREENSHARE_DEFAULT_URL: str = os.getenv("SCREENSHARE_DEFAULT_URL", "https://www.google.com")
    # Internal base URL of the frontend service (used by the agent to send presentation commands).
    # In Docker: http://frontend:3000 (internal network, bypasses Cloudflare).
    # In local dev: http://localhost:3000
    FRONTEND_BASE_URL: str = os.getenv("FRONTEND_BASE_URL", "http://frontend:3000")
