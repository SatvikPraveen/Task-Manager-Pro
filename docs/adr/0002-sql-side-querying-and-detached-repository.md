# 0002 – Query in SQL, return detached ORM objects from an injectable repository

Date: 2026-09-26 · Status: Accepted

## Context

`GET /api/tasks` loaded every task of a user and sliced the list in Python,
so latency and memory grew linearly with history. `SQLStorage` created its
own sessions from a module-global factory, which made it impossible to bind
a repository to a throw-away database in tests, and the API layer created
a second repository instance alongside the dependency-injected one.

## Decision

* `SQLStorage(session_factory=...)`: the session factory is injected
  (defaulting to the application's). Every public method runs in a
  commit/rollback context manager and **expunges** what it returns, so
  callers receive plain detached objects and never hold a session.
* `list_tasks()` performs filtering (completion, priority, due window,
  case-insensitive search), an allow-listed `ORDER BY` with a deterministic
  tie-break on `id`, and `OFFSET/LIMIT` in SQL, with a separate `COUNT(*)`
  for paging metadata.
* Ownership is part of the query (`get_user_task(user_id, task_id)`) rather
  than a post-hoc attribute check.
* A composite index `(user_id, completed, due_date)` covers the dominant
  access path.

## Consequences

* Listing cost is O(page) instead of O(history).
* `tests/test_storage.py` binds a repository to a private in-memory engine.
* Lazy relationship access on returned objects would raise
  `DetachedInstanceError`; the API never needs it, and if a future feature
  does, it should eager-load explicitly in the repository.
