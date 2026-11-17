"""Tenancy and pipeline behaviour of the shared retriever, against real Postgres."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docqa.db.models import Chunk, Document
from docqa.retrieval.retriever import Retriever
from tests.integration.helpers import ask, ingested_workspace, parse_sse

QUESTION = "Where is the company's largest supplier located?"


def _retriever(app: FastAPI) -> Retriever:
    retriever: Retriever = app.state.answer_chain.retriever
    return retriever


async def _doc_ids(db: AsyncSession, workspace_id: str) -> set[uuid.UUID]:
    rows = await db.execute(select(Document.id).where(Document.workspace_id == workspace_id))
    return set(rows.scalars())


async def test_retrieval_never_crosses_workspaces(
    app: FastAPI,
    client: AsyncClient,
    other_client: AsyncClient,
    settings: Any,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    # Two users upload the identical PDF: the best match for each exists in both workspaces.
    ws_a = await ingested_workspace(client, settings, "a@example.org")
    ws_b = await ingested_workspace(other_client, settings, "b@example.org")
    retriever = _retriever(app)
    async with db_sessionmaker() as db:
        docs_a, docs_b = await _doc_ids(db, ws_a["id"]), await _doc_ids(db, ws_b["id"])
        for ws, own, other in ((ws_a, docs_a, docs_b), (ws_b, docs_b, docs_a)):
            for cfg in (
                retriever.config,
                retriever.config.with_(use_vector=False),
                retriever.config.with_(use_keyword=False, use_rerank=False),
            ):
                passages = await retriever.retrieve(db, uuid.UUID(ws["id"]), QUESTION, cfg)
                assert passages
                assert {p.document_id for p in passages} <= own
                assert not {p.document_id for p in passages} & other
        # A workspace id nobody owns sees nothing.
        assert await retriever.retrieve(db, uuid.uuid4(), QUESTION) == []


async def test_cross_user_ask_and_passage_lookup_are_404(
    client: AsyncClient, other_client: AsyncClient, settings: Any
) -> None:
    ws_a = await ingested_workspace(client, settings, "a@example.org")
    ws_b = await ingested_workspace(other_client, settings, "b@example.org")
    events = parse_sse((await ask(client, ws_a["id"], QUESTION)).text)
    chunk_id = events[-2][1]["citations"][0]["chunk_id"]

    assert (await ask(other_client, ws_a["id"], QUESTION)).status_code == 404
    assert (
        await other_client.get(f"/workspaces/{ws_a['id']}/passages/{chunk_id}")
    ).status_code == 404
    # Even through B's own workspace, A's chunk is not visible.
    assert (
        await other_client.get(f"/workspaces/{ws_b['id']}/passages/{chunk_id}")
    ).status_code == 404
    assert (
        await client.get(f"/workspaces/{ws_a['id']}/passages/{uuid.uuid4()}")
    ).status_code == 404


async def test_library_filings_visible_only_when_attached(
    app: FastAPI,
    client: AsyncClient,
    settings: Any,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    ws = await ingested_workspace(client, settings, "a@example.org")
    # Turn the upload into a library filing, as `ingest-filings` would create it.
    async with db_sessionmaker() as db:
        [doc_id] = await _doc_ids(db, ws["id"])
        await db.execute(
            update(Document)
            .where(Document.id == doc_id)
            .values(is_library=True, workspace_id=None, ticker="NWND", company_name="Northwind")
        )
        await db.commit()
    retriever = _retriever(app)
    async with db_sessionmaker() as db:
        assert await retriever.retrieve(db, uuid.UUID(ws["id"]), QUESTION) == []

    resp = await client.post(
        f"/workspaces/{ws['id']}/library", json={"document_ids": [str(doc_id)]}
    )
    assert resp.status_code == 200, resp.text
    async with db_sessionmaker() as db:
        passages = await retriever.retrieve(db, uuid.UUID(ws["id"]), QUESTION)
    assert {p.document_id for p in passages} == {doc_id}

    await client.delete(f"/workspaces/{ws['id']}/library/{doc_id}")
    async with db_sessionmaker() as db:
        assert await retriever.retrieve(db, uuid.UUID(ws["id"]), QUESTION) == []


async def test_pipeline_stages_and_ordering(
    app: FastAPI,
    client: AsyncClient,
    settings: Any,
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    ws = await ingested_workspace(client, settings, "a@example.org")
    retriever = _retriever(app)
    wid = uuid.UUID(ws["id"])
    async with db_sessionmaker() as db:
        reranked = await retriever.retrieve(db, wid, QUESTION)
        assert "Portugal" in reranked[0].text
        scores = [p.rerank_score for p in reranked]
        assert all(s is not None for s in scores)
        assert scores == sorted(scores, reverse=True)  # type: ignore[type-var]

        fused = await retriever.retrieve(
            db, wid, QUESTION, retriever.config.with_(use_rerank=False)
        )
        assert all(p.rerank_score is None for p in fused)
        assert [p.fused_score for p in fused] == sorted(
            (p.fused_score for p in fused), reverse=True
        )

        keyword_only = retriever.config.with_(use_vector=False, use_rerank=False)
        kw = await retriever.retrieve(db, wid, "Portugal", keyword_only)
        assert [(p.keyword_rank, p.vector_rank) for p in kw] == [(1, None)]
        assert await retriever.retrieve(db, wid, "zeppelin", keyword_only) == []

        top2 = await retriever.retrieve(db, wid, QUESTION, retriever.config.with_(top_n=2))
        assert len(top2) == 2

        # Chunks from another index configuration (an ablation variant) are ignored.
        await db.execute(update(Chunk).values(index_config="naive-256-32"))
        assert await retriever.retrieve(db, wid, QUESTION) == []
        variant = retriever.config.with_(index_config="naive-256-32")
        assert await retriever.retrieve(db, wid, QUESTION, variant)
        await db.rollback()
