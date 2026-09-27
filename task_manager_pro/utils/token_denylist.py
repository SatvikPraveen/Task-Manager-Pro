"""
utils/token_denylist.py

Revocation of otherwise-valid JWTs.

Access tokens are stateless, so logging out or rotating a token requires a
small piece of shared state: the ``jti`` of every token revoked before its
natural expiry. Entries only need to live until the token's ``exp``, after
which the signature check rejects it anyway, so both backends store a TTL.

* :class:`InMemoryTokenDenylist` – single-process, zero dependencies.
* :class:`RedisTokenDenylist`    – shared between replicas (``SET ... PX``).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any, Protocol

Clock = Callable[[], float]


class TokenDenylist(Protocol):
    def revoke(self, jti: str, ttl_seconds: float) -> None:
        """Mark ``jti`` as revoked for ``ttl_seconds`` (no-op if ``ttl_seconds <= 0``)."""

    def is_revoked(self, jti: str) -> bool: ...


class InMemoryTokenDenylist:
    """Dictionary of ``jti -> expiry`` with lazy pruning; thread-safe."""

    def __init__(self, *, clock: Clock = time.monotonic, prune_every: int = 256) -> None:
        self._clock = clock
        self._expiry: dict[str, float] = {}
        self._lock = threading.Lock()
        self._ops = 0
        self._prune_every = prune_every

    def revoke(self, jti: str, ttl_seconds: float) -> None:
        if ttl_seconds <= 0:
            return
        with self._lock:
            self._expiry[jti] = self._clock() + ttl_seconds
            self._maybe_prune()

    def is_revoked(self, jti: str) -> bool:
        with self._lock:
            expiry = self._expiry.get(jti)
            if expiry is None:
                return False
            if expiry <= self._clock():
                del self._expiry[jti]
                return False
            return True

    def __len__(self) -> int:
        with self._lock:
            return len(self._expiry)

    def _maybe_prune(self) -> None:
        self._ops += 1
        if self._ops % self._prune_every:
            return
        now = self._clock()
        for key in [k for k, exp in self._expiry.items() if exp <= now]:
            del self._expiry[key]


class RedisTokenDenylist:
    """Backed by Redis string keys with a millisecond TTL."""

    def __init__(self, client: Any, *, prefix: str = "tmp:revoked:") -> None:
        self._client = client
        self._prefix = prefix

    def revoke(self, jti: str, ttl_seconds: float) -> None:
        ttl_ms = int(ttl_seconds * 1000)
        if ttl_ms <= 0:
            return
        self._client.set(self._prefix + jti, "1", px=ttl_ms)

    def is_revoked(self, jti: str) -> bool:
        return bool(self._client.exists(self._prefix + jti))
