"""Async SQLAlchemy engine and session helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from docqa.config import Settings


def create_engine(settings: Settings, url: str | None = None) -> AsyncEngine:
    """Pooled async engine.

    Each API process holds at most DB_POOL_SIZE + DB_MAX_OVERFLOW connections; a request
    waits DB_POOL_TIMEOUT_SECONDS for one before failing instead of queueing forever.
    Requests never hold a connection while the LLM streams (the chain releases it after
    retrieval), so the pool bounds concurrent retrievals, not concurrent answers.
    """
    server_settings = {"application_name": f"docqa-{settings.app_env}"}
    if settings.db_statement_timeout_ms:
        server_settings["statement_timeout"] = str(settings.db_statement_timeout_ms)
    return create_async_engine(
        url or settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_seconds,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_pre_ping=True,
        connect_args={"server_settings": server_settings},
    )


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request, from the app's sessionmaker."""
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    async with sessionmaker() as session:
        yield session
