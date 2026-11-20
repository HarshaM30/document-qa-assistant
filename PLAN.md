# Document Q&A Assistant — Implementation Plan

A full-stack RAG app for asking plain-English questions about SEC 10-K filings and
user-uploaded PDFs, with streamed, cited answers, principled refusals, and measured
retrieval and answer quality.

Local-only, memory-conscious, no paid services. Host ports: Postgres **5434**, Redis **6380**.

---

## 1. Folder structure

```
document-qa-assistant/
├── backend/
│   ├── pyproject.toml            # uv project; dependency groups: dev, bench (Locust)
│   ├── uv.lock
│   ├── Dockerfile                # API and worker share one image
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── src/docqa/
│   │   ├── main.py               # FastAPI app factory, middleware, routers
│   │   ├── config.py             # pydantic-settings, reads .env
│   │   ├── cli.py                # Typer CLI: download-edgar, ingest-filings, download-models, reset-db, check-llm, `eval …`
│   │   ├── log_config.py         # JSON (or key=value) log lines carrying the request/job ID
│   │   ├── middleware.py         # request IDs, access log, body-size limits, last-resort 500
│   │   ├── errors.py             # one error shape: {detail, code, request_id[, errors]}
│   │   ├── model_files.py        # startup check that the ONNX model files are downloaded
│   │   ├── db/
│   │   │   ├── session.py        # async engine + session dependency
│   │   │   ├── admin.py          # drop + recreate a throwaway database (E2E)
│   │   │   └── models.py         # User, Session, Workspace, Document, Section, Chunk, IngestionJob, Question, Answer
│   │   ├── auth/
│   │   │   ├── passwords.py      # argon2id hashing
│   │   │   ├── sessions.py       # opaque session tokens (hashed at rest), cookie helpers
│   │   │   ├── deps.py           # current_user dependency, CSRF check
│   │   │   └── router.py         # /auth/signup, /auth/login, /auth/logout, /auth/me
│   │   ├── api/
│   │   │   ├── health.py         # /health (db + redis; model files reported)
│   │   │   ├── workspaces.py
│   │   │   ├── documents.py      # upload, list, status, delete, passage lookup
│   │   │   └── chat.py           # POST /workspaces/{id}/ask → SSE stream; GET …/questions (history)
│   │   ├── schemas/              # Pydantic v2 request/response models
│   │   ├── ingestion/
│   │   │   ├── edgar.py          # EDGAR client: user agent, rate limiter, retries
│   │   │   ├── html_blocks.py    # (inline-XBRL) HTML → ordered text/table blocks with page numbers
│   │   │   ├── html_10k.py       # blocks → Items (sections); handles incorporated-by-reference Items
│   │   │   ├── tables.py         # table → labelled text ("Row | Column: value")
│   │   │   ├── pdf.py            # pdfplumber: PDF → pages (+ tables where detectable)
│   │   │   ├── chunking.py       # section/table-aware and naive chunkers
│   │   │   ├── embedding.py      # fastembed wrapper (lazy-loaded, batched)
│   │   │   ├── parsed.py         # parser output types shared by HTML and PDF
│   │   │   ├── library.py        # ingest the locked filings into the shared library
│   │   │   └── pipeline.py       # parse → chunk → embed → store, with progress
│   │   ├── retrieval/
│   │   │   ├── scope.py          # tenancy: chunks visible to a workspace (uploads + attached library)
│   │   │   ├── vector.py         # pgvector cosine search (HNSW)
│   │   │   ├── keyword.py        # Postgres FTS (tsvector + websearch_to_tsquery, terms OR-ed)
│   │   │   ├── fusion.py         # reciprocal rank fusion
│   │   │   ├── rerank.py         # fastembed cross-encoder
│   │   │   ├── query_filters.py  # companies/fiscal years in the question → filings; decomposition
│   │   │   └── retriever.py      # configurable pipeline (used by API and evals)
│   │   ├── generation/
│   │   │   ├── llm.py            # LiteLLM factory from env (provider + model)
│   │   │   ├── fake_provider.py  # deterministic extractive provider for tests/CI
│   │   │   ├── prompts.py
│   │   │   ├── chain.py          # LangChain LCEL chain: retrieve → prompt → stream
│   │   │   ├── citations.py      # parse [n] markers → chunk/section/page refs
│   │   │   └── refusal.py        # pre-generation gate + refusal detection
│   │   ├── ratelimit.py          # Redis sliding-window limiter
│   │   ├── storage.py            # upload file storage (local disk), size + magic-byte checks
│   │   ├── worker/
│   │   │   ├── settings.py       # arq WorkerSettings
│   │   │   └── tasks.py          # ingest_document task with retry/backoff
│   │   └── evals/                # eval code (data lives in /evals)
│   │       ├── cli.py            # `docqa eval index|verify|xbrl|retrieval|ablations|generate|human-export|agreement`
│   │       ├── configs.py        # loads evals/configs/*.yaml; stable config hashes
│   │       ├── dataset.py        # schema + loader + quote verification + gold-chunk matching
│   │       ├── retrieval_eval.py # recall@k, MRR; eval-only workspace with the library attached
│   │       ├── ablations.py
│   │       ├── generation_eval.py # answer → judge, JSONL checkpoint, scoring
│   │       ├── judge.py
│   │       ├── client.py         # non-streamed LLM calls through per-model budgets, 429 retries
│   │       ├── xbrl_check.py     # cross-check numeric gold answers vs SEC companyfacts
│   │       ├── budget.py         # daily request/token budgets (ledger per UTC day) + tokens/minute
│   │       ├── human_check.py    # export + agreement report
│   │       └── reports.py        # timestamped markdown + JSON reports
│   └── tests/
│       ├── unit/
│       ├── integration/          # real Postgres + Redis, fake LLM
│       └── fixtures/             # tiny 10-K HTML excerpt, tiny PDF
├── frontend/
│   ├── package.json
│   ├── vite.config.ts            # includes the Tailwind v4 plugin (no tailwind.config.ts)
│   ├── tsconfig.json
│   ├── eslint.config.js
│   ├── Dockerfile
│   ├── src/
│   │   ├── main.tsx, App.tsx, router.tsx
│   │   ├── api/                  # typed fetch client + TanStack Query hooks
│   │   ├── lib/sse.ts            # POST-based SSE stream reader
│   │   ├── pages/                # Login, Signup, Workspaces, Documents, Chat
│   │   └── components/           # UploadDropzone, IngestionStatus, ChatMessage, CitationPanel, ...
│   └── e2e/
│       ├── playwright.config.ts  # starts API + worker (fresh docqa_e2e DB) and the built frontend
│       ├── start-backend.sh      # reset DB, run worker + API for the tests
│       ├── happy-path.spec.ts    # sign up → upload → ask → open citation; auth; stream errors; rate limit
│       ├── demo.config.ts        # video recording config for the README demo (not part of `make e2e`)
│       └── demo.record.ts        # scripted demo session: attach library → ask → citation → refusal
├── evals/
│   ├── datasets/
│   │   ├── qa_v1.jsonl           # 50 questions with gold answers + source quotes (held-out test set)
│   │   ├── dev_v1.jsonl          # 25 tuning questions (Milestone 5b); the only set tuning may use
│   │   └── CHANGELOG.md          # dataset versioning notes
│   ├── configs/                  # ablations.yaml, tuning.yaml (dev set only), final.yaml
│   ├── checkpoints/              # generation-eval JSONL checkpoints (committed, so runs resume anywhere)
│   ├── human_check/              # exported markdown for manual agree/disagree
│   ├── reports/                  # timestamped reports (committed)
│   └── .budget/                  # gitignored: today's LLM usage per model
├── benchmarks/
│   ├── locustfile.py             # login, list documents, ask (full SSE stream)
│   ├── loadtest.py               # `make loadtest`: clone the library DB, start API + worker, run Locust per user count
│   ├── ingest_throughput.py      # `make bench-ingest`: pages/min at worker concurrency 1 and 2
│   ├── make_pdf_set.mjs          # `make bench-pdfs`: print four 10-Ks to PDF with Playwright's Chromium
│   ├── report.py                 # machine specs; rewrites its own section of results.md
│   └── results.md
├── data/
│   ├── companies.yaml            # tickers + CIKs (5 companies)
│   ├── filings.lock.json         # resolved accession numbers + SHA-256s (committed)
│   └── raw/                      # gitignored; reproduced by download script
├── docs/
│   ├── demo.gif
│   └── record_demo.py            # `make demo-gif`: clone the library DB, real answer model, Playwright video → ffmpeg GIF
├── .github/workflows/ci.yml       # lint, typecheck, unit, integration, build, e2e jobs
├── docker-compose.yml
├── Makefile
├── .env.example
├── .gitignore
├── .gitleaksignore               # reviewed false positives for `gitleaks git .`
├── PLAN.md
└── README.md
```

