"""
analytics/urgency.py

A principled "what should I do next?" ordering.

Definition
----------
For a pending task with priority weight ``w`` and ``d`` days until its due
date (negative when overdue), the urgency is

    U(d, w) = w · σ((d₀ − d) / τ),      σ(x) = 1 / (1 + e^(−x))

where ``d₀`` (``half_urgency_days``) is the horizon at which a task reaches
half of its priority weight and ``τ`` (``temperature_days``) controls how
sharply urgency rises as the deadline approaches.

Properties (all verified by property-based tests):

* **Bounded**: 0 ≤ U ≤ w (strictly positive in exact arithmetic; the
  logistic underflows to 0.0 in float64 for deadlines centuries away), so a
  low-priority task can never outrank a high-priority task that is *at
  least as* close to its deadline. Overdue tasks approach ``w``
  asymptotically instead of growing without bound, which keeps the score
  well-conditioned for very old tasks.
* **Monotone in time**: U is strictly decreasing in ``d`` — closer (or more
  overdue) deadlines are always more urgent, and the score of a fixed task
  increases as the clock advances.
* **Monotone in priority**: for equal ``d``, higher priority ⇒ higher U.
* **Completed tasks score 0** and sort last.

Ranking breaks ties on due date, then on task ID, so it is a total order and
therefore deterministic across runs and databases.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from types import MappingProxyType
from typing import Any, Optional

PRIORITY_WEIGHT: Mapping[str, float] = MappingProxyType({"low": 1.0, "medium": 2.0, "high": 3.0})
DEFAULT_HALF_URGENCY_DAYS = 3.0
DEFAULT_TEMPERATURE_DAYS = 2.0
SECONDS_PER_DAY = 86_400.0


@dataclass(frozen=True)
class UrgencyParams:
    """Tunable constants of the urgency curve."""

    half_urgency_days: float = DEFAULT_HALF_URGENCY_DAYS
    temperature_days: float = DEFAULT_TEMPERATURE_DAYS
    priority_weight: Mapping[str, float] = field(default_factory=lambda: PRIORITY_WEIGHT)

    def __post_init__(self) -> None:
        if self.temperature_days <= 0:
            raise ValueError("temperature_days must be positive")
        if any(w <= 0 for w in self.priority_weight.values()):
            raise ValueError("priority weights must be positive")


DEFAULT_PARAMS = UrgencyParams()


def _as_utc_datetime(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)


def days_until_due(due: date | datetime, now: Optional[datetime] = None) -> float:
    """Fractional days from ``now`` (default: current UTC time) to ``due``; negative if overdue."""
    now_dt = _as_utc_datetime(now) if now is not None else datetime.now(timezone.utc)
    return (_as_utc_datetime(due) - now_dt).total_seconds() / SECONDS_PER_DAY


def _sigmoid(x: float) -> float:
    # Numerically stable logistic function.
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def urgency_score(
    due: date | datetime,
    priority: str,
    *,
    completed: bool = False,
    now: Optional[datetime] = None,
    params: UrgencyParams = DEFAULT_PARAMS,
) -> float:
    """
    Urgency in ``[0, w(priority)]`` for a pending task, or ``0.0`` if completed.

    Unknown priorities fall back to the ``medium`` weight rather than failing,
    so a bad row in the database degrades gracefully.
    """
    if completed:
        return 0.0
    weight = params.priority_weight.get(priority, params.priority_weight.get("medium", 1.0))
    d = days_until_due(due, now)
    return weight * _sigmoid((params.half_urgency_days - d) / params.temperature_days)


def rank_tasks(
    tasks: Iterable[Any],
    *,
    now: Optional[datetime] = None,
    params: UrgencyParams = DEFAULT_PARAMS,
    include_completed: bool = False,
) -> list[tuple[Any, float]]:
    """
    Order tasks by descending urgency.

    Each element must expose ``due_date``, ``priority``, ``completed`` and
    ``id`` attributes (ORM rows and Pydantic models both qualify).
    Returns ``(task, score)`` pairs.
    """
    now_dt = now or datetime.now(timezone.utc)
    scored = [
        (task, urgency_score(task.due_date, task.priority, completed=task.completed, now=now_dt, params=params))
        for task in tasks
        if include_completed or not task.completed
    ]
    scored.sort(key=lambda pair: (-pair[1], _as_utc_datetime(pair[0].due_date), str(pair[0].id)))
    return scored
