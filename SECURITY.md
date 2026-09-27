# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Email the
maintainer (see `pyproject.toml`) with a description, reproduction steps and
the affected version. You will receive an acknowledgement within a few days;
fixes are released as patch versions and credited in `CHANGELOG.md`.

## What the project does

| Concern | Control |
|---|---|
| Password storage | bcrypt, cost 12 by default (`BCRYPT_ROUNDS`) |
| Authentication | HS256 JWT with `sub`, `iat`, `exp`, `jti`, `type` claims; `exp`/`sub` required on decode |
| Secret hygiene | `SECRET_KEY` must be set, non-placeholder, ≥ 32 chars, or the process refuses to start |
| User enumeration | Constant-time login (dummy bcrypt verify on unknown usernames), identical error messages |
| Brute force | Sliding-window rate limit on login/register with `429` + `Retry-After` |
| Token leakage | Refresh reads the bearer header, never a query parameter; refresh rotates (old `jti` revoked) and `logout` revokes immediately |
| Browser hardening | `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, CSP `default-src 'none'` |
| Error handling | Unhandled exceptions become a generic JSON 500 with a request ID; no stack traces |
| Input validation | Pydantic v2 on every request body and query parameter; sort columns are allow-listed |
| Data isolation | Ownership is enforced inside the SQL query; other users' tasks are 404 |
| Dependencies | `pip-audit --strict` and Bandit in CI; versions pinned by range in `pyproject.toml` |
| Container | Multi-stage image, non-root user, `tini`, health check |

## What it does not do (yet)

* No separate long-lived refresh tokens; a session lasts one access-token lifetime unless rotated.
* Rate limiting and revocation are per process unless `SHARED_STATE_BACKEND=redis` (ADR-0006).
* No account lockout, MFA or password-breach checks.
* TLS termination is the deployment's responsibility (put it behind a reverse proxy).
