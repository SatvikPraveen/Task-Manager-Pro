"""
storage/models.py

SQLAlchemy ORM models for User and Task entities.
Replaces JSON storage with relational database tables.
"""

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import List, Optional
from task_manager_pro.storage.database import Base
import uuid


def _utcnow() -> datetime:
    """Timezone-aware replacement for the deprecated datetime.utcnow()."""
    return datetime.now(timezone.utc)


class UserModel(Base):
    """SQLAlchemy model for User entity."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    email_reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationship
    tasks: Mapped[List["TaskModel"]] = relationship(
        "TaskModel", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, username={self.username}, email={self.email})>"


class TaskModel(Base):
    """SQLAlchemy model for Task entity."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # low, medium, high
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<TaskModel(id={self.id}, title={self.title}, completed={self.completed})>"
