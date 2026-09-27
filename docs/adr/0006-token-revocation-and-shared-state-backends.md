# 0006 – Token revocation via a jti denylist; pluggable shared-state backends

Date: 2026-09-27 · Status: Accepted

## Context

Access tokens are stateless JWTs: once issued they are valid until `exp`,
so there was no way to log out, and refreshing simply minted another token
while the old one lived on. At the same time the in-process rate limiter
(ADR-0005) degrades to N× the limit behind N replicas.

## Decision

* Every token already carries a unique `jti`. A **denylist** stores revoked
  `jti`s with a TTL equal to the token's remaining lifetime, after which the
  signature check rejects the token anyway, so the store never grows beyond
  the number of tokens revoked in one lifetime.
* `POST /api/auth/logout` revokes the presented token; `POST
  /api/auth/refresh-token` **rotates**: it revokes the presented token as it
  issues the new one. `get_token_payload` rejects revoked tokens with
  `401 Token has been revoked`.
* Both the denylist and the rate limiter are behind small protocols with two
  implementations each, chosen by `SHARED_STATE_BACKEND`: `memory`
  (default, single process) and `redis` (shared across replicas; the rate
  limiter uses a Lua script so check-and-record is atomic). The Redis
  client is an optional extra.

## Alternatives considered

* **Short-lived access + long-lived refresh tokens.** More moving parts and
  still needs a revocation store for the refresh tokens; deferred.
* **Storing a token version on the user row.** Revokes *all* of a user's
  sessions at once; too coarse for logout of one device.
* **Sticky sessions instead of Redis.** Does not help with rate limiting
  across replicas and fails on deploys.

## Consequences

* Logout and rotation are real; a stolen token can be invalidated.
* Redis-backed tests run only when `REDIS_URL` is set (CI provides Redis on
  the PostgreSQL job); the in-memory implementations are tested with a
  fake clock.
* Adding a third backend (e.g. a database table) means implementing two
  small protocols, nothing else.
