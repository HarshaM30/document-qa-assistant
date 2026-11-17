"""POST /workspaces/{id}/ask: a cited answer streamed as server-sent events.

Events, in order:
  token      {"text"}                     zero or more answer fragments
  refusal    {"reason", "message"}        when the question can't be answered from the docs
  citations  {"citations": [...]}         markers in the answer mapped to their passages
  done       {"question_id", "answer_id", "refused", "latency_ms"}
  error      {"message"}                  instead of citations/done if generation fails
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from litellm.exceptions import RateLimitError, Timeout
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docqa.api.workspaces import get_owned_workspace
from docqa.auth.deps import CurrentUser, DbDep
from docqa.db.models import Answer, Question
from docqa.generation.chain import AnswerChain, Refused, Retrieved, Token
from docqa.generation.citations import citations_json, resolve_citations
from docqa.generation.prompts import REFUSAL_SENTENCE
from docqa.generation.refusal import RefusalReason, is_refusal
from docqa.ratelimit import SlidingWindowLimiter
from docqa.retrieval.retriever import Passage
from docqa.schemas.chat import AskRequest

log = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


def _error_message(exc: Exception) -> str:
    if isinstance(exc, Timeout):
        return "The language model took too long to respond. Please try again."
    if isinstance(exc, RateLimitError):
        return "The language model is busy right now. Please try again in a minute."
    return "Something went wrong while answering. Please try again."


async def _answer_events(
    chain: AnswerChain,
    sessionmaker: async_sessionmaker[AsyncSession],
    workspace_id: uuid.UUID,
    question: Question,
) -> AsyncIterator[str]:
    started = time.monotonic()
    passages: list[Passage] = []
    parts: list[str] = []
    refusal: RefusalReason | None = None
    called_llm = False
    try:
        async with sessionmaker() as db:
            async for event in chain.astream(db, workspace_id, question.text):
                if isinstance(event, Retrieved):
                    passages = event.passages
                    called_llm = not event.gate.refuse
                elif isinstance(event, Refused):
                    refusal = event.reason
                elif isinstance(event, Token):
                    parts.append(event.text)
                    yield sse("token", {"text": event.text})
    except Exception as exc:
        log.exception("answering question %s failed", question.id)
        yield sse("error", {"message": _error_message(exc)})
        return

    text = "".join(parts)
    if refusal is None and is_refusal(text):
        refusal = RefusalReason.MODEL
    if refusal is not None:
        yield sse("refusal", {"reason": refusal.value, "message": REFUSAL_SENTENCE})
        text = text or REFUSAL_SENTENCE
    citations = [] if refusal else resolve_citations(text, passages)
    yield sse("citations", {"citations": citations_json(citations)})

    latency_ms = int((time.monotonic() - started) * 1000)
    answer = Answer(
        question_id=question.id,
        text=text,
        refused=refusal is not None,
        citations=citations_json(citations),
        model=chain.llm.litellm_model if called_llm else None,
        latency_ms=latency_ms,
    )
    async with sessionmaker() as db:
        db.add(answer)
        await db.commit()
    yield sse(
        "done",
        {
            "question_id": str(question.id),
            "answer_id": str(answer.id),
            "refused": answer.refused,
            "latency_ms": latency_ms,
        },
    )


@router.post(
    "/workspaces/{workspace_id}/ask",
    response_class=StreamingResponse,
    responses={
        200: {"content": {"text/event-stream": {}}, "description": "Server-sent events"},
        429: {"description": "Too many questions; see Retry-After"},
    },
)
async def ask(
    workspace_id: uuid.UUID, body: AskRequest, request: Request, user: CurrentUser, db: DbDep
) -> StreamingResponse:
    await get_owned_workspace(db, user, workspace_id)
    limiter: SlidingWindowLimiter = request.app.state.ask_limiter
    limit = await limiter.hit(str(user.id))
    if not limit.allowed:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many questions. Please wait before asking again.",
            headers={"Retry-After": str(limit.retry_after_seconds)},
        )

    question = Question(workspace_id=workspace_id, user_id=user.id, text=body.question)
    db.add(question)
    await db.commit()

    return StreamingResponse(
        _answer_events(
            request.app.state.answer_chain, request.app.state.sessionmaker, workspace_id, question
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
