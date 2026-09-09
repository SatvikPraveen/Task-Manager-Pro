"""
api/routes/tasks.py

Task management endpoints for CRUD operations.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Any, Dict, Optional
from task_manager_pro.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskListResponse, TaskPriority
from task_manager_pro.api.dependencies import get_current_user, get_storage
from task_manager_pro.storage.sql_storage import SQLStorage

router = APIRouter()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
):
    """
    Create a new task for the current user.
    
    Args:
        task_data (TaskCreate): Task creation data
        user_id (str): Current user ID from JWT
        storage (SQLStorage): Database storage
        
    Returns:
        TaskResponse: Created task
    """
    try:
        task = storage.create_task(
            user_id=user_id,
            title=task_data.title,
            description=task_data.description,
            due_date=task_data.due_date,
            priority=task_data.priority.value,
        )
        return TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            due_date=task.due_date.strftime("%Y-%m-%d"),
            priority=TaskPriority(task.priority),
            completed=task.completed,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    completed: Optional[bool] = None,
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
):
    """
    List tasks for the current user with pagination and filtering.
    
    Args:
        skip (int): Number of tasks to skip
        limit (int): Number of tasks to return
        completed (Optional[bool]): Filter by completion status
        user_id (str): Current user ID from JWT
        storage (SQLStorage): Database storage
        
    Returns:
        TaskListResponse: Paginated list of tasks
    """
    tasks = storage.get_user_tasks(user_id, completed=completed)
    total = len(tasks)
    paginated_tasks = tasks[skip : skip + limit]
    
    return TaskListResponse(
        total=total,
        tasks=[
            TaskResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                due_date=task.due_date.strftime("%Y-%m-%d"),
                priority=TaskPriority(task.priority),
                completed=task.completed,
                created_at=task.created_at.isoformat(),
                updated_at=task.updated_at.isoformat(),
                completed_at=task.completed_at.isoformat() if task.completed_at else None,
            )
            for task in paginated_tasks
        ],
        page=skip // limit + 1,
        page_size=limit,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
):
    """
    Get a specific task by ID.
    
    Args:
        task_id (str): Task ID
        user_id (str): Current user ID from JWT
        storage (SQLStorage): Database storage
        
    Returns:
        TaskResponse: Task details
        
    Raises:
        HTTPException: 404 if task not found or doesn't belong to user
    """
    task = storage.get_task(task_id)
    
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        due_date=task.due_date.strftime("%Y-%m-%d"),
        priority=TaskPriority(task.priority),
        completed=task.completed,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
    )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
):
    """
    Update a task.
    
    Args:
        task_id (str): Task ID
        task_data (TaskUpdate): Updated task data
        user_id (str): Current user ID from JWT
        storage (SQLStorage): Database storage
        
    Returns:
        TaskResponse: Updated task
        
    Raises:
        HTTPException: 404 if task not found
    """
    task = storage.get_task(task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_dict: Dict[str, Any] = {}
    if task_data.title is not None:
        update_dict["title"] = task_data.title
    if task_data.description is not None:
        update_dict["description"] = task_data.description
    if task_data.due_date is not None:
        update_dict["due_date"] = task_data.due_date
    if task_data.priority is not None:
        update_dict["priority"] = task_data.priority.value
    if task_data.completed is not None:
        update_dict["completed"] = task_data.completed

    updated_task = storage.update_task(task_id, **update_dict)
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(
        id=updated_task.id,
        title=updated_task.title,
        description=updated_task.description,
        due_date=updated_task.due_date.strftime("%Y-%m-%d"),
        priority=TaskPriority(updated_task.priority),
        completed=updated_task.completed,
        created_at=updated_task.created_at.isoformat(),
        updated_at=updated_task.updated_at.isoformat(),
        completed_at=updated_task.completed_at.isoformat() if updated_task.completed_at else None,
    )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
):
    """
    Delete a task.
    
    Args:
        task_id (str): Task ID
        user_id (str): Current user ID from JWT
        storage (SQLStorage): Database storage
        
    Raises:
        HTTPException: 404 if task not found
    """
    task = storage.get_task(task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")
    
    storage.delete_task(task_id)
