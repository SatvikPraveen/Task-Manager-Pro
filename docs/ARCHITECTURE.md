# Architecture

Task Manager PRO is a small but complete service: a FastAPI REST API and an
argparse CLI over a SQLAlchemy persistence layer, with the cross-cutting
concerns (configuration, security, observability, analytics) factored into
their own packages so each can be tested in isolation.

```
                 ┌────────────────────────────────────────────────────────────┐
  HTTP client ──▶│ RequestId → SecurityHeaders → Metrics → RateLimit → CORS   │  api/middleware, observability
                 └───────────────┬────────────────────────────────────────────┘
                                 ▼
                      ┌─────────────────────┐        ┌───────────────────────┐
                      │  api/routes         │──uses──▶ analytics             │  pure functions:
                      │  auth / tasks / users│        │ urgency, stats        │  no I/O, property-tested
                      └──────────┬──────────┘        └───────────────────────┘
                                 │ Depends(get_storage)
                                 ▼
                      ┌─────────────────────┐        ┌───────────────────────┐
                      │ storage/SQLStorage  │──uses──▶ utils/security        │  bcrypt, JWT
                      │ (repository)        │        └───────────────────────┘
                      └──────────┬──────────┘
                                 │ sessionmaker (injectable)
                                 ▼
                      ┌─────────────────────┐
                      │ SQLAlchemy engine   │  SQLite (dev/test) · PostgreSQL (prod)
                      │ + Alembic history   │
                      └─────────────────────┘

                      ┌─────────────────────┐
                      │ config.Settings     │  single validated source of truth; read lazily everywhere
                      └─────────────────────┘
```

## Packages

| Package | Responsibility | Notes |
|---|---|---|
| `task_manager_pro.config` | Typed, validated settings from env/.env | `get_settings()` is cached; `reset_settings()` for tests |
| `task_manager_pro.api` | FastAPI app factory, routes, dependencies, middleware | `create_app()` builds the stack; `app` is the ASGI entry point |
| `task_manager_pro.storage` | Engine/session factory, ORM models, `SQLStorage` repository | All filtering/sorting/paging in SQL; ORM objects returned detached |
| `task_manager_pro.schemas` | Pydantic v2 request/response models | `from_model()` on every response schema |
| `task_manager_pro.analytics` | Urgency model, per-user calibration, workload statistics | Pure; verified with Hypothesis |
| `task_manager_pro.observability` | Structured logging, Prometheus metrics | Request ID via `contextvars` |
| `task_manager_pro.utils` | bcrypt/JWT helpers, SMTP, CLI helpers | |
| `task_manager_pro.services`, `models`, `cli` | The original JSON-backed CLI | Unchanged behaviour; kept for the `task-manager` command |
| `migrations/` | Alembic environment and revision history | `alembic check` runs in CI |

## Request lifecycle

1. **RequestIdMiddleware** reads or mints `X-Request-ID`, stores it in a
   context variable, and starts a timer. Unhandled exceptions become a JSON
   500 carrying the ID, then re-raise for the server's own logging.
2. **SecurityHeadersMiddleware** adds `nosniff`, `DENY`, `no-referrer`,
   `no-store` and a `default-src 'none'` CSP (relaxed on the docs pages).
3. **MetricsMiddleware** resolves the matched route *template* and records
   `http_requests_total` / `http_request_duration_seconds`.
4. **RateLimitMiddleware** applies a per-client sliding window to
   `POST /api/auth/login` and `/register` (429 + `Retry-After`).
5. **CORSMiddleware** as configured by `CORS_ORIGINS`.
6. The route handler resolves `get_token_payload` (bearer JWT → claims,
   rejecting revoked `jti`s via the token denylist), `get_current_user` and
   `get_storage` (the repository singleton), performs the operation and
   returns a Pydantic model.

### Shared state

