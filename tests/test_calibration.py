"""
tests/test_calibration.py

Property-based and example tests for per-user urgency calibration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from task_manager_pro.analytics import DEFAULT_PARAMS, calibrate_params, lead_times_days
from task_manager_pro.analytics.calibration import D0_BOUNDS, MIN_SAMPLES, TAU_BOUNDS

NOW = datetime(2030, 6, 15, 12, 0, tzinfo=timezone.utc)


@dataclass
class T:
    id: str
    due_date: datetime
    priority: str = "medium"
    completed: bool = True
    completed_at: Optional[datetime] = None


def _done(lead_days: float, i: int = 0) -> T:
    due = NOW + timedelta(days=i)
    return T(str(i), due, completed=True, completed_at=due - timedelta(days=lead_days))


def test_lead_times_ignore_pending_and_untimestamped():
    tasks = [_done(2.0), T("p", NOW, completed=False), T("u", NOW, completed=True, completed_at=None)]
    assert lead_times_days(tasks) == [2.0]


def test_too_few_samples_returns_base_params():
    result = calibrate_params([_done(3.0, i) for i in range(MIN_SAMPLES - 1)])
    assert result.params == DEFAULT_PARAMS and not result.calibrated
    assert result.samples == MIN_SAMPLES - 1 and result.lead_days_median == 3.0


def test_calibration_uses_median_and_mad():
    leads = [1.0, 2.0, 2.0, 3.0, 40.0]  # the outlier must not dominate
    result = calibrate_params([_done(lead, i) for i, lead in enumerate(leads)])
    assert result.calibrated and result.samples == 5
    assert result.lead_days_median == 2.0 and result.lead_days_mad == 1.0
    assert result.params.half_urgency_days == 2.0
    assert result.params.temperature_days == pytest.approx(1.4826)


def test_zero_spread_falls_back_to_base_temperature():
    result = calibrate_params([_done(5.0, i) for i in range(6)])
    assert result.params.half_urgency_days == 5.0
    assert result.params.temperature_days == DEFAULT_PARAMS.temperature_days


leads_strategy = st.lists(
    st.floats(min_value=-365, max_value=365, allow_nan=False, allow_infinity=False), min_size=0, max_size=40
)


@given(leads_strategy)
@settings(max_examples=80)
def test_parameters_stay_within_bounds_and_are_deterministic(leads):
    tasks = [_done(lead, i) for i, lead in enumerate(leads)]
    a = calibrate_params(tasks)
    b = calibrate_params(list(reversed(tasks)))
    assert a == b
    assert D0_BOUNDS[0] <= a.params.half_urgency_days <= D0_BOUNDS[1]
    assert TAU_BOUNDS[0] <= a.params.temperature_days <= TAU_BOUNDS[1]
    assert a.calibrated == (len(leads) >= MIN_SAMPLES)
    assert a.params.priority_weight == DEFAULT_PARAMS.priority_weight


@given(leads_strategy, st.floats(min_value=-1000, max_value=1000, allow_nan=False))
@settings(max_examples=60)
def test_calibration_is_invariant_to_time_shift(leads, shift_days):
    tasks = [_done(lead, i) for i, lead in enumerate(leads)]
    shifted = [
        T(
            t.id,
            t.due_date + timedelta(days=shift_days),
            completed=True,
            completed_at=(t.completed_at or NOW) + timedelta(days=shift_days),
        )
        for t in tasks
    ]
    assert calibrate_params(tasks) == calibrate_params(shifted)