---

## 2. Key design decisions

| Area | Decision | Why |
|---|---|---|
| Sessions | Opaque random token in an `HttpOnly`, `SameSite=Lax` cookie; HMAC-SHA256 of the token (keyed by `SESSION_SECRET_KEY`) stored in Postgres `sessions` table | Revocable logout, no JWT pitfalls, nothing sensitive client-side; a leaked table can't be replayed, and rotating the key revokes every session |
| Passwords | argon2id (`argon2-cffi`) | Current OWASP recommendation |
| CSRF | SameSite=Lax + require `X-Requested-With` header on state-changing requests + strict CORS origin | Simple and sufficient for a same-site SPA |
| Tenancy | Every document/chunk query is scoped by `workspace_id`, and workspace ownership is checked against the session user | Users only ever see their own data; enforced in one retrieval function and tested |
| Embeddings | `BAAI/bge-small-en-v1.5` (384-d) via fastembed | Small, fast on CPU, good retrieval quality |
| Reranker | `Xenova/ms-marco-MiniLM-L-6-v2` via fastembed `TextCrossEncoder`, batch size 4 | ONNX, no PyTorch, ~90 MB. Batches of 16 push the API past 1 GB at peak; batches of 4 peak around 720 MB with the embedder loaded, at the same speed (~0.7 s for 30 passages) |
| Vector index | pgvector HNSW, cosine | Good recall/latency without tuning lists |
| Keyword search | Generated `tsvector` column + GIN index, `websearch_to_tsquery` over the question's terms joined with `or`, ranked by `ts_rank_cd` | Native, no extra service; plain `websearch_to_tsquery` ANDs every word, so a natural-language question rarely matches anything |
| Fusion | RRF with k=60 over top-30 vector + top-30 keyword; the top 30 fused results go to the reranker | Standard, parameter-light. Pools of 20, 50 and 100 were all worse on the dev set (Milestone 5b) |
| Metadata filter | Companies (registered names + aliases such as AWS, J&J) and fiscal years named in the question restrict retrieval to the matching library filings; a year without its own 10-K maps to the earliest later filing that reports it, a year no filing covers is ignored. Uploaded documents are never filtered out. Questions naming several companies run one retrieval per company, interleaved round-robin | Chosen on the dev set in Milestone 5b (recall@10 47.5% → 87.5%). Splitting per fiscal year as well hurt year-over-year questions, because one 10-K already reports both years |
| Tables | Each table emitted as its own chunk, rendered as `Row label \| Column header: value` lines with the table caption and section prepended | Keeps numbers attached to their meaning; never split mid-row |
| Citations | Prompt numbers context passages `[1]..[n]`; server maps markers to chunk → (document, Item/section or page) and sends a `citations` SSE event. Lenticular/fullwidth brackets (`【3】`, which gpt-oss emits) are rewritten to `[3]` as tokens stream, and gpt-oss's line-referenced form `[3†L9-L10]` counts as passage 3 (found by the generation eval) | Exact, verifiable sources; frontend fetches the passage on click |
| Refusal | Two layers: (1) if retrieval finds nothing, or the best rerank score < `REFUSAL_MIN_RERANK_SCORE` → refuse without calling the LLM (with reranking off, only the empty case applies); (2) prompt instructs a fixed refusal sentence, detected server-side | Saves LLM calls and makes refusal measurable |
| LLM models | Answer: `openai/gpt-oss-120b`; judge: `qwen/qwen3.8-27b` (fallback judge: `openai/gpt-oss-20b`). Both via LiteLLM `groq/` prefix | Must be on Groq's free tier and differ from each other; a judge from a different model family reduces self-preference bias. See section 4 |
| PDF parsing | pdfplumber | MIT license; page-level text and table extraction |
| Filing selection | For each company, the 3 most recent original 10-Ks on EDGAR (10-K/A excluded), resolved once and pinned in `data/filings.lock.json` | "Latest three" changes over time; the lockfile keeps the corpus and eval dataset reproducible |
| Fake LLM | LiteLLM custom provider `fake/…` that returns a deterministic extractive answer from the top passages with `[n]` markers, or the refusal sentence | Streams like a real model; tests and CI need no network or key |
| Worker concurrency | `WORKER_MAX_JOBS=1` (was 2) | Embedding is 95% of ingestion time and is CPU-bound, so a second job adds only 7–25% throughput but doubles peak memory (3.2 GB on the filings, past the worker's limit) |
| Queue | arq on Redis; job state mirrored in an `ingestion_jobs` table (status, stage, progress %, attempts, error) | UI polls Postgres state; retries with exponential backoff |
| Rate limit | Redis sliding window per user (per-minute and per-day) on `/ask`, checked and recorded atomically in one Lua script; rejected requests don't use quota; returns 429 with `Retry-After` | Protects the free-tier LLM quota |
| Chat history | Every question gets an answer row with a `status`: `complete`, `failed` (error or `ANSWER_TIMEOUT_SECONDS`, with any partial text), or `stopped` (client disconnected, with the partial text). `GET /workspaces/{id}/questions` returns the latest 50 oldest-first, and the chat page loads it on open | A refresh shows exactly what the user saw, including cut-off answers |
| Logging and errors | JSON log lines (`LOG_FORMAT=json`) with a request ID per API request (`X-Request-ID`, accepted from the client if well-formed) and per ingestion job; one access line per request. Every error body is `{detail, code, request_id}`; validation errors add `errors` and never echo the input | Lines from one request can be grepped together; clients get a stable `code` and a readable `detail` |
| Model concurrency | At most `MODEL_MAX_CONCURRENCY` (2) embed/rerank calls run at once in the API; a cancelled request's thread keeps its slot until it ends. argon2 runs in a thread, at most 4 at once | ONNX grows a memory arena per concurrent run: unbounded, the 10-user load test peaked at 1.8 GB with a worse p95 than capped. Cap 2 peaks at 1.57 GB over the full load test (API Compose limit 1792 MB); cap 1 at 1.24 GB but doubles the 10-user answer p50. A request waiting for a slot releases its DB connection first (otherwise plain reads queued behind reranks: 1.3 s p50 at 25 users, now 9 ms). argon2 on the event loop stalled every stream during a login |
| Ablation indexes | `chunks` table carries an `index_config` key (e.g. `section-512-64`, `naive-512-64`); `docqa eval index` adds ablation variants to the library filings under their own keys (the API only reads the default key), and evals query them through an eval-only workspace with the library attached | No schema churn per experiment; embedding dim stays fixed; each filing is parsed once for all variants |

---

## 3. Milestones

### Milestone 1 — Scaffold

**Tasks**
1. `backend/`: `uv init`, Python 3.12, deps (FastAPI, uvicorn, SQLAlchemy 2 async + asyncpg, Alembic, Pydantic v2, pydantic-settings, argon2-cffi, redis, arq). Dev group: pytest, pytest-asyncio, httpx, ruff, mypy.
2. `config.py` with typed settings for every variable in `.env.example`.
3. `docker-compose.yml`: `pgvector/pgvector:pg16` on host 5434, `redis:7-alpine` on host 6380, `api`, `worker`, `frontend` services; healthchecks; named volumes; memory limits.
4. SQLAlchemy models for all tables; initial Alembic migration enabling `vector` extension, HNSW and GIN indexes.
5. Auth: signup, login, logout, `/auth/me`; argon2id; session table; cookie settings from env; CSRF header check.
6. Workspaces CRUD scoped to the current user.
7. `/health` reporting DB, Redis, and status.
8. `frontend/`: Vite + React + TS, Tailwind (v4, via `@tailwindcss/vite`), TanStack Query, React Router, ESLint; placeholder pages. TypeScript is pinned to 6.0 because typescript-eslint does not yet support TypeScript 7.
9. `Makefile`: `setup`, `up`, `down`, `deps` (Postgres + Redis only), `migrate`, `dev-api`, `dev-worker`, `dev-web`, `lint`, `typecheck`, `test-unit`, `test-int`, `e2e`, `fmt`.
10. GitHub Actions CI on every push, as separate jobs: ruff + mypy, unit tests, integration tests (pgvector + Redis service containers), frontend `tsc --noEmit` + ESLint + `vite build`. Cache uv, npm, and fastembed models. (The Playwright E2E job is added in Milestone 4, once there is a UI to test.)

**Done when**
- [x] `make setup && make up` brings up Postgres, Redis, API, worker, and frontend; `curl localhost:8000/health` returns all-green.
- [x] `make migrate` applies cleanly to an empty DB and `alembic downgrade base` reverses it.
- [x] Integration tests cover: signup → login → `/auth/me` → logout → `/auth/me` returns 401; duplicate email rejected; wrong password rejected; user A cannot read user B's workspace (404).
- [x] Password hashes are argon2id; session cookie is `HttpOnly`, `SameSite=Lax`, `Secure` when configured.
- [x] `make lint typecheck test-unit test-int` passes locally; CI is green on push.
- [x] No service binds 5432, 5433, or 6379.

### Milestone 2 — Ingestion

**Tasks**
1. `data/companies.yaml`: Apple (AAPL), Microsoft (MSFT), Amazon (AMZN), JPMorgan Chase (JPM), Johnson & Johnson (JNJ), with CIKs.
2. EDGAR downloader (`docqa download-edgar`): `--resolve` reads `data.sec.gov/submissions/CIK##########.json`, picks the 3 most recent original 10-K filings per company (form `10-K`, not `10-K/A`), and writes `data/filings.lock.json` (ticker, fiscal year end, accession number, primary document URL, filing date). Without `--resolve` it downloads exactly what the lockfile lists. Expected as of Nov 2026: Apple and Microsoft FY2024–FY2026 (Sept/June year-ends), Amazon, JPMorgan, and J&J FY2023–FY2025 (calendar year-ends). It downloads each primary 10-K document, sends `SEC_USER_AGENT`, token-bucket limited to `SEC_MAX_REQUESTS_PER_SECOND` (< SEC's 10 req/s), retries on 429/5xx with backoff, skips files already present, writes a manifest with SHA-256s. Refuses to run if `SEC_USER_AGENT` is unset or still the placeholder.
3. 10-K HTML parser: strip inline XBRL wrappers, detect `Item 1`, `1A`, `7`, `7A`, `8`, … headings (skipping the table of contents), produce sections with ordered text blocks and tables. Headings are chosen as the heaviest chain of candidates in canonical Item order, so TOC entries and cross-references lose to real headings; repeated running headers/footers are dropped. Where an Item is only a stub pointing to later pages (JPMorgan's Items 7 and 8), the titled annual-report section is merged into that Item.
4. Table-to-text: resolve header rows (including multi-row/colspan headers), merge split `$`/`%`/parenthesis cells, emit `Row | Column: value` lines; keep caption and units ("in millions").
5. PDF parser using pdfplumber, producing per-page text (and tables via `extract_tables`, rendered with the same table-to-text format); pages are the citation unit.
6. Chunkers: section-aware (respects section boundaries, tables as standalone chunks, token-based size + overlap using the embedding model's tokenizer) and a naive fixed-size chunker for ablations.
7. Embedding wrapper: lazy model load, batching, configurable cache dir.
8. Upload endpoint: PDF only, size limit, MIME + magic-byte check, stores file, creates `Document` + `IngestionJob`, enqueues arq job. Also: list, delete, retry a failed upload, and library attach/detach (`POST /workspaces/{id}/library`, `DELETE /workspaces/{id}/library/{doc}`).
9. Worker task: stages `parsing → chunking → embedding → indexing → done`, progress % and per-stage seconds persisted, retries with exponential backoff (`INGEST_RETRY_BASE_DELAY_SECONDS` × 2ⁿ) up to `INGEST_MAX_RETRIES` retries, final failure recorded with a user-readable error. Unreadable files (corrupt, encrypted, image-only PDFs) fail immediately, since retrying can't help.
10. `docqa ingest-filings` (`make ingest-filings`): ingests the downloaded 10-Ks into a shared "SEC filings" library a user can attach to a workspace. Runs in-process (not via the worker); already-ingested filings are skipped unless `--force`.
11. Document status endpoint (polled by UI).

**Done when**
- [x] `filings.lock.json` is committed with 15 entries (3 per company, no amendments), and its fiscal years match the most recent 10-Ks on EDGAR as of resolution date.
- [x] `make download` fetches exactly the 15 locked filings into `data/raw/` and verifies their SHA-256s; re-running downloads nothing new; logs show the user agent and request rate stays under the limit.
- [x] Parser unit tests on a fixture excerpt: correct Item boundaries, TOC entries ignored, a known table rendered with row and column labels and units intact.
- [x] Every one of the 15 filings parses with Items 1, 1A, 7, and 8 detected (asserted by a test over `data/raw` that is skipped when data is absent).
- [x] Uploading a sample PDF produces chunks with correct page numbers; status moves through all stages to `done`.
- [x] A forced failure is retried N times then marked `failed` with an error message visible via the API.
- [x] Non-PDF and oversized uploads are rejected with 4xx.
- [x] Ingestion throughput (pages/min) is logged per job.

### Milestone 3 — Retrieval and generation

**Tasks**
0. **Model check (before anything else in this milestone):** `docqa check-llm` sends one tiny completion to each of `LLM_MODEL` and `JUDGE_MODEL` with your key, prints the actual rate limits from Groq's `x-ratelimit-*` response headers, and fails clearly on `model_not_found`. If the primary judge is unavailable, switch to the fallback judge and update `.env.example` and this plan.
1. Vector search (cosine, HNSW, `ef_search` configurable) and keyword search (FTS), both scoped by workspace.
2. RRF fusion; cross-encoder rerank to top-N; all stages toggleable for ablations.
3. LiteLLM factory from `LLM_PROVIDER`/`LLM_MODEL`; fake provider registered for `fake`. For reasoning models (gpt-oss), set low reasoning effort so hidden reasoning tokens don't use up the per-minute token limit.
4. LangChain chain: retrieve → refusal gate → prompt with numbered passages → stream tokens.
5. `POST /workspaces/{id}/ask` SSE endpoint emitting `token`, `refusal`, `citations`, `done`, and `error` events; persists question, answer, and citations.
6. Citation parsing and validation (drop markers that reference nonexistent passages).
7. Passage endpoint (`GET /workspaces/{id}/passages/{chunk_id}`): return a cited chunk's text + location, ownership-checked.
8. Redis rate limiter on `/ask` (per-minute and per-day), 429 with `Retry-After`.

**Done when**
- [x] `docqa check-llm` succeeds for both the answer and judge models with your key; their observed free-tier limits are written into this plan and used as the eval budget defaults.
- [x] Unit tests: RRF math on hand-built rankings; rerank reorders as expected; citation parser handles `[1]`, `[1][3]`, `[1, 3]`, and invalid markers.
- [x] Integration test (fake LLM): ask over fixture docs → SSE stream contains tokens, a `citations` event pointing to the right chunk, and `done`.
- [x] A question with no relevant context yields a `refusal` event and no LLM call (verified via fake-provider call counter).
- [x] Retrieval never returns chunks from another user's workspace (explicit test).
- [x] Exceeding the rate limit returns 429 with `Retry-After`; limit resets correctly.
- [x] With a real Groq key, a manual question over a 10-K streams a cited answer end-to-end.

### Milestone 4 — Frontend

**Tasks**
1. Typed API client with cookie credentials and CSRF header; TanStack Query hooks; auth-guarded routes.
2. Sign up / log in pages with validation and error states.
3. Workspaces page: list, create, rename, delete.
4. Documents page: drag-and-drop upload, per-document status with progress bar, error + retry display; attach SEC filings library.
5. Chat page: POST-based SSE reader, streaming render, stop button, refusal styling, rate-limit message (the API exposes `Retry-After` through CORS so the page can say when to try again). On open, the page loads the workspace's stored questions and answers (`GET /workspaces/{id}/questions`) and appends new turns after them, so a refresh keeps the conversation (added in Milestone 6).
6. Citation chips → side panel showing source passage, document name, and Item/section or page.
7. Playwright E2E with the fake LLM: sign up → create workspace → upload fixture PDF → wait for `done` → ask → click citation → passage visible. Also: login guard and bad credentials, a stream cut off mid-answer, and the per-minute rate limit. `make e2e` runs the API on port 8001 and the built frontend on 4173 (so dev servers can keep running), against a `docqa_e2e` database that `docqa reset-db` drops, recreates, and migrates on every run, and Redis DB 2. `FAKE_LLM_TOKEN_DELAY_MS` slows the fake model's stream so the test can see partial text before the answer finishes.
8. CI: add a separate `e2e` job that starts Postgres + Redis service containers, runs migrations, starts API + worker with `LLM_PROVIDER=fake`, serves the built frontend, runs Playwright (Chromium only), and uploads the Playwright report as an artifact on failure.

**Done when**
- [x] All pages work against the real backend; refresh preserves the session.
- [x] Refreshing the chat page restores the conversation from the server, citations included (E2E).
- [x] Streaming is visibly incremental; partial answers survive network errors with an error notice.
- [x] Clicking a citation shows the exact passage text that was cited.
- [x] `npm run typecheck && npm run lint && npm run build` pass.
- [x] `make e2e` passes headless locally from a clean DB.
- [x] The `e2e` CI job is green on push, needs no secrets, and makes no network calls to any LLM.

### Milestone 5 — Evaluation

**Tasks**
1. Dataset schema (`id`, `category`, `question`, `gold_answer`, `answerable`, `companies`, `fiscal_years`, `sources` = list of {`doc`, `section`, `quote`}, `numeric` = list of {`value`, `unit`, `company`, `fiscal_year`, `xbrl_concept` or `xbrl_note`}). Sources and numbers are lists so year-over-year and cross-company questions can carry one per filing or value.
2. Author 50 questions: ~12 factual lookups, ~12 table numbers, ~8 year-over-year, ~8 cross-company, ~10 unanswerable. Fiscal years differ by company (see Milestone 2), so cross-company questions only use fiscal years that all compared companies have filed.
3. XBRL cross-check: for numeric questions, record the XBRL concept (e.g. `us-gaap:Revenues`), and `make eval-xbrl` compares `numeric_value` against SEC's `companyfacts` API for the matching fiscal period (cached locally, same user agent + rate limiter). Mismatches must be fixed or given a documented reason, e.g. the filing reports a segment figure that XBRL tags differently.
4. Quote verifier: every source quote must appear (whitespace-normalized) in the stated Item of the parsed filing text, with tables rendered as the chunker renders them. Gold chunk IDs are derived from the quote for each index config: chunks of the source filing that contain it, or, if none do verbatim (naive chunks hold raw table cells without labels), chunks that contain every token of it.
5. Retrieval eval (no LLM): recall@5, recall@10, MRR, overall and per category. Recall@k is the fraction of a question's sources with a gold chunk in the top k; unanswerables are excluded.
6. Ablations (no LLM): chunk size {256, 512, 1024} (overlap size/8), table-aware vs naive (both 512), vector vs keyword vs hybrid, rerank on vs off. Variants are listed in `evals/configs/ablations.yaml` and built with `make eval-index`.
7. Generation eval on the final config: numeric correctness (parse numbers, normalize units/scale, tolerance), citation correctness (cited chunk contains the gold quote), refusal accuracy (precision/recall on unanswerables), faithfulness by a judge model different from the answering model (asserted at startup).
8. Budget + resume: JSONL checkpoint per run keyed by (question id, config hash); separate daily request/token budgets per model (answer and judge), plus a tokens-per-minute limit; spacing between calls; retry on 429 honoring `retry-after`; graceful stop with "resume tomorrow" message.
9. Human check: export 20 judged answers to markdown with agree/disagree checkboxes; parser computes judge-human agreement rate (and Cohen's kappa).
10. Reports: timestamped markdown + JSON in `evals/reports/`.

**Done when**
- [x] `make eval-verify` confirms all 50 source quotes exist in the filings.
- [x] `make eval-xbrl` reports zero unexplained mismatches between numeric gold answers and SEC XBRL data.
- [x] `make eval-retrieval` and `make eval-ablations` produce reports with no network calls to any LLM.
- [x] `make eval-generate` can be interrupted and resumed without repeating completed items, and stops cleanly when the budget is reached.
- [x] Judge model ≠ answer model is enforced.
- [x] Human-check file is exported; after marking, `make eval-agreement` reports the agreement rate. (20 marked: 100% agreement, Cohen's kappa 1.00; report `evals/reports/20261119T032905Z-human-agreement.md`.)
- [x] Dataset version is recorded in every report.

### Milestone 5b — Retrieval improvements, measured on a dev set

Baseline retrieval on qa_v1 was weak (recall@10 42.5%, MRR 0.181), so retrieval is tuned before
Milestone 6. qa_v1 stays the held-out test set: every choice is made on a separate dev set, and
qa_v1 is run once with the final configuration. The baseline reports are kept as they are.

**Tasks**
1. Dev set `evals/datasets/dev_v1.jsonl`: 25 new questions in the qa_v1 categories and proportions, each with a verified source quote (and XBRL concept or note for numbers). No question or quote shared with qa_v1.
2. Tuning plan `evals/configs/tuning.yaml`, pinned to the dev set (`docqa eval ablations --plan-file` refuses any other dataset). Steps are cumulative; a change is kept if it raises recall@10, or keeps recall@10 and raises MRR (rule fixed after step 1). No LLM calls.
3. Try, in order: (1) a short context header on table chunks (company, fiscal year, Item, table title) instead of the long section heading; (2) company + fiscal-year metadata filtering; (3) query decomposition for cross-company and year-over-year questions; (4) a larger candidate pool before reranking; (5) section-aware vs naive chunking again, after the changes above.
4. Run the retrieval eval and the generation eval once on qa_v1 with the final config, and write a before/after report against the Milestone 5 baseline (`docqa eval compare`, built from the saved report JSONs).

**Outcome on the dev set** (report `evals/reports/20261119T050513Z-tuning.md`): kept the metadata filter (recall@10 47.5% → 85.0%) and decomposition per company (87.5%; per company *and* year was worse, 82.5%). Not kept: the short header (42.5% on tables only, 30.0% on all chunks; 77.5% when re-checked with the final retrieval settings), larger or smaller pools (77.5–82.5%), and naive chunking (72.5%). Built as `ChunkingConfig.context` (`CHUNK_CONTEXT`, default `heading`) and `RETRIEVAL_METADATA_FILTER` / `RETRIEVAL_DECOMPOSE` / `RETRIEVAL_DECOMPOSE_BY` (defaults on / on / `company`).

**Done when**
- [x] `dev_v1` passes `make eval-verify` (25/25 quotes) and `make eval-xbrl` (0 unexplained); unit tests check it shares no questions or quotes with qa_v1.
- [x] `make eval-tune` reproduces the tuning report on the dev set with no LLM calls, and refuses qa_v1.
- [x] Each of the five changes is measured (recall@10, MRR) and kept only if it helps on the dev set.
- [x] `make eval-final-retrieval` on qa_v1 with the final config.
- [x] Generation eval on qa_v1 with the final config, and a before/after report against the baseline.

**Outcome on qa_v1 (held out, run once)**, report `evals/reports/20261119T053241Z-before-after.md`: recall@10 42.5% → 62.5%, MRR 0.181 → 0.310, gold passage in the prompt 35.0% → 60.0%, numeric correctness 47.2% → 55.6%, citation correctness 47.8% → 65.5%, refusal precision 37.0% → 47.6% (recall stays 100%), faithfulness 95.7% → 100%. Mean retrieval latency rose from 1.03 s to 1.41 s (a second rerank for cross-company questions). The test-set gain is smaller than on the dev set (47.5% → 87.5%), as expected when choices are made on dev. Year-over-year retrieval did not improve (recall@10 37.5%), and F06 and F11 went from correct to wrong (F06 is now a false refusal). These are left for later work rather than tuned against qa_v1.

### Milestone 6 — Load testing, benchmarks, hardening

**Tasks**
1. Locust scenario (fake LLM): login, list documents, ask (SSE consumed fully); report p50/p95/p99 and error rate at fixed user counts (1, 5, 10, 25). `make loadtest` clones the dev database (with the ingested library) into a throwaway `docqa_load` via `CREATE DATABASE … TEMPLATE`, so questions run the real hybrid retrieval and reranker over the 15 filings; time to first token and time to `done` are recorded as their own rows.
2. Ingestion benchmark: pages/minute for the 15 filings and a PDF set (four 10-Ks printed to PDF with Playwright's Chromium), with worker concurrency 1 and 2, using the real arq worker on a fresh `docqa_bench` database.
3. `benchmarks/results.md` with machine specs (chip, RAM, OS, Docker memory limit) and exact commands; each script rewrites its own section.
4. Hardening: structured logging with request IDs, consistent error schema, timeouts on LLM calls (LiteLLM's per-request timeout plus `ANSWER_TIMEOUT_SECONDS` for the whole answer), worker job timeouts (a per-attempt deadline that is retried; arq's own timeout is a backstop), crash recovery (arq allows one try beyond the job's attempts, so a crash in the last one is recorded as failed), graceful SSE cancellation on client disconnect (the provider stream is closed and the partial answer saved as `stopped`), upload sanitization (body-size limit before parsing, page limit, bidi/format characters stripped from names, extension kept when shortening), DB pool sizing (pool timeout, recycle, statement timeout), startup checks for model files (`MODEL_FILES_CHECK`, `docqa download-models`), bounded model and argon2 concurrency (found by the load test).
5. Chat history from Milestone 4 (see Milestone 4, task 5).

**Done when**
- [x] Locust run reproducible via `make loadtest`; results table includes p95 and error rate.
- [x] Ingestion throughput recorded in pages/minute.
- [x] Tests cover: LLM timeout → `error` SSE event; client disconnect stops generation; worker crash mid-job → job retried.
- [x] No unhandled exceptions in logs during the load test.

**Outcome** (`benchmarks/results.md`): 0% errors at 1–25 users and no ERROR records or tracebacks in the API and worker logs. Answers (retrieval + rerank over the 15 filings; fake LLM) take p50 1.2 s for one user and 2.6 s at 10 users; at 25 users the API is CPU-bound on the cross-encoder (~0.9 questions/s) and answers queue (p50 16 s), while logins and document lists stay under 0.6 s p99. Ingestion runs at 209 pages/min for the HTML filings and 260 for the PDF set with one job at a time. The load test found three problems, fixed here: unbounded model concurrency (memory), DB connections held while waiting for the models, and argon2 on the event loop. The ingestion benchmark changed the default worker concurrency to 1.

### Milestone 7 — Docs and release readiness

**Tasks**
1. README: overview, Mermaid architecture diagram, demo GIF, one-command setup, results tables (retrieval, ablations, generation, load), design decisions, limitations.
2. "Deploying to the cloud" section written explicitly as a guide (not a claim of an existing deployment).
3. Record demo GIF (Playwright video → ffmpeg → GIF). `make demo-gif` clones the dev database (with the ingested library) into a throwaway `docqa_demo`, starts an API on port 8003 with the answer model from `.env` (`DEMO_LLM_PROVIDER=fake` for none), warms the models up off camera, and records `frontend/e2e/demo.record.ts` (about four answer-model requests). Recording it showed gpt-oss's Markdown bold as literal `**`; the chat now renders `**bold**` (covered by the E2E stream test).
4. Pre-publication audit of the full git history: secrets (gitleaks or trufflehog), files that should be local-only, unexpected commit trailers, large files.

**Done when**
- [x] A fresh clone + `.env` from `.env.example` + `make setup up` works following only the README. (Checked on a clone with its own Compose project and empty volumes: all services healthy, sign up → upload → ingest → ask streams tokens, citations and `done`.)
- [ ] Mermaid diagram renders on GitHub.
- [x] History audit is clean across all commits. (`gitleaks git .`: two false positives, `index_config` keys in a test, recorded in `.gitleaksignore`; no local-only or env files ever tracked; no commit trailers; one author with a noreply address; largest blob 0.8 MB, an eval checkpoint.)

---

## 4. Decisions (resolved 2026-11-17)

1. **Companies and years.** Apple, Microsoft, Amazon, JPMorgan Chase, Johnson & Johnson. Use the three most recent fiscal years with an original 10-K on EDGAR, resolved once and pinned in `data/filings.lock.json`. Fiscal years therefore differ by company (Apple and Microsoft include FY2026).
2. **Groq models.** `llama-3.3-70b-versatile` returns `model_not_found` on the free key, and it is missing from Groq's published rate-limit table. Chosen instead, both on that table:
   - Answer: `openai/gpt-oss-120b` (production model).
   - Judge: `qwen/qwen3.8-27b` (different model family, so the judge is less likely to favor its own style of answer). It is a *preview* model and may be removed at short notice, so the fallback judge is `openai/gpt-oss-20b` (production, but the same family as the answer model).
   - Published Developer-plan limits for each model are 30 RPM, 1K RPD, 8K TPM, and 200K TPD. Free-tier limits may be lower. `docqa check-llm` (Milestone 3, task 0) checks both models with the real key and records the actual limits before any generation work.
   - **Observed with the free key (2026-11-17, `make check-llm`):** both `openai/gpt-oss-120b` and `qwen/qwen3.8-27b` answer, so the primary judge stays. Groq's `x-ratelimit-*` headers report **1,000 requests/day** and **8,000 tokens/minute** for each model, the same as the published table. Tokens/day isn't in the headers, so the published 200K is assumed. The eval budget defaults in `.env.example` stay just under these limits: 900 requests/day, 180K tokens/day, 7K tokens/minute.
   - At 8K tokens per minute, each RAG call should stay around 4–5K tokens (6 reranked passages of ≤512 tokens plus the answer), so evals run about 1–2 questions per minute. The full 50-question generation eval fits within one day's budget per model.
   - **Observed (2026-11-18, first full generation run):** answers averaged ~3.4K tokens and judge calls ~4.1K (judge prompts carry the passages too). The run took ~25 minutes and used 48 requests / 114K tokens on the answer model and 23 judged answers / 64K tokens on the judge (2 questions were refused by the rerank gate, and refused answers aren't judged). A handful of per-minute 429s were retried after Groq's `retry-after`.
3. **E2E in CI.** Yes, as a separate `e2e` job using the fake LLM (Milestone 4).
4. **PDF library.** pdfplumber.
5. **XBRL check.** Yes, numeric gold answers are cross-checked against SEC `companyfacts` (Milestone 5).
6. **Filings library.** A shared read-only library ingested once and attachable to any workspace. Uploaded PDFs stay private to their workspace.
7. **Docker.** Full stack in Compose with memory limits for one-command setup. Day-to-day development runs API, worker, and frontend on the host.
8. **Rate limits.** 5 questions per minute and 100 per day, per user.
