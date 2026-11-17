"""arq worker configuration. Run with: arq docqa.worker.settings.WorkerSettings"""

from __future__ import annotations

from typing import Any, ClassVar

from arq.connections import RedisSettings

from docqa.config import get_settings
from docqa.worker.tasks import ping, shutdown, startup

_settings = get_settings()


class WorkerSettings:
    functions: ClassVar[list[Any]] = [ping]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(_settings.redis_url)
    max_jobs = _settings.worker_max_jobs
    job_timeout = _settings.worker_job_timeout_seconds
