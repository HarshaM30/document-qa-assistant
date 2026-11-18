"""parse → chunk → embed → index, with stage and progress persisted on the ingestion job.

CPU-heavy steps run in a worker thread so the event loop stays responsive; progress is
written to Postgres between steps (and between embedding batches) for the UI to poll.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docqa.config import Settings
from docqa.db.models import (
    Chunk,
    Document,
    DocumentStatus,
    IngestionJob,
    JobStage,
    JobStatus,
    Section,
    SourceType,
)
from docqa.ingestion.chunking import ChunkDraft, ChunkingConfig, make_chunker
from docqa.ingestion.embedding import Embedder
from docqa.ingestion.html_10k import parse_10k
from docqa.ingestion.parsed import ParsedDocument
from docqa.ingestion.pdf import parse_pdf

log = logging.getLogger(__name__)

# Progress range (percent) covered by each stage.
_STAGE_RANGE = {
    JobStage.PARSING: (0.0, 10.0),
    JobStage.CHUNKING: (10.0, 20.0),
    JobStage.EMBEDDING: (20.0, 90.0),
    JobStage.INDEXING: (90.0, 100.0),
}
_EMBED_PROGRESS_EVERY = 256  # passages between progress writes
_INSERT_BATCH = 500


def default_chunking(settings: Settings) -> ChunkingConfig:
    return ChunkingConfig("section", settings.chunk_size_tokens, settings.chunk_overlap_tokens)


def document_label(doc: Document) -> str:
    """Prefix for chunk headings, e.g. "Apple Inc. 10-K FY2026"."""
    if doc.is_library and doc.company_name:
        return f"{doc.company_name} {doc.form_type or '10-K'} FY{doc.fiscal_year}"
    return doc.title


def parse_file(source_type: str, path: Path) -> ParsedDocument:
    if source_type == SourceType.HTML_10K:
        return parse_10k(path.read_bytes())
    return parse_pdf(path)


@dataclass
class IngestResult:
    chunks: int
    pages: int
    seconds: float

    @property
    def pages_per_minute(self) -> float:
        return self.pages / self.seconds * 60 if self.seconds > 0 else 0.0


class JobTracker:
    """Persists stage, progress, and per-stage timings for one ingestion job."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession], job_id: uuid.UUID) -> None:
        self._sm = sessionmaker
        self.job_id = job_id
        self.stage_seconds: dict[str, float] = {}
        self._stage: JobStage | None = None
        self._stage_started = time.monotonic()

    async def _write(self, **values: object) -> None:
        async with self._sm() as db:
            await db.execute(
                update(IngestionJob).where(IngestionJob.id == self.job_id).values(**values)
            )
            await db.commit()

    async def stage(self, stage: JobStage) -> None:
        self._close_stage()
        self._stage = stage
        self._stage_started = time.monotonic()
        await self._write(
            stage=stage, progress=_STAGE_RANGE[stage][0], stage_seconds=self.stage_seconds
        )

    async def progress(self, fraction: float) -> None:
        assert self._stage is not None
        low, high = _STAGE_RANGE[self._stage]
        await self._write(progress=round(low + (high - low) * min(1.0, fraction), 1))

    def _close_stage(self) -> None:
        if self._stage is not None:
            elapsed = time.monotonic() - self._stage_started
            self.stage_seconds[self._stage.value] = round(elapsed, 3)

    async def finish(self, pages_per_minute: float) -> None:
        self._close_stage()
        await self._write(
            status=JobStatus.DONE,
            stage=JobStage.DONE,
            progress=100.0,
            error=None,
            stage_seconds=self.stage_seconds,
            pages_per_minute=round(pages_per_minute, 1),
            finished_at=datetime.now(UTC),
        )


async def _embed(
    embedder: Embedder, drafts: Sequence[ChunkDraft], tracker: JobTracker
) -> list[list[float]]:
    texts = [d.embed_text for d in drafts]
    vectors: list[list[float]] = []
    for start in range(0, len(texts), _EMBED_PROGRESS_EVERY):
        batch = texts[start : start + _EMBED_PROGRESS_EVERY]
        vectors.extend(await asyncio.to_thread(embedder.embed_passages, batch))
        await tracker.progress(len(vectors) / len(texts))
    return vectors


