"""The retrieval pipeline shared by the API and the evals.

vector (pgvector HNSW) + keyword (Postgres FTS) → reciprocal rank fusion → cross-encoder
rerank → top-N passages. Each stage can be switched off for ablations; every query is
scoped to one workspace's visible documents.

Optionally (see `query_filters`), companies and fiscal years named in the question narrow
the search to the matching filings, and a question about several of them is decomposed
into one retrieval per (company, filing) whose results are interleaved.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Any, Literal, Self

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from docqa.config import Settings
from docqa.db.models import Chunk, Document, DocumentStatus, Section
from docqa.ingestion.embedding import Embedder
from docqa.ingestion.pipeline import default_chunking, document_label
from docqa.retrieval.fusion import reciprocal_rank_fusion
from docqa.retrieval.keyword import keyword_search
from docqa.retrieval.query_filters import (
    CompanyMatcher,
    FilingMeta,
    SubQuery,
    detect,
    interleave,
    plan_subqueries,
)
from docqa.retrieval.rerank import Scorer, rerank_order
from docqa.retrieval.scope import chunk_scope, document_visible_to
from docqa.retrieval.vector import vector_search


@dataclass(frozen=True)
class RetrievalConfig:
    index_config: str
    use_vector: bool = True
    use_keyword: bool = True
    use_rerank: bool = True
    vector_k: int = 30
    keyword_k: int = 30
    rrf_k: int = 60
    rerank_candidates: int = 30
    top_n: int = 6
    ef_search: int = 100
    metadata_filter: bool = False
    decompose: bool = False
    decompose_by: Literal["filing", "company"] = "filing"

    def __post_init__(self) -> None:
        if not (self.use_vector or self.use_keyword):
            raise ValueError("enable at least one of vector or keyword search")
        if self.decompose and not self.metadata_filter:
            raise ValueError("decompose needs metadata_filter (sub-queries are per filing)")
        if self.top_n < 1:
            raise ValueError("top_n must be at least 1")

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        return cls(
            index_config=default_chunking(settings).key,
            use_rerank=settings.rerank_enabled,
            vector_k=settings.retrieval_vector_top_k,
            keyword_k=settings.retrieval_keyword_top_k,
            rrf_k=settings.rrf_k,
            rerank_candidates=settings.retrieval_rerank_candidates,
            top_n=settings.rerank_top_n,
            ef_search=settings.retrieval_ef_search,
            metadata_filter=settings.retrieval_metadata_filter,
            decompose=settings.retrieval_decompose,
            decompose_by=settings.retrieval_decompose_by,
        )

    def with_(self, **changes: object) -> Self:
        return replace(self, **changes)  # type: ignore[arg-type]


@dataclass(frozen=True)
class Passage:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    section_title: str
    item_code: str | None
    page_start: int | None
    page_end: int | None
    heading: str
    text: str
    is_table: bool
    fused_score: float
    rerank_score: float | None = None
    vector_rank: int | None = None
    keyword_rank: int | None = None

    @property
    def pages(self) -> str | None:
        if self.page_start is None:
            return None
        if self.page_end is None or self.page_end == self.page_start:
            return f"p. {self.page_start}"
        return f"pp. {self.page_start}\u2013{self.page_end}"

    @property
    def label(self) -> str:
        """Source line shown to the model above the passage text."""
        label = self.heading or f"{self.document_title} — {self.section_title}"
        if self.pages and not self.section_title.startswith("Page "):
            label += f" ({self.pages})"
        return label


async def _load(
    db: AsyncSession, chunk_ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[Chunk, Section | None, Document]]:
    rows = await db.execute(
        select(Chunk, Section, Document)
        .join(Document, Document.id == Chunk.document_id)
        .outerjoin(Section, Section.id == Chunk.section_id)
        .where(Chunk.id.in_(chunk_ids))
    )
    return {chunk.id: (chunk, section, doc) for chunk, section, doc in rows}


async def visible_filings(
    db: AsyncSession, workspace_id: uuid.UUID
) -> tuple[list[FilingMeta], list[tuple[str, str | None]]]:
    """Ready documents the workspace can see, and the (ticker, company name) pairs among them."""
    rows = (
        await db.execute(
            select(Document.id, Document.ticker, Document.fiscal_year, Document.company_name).where(
                document_visible_to(workspace_id), Document.status == DocumentStatus.READY
            )
        )
    ).all()
    filings = [FilingMeta(r.id, r.ticker, r.fiscal_year) for r in rows]
    companies = sorted({(r.ticker, r.company_name) for r in rows if r.ticker})
    return filings, companies


@lru_cache(maxsize=16)
def _matcher(companies: tuple[tuple[str, str | None], ...]) -> CompanyMatcher:
    return CompanyMatcher(companies)


class Retriever:
    def __init__(
        self,
        embedder: Embedder,
        reranker: Scorer,
        config: RetrievalConfig,
        max_concurrent_inference: int | None = None,
        release_db_during_inference: bool = False,
    ) -> None:
        self.embedder = embedder
        # The API sets this: a request waiting for an inference slot must not hold a pooled
        # connection, or under load plain reads queue behind reranks. The session's loaded
        # objects are expired, which is fine as passages are plain copies by then.
        self.release_db = release_db_during_inference
        self.reranker = reranker
        self.config = config
        # ONNX grows a memory arena per concurrent run, so unbounded concurrency under
        # load pushes the API past its memory limit; extra requests wait for a slot.
        self._inference = (
            asyncio.Semaphore(max_concurrent_inference) if max_concurrent_inference else None
        )

    async def _infer[R](self, fn: Callable[..., R], *args: Any) -> R:
        """Run a model call in a thread, holding an inference slot until the thread ends."""
        if self._inference is None:
            return await asyncio.to_thread(fn, *args)
        slot = self._inference
        await slot.acquire()
        future = asyncio.ensure_future(asyncio.to_thread(fn, *args))

        def done(f: asyncio.Future[R]) -> None:
            slot.release()
            if not f.cancelled():
                f.exception()  # retrieved, so a failure after cancellation isn't re-logged

        future.add_done_callback(done)
        # If the request is cancelled, the thread still runs to the end and keeps its slot.
        return await asyncio.shield(future)

    async def retrieve(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        question: str,
        config: RetrievalConfig | None = None,
    ) -> list[Passage]:
        cfg = config or self.config
        scope = chunk_scope(workspace_id, cfg.index_config)
        # Embed first, before any query checks out a connection.
        embedding = (
            await self._infer(self.embedder.embed_query, question) if cfg.use_vector else None
        )
        subqueries = [SubQuery(None, None, None)]
        if cfg.metadata_filter:
            filings, companies = await visible_filings(db, workspace_id)
            flt = detect(question, _matcher(tuple(companies)))
            subqueries = plan_subqueries(flt, filings, cfg.decompose, cfg.decompose_by)

        results: list[list[Passage]] = []
        for sub in subqueries:
            sub_scope = (
                scope
                if sub.document_ids is None
                else scope & Chunk.document_id.in_(sorted(sub.document_ids))
            )
            results.append(await self._retrieve_one(db, question, embedding, sub_scope, cfg))
        if len(results) == 1:
            return results[0]
        by_id = {p.chunk_id: p for passages in results for p in passages}
        merged = interleave([[p.chunk_id for p in passages] for passages in results], cfg.top_n)
        return [by_id[cid] for cid in merged]

    async def _retrieve_one(
        self,
        db: AsyncSession,
        question: str,
        embedding: list[float] | None,
        scope: Any,
        cfg: RetrievalConfig,
    ) -> list[Passage]:
        rankings: list[list[uuid.UUID]] = []
        vector_ranks: dict[uuid.UUID, int] = {}
        keyword_ranks: dict[uuid.UUID, int] = {}
        if embedding is not None:
            hits = await vector_search(db, embedding, scope, cfg.vector_k, cfg.ef_search)
            rankings.append([cid for cid, _ in hits])
            vector_ranks = {cid: r for r, cid in enumerate(rankings[-1], start=1)}
        if cfg.use_keyword:
            hits = await keyword_search(db, question, scope, cfg.keyword_k)
            rankings.append([cid for cid, _ in hits])
            keyword_ranks = {cid: r for r, cid in enumerate(rankings[-1], start=1)}

        fused = reciprocal_rank_fusion(rankings, cfg.rrf_k)
        pool = fused[: cfg.rerank_candidates if cfg.use_rerank else cfg.top_n]
        if not pool:
            return []
        rows = await _load(db, [cid for cid, _ in pool])

        passages = []
        for cid, score in pool:
            chunk, section, doc = rows[cid]
            passages.append(
                Passage(
                    chunk_id=cid,
                    document_id=doc.id,
                    document_title=document_label(doc),
                    section_title=section.title if section else "",
                    item_code=section.item_code if section else None,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    heading=chunk.heading,
                    text=chunk.text,
                    is_table=chunk.is_table,
                    fused_score=score,
                    vector_rank=vector_ranks.get(cid),
                    keyword_rank=keyword_ranks.get(cid),
                )
            )

        if cfg.use_rerank:
            texts = [f"{p.heading}\n{p.text}" if p.heading else p.text for p in passages]
            if self.release_db:
                await db.rollback()
            scores = await self._infer(self.reranker.score, question, texts)
            passages = [replace(passages[i], rerank_score=scores[i]) for i in rerank_order(scores)]
        return passages[: cfg.top_n]
