"""
schemas/task.py

Pydantic v2 request/response models for tasks.

Due dates are ISO calendar dates (``YYYY-MM-DD``) on the wire; the ORM stores
them as UTC-midnight datetimes, and ``TaskResponse`` converts back on output.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskPriority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskSortField(str, Enum):
    """Columns the task list can be ordered by."""

    DUE_DATE = "due_date"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    PRIORITY = "priority"
    TITLE = "title"


class TaskCreate(BaseModel):
    """Payload for creating a task."""

    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, max_length=2000, description="Task description")
    due_date: date = Field(..., description="Due date (YYYY-MM-DD)")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


class TaskUpdate(BaseModel):
    """Partial update; every field is optional."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    due_date: Optional[date] = Field(None, description="Due date (YYYY-MM-DD)")
    priority: Optional[TaskPriority] = None
    completed: Optional[bool] = None

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


class TaskResponse(BaseModel):
    """A task as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str] = None
    due_date: date
    priority: TaskPriority
    completed: bool
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    @field_validator("due_date", mode="before")
    @classmethod
    def _datetime_to_date(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.date()
        return value

    @classmethod
    def from_model(cls, task: Any) -> TaskResponse:
        """Build a response from an ORM ``TaskModel`` (or any duck-typed object)."""
        return cls.model_validate(task)


class TaskListResponse(BaseModel):
    """A page of tasks plus paging metadata."""

    total: int = Field(..., description="Total number of tasks matching the filters")
    tasks: list[TaskResponse]
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)
    pages: int = Field(..., ge=0, description="Total number of pages at this page size")


class TaskWithUrgency(TaskResponse):
    """A task annotated with its urgency score (see ``analytics.urgency``)."""

    urgency: float = Field(..., ge=0.0, description="Urgency in (0, priority weight]; 0 when completed")
    days_until_due: float = Field(..., description="Fractional days until due; negative when overdue")


class UrgencyParamsResponse(BaseModel):
    """The urgency-curve parameters used for a ranking."""

    half_urgency_days: float = Field(
        ..., description="Days before due at which urgency reaches half the priority weight"
    )
    temperature_days: float = Field(..., gt=0, description="How sharply urgency rises near the deadline")
    calibrated: bool = Field(..., description="True if derived from the user's completion history")
    samples: int = Field(..., ge=0, description="Completed tasks with timestamps used for calibration")
    lead_days_median: Optional[float] = Field(None, description="Median of due_date - completed_at in days")


class NextTasksResponse(BaseModel):
    """The most urgent pending tasks, best first."""

    as_of: datetime
    params: UrgencyParamsResponse
    tasks: list[TaskWithUrgency]


class PriorityBreakdownResponse(BaseModel):
    total: int
    completed: int
    pending: int
    overdue: int


class TaskStatsResponse(BaseModel):
    """Workload summary for the caller (see ``analytics.stats``)."""

    as_of: datetime
    total: int
    completed: int
    pending: int
    overdue: int
    due_today: int
    due_next_7_days: int
    completion_rate: float = Field(..., ge=0.0, le=1.0)
    on_time_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    mean_completion_days: Optional[float] = Field(None, ge=0.0)
    median_completion_days: Optional[float] = Field(None, ge=0.0)
    by_priority: dict[str, PriorityBreakdownResponse]
