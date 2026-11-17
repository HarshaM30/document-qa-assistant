"""Answering: retrieve → refusal gate → prompt with numbered passages → streamed tokens.

The generation half is a LangChain LCEL chain (`prompt | stream_llm`) whose LLM step
streams from LiteLLM, so any provider LiteLLM supports (including the `fake` one used in
tests) plugs in unchanged.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any

import litellm
from langchain_core.messages import BaseMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import Runnable, RunnableGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from docqa.generation.citations import normalize_markers
from docqa.generation.llm import LLMSpec
from docqa.generation.prompts import answer_prompt, format_context
from docqa.generation.refusal import GateDecision, RefusalReason, pre_generation_gate
from docqa.retrieval.retriever import Passage, Retriever

_ROLES = {"system": "system", "human": "user", "ai": "assistant"}


def to_litellm_messages(messages: Sequence[BaseMessage]) -> list[dict[str, Any]]:
    return [{"role": _ROLES[m.type], "content": m.content} for m in messages]


def litellm_stream(spec: LLMSpec) -> Runnable[PromptValue, str]:
    """An LCEL step that streams text deltas from a LiteLLM chat completion."""

    async def stream(prompts: AsyncIterator[PromptValue]) -> AsyncIterator[str]:
        async for prompt in prompts:
            response = await litellm.acompletion(
                messages=to_litellm_messages(prompt.to_messages()),
                stream=True,
                **spec.completion_kwargs(),
            )
            async for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield normalize_markers(delta)

    return RunnableGenerator(stream)


@dataclass(frozen=True)
class Retrieved:
    passages: list[Passage]
    gate: GateDecision


@dataclass(frozen=True)
class Refused:
    reason: RefusalReason


@dataclass(frozen=True)
class Token:
    text: str


ChainEvent = Retrieved | Refused | Token


class AnswerChain:
    def __init__(self, retriever: Retriever, llm: LLMSpec, min_rerank_score: float) -> None:
        self.retriever = retriever
        self.llm = llm
        self.min_rerank_score = min_rerank_score
        self.generate: Runnable[dict[str, str], str] = answer_prompt() | litellm_stream(llm)

    async def astream(
        self, db: AsyncSession, workspace_id: uuid.UUID, question: str
    ) -> AsyncIterator[ChainEvent]:
        passages = await self.retriever.retrieve(db, workspace_id, question)
        await db.rollback()  # release the connection before the (slow) LLM call
        gate = pre_generation_gate(passages, self.min_rerank_score)
        yield Retrieved(passages, gate)
        if gate.refuse:
            yield Refused(RefusalReason.NO_CONTEXT)
            return
        inputs = {"context": format_context(passages), "question": question}
        async for text in self.generate.astream(inputs):
            yield Token(text)
