# Benchmarks

Both benchmarks run on the host (API, worker, and benchmark scripts as plain processes)
against Postgres and Redis from `make deps`. Each script rewrites only its own section
below, so the numbers here are exactly what the last run printed.

## Load test (`make loadtest`)

```
make deps
make loadtest                       # LOADTEST_USERS="1 5 10 25" LOADTEST_DURATION=60s
```

`benchmarks/loadtest.py` clones the dev database (with the 15 ingested filings) into a
throwaway `docqa_load` database, starts one API process and one worker on port 8002 with the
fake LLM, and runs `benchmarks/locustfile.py` headless at each user count. Each simulated
user logs in, then loops over listing documents (weight 4), asking a question and reading
the whole SSE stream (weight 2), and logging in again (weight 1). The questions mix lookups,
a year-over-year and a cross-company question over the 10-Ks with two the filings can't
answer, so both the full retrieval + rerank path and the refusal gate are exercised. The
fake LLM has no network cost, so the numbers measure this app: auth, Postgres, hybrid
retrieval, the cross-encoder, and SSE streaming.

<!-- loadtest:start -->
Machine: Apple M5 (10 cores), 16 GiB RAM, macOS 26.6.2; Docker Desktop VM 7.7 GiB, 10 CPUs (Postgres and Redis only); Python 3.12.16; run 2026-11-19.

Corpus: 15 library filings. Fake LLM streaming one word every 20 ms; 60s per row; think time 1-3 s per user; one uvicorn process. Latencies in ms.

| Users | Request | Count | p50 | p95 | p99 | Errors | Req/s |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | /auth/login | 3 | 34 | 59 | 59 | 0.0% | 0.1 |
| 1 | /workspaces/:id/documents | 12 | 14 | 15 | 15 | 0.0% | 0.2 |
| 1 | /workspaces/:id/ask (headers) | 9 | 14 | 17 | 17 | 0.0% | 0.2 |
| 1 | ask: first token | 9 | 890 | 4,000 | 4,000 | 0.0% | 0.2 |
| 1 | ask: full answer | 9 | 1,200 | 4,000 | 4,000 | 0.0% | 0.2 |
| 5 | /auth/login | 18 | 47 | 130 | 130 | 0.0% | 0.3 |
| 5 | /workspaces/:id/documents | 67 | 9 | 19 | 33 | 0.0% | 1.1 |
| 5 | /workspaces/:id/ask (headers) | 30 | 10 | 17 | 18 | 0.0% | 0.5 |
| 5 | ask: first token | 30 | 1,200 | 7,000 | 7,300 | 0.0% | 0.5 |
| 5 | ask: full answer | 30 | 1,800 | 7,000 | 7,300 | 0.0% | 0.5 |
| 10 | /auth/login | 47 | 47 | 150 | 200 | 0.0% | 0.8 |
| 10 | /workspaces/:id/documents | 110 | 8 | 13 | 22 | 0.0% | 1.9 |
| 10 | /workspaces/:id/ask (headers) | 48 | 9 | 15 | 17 | 0.0% | 0.8 |
| 10 | ask: first token | 48 | 2,300 | 9,300 | 11,000 | 0.0% | 0.8 |
| 10 | ask: full answer | 48 | 2,600 | 9,300 | 11,000 | 0.0% | 0.8 |
| 25 | /auth/login | 52 | 170 | 440 | 560 | 0.0% | 0.9 |
| 25 | /workspaces/:id/documents | 120 | 9 | 180 | 240 | 0.0% | 2.0 |
| 25 | /workspaces/:id/ask (headers) | 52 | 9 | 100 | 140 | 0.0% | 0.9 |
| 25 | ask: first token | 52 | 16,000 | 47,000 | 47,000 | 0.0% | 0.9 |
| 25 | ask: full answer | 52 | 16,000 | 47,000 | 47,000 | 0.0% | 0.9 |

