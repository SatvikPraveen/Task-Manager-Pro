"""
storage/models.py

SQLAlchemy ORM models for the ``users`` and ``tasks`` tables.

Timestamps are timezone-aware UTC. On PostgreSQL they map to ``timestamptz``;
SQLite stores them as ISO strings and returns naive values, which the API
layer treats as UTC.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from task_manager_pro.storage.database import Base


def _utcnow() -> datetime:
    """Timezone-aware replacement for the deprecated ``datetime.utcnow()``."""
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


class UserModel(Base):
    """A registered account."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    email_reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    tasks: Mapped[List["TaskModel"]] = relationship(
        "TaskModel", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, username={self.username}, email={self.email})>"


class TaskModel(Base):
    """A task owned by exactly one user."""

    __tablename__ = "tasks"
    __table_args__ = (
        # Covers the dominant query: "this user's (pending) tasks ordered by due date".
        Index("ix_tasks_user_completed_due", "user_id", "completed", "due_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)  # low|medium|high
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<TaskModel(id={self.id}, title={self.title}, completed={self.completed})>"
