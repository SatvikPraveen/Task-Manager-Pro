# 0001 – Validated settings as the single configuration source

Date: 2026-09-26 · Status: Accepted

## Context

Configuration was read with `os.getenv` at import time in five different
modules, each with its own default. The JWT secret check lived in
`utils/security.py`, the database URL in `storage/database.py`, SMTP details
in `utils/emailer.py`, CORS in `api/main.py`. Tests could not change any of
them without re-importing modules, and there was no validation beyond
"SECRET_KEY is present".

## Decision

Introduce `task_manager_pro.config.Settings` (pydantic-settings) as the only
place configuration is declared, typed, defaulted and validated. Modules call
`get_settings()` *at use time*, never at import time (the one exception is
the engine in `storage/database.py`, which must exist for the ORM to bind).
`reset_settings()` clears the cache so tests can mutate the environment.

Validation is strict where it matters: the secret must be present, not the
historical placeholder, and ≥ 32 characters; bcrypt cost is bounded to
4..31; the log level must be a real level.

## Consequences

* One `.env.template` documents every knob; startup fails with a precise
  message instead of a runtime surprise.
* The test-suite runs with `BCRYPT_ROUNDS=4` and an in-memory database
  simply by setting environment variables in `conftest.py`.
* Any new configuration must be added to `Settings`; ad-hoc `os.getenv` is
  a review failure.
