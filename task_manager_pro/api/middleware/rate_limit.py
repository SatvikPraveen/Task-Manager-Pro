"""
api/middleware/rate_limit.py

Per-client sliding-window rate limiting for the unauthenticated auth
endpoints (login/register), which are the natural targets for credential
stuffing and account-creation abuse.

Two interchangeable limiters implement the ``RateLimiter`` protocol:

* ``SlidingWindowRateLimiter`` – an in-memory ``deque`` of timestamps per
  client key. Correct for a single process; behind N replicas it degrades
  to N× the configured limit.
* ``RedisSlidingWindowRateLimiter`` – a sorted set per key, updated by a
  Lua script so the check-and-record step is atomic across replicas.

Responses that exceed the budget are ``429`` with a ``Retry-After`` header
and the ``X-RateLimit-*`` headers are set on every limited route so clients
can back off before hitting the wall.
"""

from __future__ import annotations

import json
import math
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable
from typing import Any, Optional, Protocol

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

Clock = Callable[[], float]


class RateLimiter(Protocol):
    limit: int

    def check(self, key: str) -> tuple[bool, int, float]:
        """Record an event for ``key`` if allowed; return ``(allowed, remaining, retry_after_seconds)``."""


class SlidingWindowRateLimiter:
    """Allow at most ``limit`` events per ``window_seconds`` per key."""

    def __init__(
        self, limit: int, window_seconds: float = 60.0, *, clock: Clock = time.monotonic, max_keys: int = 10_000
    ) -> None:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        self.limit = limit
        self.window = float(window_seconds)
        self._clock = clock
        self._max_keys = max_keys
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        events = self._events.setdefault(key, deque())
        cutoff = now - self.window
        while events and events[0] <= cutoff:
            events.popleft()
        return events

    def check(self, key: str) -> tuple[bool, int, float]:
        """
        Record an event for ``key`` if allowed.

        Returns ``(allowed, remaining, retry_after_seconds)``.
        """
        now = self._clock()
        with self._lock:
            events = self._prune(key, now)
            if len(events) >= self.limit:
                retry_after = max(0.0, events[0] + self.window - now)
                return False, 0, retry_after
            events.append(now)
            if len(self._events) > self._max_keys:
                self._evict_idle(now)
            return True, self.limit - len(events), 0.0

    def _evict_idle(self, now: float) -> None:
        cutoff = now - self.window
        for key in [k for k, ev in self._events.items() if not ev or ev[-1] <= cutoff]:
            del self._events[key]

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


# Atomic sliding window: prune, count, and either reject (returning the wait
# until the oldest event leaves the window) or record the new event.
_REDIS_SCRIPT = """
local key    = KEYS[1]
local now    = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit  = tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
if count >= limit then
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  return {0, 0, tostring(tonumber(oldest[2]) + window - now)}
end
redis.call('ZADD', key, now, ARGV[4])
redis.call('PEXPIRE', key, ARGV[5])
return {1, limit - count - 1, '0'}
"""


class RedisSlidingWindowRateLimiter:
    """Sliding window shared across processes via Redis (requires the ``redis`` package)."""

    def __init__(
        self,
        limit: int,
        window_seconds: float,
        client: Any,
        *,
        prefix: str = "tmp:ratelimit:",
        clock: Clock = time.time,
    ) -> None:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        self.limit = limit
        self.window = float(window_seconds)
        self._client = client
        self._prefix = prefix
        self._clock = clock
        self._script = client.register_script(_REDIS_SCRIPT)
        self._ttl_ms = str(math.ceil(self.window * 1000) + 1000)

    def check(self, key: str) -> tuple[bool, int, float]:
        now = self._clock()
        allowed, remaining, retry_after = self._script(
            keys=[self._prefix + key],
            args=[repr(now), repr(self.window), self.limit, f"{now!r}:{uuid.uuid4().hex}", self._ttl_ms],
        )
        return bool(int(allowed)), int(remaining), max(0.0, float(retry_after))

    def reset(self, key: Optional[str] = None) -> None:
        if key is not None:
            self._client.delete(self._prefix + key)
            return
        for k in self._client.scan_iter(match=self._prefix + "*"):
            self._client.delete(k)


def _client_key(scope: Scope) -> str:
    """Prefer the first X-Forwarded-For hop; fall back to the socket peer."""
    for name, value in scope.get("headers", []):
        if name == b"x-forwarded-for":
            first = value.decode("latin-1").split(",")[0].strip()
            if first:
                return first
    client = scope.get("client")
    return client[0] if client else "unknown"


class RateLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        limiter: RateLimiter,
        paths: tuple[str, ...],
        *,
        methods: tuple[str, ...] = ("POST",),
        key_func: Optional[Callable[[Scope], str]] = None,
    ) -> None:
        self.app = app
        self.limiter = limiter
        self.paths = paths
        self.methods = methods
        self.key_func = key_func or _client_key

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in self.methods or scope.get("path") not in self.paths:
            await self.app(scope, receive, send)
            return

        allowed, remaining, retry_after = self.limiter.check(self.key_func(scope))
        if not allowed:
            body = json.dumps({"detail": "Too many requests. Please retry later."}).encode()
            headers = [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"retry-after", str(max(1, int(retry_after + 0.999))).encode()),
                (b"x-ratelimit-limit", str(self.limiter.limit).encode()),
                (b"x-ratelimit-remaining", b"0"),
            ]
            await send({"type": "http.response.start", "status": 429, "headers": headers})
            await send({"type": "http.response.body", "body": body})
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                hdrs = MutableHeaders(scope=message)
                hdrs["X-RateLimit-Limit"] = str(self.limiter.limit)
                hdrs["X-RateLimit-Remaining"] = str(remaining)
            await send(message)

        await self.app(scope, receive, send_wrapper)
