"""
schemas/user.py

Pydantic v2 request/response models for authentication and user profiles.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

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

    @field_validator("password")
    @classmethod
    def _password_fits_bcrypt(cls, value: str) -> str:
        # bcrypt ignores everything past 72 bytes, so a longer password would
        # silently be weaker than the user thinks. Multi-byte characters count extra.
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes (UTF-8)")
        return value


class UserLogin(BaseModel):
    """Login payload."""

    username: str = Field(..., max_length=50)
    password: str = Field(..., max_length=255)


class UserUpdate(BaseModel):
    """Profile update; every field optional. Send ``"email": null`` to remove the email."""

    email: Optional[EmailStr] = None
    email_reminders_enabled: Optional[bool] = None

    @model_validator(mode="after")
    def _reminders_flag_not_null(self) -> UserUpdate:
        if "email_reminders_enabled" in self.model_fields_set and self.email_reminders_enabled is None:
            raise ValueError("email_reminders_enabled cannot be null")
        return self


class UserResponse(BaseModel):
    """Public view of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: Optional[str] = None
    email_reminders_enabled: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def _assume_utc(cls, value: datetime) -> datetime:
        # SQLite drops the offset on read; every stored timestamp is UTC.
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

    @classmethod
    def from_model(cls, user: Any) -> UserResponse:
        return cls.model_validate(user)


class TokenResponse(BaseModel):
    """A bare access token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Seconds until the token expires")


class UserWithToken(TokenResponse):
    """Login response: the user plus their access token."""

    user: UserResponse
