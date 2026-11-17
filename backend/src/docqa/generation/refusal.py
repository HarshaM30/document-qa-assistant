"""Two refusal layers.

1. Before generation: if retrieval found nothing, or the best cross-encoder score is below
   REFUSAL_MIN_RERANK_SCORE, refuse without calling the LLM.
2. After generation: the prompt tells the model to answer with a fixed sentence when the
   passages don't contain the answer; `is_refusal` detects it.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from docqa.generation.prompts import REFUSAL_SENTENCE
from docqa.retrieval.retriever import Passage


class RefusalReason(StrEnum):
    NO_CONTEXT = "no_relevant_context"
    MODEL = "model_refused"


@dataclass(frozen=True)
class GateDecision:
    refuse: bool
    best_score: float | None


def pre_generation_gate(passages: Sequence[Passage], min_rerank_score: float) -> GateDecision:
    if not passages:
        return GateDecision(refuse=True, best_score=None)
    scores = [p.rerank_score for p in passages if p.rerank_score is not None]
    if not scores:  # reranking disabled: nothing to threshold on
        return GateDecision(refuse=False, best_score=None)
    best = max(scores)
    return GateDecision(refuse=best < min_rerank_score, best_score=best)


def _normalize(text: str) -> str:
    text = text.replace("\u2019", "'").replace("\u2018", "'").lower()
    return re.sub(r"[^a-z0-9' ]+", "", re.sub(r"\s+", " ", text)).strip()


_REFUSAL = _normalize(REFUSAL_SENTENCE)


def is_refusal(answer: str) -> bool:
    """True when the answer opens with the refusal sentence (quotes and case ignored)."""
    return _normalize(answer).startswith(_REFUSAL)
