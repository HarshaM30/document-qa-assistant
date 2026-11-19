"""Answer deadline, saved partial answers, and stopping generation on client disconnect."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import httpx
import litellm
import pytest
import uvicorn
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docqa.auth.deps import CSRF_HEADER
from docqa.config import Settings
from docqa.db.models import Answer
from docqa.generation.fake_provider import FAKE_LLM
from docqa.main import create_app
from tests.integration.helpers import ask, ingested_workspace, parse_sse

QUESTION = "Where is the company's largest supplier located?"


@pytest.fixture
async def workspace(client: AsyncClient, settings: Settings) -> dict[str, Any]:
    return await ingested_workspace(client, settings, "owner@example.org")


async def _only_answer(sm: async_sessionmaker[AsyncSession]) -> Answer:
    async with sm() as db:
        return (await db.execute(select(Answer))).scalar_one()


async def test_answer_deadline_emits_error_and_keeps_partial_text(
    app: FastAPI,
    client: AsyncClient,
    workspace: dict[str, Any],
    db_sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(FAKE_LLM, "token_delay_seconds", 0.15)
    monkeypatch.setattr(app.state.settings, "answer_timeout_seconds", 1.0)
    events = parse_sse((await ask(client, workspace["id"], QUESTION)).text)

    names = [n for n, _ in events]
    assert names[-1] == "error"
    assert "token" in names
    assert "done" not in names
    assert "citations" not in names
    assert events[-1][1]["message"].startswith("The language model took too long")
    partial = "".join(d["text"] for n, d in events if n == "token")

    stored = await _only_answer(db_sessionmaker)
    assert (stored.status, stored.text) == ("failed", partial)
    assert stored.model == "fake/openai/gpt-oss-120b"
    for _ in range(50):  # the timed-out provider stream is closed, not left running
        if FAKE_LLM.active_streams == 0:
            break
        await asyncio.sleep(0.02)
    assert FAKE_LLM.active_streams == 0


async def test_llm_error_is_saved_as_failed(
    client: AsyncClient,
    workspace: dict[str, Any],
    db_sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def timeout(*args: object, **kwargs: object) -> None:
        raise litellm.exceptions.Timeout("slow", model="m", llm_provider="fake")

    monkeypatch.setattr(litellm, "acompletion", timeout)
    events = parse_sse((await ask(client, workspace["id"], QUESTION)).text)
    assert [n for n, _ in events] == ["error"]
    stored = await _only_answer(db_sessionmaker)
    assert (stored.status, stored.text, stored.refused) == ("failed", "", False)


@pytest.fixture
async def live_server(settings: Settings, engine: object) -> AsyncIterator[tuple[FastAPI, str]]:
    """The app behind a real uvicorn server, so a closed TCP connection is a real disconnect."""
    app = create_app(settings)
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=0, log_config=None, lifespan="on")
    )
    task = asyncio.create_task(server.serve())
    for _ in range(200):
        if server.started:
            break
        await asyncio.sleep(0.02)
    port = server.servers[0].sockets[0].getsockname()[1]
    try:
        yield app, f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        await task


async def test_client_disconnect_stops_generation_and_saves_partial_answer(
    live_server: tuple[FastAPI, str],
    settings: Settings,
    db_sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _, base_url = live_server
    async with httpx.AsyncClient(base_url=base_url, headers={CSRF_HEADER: "x"}) as c:
        workspace = await ingested_workspace(c, settings, "streamer@example.org")
        monkeypatch.setattr(FAKE_LLM, "token_delay_seconds", 0.3)
        words_before = FAKE_LLM.words_streamed

        received = []
        async with c.stream(
            "POST", f"/workspaces/{workspace['id']}/ask", json={"question": QUESTION}
        ) as resp:
            assert resp.status_code == 200
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    received.append(line)
                    # Leave after the first token: closing the stream drops the connection.
                    break

    # Generation stops promptly instead of running to the end of the answer.
    for _ in range(100):
        if FAKE_LLM.active_streams == 0:
            break
        await asyncio.sleep(0.02)
    assert FAKE_LLM.active_streams == 0
    streamed = FAKE_LLM.words_streamed - words_before
    await asyncio.sleep(0.8)  # well past two more token delays
    assert FAKE_LLM.words_streamed - words_before == streamed

    for _ in range(100):
        async with db_sessionmaker() as db:
            stored = (await db.execute(select(Answer))).scalar_one_or_none()
        if stored is not None:
            break
        await asyncio.sleep(0.02)
    assert stored is not None
    assert stored.status == "stopped"
    assert stored.text
    assert "Portugal" not in stored.text
    assert len(stored.text.split()) <= streamed
    assert "client disconnected" in caplog.text


async def test_no_db_connection_is_held_while_the_models_run(
    app: FastAPI,
    client: AsyncClient,
    workspace: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    retriever = app.state.answer_chain.retriever
    pool = app.state.engine.pool
    checked_out: list[int] = []
    real_score = retriever.reranker.score

    def score(question: str, passages: Any) -> list[float]:
        checked_out.append(pool.checkedout())
        result: list[float] = real_score(question, passages)
        return result

    monkeypatch.setattr(retriever.reranker, "score", score)
    events = parse_sse((await ask(client, workspace["id"], QUESTION)).text)
    assert events[-1][0] == "done"
    assert checked_out == [0]
