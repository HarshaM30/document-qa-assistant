"""`make bench-ingest`: ingestion throughput (pages/minute) at worker concurrency 1 and 2.

For each document set and concurrency, a child process:
1. recreates a throwaway `docqa_bench` database (migrated) and flushes Redis DB 4;
2. creates one Document + IngestionJob per document and enqueues it, exactly as an upload
   (PDFs) or a library filing (10-K HTML) would be;
3. loads the embedding model, then drains the queue with the real arq worker in burst mode
   at `max_jobs` = concurrency (one process sharing one model, like WORKER_MAX_JOBS);
4. reports pages, chunks, wall time (first job start to last job end, from the jobs'
   own timestamps), per-stage seconds, and the process's peak RSS.

Each run is a separate process so its peak memory is its own. Results go to
benchmarks/out/ingest/summary.json and the `ingest` section of benchmarks/results.md.

Sets: `filings` (the 15 locked 10-Ks in data/raw; `make download`) and `pdfs` (data/bench/
pdfs; `make bench-pdfs`). Overrides: BENCH_SETS="filings pdfs", BENCH_CONCURRENCY="1 2".
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import resource
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy import make_url as sa_make_url

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
OUT = REPO / "benchmarks" / "out" / "ingest"
PDF_DIR = REPO / "data" / "bench" / "pdfs"
BENCH_DB = "docqa_bench"
REDIS_DB = 4

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _urls() -> tuple[str, str]:
    from docqa.config import Settings

    settings = Settings()
    db = sa_make_url(settings.test_database_url).set(database=BENCH_DB)
    redis = urlsplit(settings.test_redis_url)._replace(path=f"/{REDIS_DB}").geturl()
    return db.render_as_string(hide_password=False), redis


async def _prepare(db_url: str, redis_url: str, doc_set: str) -> list[str]:
    """Fresh database with one queued job per document; returns the job ids."""
    from redis.asyncio import Redis

    from docqa.config import Settings
    from docqa.db.admin import recreate_database
    from docqa.db.models import Document, IngestionJob, SourceType, User, Workspace
    from docqa.db.session import create_engine, create_sessionmaker
    from docqa.ingestion.edgar import Lockfile
    from docqa.ingestion.library import _get_or_create

    await recreate_database(db_url)
    await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        env=os.environ | {"DATABASE_URL": db_url},
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    redis = Redis.from_url(redis_url)
    await redis.flushdb()
    await redis.aclose()

    settings = Settings(database_url=db_url)
    engine = create_engine(settings)
    sm = create_sessionmaker(engine)
    job_ids: list[str] = []
    try:
        async with sm() as db:
            if doc_set == "filings":
                lock = Lockfile.load(settings.filings_lock_file)
                docs = [await _get_or_create(db, entry, settings) for entry in lock.filings]
            else:
                pdfs = sorted(PDF_DIR.glob("*.pdf"))
                if not pdfs:
                    raise SystemExit(f"No PDFs in {PDF_DIR}; run `make bench-pdfs` first")
                user = User(email="bench@example.org", password_hash="x")
                db.add(user)
                await db.flush()
                ws = Workspace(owner_id=user.id, name="Benchmark")
                db.add(ws)
                await db.flush()
                docs = []
                for pdf in pdfs:
                    doc = Document(
                        workspace_id=ws.id,
                        title=pdf.stem,
                        filename=pdf.name,
                        source_type=SourceType.PDF,
                        storage_path=str(pdf),
                        size_bytes=pdf.stat().st_size,
                        sha256="-",
                    )
                    db.add(doc)
                    docs.append(doc)
                await db.flush()
            for doc in docs:
                job = IngestionJob(document_id=doc.id, max_attempts=1)
                db.add(job)
                await db.flush()
                job_ids.append(str(job.id))
            await db.commit()
    finally:
        await engine.dispose()
    return job_ids


async def _run(doc_set: str, concurrency: int) -> dict[str, Any]:
    from arq import create_pool
    from arq.connections import RedisSettings
    from arq.worker import Worker

    from docqa.config import Settings
    from docqa.db.models import Chunk, Document, IngestionJob
    from docqa.db.session import create_engine, create_sessionmaker
    from docqa.ingestion.embedding import get_embedder
    from docqa.log_config import configure_logging
    from docqa.worker.settings import arq_job_timeout, worker_functions
    from docqa.worker.tasks import INGEST_TASK, shutdown, startup

    db_url, redis_url = _urls()
    job_ids = await _prepare(db_url, redis_url, doc_set)
    settings = Settings(
        database_url=db_url,
        redis_url=redis_url,
        worker_max_jobs=concurrency,
        ingest_max_retries=0,
        log_format="text",
        log_level="WARNING",
    )
    configure_logging(settings.log_level, settings.log_format)

    pool = await create_pool(RedisSettings.from_dsn(redis_url))
    for jid in job_ids:
        await pool.enqueue_job(INGEST_TASK, jid, _job_id=f"ingest:{jid}:0")
    await pool.aclose()

    # Load the model (and its tokenizer) before the clock starts.
    embedder = get_embedder(settings)
    embedder.embed_passages(["warm up"])
    _ = embedder.tokenizer

    worker = Worker(
        functions=worker_functions(settings),
        redis_settings=RedisSettings.from_dsn(redis_url),
        burst=True,
        max_jobs=concurrency,
        job_timeout=arq_job_timeout(settings),
        poll_delay=0.1,
        handle_signals=False,
        on_startup=startup,
        on_shutdown=shutdown,
        ctx={"settings": settings, "embedder": embedder},
    )
    try:
        await worker.main()
    finally:
        await worker.close()

    engine = create_engine(settings)
    try:
        async with create_sessionmaker(engine)() as db:
            jobs = list((await db.execute(select(IngestionJob))).scalars())
            pages = await db.scalar(select(func.sum(Document.page_count)))
            chunks = await db.scalar(select(func.count()).select_from(Chunk))
    finally:
        await engine.dispose()
    failed = [j for j in jobs if j.status != "done"]
    if failed:
        raise SystemExit(f"{len(failed)} job(s) did not finish: {failed[0].error}")
    started = min(j.started_at for j in jobs if j.started_at)
    finished = max(j.finished_at for j in jobs if j.finished_at)
    seconds = (finished - started).total_seconds()
    stage_seconds: dict[str, float] = defaultdict(float)
    for j in jobs:
        for stage, value in (j.stage_seconds or {}).items():
            stage_seconds[stage] += float(value)
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_mb = rss / 2**20 if sys.platform == "darwin" else rss / 1024  # bytes vs KiB
    return {
        "set": "10-K filings (HTML)" if doc_set == "filings" else "10-K PDFs",
        "documents": len(jobs),
        "pages": int(pages or 0),
        "chunks": int(chunks or 0),
        "concurrency": concurrency,
        "seconds": seconds,
        "pages_per_minute": (pages or 0) / seconds * 60,
        "stage_seconds": dict(stage_seconds),
        "peak_rss_mb": rss_mb,
    }


def main() -> int:
    import report

    sets = os.environ.get("BENCH_SETS", "filings pdfs").split()
    levels = [int(c) for c in os.environ.get("BENCH_CONCURRENCY", "1 2").split()]
    OUT.mkdir(parents=True, exist_ok=True)
    runs = []
    for doc_set in sets:
        for c in levels:
            print(f"Ingesting {doc_set} with worker concurrency {c} ...", flush=True)
            proc = subprocess.run(
                [sys.executable, __file__, "--run", doc_set, str(c)],
                cwd=BACKEND,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                print(proc.stdout, proc.stderr, sep="\n", file=sys.stderr)
                return proc.returncode
            result = json.loads(proc.stdout.strip().splitlines()[-1])
            print(
                f"  {result['pages']} pages in {result['seconds']:.0f} s = "
                f"{result['pages_per_minute']:.0f} pages/min, peak {result['peak_rss_mb']:.0f} MB",
                flush=True,
            )
            runs.append(result)

    totals: dict[str, float] = defaultdict(float)
    for r in runs:
        for stage, value in r["stage_seconds"].items():
            totals[stage] += value
    all_time = sum(totals.values()) or 1
    summary = {
        "machine": report.machine_specs(),
        "runs": runs,
        "stage_share": {k: v / all_time for k, v in sorted(totals.items(), key=lambda kv: -kv[1])},
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    report.write_section("ingest", report.ingest_markdown(summary))
    print(report.ingest_markdown(summary))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", nargs=2, metavar=("SET", "CONCURRENCY"))
    args = parser.parse_args()
    if args.run:
        print(json.dumps(asyncio.run(_run(args.run[0], int(args.run[1])))))
        raise SystemExit(0)
    raise SystemExit(main())
