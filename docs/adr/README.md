# Architecture Decision Records

Short, dated records of the non-obvious choices in this codebase, in the
[Michael Nygard format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
Add a new file (`NNNN-title.md`) rather than editing an accepted one; if a
decision is reversed, add a new record that supersedes it.

| # | Title | Status |
|---|---|---|
| [0001](0001-validated-settings-single-source.md) | Validated settings as the single configuration source | Accepted |
| [0002](0002-sql-side-querying-and-detached-repository.md) | Query in SQL, return detached ORM objects from an injectable repository | Accepted |
| [0003](0003-bounded-logistic-urgency.md) | Bounded logistic urgency score for task ranking | Accepted |
| [0004](0004-pure-asgi-middleware-and-request-correlation.md) | Pure ASGI middleware; 500s handled where headers can still be set | Accepted |
| [0005](0005-in-memory-sliding-window-rate-limit.md) | In-process sliding-window rate limiting on auth endpoints | Accepted (Redis backend added by 0006) |
| [0006](0006-token-revocation-and-shared-state-backends.md) | Token revocation via a jti denylist; pluggable shared-state backends | Accepted |
