.PHONY: check-env check-db venv install-local build init up up-full down logs restart trigger-etl etl-status reset-localstack reset-all

check-env:
	@test -f .env || (echo "Missing .env. Create env and add LOCALSTACK_AUTH_TOKEN." && exit 1)
	@grep -q "^LOCALSTACK_AUTH_TOKEN=" .env || (echo "Missing LOCALSTACK_AUTH_TOKEN in .env." && exit 1)
	@if grep -q "^LOCALSTACK_AUTH_TOKEN=$$" .env; then echo "LOCALSTACK_AUTH_TOKEN is empty in .env."; exit 1; fi
	@if grep -q "^LOCALSTACK_AUTH_TOKEN=your_localstack_token$$" .env; then echo "Replace LOCALSTACK_AUTH_TOKEN placeholder in .env with your real token."; exit 1; fi

check-db:
	@docker exec handoff-postgres psql -U postgres -d postgres -c "SELECT datname FROM pg_database ORDER BY datname;"
	@echo "Canonical app database: rappi_handoff"
	@docker exec handoff-postgres psql -U postgres -d rappi_handoff -c "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema') ORDER BY table_schema, table_name;"

venv:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip

install-local: venv
	.venv/bin/python -m pip install -r requirements.txt -r requirements-ingest.txt

up: check-env
	docker compose up -d

build: check-env
	docker build -t rappi-airflow:latest -f docker/airflow/Dockerfile .
	docker compose build infra-init ingest

init: check-env
	docker compose run --rm airflow-init
	docker compose run --rm infra-init

up-full: check-env build
	docker compose up -d
	$(MAKE) init

reset-localstack:
	docker compose down
	docker volume rm rappi_localstack_data || true

reset-all:
	docker compose down -v

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose restart

trigger-etl:
	@echo "Uploading data/aliados_dataset.csv to ingest service..."
	curl -s -X POST http://localhost:8001/upload \
		-F "file=@data/aliados_dataset.csv" | python3 -m json.tool

etl-status:
	@curl -s "http://localhost:8080/api/v1/dags/etl_stores_csv/dagRuns" \
		-u airflow:airflow \
		| python3 -c "import sys,json; runs=json.load(sys.stdin).get('dag_runs',[]); [print(r['run_id'], r['state']) for r in runs[-5:]]"
