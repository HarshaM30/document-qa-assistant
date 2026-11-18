"""Retrieval eval (no LLM): recall@k and MRR against gold chunks derived from source quotes.

A question's gold chunks are, per source, the chunks of the source filing (in the index
configuration being evaluated) that contain the source quote. Recall@k is the fraction of a
question's sources with at least one gold chunk in the top k; MRR uses the rank of the first
gold chunk of any source. Unanswerable questions have no sources and are skipped.
"""

from __future__ import annotations

import statistics
import time
import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from docqa.db.models import (
    Chunk,
    Document,
    DocumentStatus,
    User,
    Workspace,
    WorkspaceLibraryDocument,
)
from docqa.evals.dataset import Dataset, QAItem, doc_id, gold_chunk_ids
from docqa.retrieval.retriever import RetrievalConfig, Retriever

EVAL_USER_EMAIL = "evals@docqa.local"
EVAL_WORKSPACE_NAME = "Evaluation (SEC filings library)"
KS = (5, 10)


async def ensure_eval_workspace(db: AsyncSession) -> uuid.UUID:
    """An eval-only user and workspace with every ready library filing attached (idempotent)."""
    user = (
        await db.execute(select(User).where(User.email == EVAL_USER_EMAIL))
    ).scalar_one_or_none()
    if user is None:
        user = User(email=EVAL_USER_EMAIL, password_hash="!")  # "!" never verifies: no login
        db.add(user)
        await db.flush()
    workspace = (
        await db.execute(
            select(Workspace).where(
                Workspace.owner_id == user.id, Workspace.name == EVAL_WORKSPACE_NAME
            )
        )
    ).scalar_one_or_none()
    if workspace is None:
        workspace = Workspace(owner_id=user.id, name=EVAL_WORKSPACE_NAME)
        db.add(workspace)
        await db.flush()
    attached = set(
        (
            await db.execute(
                select(WorkspaceLibraryDocument.document_id).where(
                    WorkspaceLibraryDocument.workspace_id == workspace.id
                )
            )
        ).scalars()
    )
    library = (
        await db.execute(
            select(Document.id).where(Document.is_library, Document.status == DocumentStatus.READY)
        )
    ).scalars()
    for document_id in library:
        if document_id not in attached:
            db.add(WorkspaceLibraryDocument(workspace_id=workspace.id, document_id=document_id))
    await db.commit()
    return workspace.id


async def library_documents(db: AsyncSession) -> dict[str, uuid.UUID]:
    """Library document ids keyed by dataset doc id, e.g. "AAPL-FY2026"."""
    rows = await db.execute(
        select(Document.id, Document.ticker, Document.fiscal_year).where(Document.is_library)
    )
    return {doc_id(t, fy): did for did, t, fy in rows if t and fy}


class GoldIndex:
    """Gold chunk ids per (question, source) for one index configuration, computed lazily."""

    def __init__(self, documents: dict[str, uuid.UUID], index_config: str) -> None:
        self.documents = documents
        self.index_config = index_config
        self._chunks: dict[uuid.UUID, list[tuple[uuid.UUID, str]]] = {}

    async def _doc_chunks(
        self, db: AsyncSession, document_id: uuid.UUID
    ) -> list[tuple[uuid.UUID, str]]:
        if document_id not in self._chunks:
            rows = await db.execute(
                select(Chunk.id, Chunk.text).where(
                    Chunk.document_id == document_id, Chunk.index_config == self.index_config
                )
            )
            self._chunks[document_id] = [(cid, text) for cid, text in rows]
        return self._chunks[document_id]

    async def for_item(self, db: AsyncSession, item: QAItem) -> list[set[uuid.UUID]]:
        """One set of gold chunk ids per source (empty if the filing or quote isn't indexed)."""
        sets: list[set[uuid.UUID]] = []
        for source in item.sources:
            document_id = self.documents.get(source.doc)
            if document_id is None:
                sets.append(set())
                continue
            chunks = await self._doc_chunks(db, document_id)
            sets.append(set(gold_chunk_ids(source.quote, chunks)))
        return sets


def first_hit_rank(gold: Sequence[set[uuid.UUID]], ranked: Sequence[uuid.UUID]) -> int | None:
    every = set().union(*gold) if gold else set()
    return next((i for i, cid in enumerate(ranked, start=1) if cid in every), None)


def recall_at(gold: Sequence[set[uuid.UUID]], ranked: Sequence[uuid.UUID], k: int) -> float:
    if not gold:
        return 0.0
    top = set(ranked[:k])
    return sum(1 for g in gold if g & top) / len(gold)


@dataclass
class QuestionResult:
    item_id: str
    category: str
    gold_counts: list[int]
    ranked: list[uuid.UUID]
    first_hit: int | None
    recall: dict[int, float]
    seconds: float

    @property
    def reciprocal_rank(self) -> float:
        return 1.0 / self.first_hit if self.first_hit else 0.0

    @property
    def missing_gold(self) -> bool:
        return any(n == 0 for n in self.gold_counts)


@dataclass
class Metrics:
    n: int
    recall: dict[int, float]
    mrr: float

    @classmethod
    def of(cls, results: Sequence[QuestionResult], ks: Sequence[int]) -> Metrics:
        if not results:
            return cls(0, dict.fromkeys(ks, 0.0), 0.0)
        return cls(
            n=len(results),
            recall={k: statistics.fmean(r.recall[k] for r in results) for k in ks},
            mrr=statistics.fmean(r.reciprocal_rank for r in results),
        )


@dataclass
class RetrievalRun:
    config: RetrievalConfig
    results: list[QuestionResult]
    ks: tuple[int, ...] = KS
    overall: Metrics = field(init=False)
    by_category: dict[str, Metrics] = field(init=False)

    def __post_init__(self) -> None:
        self.overall = Metrics.of(self.results, self.ks)
        groups: dict[str, list[QuestionResult]] = defaultdict(list)
        for r in self.results:
            groups[r.category].append(r)
        self.by_category = {c: Metrics.of(rs, self.ks) for c, rs in sorted(groups.items())}

    @property
    def mean_seconds(self) -> float:
        return statistics.fmean(r.seconds for r in self.results) if self.results else 0.0

    @property
    def missing_gold(self) -> list[str]:
        return [r.item_id for r in self.results if r.missing_gold]


async def evaluate_retrieval(
    db: AsyncSession,
    retriever: Retriever,
    workspace_id: uuid.UUID,
    dataset: Dataset,
    config: RetrievalConfig,
    gold: GoldIndex,
    ks: tuple[int, ...] = KS,
) -> RetrievalRun:
    if config.top_n < max(ks):
        raise ValueError(f"top_n ({config.top_n}) must be at least the largest k ({max(ks)})")
    if gold.index_config != config.index_config:
        raise ValueError("gold index was built for a different index configuration")
    results = []
    for item in dataset.answerable:
        gold_sets = await gold.for_item(db, item)
        started = time.perf_counter()
        passages = await retriever.retrieve(db, workspace_id, item.question, config)
        seconds = time.perf_counter() - started
        ranked = [p.chunk_id for p in passages]
        results.append(
            QuestionResult(
                item_id=item.id,
                category=item.category.value,
                gold_counts=[len(g) for g in gold_sets],
                ranked=ranked,
                first_hit=first_hit_rank(gold_sets, ranked),
                recall={k: recall_at(gold_sets, ranked, k) for k in ks},
                seconds=seconds,
            )
        )
    return RetrievalRun(config, results, ks)
