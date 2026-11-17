from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from redis.asyncio import Redis

from docqa.ratelimit import SlidingWindowLimiter, Window
from tests.integration.helpers import ask, create_workspace, signup


class Clock:
    def __init__(self) -> None:
        self.now = 1_800_000_000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
async def redis(settings: Any) -> AsyncIterator[Redis]:
    client = Redis.from_url(settings.redis_url)
    yield client
    await client.aclose()


async def test_sliding_window_blocks_then_resets(redis: Redis) -> None:
    clock = Clock()
    limiter = SlidingWindowLimiter(redis, "rl:test", [Window("minute", 60, 3)], clock)
    for _ in range(3):
        assert (await limiter.hit("u1")).allowed
        clock.now += 10  # requests at t=0, 10, 20
    blocked = await limiter.hit("u1")  # t=30
    assert not blocked.allowed
    assert blocked.retry_after_seconds == 30  # the t=0 request leaves the window at t=60

    assert (await limiter.hit("u2")).allowed  # other users are unaffected

    clock.now += 29.5  # t=59.5: still full
    assert not (await limiter.hit("u1")).allowed
    clock.now += 0.5  # t=60: the first request has expired
    assert (await limiter.hit("u1")).allowed
    assert not (await limiter.hit("u1")).allowed  # and the slot is used again


async def test_rejected_requests_do_not_consume_quota(redis: Redis) -> None:
    clock = Clock()
    limiter = SlidingWindowLimiter(redis, "rl:test", [Window("minute", 60, 1)], clock)
    assert (await limiter.hit("u")).allowed
    for _ in range(5):
        clock.now += 5
        assert not (await limiter.hit("u")).allowed
    clock.now += 35  # t=60
    assert (await limiter.hit("u")).allowed


async def test_daily_window_applies_across_minutes(redis: Redis) -> None:
    clock = Clock()
    limiter = SlidingWindowLimiter(
        redis, "rl:test", [Window("minute", 60, 2), Window("day", 86_400, 3)], clock
    )
    assert (await limiter.hit("u")).allowed
    assert (await limiter.hit("u")).allowed
    minute_block = await limiter.hit("u")
    assert not minute_block.allowed
    assert minute_block.retry_after_seconds == 60

    clock.now += 60
    assert (await limiter.hit("u")).allowed  # third of the day
    clock.now += 60
    day_block = await limiter.hit("u")
    assert not day_block.allowed
    assert day_block.retry_after_seconds == 86_400 - 120
    clock.now += 86_400 - 120
    assert (await limiter.hit("u")).allowed


def test_window_validation() -> None:
    with pytest.raises(ValueError, match="positive"):
        Window("minute", 60, 0)


async def test_ask_returns_429_with_retry_after(
    app: FastAPI, client: AsyncClient, other_client: AsyncClient, redis: Redis
) -> None:
    clock = Clock()
    app.state.ask_limiter = SlidingWindowLimiter(
        redis, "ratelimit:ask", [Window("minute", 60, 2)], clock
    )
    await signup(client, "a@example.org")
    workspace = await create_workspace(client)
    for _ in range(2):
        assert (await ask(client, workspace["id"], "Anything?")).status_code == 200
    resp = await ask(client, workspace["id"], "Anything?")
    assert resp.status_code == 429
    assert resp.headers["Retry-After"] == "60"
    assert "Too many questions" in resp.json()["detail"]

    # Limits are per user.
    await signup(other_client, "b@example.org")
    other_ws = await create_workspace(other_client)
    assert (await ask(other_client, other_ws["id"], "Anything?")).status_code == 200

    clock.now += 60
    assert (await ask(client, workspace["id"], "Anything?")).status_code == 200


async def test_default_limits_come_from_settings(app: FastAPI, settings: Any) -> None:
    windows = {w.name: w.limit for w in app.state.ask_limiter.windows}
    assert windows == {
        "minute": settings.rate_limit_questions_per_minute,
        "day": settings.rate_limit_questions_per_day,
    }


async def test_retry_after_is_readable_cross_origin(
    app: FastAPI, client: AsyncClient, redis: Redis, settings: Any
) -> None:
    app.state.ask_limiter = SlidingWindowLimiter(
        redis, "ratelimit:ask", [Window("minute", 60, 1)], Clock()
    )
    await signup(client, "a@example.org")
    workspace = await create_workspace(client)
    origin = {"Origin": settings.frontend_origin}
    assert (await ask(client, workspace["id"], "Anything?")).status_code == 200
    resp = await client.post(
        f"/workspaces/{workspace['id']}/ask", json={"question": "Again?"}, headers=origin
    )
    assert resp.status_code == 429
    assert resp.headers["Access-Control-Allow-Origin"] == settings.frontend_origin
    assert "retry-after" in resp.headers["Access-Control-Expose-Headers"].lower()
