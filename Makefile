-include .env

.PHONY: help setup up down logs dev-api dev-web check test sample

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

sample: ## Create a made-up bill in samples/output
	python3 samples/generate_sample_bill.py