Rate-limit windows and revoked tokens are the only mutable state outside
the database. `SHARED_STATE_BACKEND=memory` keeps them in-process;
`redis` (with `REDIS_URL`) shares them across replicas — the rate limiter
runs a Lua script so check-and-record is atomic. See ADR-0006.

## Data model

```
users                                  tasks
─────                                  ─────
id           varchar(36) PK            id            varchar(36) PK
username     varchar(255) UNIQUE       user_id       varchar(36) FK users.id ON DELETE CASCADE
password_hash varchar(255)             title         varchar(255)
email        varchar(255) NULL         description   text NULL
email_reminders_enabled bool           due_date      timestamptz
created_at   timestamptz               completed     bool
updated_at   timestamptz               priority      varchar(20)   -- low | medium | high
                                       created_at    timestamptz
                                       updated_at    timestamptz
                                       completed_at  timestamptz NULL

indexes: users(username), users(email), tasks(user_id), tasks(due_date), tasks(completed),
         tasks(user_id, completed, due_date)   -- covers "my pending tasks by due date"
```

Due dates are calendar dates on the wire (`YYYY-MM-DD`) and stored as UTC
midnight so that range filters and ordering work in SQL.

## The urgency model

`GET /api/tasks/next` ranks pending tasks by

    U(d, w) = w · σ((d₀ − d) / τ),    σ(x) = 1 / (1 + e^(−x))

with `w` the priority weight (low 1, medium 2, high 3), `d` the fractional
days until due (negative when overdue), `d₀ = 3` days the half-urgency
horizon and `τ = 2` days the temperature. The score is bounded by `w`,
strictly decreasing in `d`, monotone in priority, and ties break on due
date then ID. See `task_manager_pro/analytics/urgency.py` and the
property-based tests in `tests/test_analytics.py`, and ADR-0003 for why a
bounded logistic was chosen over linear or exponential penalties.

With `?calibrated=true`, `analytics/calibration.py` replaces the defaults
with per-user estimates: `d₀` is the median lead time (`due_date −
completed_at`) of the user's completed tasks and `τ` is `1.4826 · MAD` of
the same, both clipped to sane ranges, once at least five completions
exist. Both estimators are robust to outliers and invariant to time shifts,
which the tests in `tests/test_calibration.py` verify.

## Testing strategy

| Layer | Approach | Files |
|---|---|---|
| Analytics | Hypothesis property tests over dates/priorities/parameters | `tests/test_analytics.py` |
| Repository | Private in-memory engine per test via the injectable session factory | `tests/test_storage.py` |
| Middleware | Unit tests with a fake clock + a minimal app | `tests/test_middleware.py` |
| Revocation / Redis | Fake clock in-memory; real Redis when `REDIS_URL` is set (CI) | `tests/test_token_revocation.py` |
| API | `TestClient` against the real app on an in-memory database | `tests/test_api*.py` |
| Email | Fake SMTP transport | `tests/test_email.py` |

`tests/conftest.py` pins `DATABASE_URL=sqlite:///:memory:`, `BCRYPT_ROUNDS=4`
and disables rate limiting *before* the application is imported. CI runs the
suite on Python 3.10–3.13 with SQLite and on 3.12 with PostgreSQL 16, and
enforces an 80 % coverage floor.

## Operations

* **Configuration**: everything in `.env.template`; invalid values fail at
  startup with a precise message.
* **Migrations**: `alembic upgrade head` (the container entrypoint does this
  before serving). `alembic check` in CI prevents model/migration drift.
* **Health**: `GET /health` probes the database and returns 503 when it is
  unreachable; use it for readiness probes.
* **Metrics**: `GET /metrics` in Prometheus text format; `docker-compose.yml`
  ships a Prometheus that scrapes it.
* **Logs**: `LOG_JSON=true` for one JSON object per line including
  `request_id`, `method`, `path`, `status`, `duration_ms`.
* **Benchmarks**: `benchmarks/bench_api.py` (closed-loop, per-endpoint
  percentiles) and `scripts/seed_data.py` (deterministic synthetic data).
