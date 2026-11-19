"""Background tasks run by the arq worker.

Failure handling for one ingestion job (IngestionJob.max_attempts = 1 + INGEST_MAX_RETRIES):
- an exception, or an attempt running past WORKER_JOB_TIMEOUT_SECONDS, is retried with
  exponential backoff until the attempts run out;
- an unreadable file fails at once (retrying can't help);
- a worker that is stopped mid-job (SIGTERM) re-queues it, and one that crashes (SIGKILL,
  OOM) leaves it to be picked up again once arq's in-progress lock expires. arq allows
  one try more than max_attempts, so a crash during the last attempt is still recorded
  as a failure instead of leaving the job "running" forever.
"""

from __future__ import annotations

import asyncio
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
from docqa.log_config import configure_logging, request_id_var
from docqa.model_files import enforce_model_files

log = logging.getLogger(__name__)

INGEST_TASK = "ingest_document"
GENERIC_ERROR = "Processing failed due to an internal error."


async def startup(ctx: dict[str, Any]) -> None:
    settings: Settings = ctx.get("settings") or get_settings()
    configure_logging(settings.log_level, settings.log_format)
    enforce_model_files(settings, need_reranker=False)
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
    token = request_id_var.set(f"ingest:{job_id}")
    try:
        return await _ingest(ctx, settings, jid, attempt, max_attempts)
    finally:
        request_id_var.reset(token)


async def _ingest(
    ctx: dict[str, Any], settings: Settings, jid: uuid.UUID, attempt: int, max_attempts: int
) -> str:
    if attempt > max_attempts:
        # Only reachable when the worker died during the final attempt.
        await _fail(ctx, jid, max_attempts, f"{GENERIC_ERROR} The worker stopped mid-job.")
        return "failed"
    if attempt > 1:
        log.info("ingestion job %s: attempt %d/%d", jid, attempt, max_attempts)
    try:
        async with asyncio.timeout(settings.worker_job_timeout_seconds):
            result = await run_ingestion(
                ctx["sessionmaker"], settings, ctx["embedder"], jid, attempt
            )
    except asyncio.CancelledError:
        # Worker shutdown: arq puts the job back on the queue; say so instead of "running".
        await asyncio.shield(
            _mark(ctx, jid, status=JobStatus.RETRYING, error="The worker restarted; retrying.")
        )
        raise
    except DocumentParseError as exc:
        # The file itself is the problem; retrying can't help.
        await _fail(ctx, jid, attempt, str(exc))
        return "failed"
    except Exception as exc:
        if isinstance(exc, TimeoutError):
            log.warning(
                "ingestion job %s timed out after %ss (attempt %d/%d)",
                jid,
                settings.worker_job_timeout_seconds,
                attempt,
                max_attempts,
            )
        else:
            log.exception("ingestion job %s failed (attempt %d/%d)", jid, attempt, max_attempts)
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
