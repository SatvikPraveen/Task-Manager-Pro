"""
api/routes/tasks.py

Task CRUD with server-side filtering, sorting and pagination.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from task_manager_pro.analytics import DEFAULT_PARAMS, calibrate_params, compute_statistics, days_until_due, rank_tasks
from task_manager_pro.api.dependencies import get_current_user, get_storage
from task_manager_pro.schemas.task import (
    NextTasksResponse,
    TaskCreate,
    TaskListResponse,
    TaskPriority,
    TaskResponse,
    TaskSortField,
    TaskStatsResponse,
    TaskUpdate,
    TaskWithUrgency,
    UrgencyParamsResponse,
)
from task_manager_pro.storage.sql_storage import SQLStorage

router = APIRouter()

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
) -> TaskResponse:
    """Create a task owned by the caller."""
    task = storage.create_task(
        user_id=user_id,
        title=task_data.title,
        description=task_data.description,
        due_date=task_data.due_date,
        priority=task_data.priority.value,
    )
    return TaskResponse.from_model(task)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    skip: int = Query(0, ge=0, description="Number of tasks to skip"),
    limit: int = Query(10, ge=1, le=100, description="Page size"),
    completed: Optional[bool] = Query(None, description="Filter by completion state"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    due_before: Optional[date] = Query(None, description="Only tasks due on or before this date"),
    due_after: Optional[date] = Query(None, description="Only tasks due on or after this date"),
    q: Optional[str] = Query(
        None, min_length=1, max_length=255, description="Case-insensitive search in title/description"
    ),
    sort_by: TaskSortField = Query(TaskSortField.DUE_DATE, description="Sort column"),
    sort_desc: bool = Query(False, description="Sort descending"),
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
) -> TaskListResponse:
    """List the caller's tasks. Filtering, ordering and paging happen in SQL."""
    if due_before is not None and due_after is not None and due_before < due_after:
        raise HTTPException(
            status_code=422,  # HTTP_422_* constant name differs across Starlette versions
            detail="due_before must not be earlier than due_after",
        )
    page, total = storage.list_tasks(
        user_id,
        completed=completed,
        priority=priority.value if priority else None,
        due_before=due_before,
        due_after=due_after,
        search=q,
        sort_by=sort_by.value,
        sort_desc=sort_desc,
        skip=skip,
        limit=limit,
    )
    return TaskListResponse(
        total=total,
        tasks=[TaskResponse.from_model(t) for t in page],
        page=skip // limit + 1,
        page_size=limit,
        pages=math.ceil(total / limit) if total else 0,
    )


@router.get("/stats", response_model=TaskStatsResponse)
async def task_statistics(
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
) -> TaskStatsResponse:
    """
    Workload summary: counts, overdue load, completion and on-time rates,
    completion latency, and a per-priority breakdown.
    """
    stats = compute_statistics(storage.get_user_tasks(user_id), now=datetime.now(timezone.utc))
    return TaskStatsResponse.model_validate(stats.to_dict())


@router.get("/next", response_model=NextTasksResponse)
async def next_tasks(
    limit: int = Query(5, ge=1, le=50, description="How many tasks to recommend"),
    calibrated: bool = Query(
        False,
        description="Derive the urgency curve from your own completion history "
        "(falls back to the defaults with fewer than 5 completed tasks)",
    ),
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
) -> NextTasksResponse:
    """
    The caller's most urgent pending tasks, ranked by the urgency model in
    ``task_manager_pro.analytics.urgency`` (priority-weighted logistic decay
    towards the due date), optionally calibrated per user.
    """
    now = datetime.now(timezone.utc)
    all_tasks = storage.get_user_tasks(user_id)
    if calibrated:
        result = calibrate_params(all_tasks)
        params = result.params
        params_out = UrgencyParamsResponse(
            half_urgency_days=params.half_urgency_days,
            temperature_days=params.temperature_days,
            calibrated=result.calibrated,
            samples=result.samples,
            lead_days_median=result.lead_days_median,
        )
    else:
        params = DEFAULT_PARAMS
        params_out = UrgencyParamsResponse(
            half_urgency_days=params.half_urgency_days,
            temperature_days=params.temperature_days,
            calibrated=False,
            samples=0,
            lead_days_median=None,
        )
    ranked = rank_tasks((t for t in all_tasks if not t.completed), now=now, params=params)[:limit]
    return NextTasksResponse(
        as_of=now,
        params=params_out,
        tasks=[
            TaskWithUrgency(
                **TaskResponse.from_model(task).model_dump(),
                urgency=score,
                days_until_due=days_until_due(task.due_date, now),
            )
            for task, score in ranked
        ],
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
) -> TaskResponse:
    """Fetch one of the caller's tasks. Other users' tasks are reported as 404."""
    task = storage.get_user_task(user_id, task_id)
    if not task:
        raise _NOT_FOUND
    return TaskResponse.from_model(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
) -> TaskResponse:
    """Partially update one of the caller's tasks."""
    if not storage.get_user_task(user_id, task_id):
        raise _NOT_FOUND
    changes = task_data.model_dump(exclude_unset=True, exclude_none=True)
    if "priority" in changes:
        changes["priority"] = TaskPriority(changes["priority"]).value
    updated = storage.update_task(task_id, **changes)
    if not updated:
        raise _NOT_FOUND
    return TaskResponse.from_model(updated)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
) -> None:
    """Delete one of the caller's tasks."""
    if not storage.get_user_task(user_id, task_id):
        raise _NOT_FOUND
    storage.delete_task(task_id)
