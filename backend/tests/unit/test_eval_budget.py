from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from docqa.evals.budget import (
    BudgetExhaustedError,
    Ledger,
    Limits,
    ModelBudget,
    is_daily_limit,
    retry_after_seconds,
)
from docqa.evals.client import BudgetedClient, Completion
from docqa.generation.llm import LLMSpec

LIMITS = Limits(requests_per_day=3, tokens_per_day=1_000, tokens_per_minute=500,
                min_interval_seconds=1.0)  # fmt: skip


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def _budget(
    tmp_path: Path, day: str = "2026-11-17", limits: Limits = LIMITS
) -> tuple[ModelBudget, FakeTime]:
    t = FakeTime()
    return ModelBudget("m", limits, Ledger(tmp_path, lambda: day), clock=t.clock, sleep=t.sleep), t


async def test_daily_budgets_persist_per_day(tmp_path: Path) -> None:
    budget, _ = _budget(tmp_path)
    await budget.acquire(100)
    budget.record(400)
    # A new process on the same day sees the same usage.
    again, _ = _budget(tmp_path)
    assert again.remaining() == (2, 600)
    with pytest.raises(BudgetExhaustedError, match="token budget"):
        await again.acquire(700)
    # Tomorrow starts fresh.
    tomorrow, _ = _budget(tmp_path, day="2026-11-18")
    assert tomorrow.remaining() == (3, 1_000)


async def test_request_budget_exhausted(tmp_path: Path) -> None:
    budget, _ = _budget(tmp_path)
    for _ in range(3):
        await budget.acquire(1)
        budget.record(1)
    with pytest.raises(BudgetExhaustedError, match="request budget"):
        await budget.acquire(1)


async def test_spacing_and_tokens_per_minute(tmp_path: Path) -> None:
    budget, t = _budget(tmp_path, limits=Limits(100, 100_000, 500, 1.0))
    await budget.acquire(300)
    budget.record(300)
    assert t.slept == []
    await budget.acquire(100)  # fits the minute, but must wait the spacing interval
    assert t.slept == [1.0]
    budget.record(100)
    await budget.acquire(300)  # 400 + 300 > 500: wait until the first call leaves the window
    assert t.now >= 60.0


def test_retry_after_parsing() -> None:
    class Resp:
        headers = {"retry-after": "12"}

    class WithHeaderError(Exception):
        response = Resp()

    assert retry_after_seconds(WithHeaderError("x")) == 12.0
    assert retry_after_seconds(Exception("Please try again in 7.5s.")) == 7.5
    assert retry_after_seconds(Exception("Please try again in 1m2.5s.")) == 62.5
    assert retry_after_seconds(Exception("Please try again in 300ms.")) == 0.3
    assert retry_after_seconds(Exception("nope")) is None
    assert is_daily_limit(Exception("Rate limit reached on tokens per day (TPD): Limit 200000"))
    assert not is_daily_limit(Exception("on tokens per minute (TPM): Limit 8000"))


class RateLimitError(Exception):
    status_code = 429


SPEC = LLMSpec("groq", "m", 0.0, 100, 10, None, None)


async def test_client_retries_429_then_records_usage(tmp_path: Path) -> None:
    budget, t = _budget(tmp_path, limits=Limits(10, 100_000, 100_000, 0))
    calls: list[int] = []

    async def complete(spec: LLMSpec, messages: Any) -> Completion:
        calls.append(1)
        if len(calls) == 1:
            raise RateLimitError("on tokens per minute (TPM). Please try again in 3s.")
        return Completion("ok", 40, 10)

    client = BudgetedClient({"groq/m": budget}, complete, sleep=t.sleep)
    result = await client.complete(SPEC, [{"role": "user", "content": "hi"}])
    assert result.text == "ok"
    assert len(calls) == 2
    assert t.slept == [3.5]
    assert budget.ledger.used("m") == (2, 50)  # the rejected request counts as a request


async def test_client_stops_on_provider_daily_limit(tmp_path: Path) -> None:
    budget, t = _budget(tmp_path)

    async def complete(spec: LLMSpec, messages: Any) -> Completion:
        raise RateLimitError("Rate limit reached on requests per day (RPD)")

    client = BudgetedClient({"groq/m": budget}, complete, sleep=t.sleep)
    with pytest.raises(BudgetExhaustedError):
        await client.complete(SPEC, [{"role": "user", "content": "hi"}])


async def test_client_passes_other_errors_through(tmp_path: Path) -> None:
    budget, _t = _budget(tmp_path)

    async def complete(spec: LLMSpec, messages: Any) -> Completion:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await BudgetedClient({"groq/m": budget}, complete).complete(SPEC, [])
