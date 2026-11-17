"""Background tasks run by the arq worker."""

from __future__ import annotations

import logging
from typing import Any

from docqa.config import get_settings
from docqa.db.session import create_engine, create_sessionmaker

log = logging.getLogger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    settings = ctx.get("settings") or get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    engine = create_engine(settings)
    ctx["settings"] = settings
    ctx["engine"] = engine
    ctx["sessionmaker"] = create_sessionmaker(engine)
    log.info("worker started")


async def shutdown(ctx: dict[str, Any]) -> None:
    await ctx["engine"].dispose()


async def ping(ctx: dict[str, Any]) -> str:
    return "pong"
