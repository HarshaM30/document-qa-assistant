"""Redis sliding-window rate limiter.

Each window is a sorted set of request timestamps. A Lua script trims expired entries,
checks every window, and records the request in all of them only if none is full, so a
rejected request never consumes quota and concurrent requests can't overshoot.
"""

from __future__ import annotations

import math
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from redis.asyncio import Redis

# KEYS: one sorted set per window. ARGV: now_ms, member, then (window_ms, limit) per key.
# Returns 0 when allowed, otherwise milliseconds until the fullest window frees a slot.
_SCRIPT = """
local now = tonumber(ARGV[1])
local member = ARGV[2]
local wait = 0
for i, key in ipairs(KEYS) do
  local window = tonumber(ARGV[1 + 2 * i])
  local limit = tonumber(ARGV[2 + 2 * i])
  redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
  if redis.call('ZCARD', key) >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local w = tonumber(oldest[2]) + window - now
    if w > wait then wait = w end
  end
end
if wait > 0 then return wait end
for i, key in ipairs(KEYS) do
  redis.call('ZADD', key, now, member)
  redis.call('PEXPIRE', key, tonumber(ARGV[1 + 2 * i]))
end
return 0
"""


@dataclass(frozen=True)
class Window:
    name: str
    seconds: int
    limit: int

    def __post_init__(self) -> None:
        if self.seconds <= 0 or self.limit <= 0:
            raise ValueError("window seconds and limit must be positive")


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int = 0


class SlidingWindowLimiter:
    def __init__(
        self,
        redis: Redis,
        prefix: str,
        windows: Sequence[Window],
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not windows:
            raise ValueError("at least one window is required")
        self.redis = redis
        self.prefix = prefix
        self.windows = list(windows)
        self.clock = clock
        self._script = redis.register_script(_SCRIPT)

    async def hit(self, subject: str) -> RateLimitResult:
        now_ms = int(self.clock() * 1000)
        keys = [f"{self.prefix}:{subject}:{w.name}" for w in self.windows]
        args: list[int | str] = [now_ms, f"{now_ms}:{uuid.uuid4().hex}"]
        for w in self.windows:
            args += [w.seconds * 1000, w.limit]
        wait_ms = int(await self._script(keys=keys, args=args))
        if wait_ms <= 0:
            return RateLimitResult(allowed=True)
        return RateLimitResult(allowed=False, retry_after_seconds=max(1, math.ceil(wait_ms / 1000)))
