# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/).

## [0.5.0] – 2026-09-27

### Added
- `POST /api/auth/logout` revokes the presented token; `POST /api/auth/refresh-token` now rotates (the old token is revoked). Revocation is a `jti` denylist with TTL = remaining token lifetime (ADR-0006).
- `SHARED_STATE_BACKEND=redis` + `REDIS_URL`: rate-limit windows and revoked tokens shared across replicas. The Redis rate limiter is a Lua-scripted atomic sliding window. New optional extra `task-manager-pro[redis]`.
- Per-user urgency calibration: `GET /api/tasks/next?calibrated=true` estimates the half-urgency horizon and temperature from the user's completion history (median / MAD of lead time, clipped, ≥ 5 samples); responses include the `params` used.
- CI: Redis 7 service on the PostgreSQL job; Dependabot for pip, GitHub Actions and Docker; `docker compose` includes Redis.
- Tests: 88 → 101 (denylist, Redis limiter/denylist when available, logout/rotation, calibration properties).

### Changed
- `QUICKSTART.md`, `IMPLEMENTATION_SUMMARY.md` and the phase write-ups updated to the current API (bearer-header refresh, new endpoints, current test layout).

## [0.4.0] – 2026-09-27

### Added
- `task_manager_pro.config.Settings`: one validated, typed source of configuration (ADR-0001).
- SQL-side filtering (`completed`, `priority`, `due_before`, `due_after`, `q`), sorting (`sort_by`, `sort_desc`) and pagination (`pages` in the response) on `GET /api/tasks` (ADR-0002).
- `GET /api/tasks/stats`: completion/on-time rates, overdue load, completion latency, per-priority breakdown.
- `GET /api/tasks/next`: tasks ranked by a bounded logistic urgency model (ADR-0003), with Hypothesis property tests.
- Request correlation (`X-Request-ID`, `X-Process-Time`), structured JSON logging, Prometheus `/metrics`, security headers (ADR-0004).
- Sliding-window rate limiting on login/register with `429` + `Retry-After` (ADR-0005).
- Constant-time login; JWTs carry `iat`, `jti` and `type` claims; `expires_in` in token responses.
- `/health` probes the database and returns 503 when it is unreachable.
- Alembic migrations (`migrations/`) with a drift check (`alembic check`) in CI.
- Composite index `tasks(user_id, completed, due_date)`; `ON DELETE CASCADE` on `tasks.user_id`; timezone-aware timestamps.
- Tooling: Ruff (lint + format), stricter mypy with the pydantic plugin, Bandit, pip-audit, pre-commit, `Makefile`, coverage floor of 80 %.
- CI matrix: Python 3.10–3.13 on SQLite plus 3.12 on PostgreSQL 16; Docker image smoke test.
- Multi-stage, non-root Dockerfile that runs migrations then serves the API; `docker-compose.yml` with PostgreSQL and Prometheus.
- `scripts/seed_data.py` (deterministic synthetic data) and `benchmarks/bench_api.py` (per-endpoint latency percentiles).
- `docs/ARCHITECTURE.md`, `docs/adr/`, `SECURITY.md`, `CITATION.cff`.

### Changed
- `POST /api/auth/refresh-token` reads the bearer token from the `Authorization` header instead of a `token` query parameter.
- `due_date` is a real ISO date and timestamps are ISO-8601 datetimes in responses (same wire format as before for dates).
- Reopening a completed task clears `completed_at`.
- `SECRET_KEY` must now be at least 32 characters.
- The test-suite uses an in-memory database and no longer drops tables in the developer's `tasks.db`.

### Removed
- The `sys.path` hack in the package `__init__`.
- Module-level `os.getenv` configuration scattered across modules.

## [0.3.0] – 2025-09-08

- REST API (FastAPI), SQLAlchemy persistence, JWT authentication, initial CI/CD.

## [0.2.0] and earlier

- JSON-backed CLI with email reminders and cron support.
