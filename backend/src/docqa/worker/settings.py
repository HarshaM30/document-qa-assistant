"""arq worker configuration. Run with: arq docqa.worker.settings.WorkerSettings"""

from __future__ import annotations

from typing import Any, ClassVar

from arq import func
from arq.connections import RedisSettings

from docqa.config import Settings, get_settings
from docqa.worker.tasks import INGEST_TASK, ingest_document, shutdown, startup

# arq's own timeout is only a backstop: each attempt has its own deadline inside the task,
# which records the timeout and retries. The in-progress lock (and so crash recovery time)
# is arq's timeout + 10 s.
JOB_TIMEOUT_MARGIN_SECONDS = 5


def worker_functions(settings: Settings) -> list[Any]:
    return [
        # One try beyond the job's attempts, so a crash in the last one is still recorded.
        func(ingest_document, name=INGEST_TASK, max_tries=2 + settings.ingest_max_retries),
    ]


def arq_job_timeout(settings: Settings) -> int:
    return settings.worker_job_timeout_seconds + JOB_TIMEOUT_MARGIN_SECONDS


_settings = get_settings()


class WorkerSettings:
    functions: ClassVar[list[Any]] = worker_functions(_settings)
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(_settings.redis_url)
    max_jobs = _settings.worker_max_jobs
    job_timeout = arq_job_timeout(_settings)
