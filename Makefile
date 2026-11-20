# Common development tasks. Run `make help` for a list.

SHELL := /bin/bash
BACKEND := uv run --directory backend
FRONTEND := npm --prefix frontend

.DEFAULT_GOAL := help
.PHONY: help setup up down deps migrate dev-api dev-worker dev-web \
        lint typecheck fmt test-unit test-int test e2e \
        resolve-filings download ingest-filings check-llm \
        eval-index eval-verify eval-xbrl eval-retrieval eval-ablations eval-generate \
        eval-report eval-human eval-agreement eval-tune-index eval-tune eval-final-retrieval \
        models loadtest bench-pdfs bench-ingest demo-gif

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

e2e: deps ## Playwright end-to-end tests (fake LLM, fresh docqa_e2e database)
	$(FRONTEND) run e2e

resolve-filings: ## Look up the latest 10-Ks on EDGAR and rewrite data/filings.lock.json
	$(BACKEND) docqa download-edgar --resolve

download: ## Download exactly the locked 10-K filings into data/raw and verify SHA-256s
	$(BACKEND) docqa download-edgar

ingest-filings: deps ## Parse, chunk, embed and index the downloaded 10-Ks into the shared library
	$(BACKEND) docqa ingest-filings

models: ## Download the embedding and reranker models into FASTEMBED_CACHE_DIR
	$(BACKEND) docqa download-models

check-llm: ## Send one tiny request to the answer and judge models; print their rate limits
	$(BACKEND) docqa check-llm

# --- Evaluation (only eval-generate calls an LLM; see evals/configs/) ---

eval-index: deps ## Build the chunk variants used by the ablations into the filings library
	$(BACKEND) docqa eval index

eval-verify: deps ## Check every source quote exists in its filing and maps to gold chunks
	$(BACKEND) docqa eval verify

eval-xbrl: ## Cross-check numeric gold answers against SEC XBRL companyfacts
	$(BACKEND) docqa eval xbrl

eval-retrieval: deps ## Recall@5/10 and MRR for the default retrieval config (no LLM)
	$(BACKEND) docqa eval retrieval

eval-ablations: deps ## Retrieval ablations: chunk size, table-aware, search mode, rerank (no LLM)
	$(BACKEND) docqa eval ablations

eval-tune-index: deps ## Build the chunk variants used by the retrieval tuning plan
	$(BACKEND) docqa eval index --plan-file ../evals/configs/tuning.yaml

eval-tune: deps ## Retrieval tuning on the dev set only (evals/configs/tuning.yaml; no LLM)
	$(BACKEND) docqa eval ablations --plan-file ../evals/configs/tuning.yaml

eval-final-retrieval: deps ## Recall@5/10 and MRR on qa_v1 for the final config (no LLM)
	$(BACKEND) docqa eval retrieval --config-file ../evals/configs/final.yaml

eval-generate: deps ## Generation eval with the answer + judge models; resumable, stops at the daily budget
	$(BACKEND) docqa eval generate

eval-report: ## Re-score the generation checkpoint into a report (no LLM calls)
	$(BACKEND) docqa eval generate --report-only

eval-human: ## Export 20 judged answers for a manual check of the judge
	$(BACKEND) docqa eval human-export

eval-agreement: ## Judge-human agreement (and Cohen's kappa) from the marked human-check file
	$(BACKEND) docqa eval agreement

# --- Benchmarks (fake LLM only; results land in benchmarks/results.md) ---

loadtest: deps ## Locust at 1/5/10/25 users against a copy of the filings library (fake LLM)
	$(BACKEND) --group bench python ../benchmarks/loadtest.py

bench-pdfs: ## Print four locked 10-Ks to PDF (data/bench/pdfs) for the ingestion benchmark
	node benchmarks/make_pdf_set.mjs

bench-ingest: deps ## Ingestion pages/minute for the 10-K filings and the PDF set, concurrency 1 and 2
	$(BACKEND) python ../benchmarks/ingest_throughput.py

# --- Docs ---

demo-gif: deps ## Record docs/demo.gif (scripted browser session over the filings library)
	$(BACKEND) python ../docs/record_demo.py
