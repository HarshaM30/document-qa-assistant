"""GET /workspaces/{id}/questions: the stored conversation that the chat page reloads."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docqa.config import Settings
from docqa.db.models import Question
from docqa.generation.prompts import REFUSAL_SENTENCE
from tests.integration.helpers import ask, create_workspace, ingested_workspace, parse_sse, signup

ANSWERABLE = "Where is the company's largest supplier located?"
UNANSWERABLE = "Who won the 2022 FIFA World Cup?"


@pytest.fixture
async def workspace(client: AsyncClient, settings: Settings) -> dict[str, Any]:
    return await ingested_workspace(client, settings, "owner@example.org")


def _url(workspace: dict[str, Any]) -> str:
    return f"/workspaces/{workspace['id']}/questions"


async def test_history_starts_empty(client: AsyncClient, workspace: dict[str, Any]) -> None:
    resp = await client.get(_url(workspace))
    assert resp.status_code == 200
    assert resp.json() == []


async def test_history_returns_questions_and_answers_oldest_first(
    client: AsyncClient, workspace: dict[str, Any]
) -> None:
    answered = parse_sse((await ask(client, workspace["id"], ANSWERABLE)).text)
    refused = parse_sse((await ask(client, workspace["id"], UNANSWERABLE)).text)

    turns = (await client.get(_url(workspace))).json()
    assert [t["question"] for t in turns] == [ANSWERABLE, UNANSWERABLE]

    first, second = turns
    streamed_text = "".join(d["text"] for name, d in answered if name == "token")
    [citation] = answered[-2][1]["citations"]
    assert first["question_id"] == answered[-1][1]["question_id"]
    assert first["answer"]["id"] == answered[-1][1]["answer_id"]
    assert first["answer"]["text"] == streamed_text
    assert first["answer"]["status"] == "complete"
    assert first["answer"]["refused"] is False
    assert first["answer"]["citations"] == [citation]
    assert first["answer"]["latency_ms"] is not None

    assert second["question_id"] == refused[-1][1]["question_id"]
    assert second["answer"]["refused"] is True
    assert second["answer"]["text"] == REFUSAL_SENTENCE
    assert second["answer"]["citations"] == []


async def test_history_limit_keeps_the_most_recent(
    client: AsyncClient, workspace: dict[str, Any]
) -> None:
    for q in ("first question about suppliers", ANSWERABLE):
        await ask(client, workspace["id"], q)
    turns = (await client.get(_url(workspace), params={"limit": 1})).json()
    assert [t["question"] for t in turns] == [ANSWERABLE]
    assert (await client.get(_url(workspace), params={"limit": 0})).status_code == 422


async def test_question_without_a_saved_answer(
    client: AsyncClient,
    workspace: dict[str, Any],
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    me = (await client.get("/auth/me")).json()
    async with db_sessionmaker() as db:
        db.add(
            Question(
                workspace_id=uuid.UUID(workspace["id"]),
                user_id=uuid.UUID(me["id"]),
                text="asked just before a crash",
            )
        )
        await db.commit()
    [turn] = (await client.get(_url(workspace))).json()
    assert turn["question"] == "asked just before a crash"
    assert turn["answer"] is None


async def test_history_is_private(
    client: AsyncClient, other_client: AsyncClient, workspace: dict[str, Any]
) -> None:
    await ask(client, workspace["id"], ANSWERABLE)
    await signup(other_client, "intruder@example.org")
    assert (await other_client.get(_url(workspace))).status_code == 404
    own = await create_workspace(other_client, "Mine")
    assert (await other_client.get(_url(own))).json() == []
    await client.post("/auth/logout")
    assert (await client.get(_url(workspace))).status_code == 401
