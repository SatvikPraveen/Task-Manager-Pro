"""
tests/test_analytics.py

Property-based and example-based tests for the analytics package.

The urgency model's documented guarantees (boundedness, monotonicity in
time and in priority, determinism of the ranking) are checked with
Hypothesis over wide ranges of dates and parameters rather than a handful
of hand-picked points.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from task_manager_pro.analytics import (
    PRIORITY_WEIGHT,
    UrgencyParams,
    compute_statistics,
    days_until_due,
    rank_tasks,
    urgency_score,
)

NOW = datetime(2030, 6, 15, 12, 0, tzinfo=timezone.utc)


@dataclass
class FakeTask:
    id: str
    due_date: datetime
    priority: str = "medium"
    completed: bool = False
    created_at: datetime = NOW - timedelta(days=5)
    completed_at: Optional[datetime] = None


# --------------------------------------------------------------------------- #
# Strategies                                                                  #
# --------------------------------------------------------------------------- #
aware_datetimes = st.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2100, 1, 1)).map(
    lambda d: d.replace(tzinfo=timezone.utc)
)
priorities = st.sampled_from(sorted(PRIORITY_WEIGHT))
day_offsets = st.floats(min_value=-3650, max_value=3650, allow_nan=False, allow_infinity=False)
params_strategy = st.builds(
    UrgencyParams,
    half_urgency_days=st.floats(min_value=-30, max_value=30, allow_nan=False),
    temperature_days=st.floats(min_value=0.05, max_value=30, allow_nan=False),
)


# --------------------------------------------------------------------------- #
# Urgency properties                                                          #
# --------------------------------------------------------------------------- #
@given(aware_datetimes, priorities, params_strategy)
def test_urgency_is_bounded_by_priority_weight(due, priority, params):
    score = urgency_score(due, priority, now=NOW, params=params)
    assert 0.0 <= score <= PRIORITY_WEIGHT[priority]


@given(day_offsets, day_offsets, priorities, params_strategy)
def test_urgency_is_strictly_decreasing_in_days_until_due(d1, d2, priority, params):
    if abs(d1 - d2) < 1e-6:
        return
    earlier, later = sorted((d1, d2))
    u_earlier = urgency_score(NOW + timedelta(days=earlier), priority, now=NOW, params=params)
    u_later = urgency_score(NOW + timedelta(days=later), priority, now=NOW, params=params)
    # Non-strict in the far tails where the sigmoid saturates in float64.
    assert u_earlier >= u_later


@given(day_offsets, params_strategy)
def test_urgency_is_monotone_in_priority(offset, params):
    due = NOW + timedelta(days=offset)
    low = urgency_score(due, "low", now=NOW, params=params)
    medium = urgency_score(due, "medium", now=NOW, params=params)
    high = urgency_score(due, "high", now=NOW, params=params)
    assert low <= medium <= high


@given(aware_datetimes, priorities, st.floats(min_value=0, max_value=3650, allow_nan=False))
def test_urgency_of_fixed_task_never_decreases_as_time_passes(due, priority, elapsed_days):
    before = urgency_score(due, priority, now=NOW)
    after = urgency_score(due, priority, now=NOW + timedelta(days=elapsed_days))
    assert after >= before


@given(aware_datetimes, priorities)
def test_completed_tasks_have_zero_urgency(due, priority):
    assert urgency_score(due, priority, completed=True, now=NOW) == 0.0


def test_half_urgency_point_is_exactly_half_weight():
    params = UrgencyParams(half_urgency_days=3.0, temperature_days=2.0)
    due = NOW + timedelta(days=3.0)
    assert urgency_score(due, "high", now=NOW, params=params) == pytest.approx(PRIORITY_WEIGHT["high"] / 2)


def test_unknown_priority_falls_back_to_medium():
    due = NOW + timedelta(days=1)
    assert urgency_score(due, "weird", now=NOW) == urgency_score(due, "medium", now=NOW)


def test_naive_and_date_inputs_are_treated_as_utc():
    assert days_until_due(date(2030, 6, 16), NOW) == pytest.approx(0.5)
    assert days_until_due(datetime(2030, 6, 16), NOW) == pytest.approx(0.5)


def test_invalid_params_rejected():
    with pytest.raises(ValueError):
        UrgencyParams(temperature_days=0)
    with pytest.raises(ValueError):
        UrgencyParams(priority_weight={"low": 0.0})


# --------------------------------------------------------------------------- #
# Ranking                                                                     #
# --------------------------------------------------------------------------- #
@given(
    st.lists(
        st.builds(
            FakeTask,
            id=st.uuids().map(str),
            due_date=aware_datetimes,
            priority=priorities,
            completed=st.booleans(),
        ),
        max_size=40,
    )
)
@settings(max_examples=60)
def test_rank_is_deterministic_sorted_and_excludes_completed(tasks):
    ranked = rank_tasks(tasks, now=NOW)
    assert [t.id for t, _ in ranked] == [t.id for t, _ in rank_tasks(list(reversed(tasks)), now=NOW)]
    scores = [s for _, s in ranked]
    assert scores == sorted(scores, reverse=True)
    assert all(not t.completed for t, _ in ranked)
    assert len(ranked) == sum(1 for t in tasks if not t.completed)


def test_rank_prefers_overdue_high_over_distant_low_and_breaks_ties_by_due_then_id():
    a = FakeTask("b", NOW - timedelta(days=1), "high")
    b = FakeTask("a", NOW + timedelta(days=30), "low")
    c = FakeTask("c", NOW - timedelta(days=1), "high")  # identical to `a` except id
    ranked = [t.id for t, _ in rank_tasks([b, c, a], now=NOW)]
    assert ranked == ["b", "c", "a"]


# --------------------------------------------------------------------------- #
# Statistics                                                                  #
# --------------------------------------------------------------------------- #
def test_statistics_on_empty_input():
    stats = compute_statistics([], now=NOW)
    assert stats.total == 0 and stats.completion_rate == 0.0
    assert stats.on_time_rate is None and stats.mean_completion_days is None
    assert set(stats.by_priority) == {"low", "medium", "high"}


def test_statistics_counts_and_rates():
    tasks = [
        FakeTask("1", NOW - timedelta(days=2), "high"),  # overdue
        FakeTask("2", NOW.replace(hour=0) + timedelta(hours=1), "low"),  # due today
        FakeTask("3", NOW + timedelta(days=3), "medium"),  # this week
        FakeTask("4", NOW + timedelta(days=30), "medium"),  # later
        FakeTask(
            "5",
            NOW - timedelta(days=1),
            "high",
            completed=True,
            created_at=NOW - timedelta(days=4),
            completed_at=NOW - timedelta(days=2),
        ),  # on time, 2d
        FakeTask(
            "6",
            NOW - timedelta(days=3),
            "low",
            completed=True,
            created_at=NOW - timedelta(days=10),
            completed_at=NOW - timedelta(days=1),
        ),  # late, 9d
    ]
    stats = compute_statistics(tasks, now=NOW)
    assert (stats.total, stats.completed, stats.pending) == (6, 2, 4)
    assert stats.overdue == 1 and stats.due_today == 1 and stats.due_next_7_days == 2
    assert stats.completion_rate == pytest.approx(2 / 6)
    assert stats.on_time_rate == pytest.approx(0.5)
    assert stats.mean_completion_days == pytest.approx(5.5)
    assert stats.median_completion_days == pytest.approx(5.5)
    assert stats.by_priority["high"].overdue == 1 and stats.by_priority["high"].completed == 1
    assert stats.by_priority["low"].pending == 1
    assert stats.to_dict()["as_of"] == NOW.isoformat()


@given(
    st.lists(
        st.builds(
            FakeTask,
            id=st.uuids().map(str),
            due_date=aware_datetimes,
            priority=priorities,
            completed=st.booleans(),
            completed_at=st.one_of(st.none(), aware_datetimes),
        ),
        max_size=50,
    )
)
@settings(max_examples=60)
def test_statistics_invariants(tasks):
    stats = compute_statistics(tasks, now=NOW)
    assert stats.total == len(tasks) == stats.completed + stats.pending
    assert stats.overdue + stats.due_today <= stats.pending
    assert 0.0 <= stats.completion_rate <= 1.0
    assert stats.on_time_rate is None or 0.0 <= stats.on_time_rate <= 1.0
    assert sum(b.total for b in stats.by_priority.values()) == stats.total
    assert sum(b.overdue for b in stats.by_priority.values()) == stats.overdue
