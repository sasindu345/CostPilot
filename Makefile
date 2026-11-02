-include .env

.PHONY: help setup up down logs dev-api dev-web migrate e2e types reindex eval-search eval-assistant check test sample

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

eval-assistant: ## Score the assistant with real Gemini, and save the baseline
	cd apps/api && uv run pytest tests/integration/test_row_level_security.py
	cd apps/api && POSTGRES_DB=costpilot_test uv run python scripts/eval_assistant.py

types: ## Update the frontend's API types from the backend
	cd apps/api && uv run python scripts/export_openapi.py ../web/openapi.json
	cd apps/web && pnpm exec openapi-typescript openapi.json --output src/lib/api-types.ts
	rm apps/web/openapi.json

e2e: ## Test the full user journey in a real browser
	cd apps/web && E2E_BASE_URL=$(APP_PUBLIC_URL) E2E_API_URL=http://localhost:$(API_PORT) MAILPIT_URL=http://localhost:$(MAILPIT_UI_PORT) E2E_BROWSER_CHANNEL=chrome pnpm e2e

sample: ## Create a made-up bill in samples/output
	python3 samples/generate_sample_bill.py
