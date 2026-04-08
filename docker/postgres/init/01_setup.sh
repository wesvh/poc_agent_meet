#!/usr/bin/env bash
set -euo pipefail

echo "[postgres-init] Creating users and databases..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'airflow') THEN
            CREATE USER airflow WITH PASSWORD '${AIRFLOW_DB_PASSWORD}';
        END IF;
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app') THEN
            CREATE USER app WITH PASSWORD '${APP_DB_PASSWORD}';
        END IF;
    END
    \$\$;

    SELECT 'CREATE DATABASE airflow OWNER airflow'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow')\gexec

    SELECT 'CREATE DATABASE rappi_handoff OWNER app'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'rappi_handoff')\gexec
EOSQL

echo "[postgres-init] Applying schema to rappi_handoff..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "rappi_handoff" \
    -f /docker-entrypoint-initdb.d/02_schema.sql

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "rappi_handoff" <<-EOSQL
    GRANT ALL ON SCHEMA public TO app;
    GRANT ALL ON ALL TABLES IN SCHEMA public TO app;
    GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO app;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO app;
EOSQL

echo "[postgres-init] Done."
