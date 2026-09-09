"""
storage/sql_storage.py

SQLAlchemy-based storage implementation for Task Manager PRO.
Replaces JSON storage with relational database support.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from task_manager_pro.storage.interface import StorageInterface
from task_manager_pro.storage.database import SessionLocal, init_db
from task_manager_pro.storage.models import UserModel, TaskModel
from task_manager_pro.utils.security import hash_password, verify_password
import uuid


class SQLStorage(StorageInterface):
    """SQL-based storage implementation using SQLAlchemy."""
    
    def __init__(self):
        """Initialize SQL storage and create tables if needed."""
        init_db()
    
    def load_data(self) -> Dict[str, Any]:
        """
        Load all data from database (for backwards compatibility with interface).
        Returns structured dict with users and tasks.
        
        Returns:
            Dict[str, Any]: Dictionary with 'users' and 'tasks' keys
        """
        db = SessionLocal()
        try:
            users = db.query(UserModel).all()
            tasks = db.query(TaskModel).all()
            
            return {
                "users": [self._user_model_to_dict(u) for u in users],
                "tasks": [self._task_model_to_dict(t) for t in tasks],
            }
        finally:
            db.close()
    
    def save_data(self, data: Dict[str, Any]) -> None:
        """
        Save data to database (for backwards compatibility).
        Not typically used with SQL storage - operations modify DB directly.
        
        Args:
            data (Dict[str, Any]): Dictionary with 'users' and 'tasks' keys
        """
        # This is mainly for compatibility. Real operations use direct methods.
        pass
    
    # User operations
    def create_user(self, username: str, password: str, email: Optional[str] = None) -> UserModel:
        """
        Create a new user in the database.
        
        Args:
            username (str): Unique username
            password (str): Plain text password (will be hashed)
            email (Optional[str]): Optional email address
            
        Returns:
            UserModel: Created user model
        """
        db = SessionLocal()
        try:
            existing_user = db.query(UserModel).filter(UserModel.username == username).first()
            if existing_user:
                raise ValueError(f"User '{username}' already exists")
            
            password_hash = hash_password(password)
            user = UserModel(
                username=username,
                password_hash=password_hash,
                email=email,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()
    
    def get_user(self, user_id: str) -> Optional[UserModel]:
        """Get user by ID."""
        db = SessionLocal()
        try:
            return db.query(UserModel).filter(UserModel.id == user_id).first()
        finally:
            db.close()
    
    def get_user_by_username(self, username: str) -> Optional[UserModel]:
        """Get user by username."""
        db = SessionLocal()
        try:
            return db.query(UserModel).filter(UserModel.username == username).first()
        finally:
            db.close()
    
    def verify_user_password(self, username: str, password: str) -> bool:
        """
        Verify user password.
        
        Args:
            username (str): Username
            password (str): Plain text password to verify
            
        Returns:
            bool: True if credentials are valid
        """
        user = self.get_user_by_username(username)
        if not user:
            return False
        return verify_password(password, user.password_hash)
    
    def update_user(self, user_id: str, **kwargs) -> Optional[UserModel]:
        """
        Update user fields.
        
        Args:
            user_id (str): User ID
            **kwargs: Fields to update (e.g., email, email_reminders_enabled)
            
        Returns:
            Optional[UserModel]: Updated user or None if not found
        """
        db = SessionLocal()
        try:
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            if not user:
                return None
            
            for key, value in kwargs.items():
                if hasattr(user, key) and key != "password_hash":
                    setattr(user, key, value)
                elif key == "password" and value:
                    user.password_hash = hash_password(value)
            
            user.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()
    
    # Task operations
    def create_task(self, user_id: str, title: str, description: Optional[str], due_date: str,
                   priority: str = "medium") -> TaskModel:
        """
        Create a new task.
        
        Args:
            user_id (str): Owner user ID
            title (str): Task title
            description (str): Task description
            due_date (str): Due date in YYYY-MM-DD format
            priority (str): Task priority (low/medium/high)
            
        Returns:
            TaskModel: Created task model
        """
        db = SessionLocal()
        try:
            due_datetime = datetime.strptime(due_date, "%Y-%m-%d")
            task = TaskModel(
                user_id=user_id,
                title=title,
                description=description,
                due_date=due_datetime,
                priority=priority,
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return task
        finally:
            db.close()
    
    def get_task(self, task_id: str) -> Optional[TaskModel]:
        """Get task by ID."""
        db = SessionLocal()
        try:
            return db.query(TaskModel).filter(TaskModel.id == task_id).first()
        finally:
            db.close()
    
    def get_user_tasks(self, user_id: str, completed: Optional[bool] = None) -> List[TaskModel]:
        """
        Get tasks for a user.
        
        Args:
            user_id (str): User ID
            completed (Optional[bool]): Filter by completion status
            
        Returns:
            List[TaskModel]: List of tasks
        """
        db = SessionLocal()
        try:
            query = db.query(TaskModel).filter(TaskModel.user_id == user_id)
            if completed is not None:
                query = query.filter(TaskModel.completed == completed)
            return query.order_by(TaskModel.due_date).all()
        finally:
            db.close()
    
    def update_task(self, task_id: str, **kwargs) -> Optional[TaskModel]:
        """
        Update task fields.
        
        Args:
            task_id (str): Task ID
            **kwargs: Fields to update
            
        Returns:
            Optional[TaskModel]: Updated task or None if not found
        """
        db = SessionLocal()
        try:
            task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
            if not task:
                return None
            
            for key, value in kwargs.items():
                if key == "due_date" and isinstance(value, str):
                    value = datetime.strptime(value, "%Y-%m-%d")
                if hasattr(task, key):
                    setattr(task, key, value)
            
            if "completed" in kwargs and kwargs["completed"] and not task.completed_at:
                task.completed_at = datetime.now(timezone.utc)

            task.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(task)
            return task
        finally:
            db.close()
    
    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task.
        
        Args:
            task_id (str): Task ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        db = SessionLocal()
        try:
            task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
            if not task:
                return False
            db.delete(task)
            db.commit()
            return True
        finally:
            db.close()
    
    def get_due_tasks(self, before_date: Optional[str] = None) -> List[TaskModel]:
        """
        Get tasks that are due or overdue.
        
        Args:
            before_date (Optional[str]): Date in YYYY-MM-DD format. If None, uses today.
            
        Returns:
            List[TaskModel]: List of due/overdue tasks
        """
        db = SessionLocal()
        try:
            if before_date:
                cutoff_date = datetime.strptime(before_date, "%Y-%m-%d")
            else:
                cutoff_date = datetime.today()
            
            return db.query(TaskModel).filter(
                and_(
                    TaskModel.due_date <= cutoff_date,
                    TaskModel.completed == False
                )
            ).order_by(TaskModel.due_date).all()
        finally:
            db.close()
    
    # Helper methods
    def _user_model_to_dict(self, user: UserModel) -> Dict[str, Any]:
        """Convert UserModel to dictionary."""
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "email_reminders_enabled": user.email_reminders_enabled,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }
    
    def _task_model_to_dict(self, task: TaskModel) -> Dict[str, Any]:
        """Convert TaskModel to dictionary."""
        return {
            "id": task.id,
            "user_id": task.user_id,
            "title": task.title,
            "description": task.description,
            "due_date": task.due_date.strftime("%Y-%m-%d"),
            "completed": task.completed,
            "priority": task.priority,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
