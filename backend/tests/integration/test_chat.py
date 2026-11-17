from __future__ import annotations

from typing import Any

import litellm
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docqa.config import Settings
from docqa.db.models import Answer, Chunk, Question
from docqa.generation.fake_provider import FAKE_LLM
from docqa.generation.prompts import REFUSAL_SENTENCE
from tests.integration.helpers import (
    ask,
    create_workspace,
    ingested_workspace,
    parse_sse,
    signup,
)

PORTUGAL_QUESTION = "Where is the company's largest supplier located?"


@pytest.fixture
async def workspace(client: AsyncClient, settings: Settings) -> dict[str, Any]:
    return await ingested_workspace(client, settings, "owner@example.org")


def _names(events: list[tuple[str, dict[str, Any]]]) -> list[str]:
    names = [name for name, _ in events]
    # Collapse the run of token events for readability.
    return [n for i, n in enumerate(names) if n != "token" or i == 0 or names[i - 1] != "token"]


async def test_ask_streams_tokens_citations_and_done(
    client: AsyncClient,
    workspace: dict[str, Any],
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    calls = FAKE_LLM.calls
    resp = await ask(client, workspace["id"], PORTUGAL_QUESTION)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(resp.text)
    assert _names(events) == ["token", "citations", "done"]
    assert FAKE_LLM.calls == calls + 1

    tokens = [data["text"] for name, data in events if name == "token"]
    assert len(tokens) > 1
    answer = "".join(tokens)
    assert "Portugal" in answer

    [citation] = events[-2][1]["citations"]
    assert f"[{citation['marker']}]" in answer
    assert citation["section_title"] == "Page 3"
    assert (citation["page_start"], citation["page_end"]) == (3, 3)
    assert citation["document_title"] == "sample_report"

    async with db_sessionmaker() as db:
        chunk = await db.get(Chunk, citation["chunk_id"])
        assert chunk is not None
        assert "largest supplier is located in Portugal" in chunk.text
        question = (await db.execute(select(Question))).scalar_one()
        stored = (await db.execute(select(Answer))).scalar_one()
    done = events[-1][1]
    assert done["question_id"] == str(question.id)
    assert done["answer_id"] == str(stored.id)
    assert done["refused"] is False
    assert question.text == PORTUGAL_QUESTION
    assert stored.text == answer
    assert stored.refused is False
    assert stored.citations[0]["chunk_id"] == citation["chunk_id"]
    assert stored.model == "fake/openai/gpt-oss-120b"
    assert stored.latency_ms is not None


async def test_cited_passage_can_be_fetched(client: AsyncClient, workspace: dict[str, Any]) -> None:
    events = parse_sse((await ask(client, workspace["id"], PORTUGAL_QUESTION)).text)
    [citation] = events[-2][1]["citations"]
    resp = await client.get(f"/workspaces/{workspace['id']}/passages/{citation['chunk_id']}")
    assert resp.status_code == 200
    passage = resp.json()
    assert "largest supplier is located in Portugal" in passage["text"]
    assert passage["page_start"] == 3
    assert passage["document_title"] == "sample_report"


async def test_irrelevant_question_refused_without_llm_call(
    client: AsyncClient,
    workspace: dict[str, Any],
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    calls = FAKE_LLM.calls
    events = parse_sse(
        (await ask(client, workspace["id"], "Who won the 2022 FIFA World Cup?")).text
    )
    assert _names(events) == ["refusal", "citations", "done"]
    assert events[0][1] == {"reason": "no_relevant_context", "message": REFUSAL_SENTENCE}
    assert events[1][1] == {"citations": []}
    assert events[2][1]["refused"] is True
    assert FAKE_LLM.calls == calls  # the model was never called

    async with db_sessionmaker() as db:
        stored = (await db.execute(select(Answer))).scalar_one()
    assert (stored.refused, stored.text, stored.model) == (True, REFUSAL_SENTENCE, None)


async def test_empty_workspace_refuses_without_llm_call(client: AsyncClient) -> None:
    await signup(client, "empty@example.org")
    workspace = await create_workspace(client)
    calls = FAKE_LLM.calls
    events = parse_sse((await ask(client, workspace["id"], PORTUGAL_QUESTION)).text)
    assert events[0] == ("refusal", {"reason": "no_relevant_context", "message": REFUSAL_SENTENCE})
    assert FAKE_LLM.calls == calls


async def test_model_refusal_detected(
    app: FastAPI, client: AsyncClient, workspace: dict[str, Any]
) -> None:
    # Let everything past the gate so the (fake) model itself decides to refuse.
    app.state.answer_chain.min_rerank_score = float("-inf")
    calls = FAKE_LLM.calls
    events = parse_sse((await ask(client, workspace["id"], "Who won the World Cup?")).text)
    assert FAKE_LLM.calls == calls + 1
    assert _names(events) == ["token", "refusal", "citations", "done"]
    assert "".join(d["text"] for n, d in events if n == "token") == REFUSAL_SENTENCE
    assert events[-3][1]["reason"] == "model_refused"
    assert events[-2][1] == {"citations": []}


async def test_llm_failure_emits_error_event(
    client: AsyncClient, workspace: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def timeout(*args: object, **kwargs: object) -> None:
        raise litellm.exceptions.Timeout("slow", model="m", llm_provider="fake")

    monkeypatch.setattr(litellm, "acompletion", timeout)
    events = parse_sse((await ask(client, workspace["id"], PORTUGAL_QUESTION)).text)
    assert events == [
        ("error", {"message": "The language model took too long to respond. Please try again."})
    ]


async def test_question_validation(client: AsyncClient, workspace: dict[str, Any]) -> None:
    assert (await ask(client, workspace["id"], "   ")).status_code == 422
    assert (await ask(client, workspace["id"], "x" * 2001)).status_code == 422


async def test_ask_requires_auth_and_csrf_header(
    client: AsyncClient, workspace: dict[str, Any]
) -> None:
    url = f"/workspaces/{workspace['id']}/ask"
    no_csrf = await client.post(url, json={"question": "q"}, headers={"X-Requested-With": ""})
    assert no_csrf.status_code == 403
    await client.post("/auth/logout")
    assert (await client.post(url, json={"question": "q"})).status_code == 401
