"""
analytics/stats.py

Descriptive statistics for a collection of tasks.

All quantities are computed from the task rows in one pass (plus a sort for
the median), so the cost is O(n log n) in the number of tasks for one user.
Timestamps are interpreted as UTC; a task is *overdue* when its due date is
strictly before the start of "today" in UTC and it is not completed.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from statistics import mean, median
from typing import Any, Optional

from task_manager_pro.analytics.urgency import _as_utc_datetime

PRIORITIES = ("low", "medium", "high")


@dataclass(frozen=True)
class PriorityBreakdown:
    total: int = 0
    completed: int = 0
    pending: int = 0
    overdue: int = 0


@dataclass(frozen=True)
class TaskStatistics:
    """A snapshot of one user's workload. All rates are in ``[0, 1]``."""

    as_of: datetime
    total: int
    completed: int
    pending: int
    overdue: int
    due_today: int
    due_next_7_days: int
    completion_rate: float
    on_time_rate: Optional[float]
    mean_completion_days: Optional[float]
    median_completion_days: Optional[float]
    by_priority: dict[str, PriorityBreakdown] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["as_of"] = self.as_of.isoformat()
        return data


def _start_of_day(moment: datetime) -> datetime:
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def compute_statistics(tasks: Iterable[Any], *, now: Optional[datetime] = None) -> TaskStatistics:
    """
    Summarise ``tasks`` (objects exposing ``due_date``, ``priority``,
    ``completed``, ``created_at`` and ``completed_at``).

    ``on_time_rate`` is the share of completed tasks finished no later than
    the end of their due day. Latency metrics use ``completed_at − created_at``
    and are ``None`` when nothing has been completed yet.
    """
    now_dt = _as_utc_datetime(now) if now is not None else datetime.now(timezone.utc)
    today = _start_of_day(now_dt)
    tomorrow = today + timedelta(days=1)
    week_end = today + timedelta(days=7)

    total = completed = pending = overdue = due_today = due_week = 0
    on_time = 0
    latencies: list[float] = []
    per_priority: dict[str, dict[str, int]] = {
        p: {"total": 0, "completed": 0, "pending": 0, "overdue": 0} for p in PRIORITIES
    }

    for task in tasks:
        total += 1
        due = _as_utc_datetime(task.due_date)
        bucket = per_priority.setdefault(task.priority, {"total": 0, "completed": 0, "pending": 0, "overdue": 0})
        bucket["total"] += 1

        if task.completed:
            completed += 1
            bucket["completed"] += 1
            completed_at = getattr(task, "completed_at", None)
            created_at = getattr(task, "created_at", None)
            if completed_at is not None:
                finished = _as_utc_datetime(completed_at)
                if finished < _start_of_day(due) + timedelta(days=1):
                    on_time += 1
                if created_at is not None:
                    latencies.append(max(0.0, (finished - _as_utc_datetime(created_at)).total_seconds() / 86_400))
            continue

        pending += 1
        bucket["pending"] += 1
        if due < today:
            overdue += 1
            bucket["overdue"] += 1
        elif due < tomorrow:
            due_today += 1
        if today <= due < week_end:
            due_week += 1

    return TaskStatistics(
        as_of=now_dt,
        total=total,
        completed=completed,
        pending=pending,
        overdue=overdue,
        due_today=due_today,
        due_next_7_days=due_week,
        completion_rate=(completed / total) if total else 0.0,
        on_time_rate=(on_time / completed) if completed else None,
        mean_completion_days=mean(latencies) if latencies else None,
        median_completion_days=median(latencies) if latencies else None,
        by_priority={p: PriorityBreakdown(**counts) for p, counts in per_priority.items()},
    )


__all__ = ["PriorityBreakdown", "TaskStatistics", "compute_statistics", "date"]
