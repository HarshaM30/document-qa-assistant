"""Eval pipeline against real Postgres: eval workspace, retrieval metrics, resumable generation."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docqa.config import Settings
from docqa.db.models import Chunk, Document, DocumentStatus, SourceType
from docqa.evals.budget import Ledger, Limits, ModelBudget
from docqa.evals.client import BudgetedClient, Completion, litellm_complete
from docqa.evals.configs import GenerationConfig
from docqa.evals.dataset import Dataset, QAItem
from docqa.evals.generation_eval import (
    Checkpoint,
    Generator,
    generation_report,
    run_generation,
    run_hash,
)
from docqa.evals.retrieval_eval import (
    GoldIndex,
    ensure_eval_workspace,
    evaluate_retrieval,
    library_documents,
)
from docqa.generation.fake_provider import register_fake_provider
from docqa.generation.llm import LLMSpec, answer_llm
from docqa.ingestion.chunking import ChunkingConfig
from docqa.ingestion.edgar import LockEntry, Lockfile, sha256_file
from docqa.ingestion.embedding import get_embedder
from docqa.ingestion.library import build_library_index
from docqa.retrieval.retriever import Retriever
from tests.integration.helpers import ingested_workspace

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
QUOTE = "The company's largest supplier is located in Portugal."

ANSWERABLE = QAItem.model_validate(
    {
        "id": "A1",
        "category": "factual",
        "question": "Where is the company's largest supplier located?",
        "gold_answer": "Portugal.",
        "answerable": True,
        "companies": ["NWND"],
        "fiscal_years": [2025],
        "sources": [{"doc": "NWND-FY2025", "section": "1", "quote": QUOTE}],
    }
)
UNANSWERABLE = QAItem.model_validate(
    {
        "id": "U1",
        "category": "unanswerable",
        "question": "What colour is the zeppelin fleet?",
        "gold_answer": "Not in the documents.",
        "answerable": False,
        "companies": ["NWND"],
        "fiscal_years": [2025],
    }
)
DATASET = Dataset(Path("test.jsonl"), [ANSWERABLE, UNANSWERABLE])


async def _library_fixture(
    client: AsyncClient, settings: Settings, db_sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    """Ingest the sample PDF, then make it a library filing (NWND FY2025)."""
    ws = await ingested_workspace(client, settings, "owner@example.org")
    async with db_sessionmaker() as db:
        await db.execute(
            update(Document)
            .where(Document.workspace_id == uuid.UUID(ws["id"]))
            .values(is_library=True, workspace_id=None, ticker="NWND", fiscal_year=2025)
        )
        await db.commit()


def _retriever(app: FastAPI) -> Retriever:
    retriever: Retriever = app.state.answer_chain.retriever
    return retriever


async def test_eval_workspace_and_retrieval_metrics(
    app: FastAPI,
    client: AsyncClient,
    settings: Settings,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    await _library_fixture(client, settings, db_sessionmaker)
    retriever = _retriever(app)
    async with db_sessionmaker() as db:
        workspace_id = await ensure_eval_workspace(db)
        assert await ensure_eval_workspace(db) == workspace_id  # idempotent
        documents = await library_documents(db)
        assert set(documents) == {"NWND-FY2025"}

        config = retriever.config.with_(top_n=10)
        gold = GoldIndex(documents, config.index_config)
        [gold_set] = await gold.for_item(db, ANSWERABLE)
        assert gold_set

        run = await evaluate_retrieval(db, retriever, workspace_id, DATASET, config, gold)
        assert [r.item_id for r in run.results] == ["A1"]  # unanswerables are skipped
        assert run.overall.recall[5] == 1.0
        assert run.overall.mrr == 1.0
        assert not run.missing_gold


class StubJudge:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, spec: LLMSpec, messages: Any) -> Completion:
        if spec.provider == "fake":
            return await litellm_complete(spec, messages)
        self.calls += 1
        return Completion(
            '{"verdict": "faithful", "unsupported_claims": [], "reason": "ok"}', 900, 30
        )


async def test_generation_eval_stops_on_budget_and_resumes(
    app: FastAPI,
    client: AsyncClient,
    settings: Settings,
    db_sessionmaker: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    await _library_fixture(client, settings, db_sessionmaker)
    fake = register_fake_provider()
    fake.reset()
    answer = answer_llm(settings)  # the fake provider: deterministic, no network
    judge = LLMSpec("groq", "judge-model", 0.0, 100, 10, None, None)
    retriever = _retriever(app)
    config = GenerationConfig("test", retriever.config, refusal_min_rerank_score=0.0)
    hash_ = run_hash(config, answer, judge)
    checkpoint = Checkpoint(tmp_path / "run.jsonl")
    stub = StubJudge()
    ledger = Ledger(tmp_path / "budget")

    async def run(judge_tokens_per_day: int) -> Any:
        limits = {
            answer.litellm_model: Limits(100, 100_000, 100_000, 0),
            judge.litellm_model: Limits(100, judge_tokens_per_day, 100_000, 0),
        }
        budgets = {m: ModelBudget(m, lim, ledger) for m, lim in limits.items()}
        async with db_sessionmaker() as db:
            gen = Generator(
                db=db,
                retriever=retriever,
                config=config,
                client=BudgetedClient(budgets, stub),
                answer_spec=answer,
                judge_spec=judge,
                workspace_id=await ensure_eval_workspace(db),
                gold=GoldIndex(await library_documents(db), config.retrieval.index_config),
                hash=hash_,
            )
            return await run_generation(gen, DATASET.items, checkpoint)

    # Day 1: the judge's budget is too small for even one call.
    first = await run(judge_tokens_per_day=10)
    assert not first.finished
    assert "groq/judge-model" in first.stopped
    answered = checkpoint.get(f"A1:{hash_}")
    assert answered is not None
    assert answered["judge"] is None
    assert answered["cited_chunk_ids"]
    assert stub.calls == 0
    answer_calls = fake.calls

    # Day 2: resumes from the checkpoint; answers are not regenerated, only judged.
    reloaded = Checkpoint(checkpoint.path)
    checkpoint.records = reloaded.records
    second = await run(judge_tokens_per_day=100_000)
    assert second.finished
    assert fake.calls == answer_calls
    assert stub.calls == 1  # the unanswerable question was refused, so nothing to judge

    data, markdown = generation_report(
        DATASET, checkpoint, config, hash_, answer.litellm_model, judge.litellm_model
    )
    assert data["complete"]
    summary = data["summary"]
    assert summary["citation_accuracy"] == 1.0
    assert summary["refusal_recall"] == 1.0
    assert summary["faithfulness"] == 1.0
    assert "Status: **complete**" in markdown


async def test_build_library_index_adds_variants_once(
    settings: Settings, db_sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    path = FIXTURES / "sample_10k.htm"
    entry = LockEntry(
        ticker="NWND", company="Northwind", cik=1, form="10-K", fiscal_year=2025,
        period_of_report="2025-12-31", filing_date="2026-02-01", accession_number="0000000001-26-1",
        primary_document=path.name, url="u", local_path=path.name, sha256=sha256_file(path),
        size_bytes=path.stat().st_size,
    )  # fmt: skip
    async with db_sessionmaker() as db:
        doc = Document(
            is_library=True, title="Northwind 10-K FY2025", filename=path.name,
            source_type=SourceType.HTML_10K, status=DocumentStatus.READY, storage_path=str(path),
            size_bytes=entry.size_bytes, sha256=entry.sha256, ticker="NWND",
            company_name="Northwind", form_type="10-K", fiscal_year=2025,
            accession_number=entry.accession_number,
        )  # fmt: skip
        db.add(doc)
        await db.commit()
        doc_id = doc.id
    lock = Lockfile("2026-11-17", "10-K", 1, [entry])
    variant = ChunkingConfig("naive", 128, 16)
    embedder = get_embedder(settings)

    first = await build_library_index(db_sessionmaker, embedder, lock, settings, [variant])
    assert [o.status for o in first] == ["built"]
    assert first[0].chunks > 0
    async with db_sessionmaker() as db:
        count = await db.scalar(
            select(func.count()).where(
                Chunk.document_id == doc_id, Chunk.index_config == variant.key
            )
        )
    assert count == first[0].chunks

    again = await build_library_index(db_sessionmaker, embedder, lock, settings, [variant])
    assert [o.status for o in again] == ["skipped"]
