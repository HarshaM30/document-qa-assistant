"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from docqa import __version__
from docqa.api import health, workspaces
from docqa.auth import router as auth_router
from docqa.auth.deps import CSRF_HEADER, csrf_protect
from docqa.config import Settings, get_settings
from docqa.db.session import create_engine, create_sessionmaker


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level.upper())

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings)
        redis = Redis.from_url(settings.redis_url)
        app.state.engine = engine
        app.state.sessionmaker = create_sessionmaker(engine)
        app.state.redis = redis
        try:
            yield
        finally:
            await redis.aclose()
            await engine.dispose()

    app = FastAPI(
        title="Document Q&A Assistant",
        version=__version__,
        lifespan=lifespan,
        dependencies=[Depends(csrf_protect)],
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", CSRF_HEADER],
    )

    app.include_router(health.router)
    app.include_router(auth_router.router)
    app.include_router(workspaces.router)
    return app
