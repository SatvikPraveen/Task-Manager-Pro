"""
schemas/user.py

Pydantic v2 request/response models for authentication and user profiles.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


class UserRegister(BaseModel):
    """Registration payload."""

    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=8, max_length=255, description="Password (min 8 chars)")
    email: Optional[EmailStr] = Field(None, description="Email address for reminders")

    @field_validator("username")
    @classmethod
    def _username_alphanumeric(cls, value: str) -> str:
        if not _USERNAME_RE.match(value):
            raise ValueError("Username must contain only alphanumeric characters and underscores")
        return value


class UserLogin(BaseModel):
    """Login payload."""

    username: str = Field(..., max_length=50)
    password: str = Field(..., max_length=255)


class UserUpdate(BaseModel):
    """Profile update; every field optional."""

    email: Optional[EmailStr] = None
    email_reminders_enabled: Optional[bool] = None


class UserResponse(BaseModel):
    """Public view of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: Optional[str] = None
    email_reminders_enabled: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, user: Any) -> "UserResponse":
        return cls.model_validate(user)


class TokenResponse(BaseModel):
    """A bare access token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Seconds until the token expires")


class UserWithToken(TokenResponse):
    """Login response: the user plus their access token."""

    user: UserResponse
