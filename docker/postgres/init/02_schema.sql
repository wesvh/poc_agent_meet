-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ETL run tracking
CREATE TABLE IF NOT EXISTS etl_runs (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_file_name TEXT       NOT NULL,
    source_file_hash TEXT       NOT NULL,
    s3_raw_key      TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running', 'success', 'failed')),
    rows_raw        INT         NOT NULL DEFAULT 0,
    rows_valid      INT         NOT NULL DEFAULT 0,
    rows_invalid    INT         NOT NULL DEFAULT 0,
    rows_upserted   INT         NOT NULL DEFAULT 0
);

-- ETL error log
CREATE TABLE IF NOT EXISTS etl_errors (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    etl_run_id      UUID        REFERENCES etl_runs(id) ON DELETE CASCADE,
    source_row_number INT,
    store_id        TEXT,
    field_name      TEXT,
    raw_value       TEXT,
    error_message   TEXT        NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_etl_errors_run ON etl_errors(etl_run_id);
CREATE INDEX IF NOT EXISTS idx_etl_runs_hash ON etl_runs(source_file_hash);
CREATE INDEX IF NOT EXISTS idx_etl_runs_status ON etl_runs(status);

-- Raw staging (append-only)
CREATE TABLE IF NOT EXISTS stg_stores_raw (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    etl_run_id          UUID        REFERENCES etl_runs(id) ON DELETE CASCADE,
    source_file_name    TEXT        NOT NULL,
    source_row_number   INT         NOT NULL,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_data            JSONB       NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_stg_stores_raw_run ON stg_stores_raw(etl_run_id);

-- Curated stores
CREATE TABLE IF NOT EXISTS stores (
    store_id                    TEXT        PRIMARY KEY,
    store_name                  TEXT        NOT NULL,
    owner_name                  TEXT        NOT NULL,
    phone                       TEXT,
    email                       TEXT,
    city                        TEXT,
    address                     TEXT,
    address_pin_lat             NUMERIC(9,6),
    address_pin_lng             NUMERIC(9,6),
    category                    TEXT,
    years_operating             NUMERIC(5,2),
    monthly_orders_avg          INT,
    average_ticket_usd          NUMERIC(10,2),
    schedule_open               TIME,
    schedule_close              TIME,
    menu_items_count            INT,
    has_rappialiados_access     BOOLEAN     NOT NULL DEFAULT FALSE,
    has_portal_partners_access  BOOLEAN     NOT NULL DEFAULT FALSE,
    onboarding_status           TEXT
                                CHECK (onboarding_status IN ('pendiente', 'en_proceso', 'completado')),
    support_channel             TEXT
                                CHECK (support_channel IN ('whatsapp', 'email')),
    commission_rate_pct         NUMERIC(5,2),
    notes                       TEXT,
    is_ready_for_handoff        BOOLEAN     NOT NULL DEFAULT FALSE,
    data_quality_status         TEXT        NOT NULL DEFAULT 'valid'
                                CHECK (data_quality_status IN ('valid', 'invalid', 'warning')),
    validation_errors           JSONB       NOT NULL DEFAULT '[]'::jsonb,
    source_file_name            TEXT,
    source_row_number           INT,
    ingested_at                 TIMESTAMPTZ,
    normalized_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_stores_onboarding ON stores(onboarding_status);
CREATE INDEX IF NOT EXISTS idx_stores_city ON stores(city);
CREATE INDEX IF NOT EXISTS idx_stores_handoff ON stores(is_ready_for_handoff) WHERE is_ready_for_handoff = TRUE;
CREATE INDEX IF NOT EXISTS idx_stores_quality ON stores(data_quality_status);

-- Payment methods (child table)
CREATE TABLE IF NOT EXISTS store_payment_methods (
    id          UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id    TEXT    NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
    method      TEXT    NOT NULL
                CHECK (method IN ('efectivo','tarjeta','nequi','daviplata','pse')),
    UNIQUE (store_id, method)
);

-- Schedule days (child table)
CREATE TABLE IF NOT EXISTS store_schedule_days (
    id          UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id    TEXT    NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
    day         TEXT    NOT NULL
                CHECK (day IN ('lunes','martes','miercoles','jueves','viernes','sabado','domingo')),
    UNIQUE (store_id, day)
);

-- Meetings
CREATE TABLE IF NOT EXISTS meetings (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id        TEXT        NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
    scheduled_at    TIMESTAMPTZ,
    meeting_link    TEXT,
    status          TEXT        NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'completed', 'cancelled')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE NULLS NOT DISTINCT (store_id, scheduled_at, meeting_link)
);

CREATE INDEX IF NOT EXISTS idx_meetings_store ON meetings(store_id);
CREATE INDEX IF NOT EXISTS idx_meetings_scheduled ON meetings(scheduled_at) WHERE status = 'pending';

-- Handoff sessions (agent conversations)
CREATE TABLE IF NOT EXISTS handoff_sessions (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id            TEXT        NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
    meeting_id          UUID        REFERENCES meetings(id) ON DELETE SET NULL,
    status              TEXT        NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'completed', 'abandoned')),
    blocks_completed    JSONB       NOT NULL DEFAULT '{}'::jsonb,
    collected_data      JSONB       NOT NULL DEFAULT '{}'::jsonb,
    issues_detected     JSONB       NOT NULL DEFAULT '[]'::jsonb,
    commitments         JSONB       NOT NULL DEFAULT '[]'::jsonb,
    transcript          JSONB,
    summary             TEXT,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at            TIMESTAMPTZ,
    turn_count          INT         NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_store ON handoff_sessions(store_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON handoff_sessions(status);
