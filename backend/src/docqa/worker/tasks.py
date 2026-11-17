"""Background tasks run by the arq worker."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from arq import Retry
from sqlalchemy import update

from docqa.config import Settings, get_settings
from docqa.db.models import Document, DocumentStatus, IngestionJob, JobStatus
from docqa.db.session import create_engine, create_sessionmaker
from docqa.ingestion.embedding import get_embedder
from docqa.ingestion.parsed import DocumentParseError
from docqa.ingestion.pipeline import run_ingestion

log = logging.getLogger(__name__)

INGEST_TASK = "ingest_document"
GENERIC_ERROR = "Processing failed due to an internal error."


async def startup(ctx: dict[str, Any]) -> None:
    settings: Settings = ctx.get("settings") or get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    engine = create_engine(settings)
    ctx["settings"] = settings
    ctx["engine"] = engine
    ctx["sessionmaker"] = create_sessionmaker(engine)
    ctx.setdefault("embedder", get_embedder(settings))
    log.info("worker started")


async def shutdown(ctx: dict[str, Any]) -> None:
    await ctx["engine"].dispose()


def retry_delay_seconds(settings: Settings, attempt: int) -> float:
    """Exponential backoff: base, 2*base, 4*base, ..."""
    return float(settings.ingest_retry_base_delay_seconds * 2 ** (attempt - 1))


async def _mark(ctx: dict[str, Any], job_id: uuid.UUID, **values: Any) -> uuid.UUID | None:
    async with ctx["sessionmaker"]() as db:
        job = await db.get(IngestionJob, job_id)
        if job is None:
            return None
        for key, value in values.items():
            setattr(job, key, value)
        await db.commit()
        document_id: uuid.UUID = job.document_id
        return document_id


async def ingest_document(ctx: dict[str, Any], job_id: str) -> str:
    settings: Settings = ctx["settings"]
    attempt: int = ctx.get("job_try", 1)
    max_attempts = 1 + settings.ingest_max_retries
    jid = uuid.UUID(job_id)
    try:
        result = await run_ingestion(ctx["sessionmaker"], settings, ctx["embedder"], jid, attempt)
    except DocumentParseError as exc:
        # The file itself is the problem; retrying can't help.
        await _fail(ctx, jid, attempt, str(exc))
        return "failed"
    except Exception as exc:
        log.exception("ingestion job %s failed (attempt %d/%d)", job_id, attempt, max_attempts)
        if attempt < max_attempts:
            delay = retry_delay_seconds(settings, attempt)
            await _mark(
                ctx,
                jid,
                status=JobStatus.RETRYING,
                attempts=attempt,
                error=f"Attempt {attempt} failed; retrying in {delay:g}s. ({type(exc).__name__})",
            )
            raise Retry(defer=delay) from exc
        await _fail(ctx, jid, attempt, f"{GENERIC_ERROR} Gave up after {attempt} attempts.")
        return "failed"
    return f"ok: {result.chunks} chunks"


async def _fail(ctx: dict[str, Any], job_id: uuid.UUID, attempt: int, message: str) -> None:
    document_id = await _mark(
        ctx,
        job_id,
        status=JobStatus.FAILED,
        attempts=attempt,
        error=message,
        finished_at=datetime.now(UTC),
    )
    if document_id is not None:
        async with ctx["sessionmaker"]() as db:
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(status=DocumentStatus.FAILED)
            )
            await db.commit()
