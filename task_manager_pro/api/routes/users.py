"""
api/routes/users.py

Profile endpoints for the authenticated user.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from task_manager_pro.api.dependencies import get_current_user, get_storage
from task_manager_pro.schemas.user import UserResponse, UserUpdate
from task_manager_pro.storage.sql_storage import SQLStorage

router = APIRouter()

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
) -> UserResponse:
    """Return the caller's profile."""
    user = storage.get_user(user_id)
    if not user:
        raise _NOT_FOUND
    return UserResponse.from_model(user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
) -> UserResponse:
    """Update email and/or reminder preference."""
    changes = user_data.model_dump(exclude_unset=True, exclude_none=True)
    updated = storage.update_user(user_id, **changes)
    if not updated:
        raise _NOT_FOUND
    return UserResponse.from_model(updated)


@router.post("/me/toggle-reminders", response_model=UserResponse)
async def toggle_email_reminders(
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
) -> UserResponse:
    """Flip the caller's email-reminder preference."""
    user = storage.get_user(user_id)
    if not user:
        raise _NOT_FOUND
    updated = storage.update_user(user_id, email_reminders_enabled=not user.email_reminders_enabled)
    if not updated:
        raise _NOT_FOUND
    return UserResponse.from_model(updated)
