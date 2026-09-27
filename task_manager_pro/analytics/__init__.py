"""
Pure, side-effect-free analytics over task collections.

* :mod:`.urgency`     — a bounded, monotone urgency score and a ranking built on it.
* :mod:`.calibration` — per-user estimation of the urgency parameters from history.
* :mod:`.stats`       — descriptive statistics (throughput, overdue load, latency).

Everything here operates on plain attribute-bearing objects (ORM rows,
dataclasses, test doubles) and never touches the database, which is what makes
the property-based tests in ``tests/test_analytics.py`` possible.
"""

from task_manager_pro.analytics.calibration import CalibrationResult, calibrate_params, lead_times_days
from task_manager_pro.analytics.stats import TaskStatistics, compute_statistics
from task_manager_pro.analytics.urgency import (
    DEFAULT_HALF_URGENCY_DAYS,
    DEFAULT_PARAMS,
    DEFAULT_TEMPERATURE_DAYS,
    PRIORITY_WEIGHT,
    UrgencyParams,
    days_until_due,
    rank_tasks,
    urgency_score,
)

__all__ = [
    "DEFAULT_HALF_URGENCY_DAYS",
    "DEFAULT_PARAMS",
    "DEFAULT_TEMPERATURE_DAYS",
    "PRIORITY_WEIGHT",
    "CalibrationResult",
    "TaskStatistics",
    "UrgencyParams",
    "calibrate_params",
    "compute_statistics",
    "days_until_due",
    "lead_times_days",
    "rank_tasks",
    "urgency_score",
]
