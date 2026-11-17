"""Prompt for answering from numbered context passages."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from langchain_core.prompts import ChatPromptTemplate

REFUSAL_SENTENCE = "I can't answer that from the provided documents."

QUESTION_LABEL = "Question:"
CONTEXT_LABEL = "Context passages:"

SYSTEM_PROMPT = """You answer questions about company filings and other documents, using only \
the numbered context passages you are given.

Rules:
- Use only facts stated in the passages. Never use outside knowledge.
- Cite every factual claim with the number of the passage it came from in plain ASCII \
square brackets, e.g. [2]. Cite several passages as [1][3].
- Copy numbers exactly as written in the passage, with their units and scale \
(e.g. "$391,035 million"). Say which fiscal year a number belongs to.
- If the passages do not contain the answer, reply with exactly this sentence and nothing \
else: {refusal}
- Be concise: give the direct answer first, then brief supporting detail if it helps."""

USER_PROMPT = CONTEXT_LABEL + "\n\n{context}\n\n" + QUESTION_LABEL + " {question}"


class PromptPassage(Protocol):
    @property
    def label(self) -> str: ...

    @property
    def text(self) -> str: ...


def format_context(passages: Sequence[PromptPassage]) -> str:
    """Number passages [1]..[n]; the numbers are what the model cites."""
    return "\n\n".join(f"[{i}] {p.label}\n{p.text}" for i, p in enumerate(passages, start=1))


def answer_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", USER_PROMPT)]
    ).partial(refusal=REFUSAL_SENTENCE)
