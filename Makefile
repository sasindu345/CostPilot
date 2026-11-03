-include .env

STANDARD_EVAL = ../../knowledge/assistant-questions.yaml src/costpilot/modules/documents/infrastructure/sample-aws-bill.csv ../../knowledge/assistant-baseline.json
KNOWLEDGE_EVAL = ../../knowledge/assistant-knowledge-questions.yaml tests/fixtures/billing/eval-bill.csv
HARD_EVAL = ../../knowledge/assistant-hard-questions.yaml tests/fixtures/billing/eval-bill.csv

.PHONY: help setup up down logs dev-api dev-web migrate e2e types reindex eval-search eval-assistant eval-agents eval-knowledge check test sample backup-check infra-check monitoring eval-quality load-test screenshots

help: ## Show this list
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

setup: ## Install everything and create your .env
	./scripts/setup.sh

up: ## Start all services in Docker
	docker compose up --build --detach --wait

down: ## Stop all services
	docker compose down

logs: ## Follow the logs of all services
	docker compose logs --follow

dev-api: ## Run the API with live reload
	cd apps/api && uv run uvicorn costpilot.main:app --reload --port $(API_PORT)

migrate: ## Update the database to the latest version
	cd apps/api && uv run alembic upgrade head

dev-web: ## Run the web app with live reload
	cd apps/web && API_INTERNAL_URL=http://localhost:$(API_PORT) pnpm dev

check: ## Run all tests, style checks and rule checks
	python3 scripts/check_no_hardcoded.py
	cd apps/api && uv run ruff check . && uv run ruff format --check .
	cd apps/api && uv run lint-imports
	cd apps/api && uv run bandit --quiet --recursive src --configfile pyproject.toml
	cd apps/api && uv run pytest
	cd apps/web && pnpm lint && pnpm typecheck && pnpm test

test: ## Run tests only
	cd apps/api && uv run pytest
	cd apps/web && pnpm test

reindex: ## Rebuild the documentation search. Safe to run again
	cd apps/api && uv run python scripts/reindex.py

eval-search: ## Measure how well documentation search works
	cd apps/api && uv run python scripts/eval_search.py

eval-assistant: ## Score the assistant on the standard questions with real Gemini
	cd apps/api && uv run pytest tests/integration/test_row_level_security.py
	cd apps/api && POSTGRES_DB=costpilot_test uv run python scripts/eval_assistant.py $(STANDARD_EVAL)

eval-quality: ## Grade answers against reference answers, with a second Gemini model as judge
	cd apps/api && uv run pytest tests/integration/test_row_level_security.py
	cd apps/api && POSTGRES_DB=costpilot_test uv run python scripts/eval_quality.py ../../knowledge/quality-cases.yaml src/costpilot/modules/documents/infrastructure/sample-aws-bill.csv ../../knowledge/eval-quality.json

eval-agents: ## Compare the hard questions with and without AI specialists
	cd apps/api && uv run pytest tests/integration/test_row_level_security.py
	cd apps/api && POSTGRES_DB=costpilot_test ASSISTANT_AI_SPECIALISTS='[]' uv run python scripts/eval_assistant.py $(HARD_EVAL) ../../knowledge/eval-without-agents.json
	cd apps/api && POSTGRES_DB=costpilot_test uv run python scripts/eval_assistant.py $(HARD_EVAL) ../../knowledge/eval-with-agents.json

eval-knowledge: ## Compare documentation questions with and without the Knowledge Agent
	cd apps/api && uv run pytest tests/integration/test_row_level_security.py
	cd apps/api && POSTGRES_DB=costpilot_test ASSISTANT_AI_SPECIALISTS='["anomaly","optimization"]' uv run python scripts/eval_assistant.py $(KNOWLEDGE_EVAL) ../../knowledge/eval-knowledge-off.json
	cd apps/api && POSTGRES_DB=costpilot_test ASSISTANT_AI_SPECIALISTS='["anomaly","optimization","knowledge"]' uv run python scripts/eval_assistant.py $(KNOWLEDGE_EVAL) ../../knowledge/eval-knowledge-on.json

types: ## Update the frontend's API types from the backend
	cd apps/api && uv run python scripts/export_openapi.py ../web/openapi.json
	cd apps/web && pnpm exec openapi-typescript openapi.json --output src/lib/api-types.ts
	rm apps/web/openapi.json

e2e: ## Test the full user journey in a real browser
	cd apps/web && E2E_BASE_URL=$(APP_PUBLIC_URL) E2E_API_URL=http://localhost:$(API_PORT) MAILPIT_URL=http://localhost:$(MAILPIT_UI_PORT) E2E_BROWSER_CHANNEL=chrome pnpm e2e

sample: ## Create a made-up bill in samples/output
	python3 samples/generate_sample_bill.py

backup-check: ## Back up the local databases, restore them into copies, and compare every table
	@dir=$$(mktemp -d); ./infra/production/backup.sh "$$dir" && ./infra/production/restore.sh check "$$dir"/*; status=$$?; rm -rf "$$dir"; exit $$status

infra-check: ## Check the Terraform files and server scripts
	terraform -chdir=infra/terraform fmt -check
	terraform -chdir=infra/terraform init -backend=false -input=false > /dev/null
	terraform -chdir=infra/terraform validate
	terraform -chdir=infra/terraform test
	docker run --rm -v "$$PWD:/mnt" -w /mnt koalaman/shellcheck:v0.11.0 infra/production/*.sh infra/postgres/*.sh

monitoring: ## Start everything with traces and metrics, and Grafana on GRAFANA_PORT
	OTEL_EXPORTER_OTLP_ENDPOINT=http://monitoring:4318 docker compose --profile monitoring up --build --detach --wait
	@echo "Grafana: http://localhost:$(GRAFANA_PORT)  (dashboard: CostPilot)"

load-test: ## Many users open the dashboards at once. Needs `make up`. Uses no AI
	@cookie=$$(cd apps/api && uv run python scripts/load_test_session.py "$(KEYCLOAK_ADMIN_USER)" "$(KEYCLOAK_ADMIN_PASSWORD)") && \
	sleep 5 && \
	docker run --rm --network costpilot_default -v "$$PWD/infra/load-test:/scripts:ro" \
		-e API_URL=http://api:8000 -e COOKIE_NAME=$(SESSION_COOKIE_NAME) -e SESSION_COOKIE="$$cookie" \
		-e PEAK_USERS=$(or $(PEAK_USERS),25) \
		grafana/k6:2.3.0 run --quiet /scripts/dashboard.js

screenshots: ## Save README screenshots of the running app to docs/images. Uses made-up data
	@cookie=$$(cd apps/api && uv run python scripts/load_test_session.py "$(KEYCLOAK_ADMIN_USER)" "$(KEYCLOAK_ADMIN_PASSWORD)") && \
	sleep 5 && \
	cd apps/web && node scripts/screenshots.mjs "$(APP_PUBLIC_URL)" "$(SESSION_COOKIE_NAME)" "$$cookie" ../../docs/images \
		"http://localhost:$(GRAFANA_PORT)/d/costpilot/costpilot?orgId=1&kiosk&from=now-30m&to=now"
