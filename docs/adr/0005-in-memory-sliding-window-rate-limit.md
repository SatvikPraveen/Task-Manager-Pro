# 0005 – In-process sliding-window rate limiting on auth endpoints

Date: 2026-09-26 · Status: Accepted

## Context

`/api/auth/login` and `/api/auth/register` are unauthenticated and are the
natural targets for credential stuffing and bulk account creation. bcrypt
at cost 12 also makes them the most CPU-expensive endpoints, so an
attacker can degrade the service cheaply.

## Decision

Apply a per-client sliding-window limiter (default 20 requests/minute,
`AUTH_RATE_LIMIT_PER_MINUTE`) keyed on the first `X-Forwarded-For` hop or
the socket peer. State is an in-memory `deque` of timestamps per key with
idle-key eviction. Responses carry `X-RateLimit-Limit/Remaining`; rejections
are `429` with `Retry-After`. The limiter takes an injectable clock.

## Consequences

* Single-process correctness; with N replicas the effective limit is up to
  N× the configured value, which still bounds abuse. Moving to a shared
  store (Redis) only requires a new limiter class with the same `check()`
  contract.
* Login is additionally made constant-time with respect to username
  existence (`verify_password_dummy`) so the limiter is not the only
  defence against enumeration.
* Tests disable the limiter globally (`RATE_LIMIT_ENABLED=false`) and test
  it in isolation with a fake clock.
