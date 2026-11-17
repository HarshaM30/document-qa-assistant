"""Integration fixtures: a real Postgres (test database) and Redis, the app in-process."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import AsyncClient
from pydantic import SecretStr
from redis.asyncio import Redis
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from docqa.config import Settings
from docqa.main import create_app
from tests.integration.helpers import make_client

BACKEND_DIR = Path(__file__).resolve().parents[2]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "integration" in item.path.parts:
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def settings(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    base = Settings()
    return Settings(
        app_env="test",
        database_url=base.test_database_url,
        redis_url=base.test_redis_url,
        upload_dir=tmp_path_factory.mktemp("uploads"),
        session_secret_key=SecretStr("test-session-secret"),
        ingest_retry_base_delay_seconds=0,
        llm_provider="fake",
    )


async def _ensure_database(url: str) -> None:
    target = make_url(url)
    admin = create_async_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": target.database}
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    finally:
        await admin.dispose()


def _alembic_config(url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["db_url"] = url
    cfg.attributes["configure_logger"] = False
    return cfg


@pytest.fixture(scope="session")
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    await _ensure_database(settings.database_url)
    eng = create_async_engine(settings.database_url)
    cfg = _alembic_config(settings.database_url)
    # Rebuild the schema from scratch so every run starts clean and exercises the migrations.
    async with eng.begin() as conn:
        await conn.run_sync(lambda c: _run_alembic(cfg, c, "downgrade", "base"))
        await conn.run_sync(lambda c: _run_alembic(cfg, c, "upgrade", "head"))
    yield eng
    await eng.dispose()


def _run_alembic(cfg: Config, connection: object, action: str, revision: str) -> None:
    cfg.attributes["connection"] = connection
    getattr(command, action)(cfg, revision)


_TABLES = (
    "answers, questions, chunks, sections, ingestion_jobs, workspace_library_documents, "
    "documents, workspaces, sessions, users"
)


@pytest.fixture(autouse=True)
async def clean_state(engine: AsyncEngine, settings: Settings) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {_TABLES} CASCADE"))
    redis = Redis.from_url(settings.redis_url)
    await redis.flushdb()
    await redis.aclose()


@pytest.fixture
def db_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def app(settings: Settings, engine: AsyncEngine) -> AsyncIterator[object]:
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: object) -> AsyncIterator[AsyncClient]:
    async with make_client(app) as c:
        yield c


@pytest.fixture
async def other_client(app: object) -> AsyncIterator[AsyncClient]:
    async with make_client(app) as c:
        yield c
