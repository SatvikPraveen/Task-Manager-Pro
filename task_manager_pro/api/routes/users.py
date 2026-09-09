"""
api/routes/users.py

User management endpoints for profile and settings.
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status, Depends
from task_manager_pro.schemas.user import UserResponse, UserUpdate
from task_manager_pro.api.dependencies import get_current_user, get_storage
from task_manager_pro.storage.sql_storage import SQLStorage

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
):
    """
    Get current user's profile information.
    
    Args:
        user_id (str): Current user ID from JWT
        storage (SQLStorage): Database storage
        
    Returns:
        UserResponse: Current user information
    """
    user = storage.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        email_reminders_enabled=user.email_reminders_enabled,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
):
    """
    Update current user's profile.
    
    Args:
        user_data (UserUpdate): Updated user data
        user_id (str): Current user ID from JWT
        storage (SQLStorage): Database storage
        
    Returns:
        UserResponse: Updated user information
    """
    update_dict: Dict[str, Any] = {}
    if user_data.email is not None:
        update_dict["email"] = user_data.email
    if user_data.email_reminders_enabled is not None:
        update_dict["email_reminders_enabled"] = user_data.email_reminders_enabled
    
    updated_user = storage.update_user(user_id, **update_dict)
    
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        email_reminders_enabled=updated_user.email_reminders_enabled,
        created_at=updated_user.created_at.isoformat(),
        updated_at=updated_user.updated_at.isoformat(),
    )


@router.post("/me/toggle-reminders", response_model=UserResponse)
async def toggle_email_reminders(
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
):
    """
    Toggle email reminders for current user.
    
    Args:
        user_id (str): Current user ID from JWT
        storage (SQLStorage): Database storage
        
    Returns:
        UserResponse: Updated user information
    """
    user = storage.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_status = not user.email_reminders_enabled
    updated_user = storage.update_user(user_id, email_reminders_enabled=new_status)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        email_reminders_enabled=updated_user.email_reminders_enabled,
        created_at=updated_user.created_at.isoformat(),
        updated_at=updated_user.updated_at.isoformat(),
    )
