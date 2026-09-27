# 0004 – Pure ASGI middleware; 500s handled where headers can still be set

Date: 2026-09-26 · Status: Accepted

## Context

We wanted every response — including failures — to carry a correlation ID
and timing, and every unhandled exception to be logged with that ID and
returned as JSON without a stack trace. Starlette's `BaseHTTPMiddleware` is
simpler to write but buffers streaming responses and has known
interactions with background tasks; and FastAPI's `@app.exception_handler(Exception)`
runs inside `ServerErrorMiddleware`, which sits *outside* every user
middleware, so headers added by our middleware never reach that response.

## Decision

* All middleware is written as pure ASGI callables (`__call__(scope,
  receive, send)`) wrapping `send` to add headers on `http.response.start`.
* `RequestIdMiddleware` catches unhandled exceptions itself: if no
  response has started it sends a JSON 500 (with `X-Request-ID` and the ID
  in the body), logs with `logger.exception`, and **re-raises** so
  `ServerErrorMiddleware` and test clients still observe the failure.
* Metrics are labelled by the matched route *template* to keep cardinality
  bounded; the template is resolved by matching the scope against the
  router before the request runs.

## Consequences

* No stack traces leak; every 500 is greppable by request ID.
* `TestClient(app, raise_server_exceptions=False)` sees the JSON body,
  while the default `raise_server_exceptions=True` still raises — both
  behaviours are tested.
* Middleware order matters and is documented in `api/main.py`.