| Users | All HTTP requests | Error rate | API peak RSS |
|---:|---:|---:|---:|
| 1 | 24 | 0.00% | 960 MB |
| 5 | 115 | 0.00% | 1209 MB |
| 10 | 205 | 0.00% | 1395 MB |
| 25 | 224 | 0.00% | 1572 MB |

Logs during the run: 0 ERROR/CRITICAL records, 0 tracebacks (API and worker).
<!-- loadtest:end -->

## Ingestion throughput (`make bench-ingest`)

```
make deps
make bench-pdfs                     # once: print five 10-Ks to PDF with Playwright's Chromium
make bench-ingest
```

`benchmarks/ingest_throughput.py` creates a fresh `docqa_bench` database for each run,
queues every document of a set as an ingestion job, and drains the queue with the real arq
worker at `max_jobs` 1 and then 2 (one process, sharing one embedding model, as
`WORKER_MAX_JOBS` does). Wall time runs from the first job starting to the last finishing,
with the embedding model already loaded. Sets: the 15 locked 10-K filings (inline-XBRL
HTML; pages are the filings' own page numbers) and the PDF set (the latest 10-K of Apple,
Amazon, Johnson & Johnson and Microsoft printed to PDF, parsed with pdfplumber).

<!-- ingest:start -->
Machine: Apple M5 (10 cores), 16 GiB RAM, macOS 26.6.2; Docker Desktop VM 7.7 GiB, 10 CPUs (Postgres and Redis only); Python 3.12.16; run 2026-11-19.

| Set | Documents | Pages | Worker concurrency | Wall time | Pages/min | Chunks | Worker peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| 10-K PDFs | 4 | 457 | 1 | 106 s | 260 | 989 | 1318 MB |
| 10-K PDFs | 4 | 457 | 2 | 84 s | 325 | 989 | 2402 MB |
| 10-K filings (HTML) | 15 | 2099 | 1 | 603 s | 209 | 6628 | 1482 MB |
| 10-K filings (HTML) | 15 | 2099 | 2 | 561 s | 225 | 6628 | 3207 MB |

Share of job time by stage (all runs): embedding 95%, parsing 3%, indexing 1%, chunking 0%.
<!-- ingest:end -->

## Findings

- **Model concurrency.** The API originally ran every embed/rerank call at once. At 10
  users that peaked at 1.78 GB with a p95 time to first token of 9.5 s. Capping concurrent
  model calls (`MODEL_MAX_CONCURRENCY`) at 2 gave 1.06 GB and 7.2 s, and a cap of 1 gave
  0.95 GB but a p50 of 3.2 s instead of 1.7 s (40 s runs at 10 users). The default is 2.
  Over the full run above the API reaches 1.57 GB, so its Compose limit is 1792 MB.
- **DB connections held during inference.** In the first full run, `GET /documents` at
  25 users had a p50 of 1.3 s: each question kept its pooled connection while queued for
  a model slot, so 10 connections were shared by 25 users mostly waiting on the
  cross-encoder. Embedding the question before any query and releasing the connection
  before reranking brought it to 9 ms (test: `test_no_db_connection_is_held_while_the_models_run`).
- **argon2 on the event loop.** Password hashing (~50 ms, 64 MiB) ran inline, stalling
  every open stream during a login. It now runs in a thread, at most 4 at once.
- **Saturation.** With the fake LLM, a question costs about a second of cross-encoder CPU
  (30 passages, twice for cross-company questions). Throughput tops out near 0.9
  questions/s per API process, so at 25 users answers queue (p50 16 s, p95 47 s) while
  other endpoints stay fast. Scaling out means more API processes (each with its own
  model copy) or fewer rerank candidates.
- **Worker concurrency.** Embedding is 95% of ingestion time and already uses the CPU
  threads it is given, so a second concurrent job adds 7% (filings) to 25% (PDFs)
  throughput while doubling peak memory to 3.2 GB. `WORKER_MAX_JOBS` now defaults to 1, and
  the worker's Compose limit is 1792 MB (one job peaked at 1.48 GB).
- RSS figures are macOS resident set sizes of the host processes; Linux containers report
  memory differently, so the Compose limits keep some headroom above them.
