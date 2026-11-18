"""Daily request/token budgets and a tokens-per-minute limiter, per model.

Usage is persisted to a small ledger file per UTC day, so separate runs on the same day
share one budget. Each model (answer, judge) has its own budget, matching Groq's per-model
limits. When a budget would be exceeded the run stops with `BudgetExhaustedError` and resumes
from its checkpoint on the next day.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from docqa.config import REPO_ROOT, Settings

LEDGER_DIR = REPO_ROOT / "evals" / ".budget"
WINDOW_SECONDS = 60.0


class BudgetExhaustedError(Exception):
    def __init__(self, model: str, reason: str) -> None:
        super().__init__(f"{model}: {reason}")
        self.model = model
        self.reason = reason


@dataclass(frozen=True)
class Limits:
    requests_per_day: int
    tokens_per_day: int
    tokens_per_minute: int
    min_interval_seconds: float

    @classmethod
    def from_settings(cls, settings: Settings) -> Limits:
        return cls(
            requests_per_day=settings.eval_daily_request_budget,
            tokens_per_day=settings.eval_daily_token_budget,
            tokens_per_minute=settings.eval_tokens_per_minute,
            min_interval_seconds=settings.eval_request_interval_seconds,
        )


def utc_day() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


class Ledger:
    """Requests and tokens used per model today, stored as JSON in `<dir>/<UTC day>.json`."""

    def __init__(self, directory: Path = LEDGER_DIR, day: Callable[[], str] = utc_day) -> None:
        self.directory = directory
        self._day = day

    @property
    def path(self) -> Path:
        return self.directory / f"{self._day()}.json"

    def _read(self) -> dict[str, dict[str, int]]:
        if not self.path.exists():
            return {}
        data: dict[str, dict[str, int]] = json.loads(self.path.read_text())
        return data

    def used(self, model: str) -> tuple[int, int]:
        entry = self._read().get(model, {})
        return entry.get("requests", 0), entry.get("tokens", 0)

    def add(self, model: str, requests: int, tokens: int) -> None:
        data = self._read()
        entry = data.setdefault(model, {"requests": 0, "tokens": 0})
        entry["requests"] += requests
        entry["tokens"] += tokens
        self.directory.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
        tmp.replace(self.path)


class ModelBudget:
    def __init__(
        self,
        model: str,
        limits: Limits,
        ledger: Ledger,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ) -> None:
        self.model = model
        self.limits = limits
        self.ledger = ledger
        self._clock = clock
        self._sleep = sleep
        self._window: deque[tuple[float, int]] = deque()
        self._last_call: float | None = None

    def remaining(self) -> tuple[int, int]:
        requests, tokens = self.ledger.used(self.model)
        return (
            self.limits.requests_per_day - requests,
            self.limits.tokens_per_day - tokens,
        )

    def _window_tokens(self, now: float) -> int:
        while self._window and now - self._window[0][0] >= WINDOW_SECONDS:
            self._window.popleft()
        return sum(t for _, t in self._window)

    async def acquire(self, estimated_tokens: int) -> None:
        """Wait until a call of about `estimated_tokens` fits; raise if today's budget can't."""
        requests_left, tokens_left = self.remaining()
        if requests_left < 1:
            raise BudgetExhaustedError(
                self.model, f"daily request budget used ({self.limits.requests_per_day})"
            )
        if estimated_tokens > tokens_left:
            raise BudgetExhaustedError(
                self.model,
                f"daily token budget nearly used ({tokens_left:,} of "
                f"{self.limits.tokens_per_day:,} left; next call needs ~{estimated_tokens:,})",
            )
        if self._last_call is not None:
            wait = self.limits.min_interval_seconds - (self._clock() - self._last_call)
            if wait > 0:
                await self._sleep(wait)
        tpm = self.limits.tokens_per_minute
        while self._window and self._window_tokens(self._clock()) + estimated_tokens > tpm:
            oldest = self._window[0][0]
            await self._sleep(max(0.0, WINDOW_SECONDS - (self._clock() - oldest)) + 0.05)

    def record(self, tokens: int) -> None:
        now = self._clock()
        self._last_call = now
        self._window.append((now, tokens))
        self.ledger.add(self.model, 1, tokens)


# --- Rate-limit errors -------------------------------------------------------------------

_TRY_AGAIN = re.compile(r"try again in\s+(?:(\d+)m)?\s*([\d.]+)\s*(ms|s)?", re.I)
_DAILY = re.compile(r"per day|\bRPD\b|\bTPD\b", re.I)


def retry_after_seconds(exc: BaseException) -> float | None:
    """Seconds to wait from a 429: the `retry-after` header, else "try again in 7.5s"."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or {}
    value = headers.get("retry-after") if hasattr(headers, "get") else None
    if value:
        try:
            return max(0.0, float(value))
        except ValueError:
            pass
    match = _TRY_AGAIN.search(str(exc))
    if not match:
        return None
    minutes, amount, unit = match.groups()
    seconds = float(amount) / 1000 if unit == "ms" else float(amount)
    return seconds + 60 * int(minutes or 0)


def is_daily_limit(exc: BaseException) -> bool:
    return bool(_DAILY.search(str(exc)))
