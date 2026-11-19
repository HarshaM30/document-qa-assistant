"""Liveness/readiness endpoint."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from docqa import __version__

router = APIRouter(tags=["health"])

_CHECK_TIMEOUT_SECONDS = 2.0


async def _check_db(engine: AsyncEngine) -> str:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return "ok"


async def _check_redis(redis: Redis) -> str:
    await redis.ping()
    return "ok"


async def _run(check: Any) -> str:
    try:
        return str(await asyncio.wait_for(check, _CHECK_TIMEOUT_SECONDS))
    except Exception as exc:  # health checks report failures rather than raising
        return f"error: {type(exc).__name__}"


@router.get("/health")
async def health(request: Request, response: Response) -> dict[str, Any]:
    db_status, redis_status = await asyncio.gather(
        _run(_check_db(request.app.state.engine)),
        _run(_check_redis(request.app.state.redis)),
    )
    checks = {"database": db_status, "redis": redis_status}
    healthy = all(v == "ok" for v in checks.values())
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ok" if healthy else "degraded",
        "version": __version__,
        "checks": checks,
        # Informational: missing models are downloaded on first use (MODEL_FILES_CHECK=warn).
        "models": _model_status(request),
    }


def _model_status(request: Request) -> dict[str, str]:
    files = getattr(request.app.state, "model_files", None) or []
    return {f.kind: "ok" if f.present else "missing" for f in files} or {"check": "off"}
