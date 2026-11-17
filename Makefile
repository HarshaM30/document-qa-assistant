# Common development tasks. Run `make help` for a list.

SHELL := /bin/bash
BACKEND := uv run --directory backend
FRONTEND := npm --prefix frontend

.DEFAULT_GOAL := help
.PHONY: help setup up down deps migrate dev-api dev-worker dev-web \
        lint typecheck fmt test-unit test-int test e2e \
        resolve-filings download ingest-filings check-llm

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: ## Install backend and frontend dependencies; create .env from the example if missing
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example - edit it before continuing.")
	cd backend && uv sync
	$(FRONTEND) ci

up: ## Build and start the full stack (Postgres, Redis, API, worker, frontend)
	docker compose up -d --build --wait

down: ## Stop the stack (data volumes are kept)
	docker compose down

deps: ## Start only Postgres and Redis (for running the app on the host)
	docker compose up -d --wait db redis

migrate: ## Apply database migrations
	$(BACKEND) alembic upgrade head

dev-api: ## Run the API on the host with auto-reload
	$(BACKEND) uvicorn docqa.main:create_app --factory --reload --port 8000

dev-worker: ## Run the ingestion worker on the host
	$(BACKEND) arq docqa.worker.settings.WorkerSettings

dev-web: ## Run the Vite dev server
	$(FRONTEND) run dev

lint: ## Lint backend (ruff) and frontend (eslint)
	$(BACKEND) ruff check .
	$(BACKEND) ruff format --check .
	$(FRONTEND) run lint

typecheck: ## Type-check backend (mypy) and frontend (tsc)
	$(BACKEND) mypy
	$(FRONTEND) run typecheck

fmt: ## Auto-format and auto-fix backend code
	$(BACKEND) ruff format .
	$(BACKEND) ruff check --fix .

test-unit: ## Backend unit tests (no services needed)
	$(BACKEND) pytest tests/unit

test-int: deps ## Backend integration tests (starts Postgres and Redis if needed)
	$(BACKEND) pytest tests/integration

test: test-unit test-int ## All backend tests

e2e: ## Playwright end-to-end tests (added in Milestone 4)
	@echo "E2E tests arrive with the UI in Milestone 4." && exit 1

resolve-filings: ## Look up the latest 10-Ks on EDGAR and rewrite data/filings.lock.json
	$(BACKEND) docqa download-edgar --resolve

download: ## Download exactly the locked 10-K filings into data/raw and verify SHA-256s
	$(BACKEND) docqa download-edgar

ingest-filings: deps ## Parse, chunk, embed and index the downloaded 10-Ks into the shared library
	$(BACKEND) docqa ingest-filings

check-llm: ## Send one tiny request to the answer and judge models; print their rate limits
	$(BACKEND) docqa check-llm
