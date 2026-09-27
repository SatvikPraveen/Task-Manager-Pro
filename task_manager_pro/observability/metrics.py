"""
observability/metrics.py

Prometheus instrumentation.

Two metrics, labelled by the *route template* (``/api/tasks/{task_id}``)
rather than the concrete path so that cardinality stays bounded:

* ``http_requests_total{method,route,status}``
* ``http_request_duration_seconds{method,route}``  (histogram)

The exposition endpoint is mounted at ``/metrics`` by the application when
``METRICS_ENABLED`` is true.
"""

from __future__ import annotations

import time
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match, Route
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


def _route_template(scope: Scope) -> str:
    """Return the matched route's path template, or ``unmatched``."""
    app = scope.get("app")
    if app is None:
        return "unmatched"
    for route in app.router.routes:
        if isinstance(route, Route):
            match, _ = route.matches(scope)
            if match == Match.FULL:
                return route.path
    return "unmatched"


class MetricsMiddleware:
    """Pure-ASGI middleware recording count and latency per route."""

    def __init__(self, app: ASGIApp, skip_paths: tuple[str, ...] = ("/metrics",)) -> None:
        self.app = app
        self.skip_paths = skip_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in self.skip_paths:
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        route = _route_template(scope)
        start = time.perf_counter()
        status_holder = {"status": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            REQUEST_LATENCY.labels(method, route).observe(time.perf_counter() - start)
            REQUEST_COUNT.labels(method, route, str(status_holder["status"])).inc()


def metrics_endpoint(_: Request) -> Response:
    """Starlette endpoint serving the Prometheus text exposition format."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


__all__ = ["MetricsMiddleware", "metrics_endpoint", "REQUEST_COUNT", "REQUEST_LATENCY"]
