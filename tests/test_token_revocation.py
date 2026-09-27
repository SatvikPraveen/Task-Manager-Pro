"""
tests/test_token_revocation.py

Denylist unit tests (in-memory with a fake clock; Redis when REDIS_URL is
set), the Redis rate limiter, and API tests for logout and token rotation.
"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from task_manager_pro.api.main import app
from task_manager_pro.storage.database import Base, engine
from task_manager_pro.utils.token_denylist import InMemoryTokenDenylist
from tests.helpers import auth_headers


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_in_memory_denylist_expires_entries_and_ignores_nonpositive_ttl():
    clock = FakeClock()
    denylist = InMemoryTokenDenylist(clock=clock, prune_every=1)
    denylist.revoke("a", 10)
    denylist.revoke("b", 0)
    denylist.revoke("c", -5)
    assert denylist.is_revoked("a") and not denylist.is_revoked("b") and not denylist.is_revoked("c")
    clock.now += 10
    assert not denylist.is_revoked("a")
    assert len(denylist) == 0

    # Pruning sweeps expired keys that were never queried again.
    denylist.revoke("x", 1)
    clock.now += 5
    denylist.revoke("y", 1)  # every revoke prunes (prune_every=1)
    assert len(denylist) == 1 and denylist.is_revoked("y")


# --------------------------------------------------------------------------- #
# Redis-backed variants (only when a server is available)                     #
# --------------------------------------------------------------------------- #
@pytest.fixture
def redis_client():
    url = os.environ.get("REDIS_URL")
    if not url:
        pytest.skip("REDIS_URL not set")
    redis = pytest.importorskip("redis")
    client = redis.Redis.from_url(url, decode_responses=True)
    try:
        client.ping()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Redis unreachable: {exc}")
    return client


def test_redis_denylist(redis_client):
    from task_manager_pro.utils.token_denylist import RedisTokenDenylist

    denylist = RedisTokenDenylist(redis_client, prefix=f"test:{uuid.uuid4().hex}:")
    jti = uuid.uuid4().hex
    assert not denylist.is_revoked(jti)
    denylist.revoke(jti, 30)
    assert denylist.is_revoked(jti)
    denylist.revoke("never", 0)
    assert not denylist.is_revoked("never")


def test_redis_rate_limiter_sliding_window(redis_client):
    from task_manager_pro.api.middleware import RedisSlidingWindowRateLimiter

    clock = FakeClock()
    limiter = RedisSlidingWindowRateLimiter(3, 60, redis_client, prefix=f"test:{uuid.uuid4().hex}:", clock=clock)
    key = "client-1"
    for expected_remaining in (2, 1, 0):
        allowed, remaining, _ = limiter.check(key)
        assert allowed and remaining == expected_remaining
        clock.now += 10
    allowed, remaining, retry_after = limiter.check(key)  # t=30
    assert not allowed and remaining == 0 and retry_after == pytest.approx(30.0, abs=0.01)
    clock.now += 31  # t=61: first event expired
    allowed, remaining, _ = limiter.check(key)
    assert allowed and remaining == 0
    assert limiter.check("other")[0]
    limiter.reset(key)
    assert limiter.check(key)[1] == 2
    limiter.reset()


# --------------------------------------------------------------------------- #
# API                                                                         #
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def test_logout_revokes_only_the_presented_token(client):
    headers = auth_headers(client, "alice")
    other = auth_headers(client, "alice")  # a second session for the same user
    assert client.get("/api/users/me", headers=headers).status_code == 200

    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    r = client.get("/api/users/me", headers=headers)
    assert r.status_code == 401 and r.json()["detail"] == "Token has been revoked"
    assert client.post("/api/auth/logout", headers=headers).status_code == 401
    assert client.get("/api/users/me", headers=other).status_code == 200


def test_refresh_rotates_and_revokes_old_token(client):
    headers = auth_headers(client, "alice")
    r = client.post("/api/auth/refresh-token", headers=headers)
    assert r.status_code == 200
    new_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/users/me", headers=headers).status_code == 401
    assert client.get("/api/users/me", headers=new_headers).status_code == 200
    # Replaying the old token for another refresh fails too.
    assert client.post("/api/auth/refresh-token", headers=headers).status_code == 401
