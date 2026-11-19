"""Ingestion jobs survive timeouts, worker shutdowns, and worker crashes."""

from __future__ import annotations

import asyncio
import os
import signal
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docqa.config import Settings
from docqa.db.models import IngestionJob
from docqa.ingestion.embedding import get_embedder
from docqa.worker import tasks
from docqa.worker.settings import arq_job_timeout
from tests.integration.helpers import create_workspace, run_worker, signup, upload_pdf

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture
async def workspace(client: AsyncClient) -> dict[str, Any]:
    await signup(client, "owner@example.org")
    return await create_workspace(client, "Reports")


async def _status(client: AsyncClient, workspace: dict[str, Any], doc_id: str) -> Any:
    return (await client.get(f"/workspaces/{workspace['id']}/documents/{doc_id}")).json()


async def _job(sm: async_sessionmaker[AsyncSession], job_id: str) -> IngestionJob:
    async with sm() as db:
        job = await db.get(IngestionJob, uuid.UUID(job_id))
        assert job is not None
        return job


async def test_attempt_that_times_out_is_retried(
    client: AsyncClient,
    workspace: dict[str, Any],
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from docqa.ingestion.pipeline import run_ingestion as real

    calls: list[int] = []

    async def first_attempt_hangs(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        if len(calls) == 1:
            await asyncio.sleep(60)
        return await real(*args, **kwargs)

    monkeypatch.setattr(tasks, "run_ingestion", first_attempt_hangs)
    doc = (await upload_pdf(client, workspace["id"])).json()
    await run_worker(settings.model_copy(update={"worker_job_timeout_seconds": 1}))

    status = await _status(client, workspace, doc["id"])
    assert len(calls) == 2
    assert status["status"] == "ready"
    assert (status["job"]["status"], status["job"]["attempts"]) == ("done", 2)


async def test_worker_shutdown_mid_job_marks_it_for_retry(
    client: AsyncClient,
    workspace: dict[str, Any],
    settings: Settings,
    db_sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = asyncio.Event()

    async def hang(*args: Any, **kwargs: Any) -> None:
        started.set()
        await asyncio.sleep(60)

    monkeypatch.setattr(tasks, "run_ingestion", hang)
    doc = (await upload_pdf(client, workspace["id"])).json()
    ctx = {"settings": settings, "sessionmaker": db_sessionmaker, "embedder": None, "job_try": 1}
    job = asyncio.create_task(tasks.ingest_document(ctx, doc["job"]["id"]))
    await started.wait()
    job.cancel()  # what arq does to running jobs on SIGTERM
    with pytest.raises(asyncio.CancelledError):
        await job
    stored = await _job(db_sessionmaker, doc["job"]["id"])
    assert stored.status == "retrying"
    assert stored.error == "The worker restarted; retrying."


async def test_crash_during_the_last_attempt_is_recorded_as_failed(
    client: AsyncClient,
    workspace: dict[str, Any],
    settings: Settings,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    doc = (await upload_pdf(client, workspace["id"])).json()
    max_attempts = 1 + settings.ingest_max_retries
    # arq hands out one extra try after a crash in the final attempt.
    ctx = {
        "settings": settings,
        "sessionmaker": db_sessionmaker,
        "embedder": get_embedder(settings),
        "job_try": max_attempts + 1,
    }
    assert await tasks.ingest_document(ctx, doc["job"]["id"]) == "failed"
    status = await _status(client, workspace, doc["id"])
    assert status["status"] == "failed"
    assert status["job"]["attempts"] == max_attempts
    assert status["job"]["error"].endswith("The worker stopped mid-job.")


async def test_worker_killed_mid_job_is_retried_by_the_next_worker(
    client: AsyncClient,
    workspace: dict[str, Any],
    settings: Settings,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    timeout = 2  # keeps arq's in-progress lock (timeout + margin + 10 s) short
    env = os.environ | {
        "APP_ENV": "test",
        "DATABASE_URL": settings.database_url,
        "REDIS_URL": settings.redis_url,
        "LLM_PROVIDER": "fake",
        "LOG_FORMAT": "text",
        "WORKER_JOB_TIMEOUT_SECONDS": str(timeout),
        "MODEL_FILES_CHECK": "off",
    }
    doc = (await upload_pdf(client, workspace["id"])).json()
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "tests.integration.crash_worker",
        cwd=BACKEND_DIR,
        env=env,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        for _ in range(600):
            if (await _job(db_sessionmaker, doc["job"]["id"])).status == "running":
                break
            await asyncio.sleep(0.02)
        else:
            pytest.fail("the crashing worker never started the job")
        proc.send_signal(signal.SIGKILL)  # no cleanup at all, like an OOM kill
        await asyncio.wait_for(proc.wait(), timeout=10)
    finally:
        if proc.returncode is None:
            proc.kill()

    stuck = await _job(db_sessionmaker, doc["job"]["id"])
    assert (stuck.status, stuck.attempts) == ("running", 1)

    # The next worker gets the job once the dead worker's in-progress lock expires.
    lock_seconds = (
        arq_job_timeout(settings.model_copy(update={"worker_job_timeout_seconds": timeout})) + 10
    )
    await asyncio.wait_for(run_worker(settings), timeout=lock_seconds + 30)

    status = await _status(client, workspace, doc["id"])
    assert status["status"] == "ready"
    assert (status["job"]["status"], status["job"]["attempts"]) == ("done", 2)
