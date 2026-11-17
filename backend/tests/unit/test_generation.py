from __future__ import annotations

from collections.abc import AsyncIterator

import litellm
import pytest

from docqa.config import Settings
from docqa.generation.chain import litellm_stream
from docqa.generation.fake_provider import FAKE_LLM, extractive_answer
from docqa.generation.llm import answer_llm, judge_llm
from docqa.generation.prompts import REFUSAL_SENTENCE, answer_prompt, format_context
from docqa.retrieval.keyword import or_query
from tests.unit.fakes import make_passage

PASSAGES = [
    make_passage(1, "The company operates 42 retail stores. It sells boots.", heading="Doc — P1"),
    make_passage(2, "Our largest supplier is located in Portugal.", heading="Doc — P3"),
]


def _messages(question: str) -> list[dict[str, str]]:
    prompt = answer_prompt().invoke({"context": format_context(PASSAGES), "question": question})
    roles = {"system": "system", "human": "user"}
    return [{"role": roles[m.type], "content": str(m.content)} for m in prompt.to_messages()]


def test_context_numbers_passages_with_labels() -> None:
    context = format_context(PASSAGES)
    assert context.startswith("[1] Doc — P1 (p. 1)\nThe company operates")
    assert "\n\n[2] Doc — P3 (p. 2)\nOur largest supplier" in context


def test_prompt_contains_refusal_rule_and_question() -> None:
    system, user = _messages("Where is the supplier?")
    assert REFUSAL_SENTENCE in system["content"]
    assert user["content"].endswith("Question: Where is the supplier?")


def test_fake_answers_extractively_with_marker() -> None:
    answer = extractive_answer(_messages("Where is the largest supplier located?"))
    assert answer == "Our largest supplier is located in Portugal. [2]"


def test_fake_refuses_without_overlap() -> None:
    assert extractive_answer(_messages("Who won the World Cup?")) == REFUSAL_SENTENCE


async def test_fake_provider_streams_through_litellm_and_counts_calls() -> None:
    spec = answer_llm(Settings(llm_provider="fake"))
    assert spec.litellm_model == "fake/openai/gpt-oss-120b"
    chain = answer_prompt() | litellm_stream(spec)
    before = FAKE_LLM.calls
    inputs = {"context": format_context(PASSAGES), "question": "How many retail stores?"}
    pieces = [piece async for piece in chain.astream(inputs)]
    assert len(pieces) > 1  # streamed word by word
    assert "".join(pieces) == "The company operates 42 retail stores. [1]"
    assert FAKE_LLM.calls == before + 1


def test_reasoning_effort_only_for_reasoning_models() -> None:
    settings = Settings(llm_provider="groq", llm_reasoning_effort="low")
    assert answer_llm(settings).completion_kwargs()["reasoning_effort"] == "low"
    judge = judge_llm(Settings(judge_provider="groq", judge_model="qwen/qwen3.8-27b"))
    assert "reasoning_effort" not in judge.completion_kwargs()
    kwargs = answer_llm(settings).completion_kwargs()
    assert kwargs["model"] == "groq/openai/gpt-oss-120b"
    assert kwargs["num_retries"] == 0


def test_or_query_matches_any_term() -> None:
    assert or_query("What was Apple's revenue, or net sales?") == (
        "What or was or Apple or s or revenue or net or sales"
    )
    assert or_query("?!") == ""


async def test_litellm_errors_propagate_from_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    async def timeout(*args: object, **kwargs: object) -> None:
        raise litellm.exceptions.Timeout("slow", model="m", llm_provider="fake")

    monkeypatch.setattr(litellm, "acompletion", timeout)
    chain = answer_prompt() | litellm_stream(answer_llm(Settings(llm_provider="fake")))
    with pytest.raises(litellm.exceptions.Timeout):
        async for _ in chain.astream({"context": "", "question": "q"}):
            pass


async def test_stream_normalizes_lenticular_citation_brackets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deltas = [
        "Sales were $1 million ",
        "\N{LEFT BLACK LENTICULAR BRACKET}",
        "2",
        "\N{RIGHT BLACK LENTICULAR BRACKET}.",
    ]

    class Chunk:
        def __init__(self, text: str) -> None:
            delta = type("Delta", (), {"content": text})()
            self.choices = [type("Choice", (), {"delta": delta})()]

    async def fake_stream() -> AsyncIterator[Chunk]:
        for d in deltas:
            yield Chunk(d)

    async def acompletion(*args: object, **kwargs: object) -> AsyncIterator[Chunk]:
        return fake_stream()

    monkeypatch.setattr(litellm, "acompletion", acompletion)
    chain = answer_prompt() | litellm_stream(answer_llm(Settings(llm_provider="fake")))
    out = [p async for p in chain.astream({"context": "", "question": "q"})]
    assert "".join(out) == "Sales were $1 million [2]."
