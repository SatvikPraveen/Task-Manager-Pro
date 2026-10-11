# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `PUT /api/users/me/password` (`current_password`, `new_password`) to change a password.
- `FORWARDED_ALLOW_IPS` for the container: the proxies whose `X-Forwarded-For` is trusted (default `127.0.0.1`).

### Changed
- CLI single-task commands share one ownership lookup and the `@require_login` decorator.
- The JSON→SQL migration gives each account a random one-time password (printed once) instead of `<username>@temp123`, skips usernames that already exist together with their tasks (re-runs no longer duplicate), and keeps `created_at`.
- `PUT /api/tasks/{id}` and `PUT /api/users/me` accept `null` to clear `description` / `email`; required fields reject `null` with `422`.
- `JWT_ALGORITHM` is limited to `HS256`, `HS384` and `HS512`.

### Fixed
- CLI: `complete` and `delete` now require a login and only act on the current user's own tasks, matching `update`. Previously any user who knew another user's task ID could complete or delete it (#6).
- CLI: `list-tasks` while logged out listed every user's tasks.
- Security: the auth rate limit was keyed on the client-supplied `X-Forwarded-For`, so a new header per request bypassed it; the container also trusted forwarded headers from any address.
- Security: passwords over 72 bytes returned `500` at login for unknown usernames only, revealing which accounts exist; registration now rejects them with `422`.
- Security: parallel refreshes of one token each received a new token; revocation is now atomic and happens before issuing.
- Concurrent registration of one username returned `500` instead of `400`.
- Due dates read one day early from PostgreSQL in a non-UTC session; SQLite timestamps were returned without a UTC offset.
- Task search treated `%` and `_` as wildcards.
- CLI: one run of `send_reminders` (which stores `last_reminder_date`) made every later command crash for that user.
- CLI: email reminders were sent even after `toggle-email-reminders` turned them off.
- `send_reminders` recorded failed sends as delivered, so they were never retried; one task with a bad date stopped reminders for everyone.
- CLI: `update-task --due` stored any string, after which listing and reminders crashed; `add-task` crashed on a bad date.
- CLI: `tasks.json` is written atomically, and an empty or corrupt file produces a clear error instead of a traceback.
- CLI: `login` crashed without a terminal (cron, scripts, `docker run`) and ignored `--email` for existing users.
- Migration: completed tasks were stamped with the migration time, skewing stats and calibration.
- `demo_api.py` crashed at step 5 (it iterated the list response object) and depended on the undeclared `requests` package.
- Docker: `task-manager` commands in the container failed to write their data files.

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
