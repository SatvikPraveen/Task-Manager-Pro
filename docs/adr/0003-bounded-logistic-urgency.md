# 0003 – Bounded logistic urgency score for task ranking

Date: 2026-09-26 · Status: Accepted

## Context

"What should I work on next?" needs a total order over pending tasks that
combines priority and deadline proximity. Candidate scores:

1. **Sort by due date, then priority** – ignores that a high-priority task
   due in four days usually beats a low-priority task due in three.
2. **Linear penalty** `w − k·d` – unbounded for overdue tasks, so a
   long-overdue low-priority chore eventually outranks everything.
3. **Exponential decay** `w·e^(−d/τ)` – also unbounded when `d < 0`, and
   numerically unpleasant for very old tasks.
4. **Priority-weighted logistic** `w·σ((d₀ − d)/τ)` – bounded in `[0, w]`,
   smooth, monotone in both inputs, with two interpretable parameters.

## Decision

Use (4) with `w ∈ {1, 2, 3}` for low/medium/high, `d₀ = 3` days (a task
reaches half its weight three days out) and `τ = 2` days. Completed tasks
score 0. Ties break on due date then ID so the ranking is a total order.
The parameters live in a frozen `UrgencyParams` dataclass so experiments can
vary them without touching the function.

## Consequences

* A low-priority task can never outrank a high-priority task that is at
  least as close to its deadline — the bound `U ≤ w` guarantees it.
* Overdue tasks saturate rather than explode, keeping the ranking stable
  for stale backlogs.
* The properties (bounded, monotone in time, monotone in priority, 0 for
  completed, deterministic ranking) are executable specifications in
  `tests/test_analytics.py` via Hypothesis, so a future tweak that breaks
  one of them fails CI.
* The score is *not* calibrated against user behaviour; it is a documented
  heuristic. Learning `d₀`/`τ` per user from completion data is future work.
