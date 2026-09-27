"""
analytics/calibration.py

Per-user calibration of the urgency curve from completion history.

The default ``UrgencyParams`` (half-urgency horizon d₀ = 3 days, temperature
τ = 2 days) encode a generic working style. A user's own history says how
far ahead of a deadline they actually finish things: the *lead time*

    lead = due_date − completed_at        (in days; negative when late)

of each completed task. We set

    d₀ = clip(median(lead), 0.5, 14)      — reach half urgency where the user
                                             typically finishes
    τ  = clip(1.4826 · MAD(lead), 0.5, 7)  — spread of their behaviour
                                             (robust σ estimate); falls back
                                             to the base τ when MAD is 0

Both statistics are robust to outliers (a single very early or very late
completion does not move them much), the result is deterministic, and it is
invariant to shifting every timestamp by the same amount. With fewer than
``min_samples`` completions the base parameters are returned unchanged and
``calibrated`` is ``False``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from statistics import median
from typing import Any, Optional

from task_manager_pro.analytics.urgency import DEFAULT_PARAMS, UrgencyParams, _as_utc_datetime

MIN_SAMPLES = 5
D0_BOUNDS = (0.5, 14.0)
TAU_BOUNDS = (0.5, 7.0)
_MAD_TO_SIGMA = 1.4826  # consistency constant for normally distributed data
SECONDS_PER_DAY = 86_400.0


@dataclass(frozen=True)
class CalibrationResult:
    params: UrgencyParams
    calibrated: bool
    samples: int
    lead_days_median: Optional[float]
    lead_days_mad: Optional[float]


def _clip(value: float, bounds: tuple[float, float]) -> float:
    lo, hi = bounds
    return max(lo, min(hi, value))


def lead_times_days(tasks: Iterable[Any], *, now: Optional[datetime] = None) -> list[float]:
    """``due_date − completed_at`` in days for every completed task with a completion timestamp."""
    leads: list[float] = []
    for task in tasks:
        completed_at = getattr(task, "completed_at", None)
        if not getattr(task, "completed", False) or completed_at is None:
            continue
        due = _as_utc_datetime(task.due_date)
        done = _as_utc_datetime(completed_at)
        leads.append((due - done).total_seconds() / SECONDS_PER_DAY)
    return leads


def calibrate_params(
    tasks: Iterable[Any],
    *,
    base: UrgencyParams = DEFAULT_PARAMS,
    min_samples: int = MIN_SAMPLES,
) -> CalibrationResult:
    """Derive per-user ``UrgencyParams`` from completed tasks (see module docstring)."""
    leads = lead_times_days(tasks)
    if len(leads) < min_samples:
        return CalibrationResult(base, False, len(leads), median(leads) if leads else None, None)

    med = median(leads)
    mad = median(abs(x - med) for x in leads)
    d0 = _clip(med, D0_BOUNDS)
    tau = _clip(_MAD_TO_SIGMA * mad, TAU_BOUNDS) if mad > 0 else base.temperature_days
    params = UrgencyParams(half_urgency_days=d0, temperature_days=tau, priority_weight=base.priority_weight)
    return CalibrationResult(params, True, len(leads), med, mad)


__all__ = ["MIN_SAMPLES", "CalibrationResult", "calibrate_params", "lead_times_days"]
