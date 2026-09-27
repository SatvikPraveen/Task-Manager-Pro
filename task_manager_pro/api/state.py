"""
api/state.py

Factories for the pieces of shared mutable state the API needs (rate-limit
windows and revoked tokens), selected by ``SHARED_STATE_BACKEND``.

``memory`` is the default and correct for one process. ``redis`` makes both
structures shared between replicas; it requires ``REDIS_URL`` and the
``redis`` package (``pip install "task-manager-pro[redis]"``).
"""

from __future__ import annotations

from typing import Any, Optional

from task_manager_pro.api.middleware.rate_limit import (
    RateLimiter,
    RedisSlidingWindowRateLimiter,
    SlidingWindowRateLimiter,
)
from task_manager_pro.config import Settings
from task_manager_pro.utils.token_denylist import InMemoryTokenDenylist, RedisTokenDenylist, TokenDenylist


def build_redis_client(settings: Settings) -> Any:
    """Create a Redis client from ``REDIS_URL`` (imported lazily; optional dependency)."""
    try:
        import redis
    except ImportError as exc:  # pragma: no cover - exercised only without the extra installed
        raise RuntimeError(
            'SHARED_STATE_BACKEND=redis requires the "redis" package: pip install "task-manager-pro[redis]"'
        ) from exc
    return redis.Redis.from_url(settings.redis_url or "", decode_responses=True)


def build_rate_limiter(settings: Settings, client: Optional[Any] = None) -> RateLimiter:
    if settings.shared_state_backend == "redis":
        return RedisSlidingWindowRateLimiter(
            settings.auth_rate_limit_per_minute, 60.0, client or build_redis_client(settings)
        )
    return SlidingWindowRateLimiter(settings.auth_rate_limit_per_minute, 60.0)


def build_token_denylist(settings: Settings, client: Optional[Any] = None) -> TokenDenylist:
    if settings.shared_state_backend == "redis":
        return RedisTokenDenylist(client or build_redis_client(settings))
    return InMemoryTokenDenylist()
