"""
api/middleware/request_id.py

Assigns every request a correlation ID.

The incoming ``X-Request-ID`` header is honoured (so upstream proxies can
propagate their own IDs); otherwise a UUID4 is generated. The ID is exposed
to the logging layer through a context variable and echoed back on the
response, together with an ``X-Process-Time`` header (seconds).

Unhandled exceptions are converted here, rather than in Starlette's
outermost ``ServerErrorMiddleware``, so that the 500 response still carries
the correlation headers and the body includes the ID for support lookups.
The exception is re-raised afterwards so the server's own error logging and
test clients still see it.
"""

from __future__ import annotations

import json
import logging
import time
import uuid

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from task_manager_pro.observability.logging import request_id_var

logger = logging.getLogger("task_manager_pro.access")

_MAX_ID_LENGTH = 128


def _incoming_request_id(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"x-request-id":
            candidate = value.decode("latin-1").strip()
            if 0 < len(candidate) <= _MAX_ID_LENGTH and candidate.isprintable():
                return candidate
    return None


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _incoming_request_id(scope) or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        scope.setdefault("state", {})["request_id"] = request_id
        start = time.perf_counter()
        status_holder = {"status": 0}
        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_holder["status"] = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                headers["X-Process-Time"] = f"{time.perf_counter() - start:.6f}"
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception("Unhandled error on %s %s", scope.get("method"), scope.get("path"))
            if not response_started:
                body = json.dumps({"detail": "Internal server error", "request_id": request_id}).encode()
                await send_wrapper(
                    {
                        "type": "http.response.start",
                        "status": 500,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode()),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": body})
            raise
        finally:
            request_id_var.reset(token)
            logger.info(
                "%s %s -> %s",
                scope.get("method"),
                scope.get("path"),
                status_holder["status"],
                extra={
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status": status_holder["status"],
                    "duration_ms": round((time.perf_counter() - start) * 1000, 3),
                    "request_id": request_id,
                },
            )
