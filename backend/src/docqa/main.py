"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from docqa import __version__
from docqa.api import chat, documents, health, workspaces
from docqa.auth import router as auth_router
from docqa.auth.deps import CSRF_HEADER, csrf_protect
from docqa.config import Settings, get_settings
from docqa.db.session import create_engine, create_sessionmaker
from docqa.generation.chain import AnswerChain
from docqa.generation.llm import answer_llm
from docqa.ingestion.embedding import get_embedder
from docqa.ratelimit import SlidingWindowLimiter, Window
from docqa.retrieval.rerank import get_reranker
from docqa.retrieval.retriever import RetrievalConfig, Retriever


def build_answer_chain(settings: Settings) -> AnswerChain:
    retriever = Retriever(
        get_embedder(settings), get_reranker(settings), RetrievalConfig.from_settings(settings)
    )
    return AnswerChain(retriever, answer_llm(settings), settings.refusal_min_rerank_score)


def ask_limiter(redis: Redis, settings: Settings) -> SlidingWindowLimiter:
    return SlidingWindowLimiter(
        redis,
        "ratelimit:ask",
        [
            Window("minute", 60, settings.rate_limit_questions_per_minute),
            Window("day", 86_400, settings.rate_limit_questions_per_day),
        ],
    )


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
        app.state.arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        app.state.ask_limiter = ask_limiter(redis, settings)
        try:
            yield
        finally:
            await app.state.arq.aclose()
            await redis.aclose()
            await engine.dispose()

    app = FastAPI(
        title="Document Q&A Assistant",
        version=__version__,
        lifespan=lifespan,
        dependencies=[Depends(csrf_protect)],
    )
    app.state.settings = settings
    # Models load lazily on the first question, not at startup.
    app.state.answer_chain = build_answer_chain(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", CSRF_HEADER],
        # Lets the SPA read how long to wait after a 429.
        expose_headers=["Retry-After"],
    )

    app.include_router(health.router)
    app.include_router(auth_router.router)
    app.include_router(workspaces.router)
    app.include_router(documents.router)
    app.include_router(chat.router)
    return app
