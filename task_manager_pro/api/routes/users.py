"""
api/routes/users.py

Profile endpoints for the authenticated user.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from task_manager_pro.api.dependencies import get_current_user, get_storage
from task_manager_pro.schemas.user import PasswordChange, UserResponse, UserUpdate
from task_manager_pro.storage.sql_storage import SQLStorage
from task_manager_pro.utils.security import verify_password

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
    changes = user_data.model_dump(exclude_unset=True)
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


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: PasswordChange,
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
) -> Response:
    """Set a new password after checking the current one (e.g. replacing a migration one-time password)."""
    user = storage.get_user(user_id)
    if not user:
        raise _NOT_FOUND
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    storage.update_user(user_id, password=body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