async def store_chunks(
    db: AsyncSession,
    document_id: uuid.UUID,
    parsed: ParsedDocument,
    config_key: str,
    drafts: Sequence[ChunkDraft],
    vectors: Sequence[list[float]],
) -> None:
    """Write sections (once per document) and replace this config's chunks, atomically."""
    section_ids = list(
        (
            await db.execute(
                select(Section.id)
                .where(Section.document_id == document_id)
                .order_by(Section.ordinal)
            )
        ).scalars()
    )
    if len(section_ids) != len(parsed.sections):
        await db.execute(delete(Section).where(Section.document_id == document_id))
        section_ids = [uuid.uuid4() for _ in parsed.sections]
        await db.execute(
            insert(Section),
            [
                {
                    "id": sid,
                    "document_id": document_id,
                    "ordinal": i,
                    "item_code": s.item_code,
                    "title": s.title[:500],
                    "page_start": s.page_start,
                    "page_end": s.page_end,
                }
                for i, (sid, s) in enumerate(zip(section_ids, parsed.sections, strict=True))
            ],
        )
    await db.execute(
        delete(Chunk).where(Chunk.document_id == document_id, Chunk.index_config == config_key)
    )
    rows = [
        {
            "document_id": document_id,
            "section_id": section_ids[d.section_index],
            "index_config": config_key,
            "ordinal": i,
            "heading": d.heading,
            "text": d.text,
            "token_count": d.token_count,
            "is_table": d.is_table,
            "page_start": d.page_start,
            "page_end": d.page_end,
            "embedding": v,
        }
        for i, (d, v) in enumerate(zip(drafts, vectors, strict=True))
    ]
    for start in range(0, len(rows), _INSERT_BATCH):
        await db.execute(insert(Chunk), rows[start : start + _INSERT_BATCH])


async def run_ingestion(
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
    embedder: Embedder,
    job_id: uuid.UUID,
    attempt: int = 1,
    config: ChunkingConfig | None = None,
) -> IngestResult:
    config = config or default_chunking(settings)
    async with sessionmaker() as db:
        job = await db.get(IngestionJob, job_id)
        if job is None:
            raise LookupError(f"ingestion job {job_id} not found")
        document = await db.get(Document, job.document_id)
        assert document is not None
        job.status = JobStatus.RUNNING
        job.attempts = attempt
        job.started_at = job.started_at or datetime.now(UTC)
        document.status = DocumentStatus.PROCESSING
        await db.commit()
        document_id, source_type = document.id, document.source_type
        path, label = Path(document.storage_path), document_label(document)

    tracker = JobTracker(sessionmaker, job_id)
    started = time.monotonic()

    await tracker.stage(JobStage.PARSING)
    parsed = await asyncio.to_thread(parse_file, source_type, path)

    await tracker.stage(JobStage.CHUNKING)
    tokenizer = await asyncio.to_thread(lambda: embedder.tokenizer)
    drafts = await asyncio.to_thread(make_chunker(tokenizer, config).chunk, parsed, label)

    await tracker.stage(JobStage.EMBEDDING)
    vectors = await _embed(embedder, drafts, tracker)

    await tracker.stage(JobStage.INDEXING)
    async with sessionmaker() as db:
        await store_chunks(db, document_id, parsed, config.key, drafts, vectors)
        await db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(status=DocumentStatus.READY, page_count=parsed.page_count)
        )
        await db.commit()

    result = IngestResult(len(drafts), parsed.page_count, time.monotonic() - started)
    await tracker.finish(result.pages_per_minute)
    log.info(
        "ingested document %s: %d pages, %d chunks in %.1fs (%.1f pages/min)",
        document_id,
        result.pages,
        result.chunks,
        result.seconds,
        result.pages_per_minute,
    )
    return result
