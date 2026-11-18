from __future__ import annotations

import pytest

from docqa.evals.judge import SameModelError, Verdict, assert_distinct_models, parse_verdict
from docqa.generation.llm import LLMSpec


def _spec(provider: str, model: str) -> LLMSpec:
    return LLMSpec(provider, model, 0.0, 100, 10, None, None)


def test_judge_must_differ_from_answer_model() -> None:
    assert_distinct_models(_spec("groq", "openai/gpt-oss-120b"), _spec("groq", "qwen/qwen3.8-27b"))
    with pytest.raises(SameModelError, match="must differ"):
        assert_distinct_models(
            _spec("groq", "openai/gpt-oss-120b"), _spec("groq", "openai/GPT-OSS-120b")
        )


def test_parse_verdict_variants() -> None:
    plain = parse_verdict('{"verdict": "faithful", "unsupported_claims": [], "reason": "ok"}')
    assert plain.faithful is True
    assert plain.reason == "ok"
    wrapped = parse_verdict(
        '<think>{"verdict": "faithful"} hmm</think>\n```json\n'
        '{"verdict": "Unfaithful", "unsupported_claims": ["the 20% figure"], "reason": "r"}\n```'
    )
    assert wrapped.faithful is False
    assert wrapped.unsupported_claims == ("the 20% figure",)
    assert parse_verdict("The answer is unfaithful.").faithful is False
    assert parse_verdict("no idea").faithful is None


def test_verdict_round_trips() -> None:
    v = Verdict(False, "r", ("c",), "raw")
    assert Verdict.from_json(v.to_json()) == v
    assert Verdict.from_json(Verdict(None).to_json()).label == "unparsed"
