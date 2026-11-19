"""Questions and answers: POST /workspaces/{id}/ask streams a cited answer as server-sent
events; GET /workspaces/{id}/questions returns the stored conversation.

Events, in order:
  token      {"text"}                     zero or more answer fragments
  refusal    {"reason", "message"}        when the question can't be answered from the docs
  citations  {"citations": [...]}         markers in the answer mapped to their passages
  done       {"question_id", "answer_id", "refused", "latency_ms"}
  error      {"message"}                  instead of citations/done if generation fails

Every question gets an answer row: `complete` when the stream finishes, `failed` (with any
partial text) when generation errors or runs past ANSWER_TIMEOUT_SECONDS, and `stopped`
(with the partial text) when the client disconnects, which also stops the LLM stream.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator, Coroutine
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from litellm.exceptions import RateLimitError, Timeout
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docqa.api.workspaces import get_owned_workspace
from docqa.auth.deps import CurrentUser, DbDep
from docqa.db.models import Answer, AnswerStatus, Question
from docqa.generation.chain import AnswerChain, Refused, Retrieved, Token
from docqa.generation.citations import citations_json, resolve_citations
from docqa.generation.prompts import REFUSAL_SENTENCE
from docqa.generation.refusal import RefusalReason, is_refusal
from docqa.ratelimit import SlidingWindowLimiter
from docqa.retrieval.retriever import Passage
from docqa.schemas.chat import AnswerOut, AskRequest, ChatTurnOut

log = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


# Saves started while a request is being cancelled; kept referenced until they finish.
_background_saves: set[asyncio.Task[None]] = set()


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


def _error_message(exc: BaseException) -> str:
    if isinstance(exc, Timeout | TimeoutError):
        return "The language model took too long to respond. Please try again."
    if isinstance(exc, RateLimitError):
        return "The language model is busy right now. Please try again in a minute."
    return "Something went wrong while answering. Please try again."


async def with_deadline[T](events: AsyncIterator[T], seconds: float) -> AsyncIterator[T]:
    """Re-yield `events`, raising TimeoutError once `seconds` have passed in total.

    The timeout wraps each `anext()` rather than the whole loop, so it can never fire
    while this generator is suspended at a `yield` (i.e. inside the caller's code).
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + seconds
    try:
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise TimeoutError
            try:
                item = await asyncio.wait_for(anext(events), remaining)
            except StopAsyncIteration:
                return
            yield item
    finally:
        aclose = getattr(events, "aclose", None)
        if aclose is not None:
            await aclose()


def _save_detached(save: Coroutine[Any, Any, None]) -> None:
    """Run a DB write to completion even though the request task is being cancelled."""
    task = asyncio.ensure_future(save)
    _background_saves.add(task)
    task.add_done_callback(_background_saves.discard)


async def _answer_events(
    chain: AnswerChain,
    sessionmaker: async_sessionmaker[AsyncSession],
    workspace_id: uuid.UUID,
    question: Question,
    timeout_seconds: float,
) -> AsyncIterator[str]:
    started = time.monotonic()
    passages: list[Passage] = []
    parts: list[str] = []
    refusal: RefusalReason | None = None
    called_llm = False

    def answer_row(text: str, answer_status: AnswerStatus) -> Answer:
        citations = [] if refusal else resolve_citations(text, passages)
        return Answer(
            question_id=question.id,
            text=text,
            refused=refusal is not None,
            status=answer_status,
            citations=citations_json(citations),
            model=chain.llm.litellm_model if called_llm else None,
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    async def save(answer: Answer) -> None:
        try:
            async with sessionmaker() as db:
                db.add(answer)
                await db.commit()
        except Exception:
            log.exception("could not save the answer to question %s", question.id)

    try:
        async with sessionmaker() as db:
            stream = with_deadline(chain.astream(db, workspace_id, question.text), timeout_seconds)
            async for event in stream:
                if isinstance(event, Retrieved):
                    passages = event.passages
                    called_llm = not event.gate.refuse
                elif isinstance(event, Refused):
                    refusal = event.reason
                elif isinstance(event, Token):
                    parts.append(event.text)
                    yield sse("token", {"text": event.text})
    except (asyncio.CancelledError, GeneratorExit):
        # The client went away: Starlette cancels the response on http.disconnect, which
        # lands here as CancelledError (or as GeneratorExit if it hit while a chunk was
        # being sent). The LLM stream is closed by now; keep the partial text for history.
        log.info(
            "client disconnected; stopped answering question %s after %d fragments",
            question.id,
            len(parts),
            extra={"question_id": str(question.id), "fragments": len(parts)},
        )
        _save_detached(save(answer_row("".join(parts), AnswerStatus.STOPPED)))
        raise
    except Exception as exc:
        if isinstance(exc, TimeoutError):
            log.warning(
                "answering question %s exceeded %ss",
                question.id,
                timeout_seconds,
                extra={"question_id": str(question.id)},
            )
        else:
            log.exception("answering question %s failed", question.id)
        await save(answer_row("".join(parts), AnswerStatus.FAILED))
        yield sse("error", {"message": _error_message(exc)})
        return

    text = "".join(parts)
    if refusal is None and is_refusal(text):
        refusal = RefusalReason.MODEL
    if refusal is not None:
        text = text or REFUSAL_SENTENCE
    answer = answer_row(text, AnswerStatus.COMPLETE)
    await save(answer)  # before the final events, so a disconnect now can't lose it
    if refusal is not None:
        yield sse("refusal", {"reason": refusal.value, "message": REFUSAL_SENTENCE})
    yield sse("citations", {"citations": answer.citations})
    yield sse(
        "done",
        {
            "question_id": str(question.id),
            "answer_id": str(answer.id),
            "refused": answer.refused,
            "latency_ms": answer.latency_ms,
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
            request.app.state.answer_chain,
            request.app.state.sessionmaker,
            workspace_id,
            question,
            request.app.state.settings.answer_timeout_seconds,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/workspaces/{workspace_id}/questions")
async def list_questions(
    workspace_id: uuid.UUID,
    user: CurrentUser,
    db: DbDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[ChatTurnOut]:
    """The workspace's most recent questions with their answers, oldest first."""
    await get_owned_workspace(db, user, workspace_id)
    rows = await db.execute(
        select(Question, Answer)
        .outerjoin(Answer, Answer.question_id == Question.id)
        .where(Question.workspace_id == workspace_id)
        .order_by(Question.created_at.desc(), Question.id.desc())
        .limit(limit)
    )
    turns = [
        ChatTurnOut(
            question_id=q.id,
            question=q.text,
            asked_at=q.created_at,
            answer=AnswerOut.model_validate(a) if a is not None else None,
        )
        for q, a in rows
    ]
    turns.reverse()
    return turns
