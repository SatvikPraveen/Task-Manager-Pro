"""
api/routes/auth.py

Registration, login and token refresh.

Login is constant-time with respect to whether the username exists (see
``SQLStorage.verify_user_password``), and every failure returns the same
message so the API does not leak which accounts exist.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from task_manager_pro.api.dependencies import get_current_user, get_storage
from task_manager_pro.config import get_settings
from task_manager_pro.schemas.user import TokenResponse, UserLogin, UserRegister, UserResponse, UserWithToken
from task_manager_pro.storage.sql_storage import SQLStorage
from task_manager_pro.utils.security import create_access_token

router = APIRouter()

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid username or password",
    headers={"WWW-Authenticate": "Bearer"},
)


def _issue_token(user_id: str) -> tuple[str, int]:
    minutes = get_settings().access_token_expire_minutes
    token = create_access_token({"sub": user_id}, expires_delta=timedelta(minutes=minutes))
    return token, minutes * 60


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, storage: SQLStorage = Depends(get_storage)) -> UserResponse:
    """Create a new account. Returns ``400`` if the username is taken."""
    try:
        user = storage.create_user(
            username=user_data.username,
            password=user_data.password,
            email=user_data.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserResponse.from_model(user)


@router.post("/login", response_model=UserWithToken)
async def login(credentials: UserLogin, storage: SQLStorage = Depends(get_storage)) -> UserWithToken:
    """Exchange username/password for a bearer token."""
    if not storage.verify_user_password(credentials.username, credentials.password):
        raise _INVALID_CREDENTIALS
    user = storage.get_user_by_username(credentials.username)
    if not user:  # pragma: no cover - race between verify and fetch
        raise _INVALID_CREDENTIALS

    token, expires_in = _issue_token(user.id)
    return UserWithToken(
        user=UserResponse.from_model(user),
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
    )


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    user_id: str = Depends(get_current_user),
    storage: SQLStorage = Depends(get_storage),
) -> TokenResponse:
    """
    Issue a fresh access token for the caller of a still-valid bearer token.

    The token is taken from the ``Authorization`` header, never from the query
    string, so it does not end up in access logs.
    """
    if storage.get_user(user_id) is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    token, expires_in = _issue_token(user_id)
    return TokenResponse(access_token=token, token_type="bearer", expires_in=expires_in)
