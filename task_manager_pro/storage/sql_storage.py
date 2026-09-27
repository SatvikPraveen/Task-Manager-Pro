"""
storage/sql_storage.py

Repository over the SQLAlchemy models.

Every public method opens its own short-lived session from an injectable
``session_factory`` and returns *detached* ORM instances. That keeps the API
layer free of session lifecycle concerns and lets tests bind a repository to
a throw-away engine.

Listing is done in SQL (filter → order → offset/limit) with a separate
``COUNT(*)`` so that pagination cost does not grow with the user's history.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from task_manager_pro.storage.database import SessionLocal, engine, init_db
from task_manager_pro.storage.interface import StorageInterface
from task_manager_pro.storage.models import TaskModel, UserModel
from task_manager_pro.utils.security import hash_password, verify_password, verify_password_dummy

SORTABLE_COLUMNS = {
    "due_date": TaskModel.due_date,
    "created_at": TaskModel.created_at,
    "updated_at": TaskModel.updated_at,
    "priority": TaskModel.priority,
    "title": TaskModel.title,
}


def _to_datetime(value: str | date | datetime) -> datetime:
    """Normalise a due date (string, date or datetime) to a UTC midnight datetime."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    parsed = datetime.strptime(value, "%Y-%m-%d")
    return parsed.replace(tzinfo=timezone.utc)


