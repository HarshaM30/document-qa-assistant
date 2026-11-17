"""arq worker configuration. Run with: arq docqa.worker.settings.WorkerSettings"""

from __future__ import annotations

from typing import Any, ClassVar

from arq import func
from arq.connections import RedisSettings

from docqa.config import Settings, get_settings
from docqa.worker.tasks import INGEST_TASK, ingest_document, shutdown, startup


def worker_functions(settings: Settings) -> list[Any]:
    return [
        func(ingest_document, name=INGEST_TASK, max_tries=1 + settings.ingest_max_retries),
    ]


_settings = get_settings()


class WorkerSettings:
    functions: ClassVar[list[Any]] = worker_functions(_settings)
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(_settings.redis_url)
    max_jobs = _settings.worker_max_jobs
    job_timeout = _settings.worker_job_timeout_seconds
