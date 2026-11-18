"""Ingest the locked 10-K filings into the shared, read-only filings library."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docqa.config import Settings
from docqa.db.models import Chunk, Document, DocumentStatus, IngestionJob, SourceType
from docqa.ingestion.chunking import ChunkingConfig, make_chunker
from docqa.ingestion.edgar import LockEntry, Lockfile, sha256_file
from docqa.ingestion.embedding import Embedder
from docqa.ingestion.pipeline import (
    IngestResult,
    document_label,
    parse_file,
    run_ingestion,
    store_chunks,
)

log = logging.getLogger(__name__)


@dataclass
class FilingOutcome:
    entry: LockEntry
    status: str  # "ingested" | "skipped" | "missing"
    result: IngestResult | None = None


async def _get_or_create(db: AsyncSession, entry: LockEntry, settings: Settings) -> Document:
    path = settings.raw_data_dir / entry.local_path
    doc = (
        await db.execute(
            select(Document).where(
                Document.is_library, Document.accession_number == entry.accession_number
            )
        )
    ).scalar_one_or_none()
    if doc is None:
        doc = Document(
            is_library=True,
            title=f"{entry.company} {entry.form} FY{entry.fiscal_year}",
            filename=entry.primary_document,
            source_type=SourceType.HTML_10K,
            status=DocumentStatus.QUEUED,
            storage_path=str(path),
            size_bytes=entry.size_bytes,
            sha256=entry.sha256,
            ticker=entry.ticker,
            company_name=entry.company,
            form_type=entry.form,
            fiscal_year=entry.fiscal_year,
            period_of_report=entry.period_of_report,
            accession_number=entry.accession_number,
        )
        db.add(doc)
    doc.storage_path = str(path)
    await db.commit()
    return doc


async def ingest_filings(
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
    embedder: Embedder,
    lock: Lockfile,
    *,
    tickers: set[str] | None = None,
    force: bool = False,
) -> list[FilingOutcome]:
    outcomes: list[FilingOutcome] = []
    for entry in lock.filings:
        if tickers and entry.ticker not in tickers:
            continue
        path = settings.raw_data_dir / entry.local_path
        if not path.exists() or sha256_file(path) != entry.sha256:
            log.warning("%s is missing or changed; run `make download` first", entry.local_path)
            outcomes.append(FilingOutcome(entry, "missing"))
            continue
        async with sessionmaker() as db:
            doc = await _get_or_create(db, entry, settings)
            if doc.status == DocumentStatus.READY and not force:
                outcomes.append(FilingOutcome(entry, "skipped"))
                continue
            job = IngestionJob(document_id=doc.id, max_attempts=1)
            db.add(job)
            await db.commit()
            job_id = job.id
        result = await run_ingestion(sessionmaker, settings, embedder, job_id)
        log.info(
            "%s FY%d: %d pages, %d chunks, %.1f pages/min",
            entry.ticker,
            entry.fiscal_year,
            result.pages,
            result.chunks,
            result.pages_per_minute,
        )
        outcomes.append(FilingOutcome(entry, "ingested", result))
    return outcomes


@dataclass
class IndexOutcome:
    entry: LockEntry
    config_key: str
    status: str  # "built" | "skipped" | "missing"
    chunks: int = 0


async def build_library_index(
    sessionmaker: async_sessionmaker[AsyncSession],
    embedder: Embedder,
    lock: Lockfile,
    settings: Settings,
    configs: list[ChunkingConfig],
    *,
    force: bool = False,
) -> list[IndexOutcome]:
    """Add extra chunk variants (e.g. for ablations) to already-ingested library filings.

    Each filing is parsed once and chunked under every config. Chunks are stored under the
    config's key, so the API (which only reads the default key) never sees them.
    """
    outcomes: list[IndexOutcome] = []
    for entry in lock.filings:
        async with sessionmaker() as db:
            doc = (
                await db.execute(
                    select(Document).where(
                        Document.is_library,
                        Document.accession_number == entry.accession_number,
                        Document.status == DocumentStatus.READY,
                    )
                )
            ).scalar_one_or_none()
            if doc is None:
                outcomes.extend(IndexOutcome(entry, c.key, "missing") for c in configs)
                continue
            existing = dict(
                (
                    await db.execute(
                        select(Chunk.index_config, func.count())
                        .where(Chunk.document_id == doc.id)
                        .group_by(Chunk.index_config)
                    )
                ).all()
            )
            document_id, path, label = doc.id, Path(doc.storage_path), document_label(doc)
        todo = [c for c in configs if force or not existing.get(c.key)]
        outcomes.extend(
            IndexOutcome(entry, c.key, "skipped", existing[c.key]) for c in configs if c not in todo
        )
        if not todo:
            continue
        parsed = await asyncio.to_thread(parse_file, SourceType.HTML_10K, path)
        tokenizer = await asyncio.to_thread(lambda: embedder.tokenizer)
        for config in todo:
            drafts = await asyncio.to_thread(make_chunker(tokenizer, config).chunk, parsed, label)
            vectors = await asyncio.to_thread(
                embedder.embed_passages, [d.embed_text for d in drafts]
            )
            async with sessionmaker() as db:
                await store_chunks(db, document_id, parsed, config.key, drafts, vectors)
                await db.commit()
            log.info(
                "%s FY%d %s: %d chunks", entry.ticker, entry.fiscal_year, config.key, len(drafts)
            )
            outcomes.append(IndexOutcome(entry, config.key, "built", len(drafts)))
    return outcomes
