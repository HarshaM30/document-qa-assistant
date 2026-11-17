from __future__ import annotations

from docqa.generation.prompts import REFUSAL_SENTENCE
from docqa.generation.refusal import is_refusal, pre_generation_gate
from tests.unit.fakes import make_passage


def test_gate_refuses_without_passages() -> None:
    assert pre_generation_gate([], 0.0).refuse


def test_gate_uses_best_rerank_score() -> None:
    low = [make_passage(1, rerank_score=-8.0), make_passage(2, rerank_score=-2.5)]
    decision = pre_generation_gate(low, 0.0)
    assert decision.refuse
    assert decision.best_score == -2.5
    ok = [*low, make_passage(3, rerank_score=0.4)]
    assert not pre_generation_gate(ok, 0.0).refuse


def test_gate_passes_when_rerank_disabled() -> None:
    assert not pre_generation_gate([make_passage(1)], 0.0).refuse


def test_detects_refusal_sentence_variants() -> None:
    assert is_refusal(REFUSAL_SENTENCE)
    assert is_refusal(f'"{REFUSAL_SENTENCE}"')
    assert is_refusal(
        "  I CAN\N{RIGHT SINGLE QUOTATION MARK}T answer that from the provided documents"
    )
    assert is_refusal(REFUSAL_SENTENCE + " The passages only cover 2024.")


def test_answers_are_not_refusals() -> None:
    assert not is_refusal("Revenue was $10 million [1].")
    assert not is_refusal("")
    assert not is_refusal("Revenue grew [1]. " + REFUSAL_SENTENCE)
