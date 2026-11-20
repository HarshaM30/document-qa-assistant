"""`make loadtest`: run benchmarks/locustfile.py at fixed user counts and record the results.

Steps:
1. Clone the dev database (with its ingested filings library) into a throwaway
   `docqa_load` database via CREATE DATABASE ... TEMPLATE, migrate it, and drop users,
   uploads, and ablation-only chunk variants, so retrieval runs over the same library the
   app serves. With no library, the locustfile falls back to uploading the sample PDF.
2. Start an API (one uvicorn process, as in docker-compose) and a worker on port 8002,
   with the fake LLM, JSON logs, and a per-user rate limit high enough not to interfere.
3. Run Locust headless for each user count, sampling the API's memory (RSS) meanwhile.
4. Stop both processes, count ERROR/CRITICAL records and tracebacks in their logs, and
   write the table into benchmarks/results.md (between the loadtest markers) plus the raw
   numbers into benchmarks/out/loadtest/summary.json.

Run from the repo root: `make loadtest` (needs `make deps`). Environment overrides:
LOADTEST_USERS="1 5 10 25", LOADTEST_DURATION=60s, LOADTEST_PORT=8002,
LOADTEST_TOKEN_DELAY_MS=20, LOADTEST_TEMPLATE_DB (default: DATABASE_URL's database).
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import create_async_engine

from docqa.config import Settings
from docqa.ingestion.pipeline import default_chunking

sys.path.insert(0, str(Path(__file__).resolve().parent))
import report

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
OUT = REPO / "benchmarks" / "out" / "loadtest"
LOCUSTFILE = REPO / "benchmarks" / "locustfile.py"

USERS = [int(u) for u in os.environ.get("LOADTEST_USERS", "1 5 10 25").split()]
DURATION = os.environ.get("LOADTEST_DURATION", "60s")
PORT = int(os.environ.get("LOADTEST_PORT", "8002"))
TOKEN_DELAY_MS = os.environ.get("LOADTEST_TOKEN_DELAY_MS", "20")
LOAD_DB = "docqa_load"
REDIS_DB = 3


def _quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


async def prepare_database(settings: Settings, name: str = LOAD_DB) -> tuple[str, int]:
    """Clone the template DB into `name`; return its URL and how many filings it has.

    Also used by docs/record_demo.py (`make demo-gif`).
    """
    template = os.environ.get("LOADTEST_TEMPLATE_DB") or make_url(settings.database_url).database
    target = make_url(settings.test_database_url).set(database=name)
    url = target.render_as_string(hide_password=False)
    admin = create_async_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            await conn.execute(text(f"DROP DATABASE IF EXISTS {_quoted(name)} WITH (FORCE)"))
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": template}
            )
            try:
                if not exists:
                    raise RuntimeError(f"template database {template!r} not found")
                await conn.execute(
                    text(f"CREATE DATABASE {_quoted(name)} TEMPLATE {_quoted(str(template))}")
                )
            except Exception as exc:
                print(
                    f"Could not copy {template!r} ({type(exc).__name__}); is the dev API or "
                    "worker connected to it? Starting from an empty database instead.",
                    flush=True,
                )
                await conn.execute(text(f"CREATE DATABASE {_quoted(name)}"))
    finally:
        await admin.dispose()

    await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        env=os.environ | {"DATABASE_URL": url},
        check=True,
        stdout=subprocess.DEVNULL,
    )
    key = default_chunking(settings).key
    engine = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            # Row deletes follow ON DELETE CASCADE (sessions, workspaces, uploads, Q&A);
            # TRUNCATE ... CASCADE would empty every referencing table, library included.
            await conn.execute(text("DELETE FROM documents WHERE NOT is_library"))
            await conn.execute(text("DELETE FROM users"))
            await conn.execute(text("DELETE FROM chunks WHERE index_config <> :k"), {"k": key})
            await conn.execute(text("VACUUM ANALYZE chunks"))
            filings = await conn.scalar(
                text("SELECT count(*) FROM documents WHERE is_library AND status = 'ready'")
            )
            chunks = await conn.scalar(text("SELECT count(*) FROM chunks"))
    finally:
        await engine.dispose()
    print(f"Database {name} ready: {filings} filings, {chunks} chunks ({key})", flush=True)
    return url, int(filings or 0)


def _env(settings: Settings, db_url: str) -> dict[str, str]:
    redis = urlsplit(settings.test_redis_url)._replace(path=f"/{REDIS_DB}").geturl()
    return os.environ | {
        "APP_ENV": "test",
        "DATABASE_URL": db_url,
        "REDIS_URL": redis,
        "LLM_PROVIDER": "fake",
        "GROQ_API_KEY": "",
        "FAKE_LLM_TOKEN_DELAY_MS": TOKEN_DELAY_MS,
        "RATE_LIMIT_QUESTIONS_PER_MINUTE": "1000000",
        "RATE_LIMIT_QUESTIONS_PER_DAY": "100000000",
        "LOG_FORMAT": "json",
        "LOG_LEVEL": "INFO",
        "MODEL_FILES_CHECK": "require",
        "UPLOAD_DIR": str(OUT / "uploads"),
        "FRONTEND_ORIGIN": "http://localhost",
    }


def _flush_redis(env: dict[str, str]) -> None:
    from redis import Redis

    Redis.from_url(env["REDIS_URL"]).flushdb()


def _wait_healthy(proc: subprocess.Popen[bytes], timeout: float = 120) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("the API exited during startup; see benchmarks/out/loadtest/api.log")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as r:
                if r.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.5)
    raise RuntimeError("the API did not become healthy")


class RssSampler:
    """Peak resident memory of one process, sampled every 0.5 s."""

    def __init__(self, pid: int) -> None:
        self.pid, self.peak_kb = pid, 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.is_set():
            out = subprocess.run(
                ["ps", "-o", "rss=", "-p", str(self.pid)], capture_output=True, text=True
            ).stdout.strip()
            if out:
                self.peak_kb = max(self.peak_kb, int(out))
            self._stop.wait(0.5)

    def __enter__(self) -> RssSampler:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join()


def _read_stats(prefix: Path) -> list[dict[str, str]]:
    with prefix.with_name(prefix.name + "_stats.csv").open() as fh:
        return list(csv.DictReader(fh))


def run_level(users: int, env: dict[str, str], api_pid: int) -> dict[str, Any]:
    prefix = OUT / f"u{users}"
    cmd = [
        sys.executable, "-m", "locust",
        "-f", str(LOCUSTFILE),
        "--headless", "--only-summary",
        "--host", f"http://127.0.0.1:{PORT}",
        "-u", str(users), "-r", str(users),
        "-t", DURATION,
        "--csv", str(prefix),
        "--exit-code-on-error", "0",
    ]  # fmt: skip
    print(f"Running {users} user(s) for {DURATION} ...", flush=True)
    with RssSampler(api_pid) as rss:
        subprocess.run(cmd, cwd=BACKEND, env=env, check=True, stdout=subprocess.DEVNULL)
    return {"users": users, "rows": _read_stats(prefix), "api_peak_rss_mb": rss.peak_kb / 1024}


def scan_logs(*paths: Path) -> dict[str, Any]:
    """Count ERROR/CRITICAL records and tracebacks across the API and worker logs."""
    errors: list[str] = []
    tracebacks = 0
    for path in paths:
        for line in path.read_text(errors="replace").splitlines():
            tracebacks += line.startswith("Traceback")
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict) and record.get("level") in ("ERROR", "CRITICAL"):
                errors.append(f"{path.name}: {record.get('msg')}")
                tracebacks += "Traceback" in str(record.get("exc_info", ""))
    return {"error_records": len(errors), "tracebacks": tracebacks, "examples": errors[:5]}


def main() -> int:
    settings = Settings()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*"):
        if old.is_file():
            old.unlink()
    db_url, filings = asyncio.run(prepare_database(settings))
    env = _env(settings, db_url)
    _flush_redis(env)

    with (OUT / "worker.log").open("wb") as wlog, (OUT / "api.log").open("wb") as alog:
        worker = subprocess.Popen(
            [sys.executable, "-m", "arq", "docqa.worker.settings.WorkerSettings"],
            cwd=BACKEND, env=env, stdout=wlog, stderr=subprocess.STDOUT,
        )  # fmt: skip
        api = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "docqa.main:create_app", "--factory",
                "--host", "127.0.0.1", "--port", str(PORT), "--no-access-log",
            ],
            cwd=BACKEND, env=env, stdout=alog, stderr=subprocess.STDOUT,
        )  # fmt: skip
        try:
            _wait_healthy(api)
            levels = [run_level(u, env, api.pid) for u in USERS]
        finally:
            for proc in (api, worker):
                proc.send_signal(signal.SIGTERM)
            for proc in (api, worker):
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    proc.kill()

    logs = scan_logs(OUT / "api.log", OUT / "worker.log")
    summary = {
        "machine": report.machine_specs(),
        "duration": DURATION,
        "token_delay_ms": int(TOKEN_DELAY_MS),
        "corpus": f"{filings} library filings" if filings else "sample PDF (no library)",
        "levels": levels,
        "logs": logs,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    report.write_section("loadtest", report.loadtest_markdown(summary))
    print(report.loadtest_markdown(summary))
    if logs["error_records"] or logs["tracebacks"]:
        print(f"Errors in the logs: {logs['examples']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
