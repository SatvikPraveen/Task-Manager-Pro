"""
storage/models.py

SQLAlchemy ORM models for User and Task entities.
Replaces JSON storage with relational database tables.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from task_manager_pro.storage.database import Base
import uuid


def _utcnow() -> datetime:
    """Timezone-aware replacement for the deprecated datetime.utcnow()."""
    return datetime.now(timezone.utc)


class UserModel(Base):
    """SQLAlchemy model for User entity."""
    
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    email_reminders_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    
    # Relationship
    tasks = relationship("TaskModel", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<UserModel(id={self.id}, username={self.username}, email={self.email})>"


class TaskModel(Base):
    """SQLAlchemy model for Task entity."""
    
    __tablename__ = "tasks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=False, index=True)
    completed = Column(Boolean, default=False, index=True)
    priority = Column(String(20), default="medium")  # low, medium, high
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("UserModel", back_populates="tasks")
    
    def __repr__(self):
        return f"<TaskModel(id={self.id}, title={self.title}, completed={self.completed})>"
