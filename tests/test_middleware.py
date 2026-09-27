"""
tests/test_middleware.py

Unit tests for the rate limiter, and integration tests for the request-ID,
security-header, metrics and rate-limit middleware wired into a minimal app.
"""

from __future__ import annotations

import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from task_manager_pro.api.main import app as real_app
from task_manager_pro.api.middleware import (
    RateLimitMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
    SlidingWindowRateLimiter,
)
from task_manager_pro.observability.logging import JsonFormatter, RequestIdFilter, request_id_var
from task_manager_pro.observability.metrics import MetricsMiddleware, metrics_endpoint


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_limiter_allows_up_to_limit_then_blocks_until_window_slides():
    clock = FakeClock()
    limiter = SlidingWindowRateLimiter(3, 60, clock=clock)
    for expected_remaining in (2, 1, 0):  # events at t=0, 10, 20
        allowed, remaining, _ = limiter.check("k")
        assert allowed and remaining == expected_remaining
        clock.now += 10
    # t=30: three events inside the window → blocked until the first (t=0) expires at t=60.
    allowed, remaining, retry_after = limiter.check("k")
    assert not allowed and remaining == 0 and retry_after == pytest.approx(30.0)

    clock.now += 29  # t=59: still blocked
    assert limiter.check("k")[0] is False
    clock.now += 2  # t=61: the t=0 event has slid out
    allowed, remaining, _ = limiter.check("k")
    assert allowed and remaining == 0


def test_limiter_keys_are_independent_and_reset_works():
    limiter = SlidingWindowRateLimiter(1, 60, clock=FakeClock())
    assert limiter.check("a")[0] and limiter.check("b")[0]
    assert not limiter.check("a")[0]
    limiter.reset()
    assert limiter.check("a")[0]


def test_limiter_rejects_nonpositive_limit():
    with pytest.raises(ValueError):
        SlidingWindowRateLimiter(0)


@pytest.fixture
def mini_client():
    mini = FastAPI()

    @mini.post("/login")
    async def login():
        return {"ok": True}

    @mini.get("/boom")
    async def boom():
        raise RuntimeError("kaboom")

    @mini.get("/items/{item_id}")
    async def item(item_id: str):
        return {"id": item_id}

    mini.add_route("/metrics", metrics_endpoint, methods=["GET"])
    mini.add_middleware(RateLimitMiddleware, limiter=SlidingWindowRateLimiter(2, 60), paths=("/login",))
    mini.add_middleware(MetricsMiddleware)
    mini.add_middleware(SecurityHeadersMiddleware)
    mini.add_middleware(RequestIdMiddleware)
    return TestClient(mini, raise_server_exceptions=False)


def test_request_id_generated_and_echoed(mini_client):
    r = mini_client.get("/items/1")
    assert r.status_code == 200
    assert len(r.headers["X-Request-ID"]) == 32
    assert float(r.headers["X-Process-Time"]) >= 0

    r = mini_client.get("/items/1", headers={"X-Request-ID": "trace-abc-123"})
    assert r.headers["X-Request-ID"] == "trace-abc-123"


def test_security_headers_present(mini_client):
    r = mini_client.get("/items/1")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Cache-Control"] == "no-store"
    assert "default-src 'none'" in r.headers["Content-Security-Policy"]


def test_docs_pages_are_exempt_from_csp():
    client = TestClient(real_app)
    r = client.get("/api/docs")
    assert r.status_code == 200
    assert "Content-Security-Policy" not in r.headers
    assert r.headers["X-Frame-Options"] == "DENY"


def test_rate_limit_returns_429_with_retry_after(mini_client):
    assert mini_client.post("/login").status_code == 200
    second = mini_client.post("/login")
    assert second.status_code == 200 and second.headers["X-RateLimit-Remaining"] == "0"
    third = mini_client.post("/login")
    assert third.status_code == 429
    assert int(third.headers["Retry-After"]) >= 1
    assert third.json()["detail"].startswith("Too many requests")
    # Other paths are not limited.
    assert mini_client.get("/items/1").status_code == 200


def test_rate_limit_keys_on_forwarded_for(mini_client):
    for ip in ("10.0.0.1", "10.0.0.2"):
        for _ in range(2):
            assert mini_client.post("/login", headers={"X-Forwarded-For": f"{ip}, 1.2.3.4"}).status_code == 200
    assert mini_client.post("/login", headers={"X-Forwarded-For": "10.0.0.1"}).status_code == 429
    assert mini_client.post("/login", headers={"X-Forwarded-For": "10.0.0.3"}).status_code == 200


def test_metrics_use_route_template_not_concrete_path(mini_client):
    mini_client.get("/items/42")
    mini_client.get("/items/43")
    body = mini_client.get("/metrics").text
    assert 'route="/items/{item_id}"' in body
    assert "/items/42" not in body
    assert "http_request_duration_seconds_bucket" in body


def test_unhandled_exception_is_counted_as_500(mini_client):
    r = mini_client.get("/boom")
    assert r.status_code == 500
    assert 'route="/boom",status="500"' in mini_client.get("/metrics").text


def test_real_app_returns_json_500_with_request_id(monkeypatch):
    from task_manager_pro.api import dependencies

    def broken():
        raise RuntimeError("db exploded")

    real_app.dependency_overrides[dependencies.get_storage] = broken
    try:
        client = TestClient(real_app, raise_server_exceptions=False)
        r = client.post("/api/auth/register", json={"username": "zed", "password": "securepass123"})
        assert r.status_code == 500
        assert r.json() == {"detail": "Internal server error", "request_id": r.headers["X-Request-ID"]}
    finally:
        real_app.dependency_overrides.clear()


def test_health_reports_database_status():
    r = TestClient(real_app).get("/health")
    assert r.status_code == 200
    assert r.json()["database"] == "ok"


def test_json_formatter_includes_request_id_and_extras():
    token = request_id_var.set("req-1")
    try:
        record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello %s", ("world",), None)
        record.duration_ms = 1.5
        RequestIdFilter().filter(record)
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)
    assert payload["message"] == "hello world"
    assert payload["request_id"] == "req-1"
    assert payload["duration_ms"] == 1.5
    assert payload["level"] == "INFO"
