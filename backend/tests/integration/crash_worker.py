"""A real arq worker whose pipeline hangs after marking the job running.

test_worker_resilience starts this in a subprocess and SIGKILLs it mid-job, to check that
another worker picks the job up again. Settings come from the environment.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from arq.connections import RedisSettings
from arq.worker import Worker

import docqa.worker.tasks as tasks
from docqa.config import get_settings
from docqa.db.models import IngestionJob, JobStatus
from docqa.worker.settings import arq_job_timeout, worker_functions


async def hang(
    sessionmaker: Any, settings: Any, embedder: Any, job_id: uuid.UUID, attempt: int = 1, **_: Any
) -> None:
    async with sessionmaker() as db:
        job = await db.get(IngestionJob, job_id)
        job.status, job.attempts = JobStatus.RUNNING, attempt
        await db.commit()
    await asyncio.sleep(3600)


async def main() -> None:
    settings = get_settings()
    setattr(tasks, "run_ingestion", hang)  # noqa: B010 (tasks imports it by name)
    worker = Worker(
        functions=worker_functions(settings),
        redis_settings=RedisSettings.from_dsn(settings.redis_url),
        job_timeout=arq_job_timeout(settings),
        poll_delay=0.05,
        max_jobs=1,
        on_startup=tasks.startup,
        on_shutdown=tasks.shutdown,
    )
    await worker.main()


if __name__ == "__main__":
    asyncio.run(main())