class SQLStorage(StorageInterface):
    """SQL-backed repository for users and tasks."""

    def __init__(self, session_factory: Optional[sessionmaker[Session]] = None, *, create_tables: bool = True):
        self._session_factory: sessionmaker[Session] = session_factory or SessionLocal
        if create_tables:
            bind = self._session_factory.kw.get("bind", engine)
            init_db(bind)

    @contextmanager
    def _session(self) -> Iterator[Session]:
        db = self._session_factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ------------------------------------------------------------------ #
    # StorageInterface compatibility                                     #
    # ------------------------------------------------------------------ #
    def load_data(self) -> dict[str, Any]:
        """Dump all users and tasks as plain dicts (interface compatibility)."""
        with self._session() as db:
            users = db.scalars(select(UserModel)).all()
            tasks = db.scalars(select(TaskModel)).all()
            return {
                "users": [self._user_model_to_dict(u) for u in users],
                "tasks": [self._task_model_to_dict(t) for t in tasks],
            }

    def save_data(self, data: dict[str, Any]) -> None:
        """No-op: SQL operations persist immediately."""

    # ------------------------------------------------------------------ #
    # Users                                                              #
    # ------------------------------------------------------------------ #
    def create_user(self, username: str, password: str, email: Optional[str] = None) -> UserModel:
        with self._session() as db:
            exists = db.scalar(select(UserModel.id).where(UserModel.username == username))
            if exists:
                raise ValueError(f"User '{username}' already exists")
            user = UserModel(username=username, password_hash=hash_password(password), email=email)
            db.add(user)
            db.flush()
            db.refresh(user)
            db.expunge(user)
            return user

    def get_user(self, user_id: str) -> Optional[UserModel]:
        with self._session() as db:
            user = db.get(UserModel, user_id)
            if user:
                db.expunge(user)
            return user

    def get_user_by_username(self, username: str) -> Optional[UserModel]:
        with self._session() as db:
            user = db.scalar(select(UserModel).where(UserModel.username == username))
            if user:
                db.expunge(user)
            return user

    def verify_user_password(self, username: str, password: str) -> bool:
        """
        Check credentials. Takes the same time whether or not the user exists.
        """
        user = self.get_user_by_username(username)
        if not user:
            verify_password_dummy(password)
            return False
        return verify_password(password, user.password_hash)

    def update_user(self, user_id: str, **fields: Any) -> Optional[UserModel]:
        with self._session() as db:
            user = db.get(UserModel, user_id)
            if not user:
                return None
            for key, value in fields.items():
                if key == "password":
                    if value:
                        user.password_hash = hash_password(value)
                elif key != "password_hash" and hasattr(user, key):
                    setattr(user, key, value)
            user.updated_at = datetime.now(timezone.utc)
            db.flush()
            db.refresh(user)
            db.expunge(user)
            return user

    # ------------------------------------------------------------------ #
    # Tasks                                                              #
    # ------------------------------------------------------------------ #
    def create_task(
        self,
        user_id: str,
        title: str,
        description: Optional[str],
        due_date: str | date | datetime,
        priority: str = "medium",
    ) -> TaskModel:
        with self._session() as db:
            task = TaskModel(
                user_id=user_id,
                title=title,
                description=description,
                due_date=_to_datetime(due_date),
                priority=priority,
            )
            db.add(task)
            db.flush()
            db.refresh(task)
            db.expunge(task)
            return task

    def get_task(self, task_id: str) -> Optional[TaskModel]:
        with self._session() as db:
            task = db.get(TaskModel, task_id)
            if task:
                db.expunge(task)
            return task

    def get_user_task(self, user_id: str, task_id: str) -> Optional[TaskModel]:
        """Fetch a task only if it belongs to ``user_id`` (ownership in the query)."""
        with self._session() as db:
            task = db.scalar(select(TaskModel).where(TaskModel.id == task_id, TaskModel.user_id == user_id))
            if task:
                db.expunge(task)
            return task

    def list_tasks(
        self,
        user_id: str,
        *,
        completed: Optional[bool] = None,
        priority: Optional[str] = None,
        due_before: Optional[date] = None,
        due_after: Optional[date] = None,
        search: Optional[str] = None,
        sort_by: str = "due_date",
        sort_desc: bool = False,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[list[TaskModel], int]:
        """
        Filter, sort and paginate a user's tasks in SQL.

        Returns ``(page, total)`` where ``total`` is the count *after*
        filtering, so clients can compute the number of pages.
        """
        column = SORTABLE_COLUMNS.get(sort_by)
        if column is None:
            raise ValueError(f"Cannot sort by '{sort_by}'. Choose one of: {', '.join(SORTABLE_COLUMNS)}")

        criteria = [TaskModel.user_id == user_id]
        if completed is not None:
            criteria.append(TaskModel.completed == completed)
        if priority is not None:
            criteria.append(TaskModel.priority == priority)
        if due_before is not None:
            criteria.append(TaskModel.due_date <= _to_datetime(due_before))
        if due_after is not None:
            criteria.append(TaskModel.due_date >= _to_datetime(due_after))
        if search:
            pattern = f"%{search.strip()}%"
            criteria.append(or_(TaskModel.title.ilike(pattern), TaskModel.description.ilike(pattern)))

        order = column.desc() if sort_desc else column.asc()
        with self._session() as db:
            total = db.scalar(select(func.count()).select_from(TaskModel).where(*criteria)) or 0
            stmt = (
                select(TaskModel)
                .where(*criteria)
                .order_by(order, TaskModel.id.asc())  # deterministic tie-break
                .offset(skip)
                .limit(limit)
            )
            page = list(db.scalars(stmt).all())
            for task in page:
                db.expunge(task)
            return page, int(total)

    def get_user_tasks(self, user_id: str, completed: Optional[bool] = None) -> list[TaskModel]:
        """All of a user's tasks ordered by due date (no pagination)."""
        with self._session() as db:
            stmt = select(TaskModel).where(TaskModel.user_id == user_id)
            if completed is not None:
                stmt = stmt.where(TaskModel.completed == completed)
            tasks = list(db.scalars(stmt.order_by(TaskModel.due_date, TaskModel.id)).all())
            for task in tasks:
                db.expunge(task)
            return tasks

    def update_task(self, task_id: str, **fields: Any) -> Optional[TaskModel]:
        with self._session() as db:
            task = db.get(TaskModel, task_id)
            if not task:
                return None
            for key, value in fields.items():
                if key == "due_date":
                    value = _to_datetime(value)
                if hasattr(task, key):
                    setattr(task, key, value)

            if "completed" in fields:
                if fields["completed"] and task.completed_at is None:
                    task.completed_at = datetime.now(timezone.utc)
                elif not fields["completed"]:
                    task.completed_at = None

            task.updated_at = datetime.now(timezone.utc)
            db.flush()
            db.refresh(task)
            db.expunge(task)
            return task

    def delete_task(self, task_id: str) -> bool:
        with self._session() as db:
            task = db.get(TaskModel, task_id)
            if not task:
                return False
            db.delete(task)
            return True

    def get_due_tasks(self, before_date: Optional[str] = None) -> list[TaskModel]:
        """Pending tasks due on or before ``before_date`` (default: today, UTC)."""
        cutoff = _to_datetime(before_date) if before_date else datetime.now(timezone.utc)
        with self._session() as db:
            stmt = (
                select(TaskModel)
                .where(TaskModel.due_date <= cutoff, TaskModel.completed.is_(False))
                .order_by(TaskModel.due_date, TaskModel.id)
            )
            tasks = list(db.scalars(stmt).all())
            for task in tasks:
                db.expunge(task)
            return tasks

    # ------------------------------------------------------------------ #
    # Serialisation helpers                                              #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _user_model_to_dict(user: UserModel) -> dict[str, Any]:
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "email_reminders_enabled": user.email_reminders_enabled,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }

    @staticmethod
    def _task_model_to_dict(task: TaskModel) -> dict[str, Any]:
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
