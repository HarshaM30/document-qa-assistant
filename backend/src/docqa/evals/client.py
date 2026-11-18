"""LLM calls for the generation eval: non-streamed, budgeted, and retried on 429s."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from docqa.evals.budget import (
    BudgetExhaustedError,
    ModelBudget,
    is_daily_limit,
    retry_after_seconds,
)
from docqa.generation.citations import normalize_markers
from docqa.generation.llm import LLMSpec

log = logging.getLogger(__name__)

Messages = list[dict[str, Any]]
CHARS_PER_TOKEN = 3.5  # conservative for English prose and numeric tables


@dataclass(frozen=True)
class Completion:
    text: str
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class Completer(Protocol):
    async def __call__(self, spec: LLMSpec, messages: Messages) -> Completion: ...


def estimate_tokens(messages: Messages, completion_allowance: int) -> int:
    chars = sum(len(str(m.get("content", ""))) for m in messages)
    return int(chars / CHARS_PER_TOKEN) + completion_allowance


async def litellm_complete(spec: LLMSpec, messages: Messages) -> Completion:
    import litellm

    response: Any = await litellm.acompletion(messages=messages, **spec.completion_kwargs())
    text = normalize_markers(response.choices[0].message.content or "")
    usage = getattr(response, "usage", None)
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion = int(getattr(usage, "completion_tokens", 0) or 0)
    if not usage:  # providers without usage reporting (the fake one): estimate
        prompt, completion = estimate_tokens(messages, 0), int(len(text) / CHARS_PER_TOKEN)
    return Completion(text, prompt, completion)


def _is_rate_limit(exc: BaseException) -> bool:
    return getattr(exc, "status_code", None) == 429 or type(exc).__name__ == "RateLimitError"


class BudgetedClient:
    """Wraps a completer with one `ModelBudget` per model and 429 handling."""

    def __init__(
        self,
        budgets: dict[str, ModelBudget],
        complete: Completer = litellm_complete,
        *,
        completion_allowance: int = 600,
        max_rate_limit_retries: int = 5,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ) -> None:
        self.budgets = budgets
        self._complete = complete
        self.completion_allowance = completion_allowance
        self.max_retries = max_rate_limit_retries
        self._sleep = sleep

    async def complete(self, spec: LLMSpec, messages: Messages) -> Completion:
        budget = self.budgets[spec.litellm_model]
        estimate = estimate_tokens(messages, self.completion_allowance)
        for attempt in range(self.max_retries + 1):
            await budget.acquire(estimate)
            try:
                result = await self._complete(spec, messages)
            except Exception as exc:
                if not _is_rate_limit(exc):
                    raise
                budget.record(0)  # the rejected request still counts toward requests/day
                if is_daily_limit(exc):
                    raise BudgetExhaustedError(spec.litellm_model, "provider daily limit") from exc
                if attempt == self.max_retries:
                    raise
                wait = retry_after_seconds(exc) or 2.0 * 2**attempt
                log.warning("429 from %s; retrying in %.1fs", spec.litellm_model, wait)
                await self._sleep(wait + 0.5)
                continue
            budget.record(result.total_tokens)
            return result
        raise AssertionError("unreachable")
