"""Deterministic extractive LLM, registered with LiteLLM as provider `fake`.

It reads the numbered passages and the question out of the prompt, picks the sentence
that shares the most content words with the question, and answers with that sentence plus
its `[n]` marker. With no overlap at all it returns the refusal sentence. Output is streamed
word by word, so tests, CI, E2E, and load tests exercise the same streaming path as a real
model without any network access or API key.
"""

from __future__ import annotations

import asyncio
import re
import threading
import time
from collections.abc import AsyncIterator, Iterator
from typing import Any

import litellm
from litellm.llms.custom_llm import CustomLLM
from litellm.types.utils import GenericStreamingChunk, ModelResponse

from docqa.generation.prompts import CONTEXT_LABEL, QUESTION_LABEL, REFUSAL_SENTENCE

FAKE_PROVIDER = "fake"

_PASSAGE = re.compile(r"^\[(\d+)\] [^\n]*\n(.*?)(?=\n\n\[\d+\] |\Z)", re.MULTILINE | re.DOTALL)
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "did",
        "do",
        "does",
        "for",
        "from",
        "has",
        "have",
        "how",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "this",
        "to",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
    ]
)


def _content_words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOPWORDS and len(w) > 1}


def _last_user_message(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content") or "")
    return ""


def extractive_answer(messages: list[dict[str, Any]]) -> str:
    prompt = _last_user_message(messages)
    context, _, question = prompt.rpartition(QUESTION_LABEL)
    context = context.removeprefix(CONTEXT_LABEL).strip()
    wanted = _content_words(question)

    best: tuple[int, int, str] | None = None  # (overlap, -passage number, sentence)
    for match in _PASSAGE.finditer(context):
        number, body = int(match.group(1)), match.group(2)
        for sentence in _SENTENCE.split(body):
            sentence = sentence.strip()
            overlap = len(wanted & _content_words(sentence))
            if overlap and (best is None or (overlap, -number) > best[:2]):
                best = (overlap, -number, sentence)
    if best is None:
        return REFUSAL_SENTENCE
    return f"{best[2]} [{-best[1]}]"


def _words(text: str) -> Iterator[str]:
    parts = text.split(" ")
    for i, part in enumerate(parts):
        yield part if i == len(parts) - 1 else part + " "


class FakeLLM(CustomLLM):
    """Counts calls so tests can assert that a refusal never reached the model."""

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self.calls = 0
        # Pause between streamed words so the UI's incremental rendering is observable.
        self.token_delay_seconds = 0.0

    def _record(self) -> None:
        with self._lock:
            self.calls += 1

    def reset(self) -> None:
        with self._lock:
            self.calls = 0

    def _complete(self, model: str, messages: list[Any]) -> ModelResponse:
        self._record()
        return ModelResponse(
            model=model,
            created=int(time.time()),
            choices=[{"message": {"role": "assistant", "content": extractive_answer(messages)}}],
        )

    def completion(self, model: str, messages: list[Any], *args: Any, **kwargs: Any) -> Any:
        return self._complete(model, messages)

    async def acompletion(self, model: str, messages: list[Any], *args: Any, **kwargs: Any) -> Any:
        return self._complete(model, messages)

    def _chunks(self, messages: list[Any]) -> Iterator[GenericStreamingChunk]:
        self._record()
        words = list(_words(extractive_answer(messages)))
        for i, word in enumerate(words):
            last = i == len(words) - 1
            yield GenericStreamingChunk(
                text=word,
                tool_use=None,
                is_finished=last,
                finish_reason="stop" if last else "",
                usage=None,
                index=0,
            )

    def streaming(self, model: str, messages: list[Any], *args: Any, **kwargs: Any) -> Any:
        yield from self._chunks(messages)

    async def astreaming(  # type: ignore[override]
        self, model: str, messages: list[Any], *args: Any, **kwargs: Any
    ) -> AsyncIterator[GenericStreamingChunk]:
        for i, chunk in enumerate(self._chunks(messages)):
            if i and self.token_delay_seconds:
                await asyncio.sleep(self.token_delay_seconds)
            yield chunk


FAKE_LLM = FakeLLM()


def register_fake_provider(token_delay_ms: float = 0) -> FakeLLM:
    """Make `fake/<anything>` resolve to FAKE_LLM (idempotent)."""
    FAKE_LLM.token_delay_seconds = token_delay_ms / 1000
    providers = list(litellm.custom_provider_map or [])
    if not any(p.get("provider") == FAKE_PROVIDER for p in providers):
        providers.append({"provider": FAKE_PROVIDER, "custom_handler": FAKE_LLM})
        litellm.custom_provider_map = providers
    return FAKE_LLM
