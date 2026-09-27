"""
tests/test_storage.py

Repository tests against a private in-memory engine, exercising the
session-factory injection point, SQL-side filtering/sorting/pagination and
ownership checks.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.orm import sessionmaker

from task_manager_pro.storage.database import Base, make_engine
from task_manager_pro.storage.sql_storage import SQLStorage


@pytest.fixture
def storage() -> SQLStorage:
    engine = make_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return SQLStorage(sessionmaker(bind=engine), create_tables=False)


@pytest.fixture
def user_id(storage: SQLStorage) -> str:
    return storage.create_user("alice", "password123", "alice@example.com").id


def _seed(storage: SQLStorage, user_id: str) -> None:
    storage.create_task(user_id, "Write paper", "draft intro", "2030-01-10", "high")
    storage.create_task(user_id, "Run experiments", None, "2030-01-05", "medium")
    storage.create_task(user_id, "Buy milk", "2 litres", "2030-01-01", "low")
    done = storage.create_task(user_id, "Read reviews", "carefully", "2029-12-31", "high")
    storage.update_task(done.id, completed=True)


def test_create_user_rejects_duplicate(storage):
    storage.create_user("bob", "password123")
    with pytest.raises(ValueError, match="already exists"):
        storage.create_user("bob", "another-pass")


def test_verify_password_and_unknown_user_constant_path(storage):
    storage.create_user("carol", "password123")
    assert storage.verify_user_password("carol", "password123")
    assert not storage.verify_user_password("carol", "wrong")
    assert not storage.verify_user_password("nobody", "whatever")


def test_update_user_hashes_password_and_ignores_hash_field(storage):
    user = storage.create_user("dave", "password123")
    updated = storage.update_user(user.id, password="newpassword1", password_hash="junk", email="d@x.io")
    assert updated is not None
    assert updated.email == "d@x.io"
    assert updated.password_hash != "junk"
    assert storage.verify_user_password("dave", "newpassword1")


def test_list_defaults_sort_by_due_date_ascending(storage, user_id):
    _seed(storage, user_id)
    page, total = storage.list_tasks(user_id, limit=10)
    assert total == 4
    assert [t.title for t in page] == ["Read reviews", "Buy milk", "Run experiments", "Write paper"]


def test_list_filters_are_conjunctive(storage, user_id):
    _seed(storage, user_id)
    page, total = storage.list_tasks(user_id, completed=False, priority="high")
    assert total == 1 and page[0].title == "Write paper"

    page, total = storage.list_tasks(user_id, due_after=date(2030, 1, 2), due_before=date(2030, 1, 6))
    assert [t.title for t in page] == ["Run experiments"]

    page, total = storage.list_tasks(user_id, search="MILK")
    assert total == 1 and page[0].title == "Buy milk"

    page, total = storage.list_tasks(user_id, search="carefully")
    assert [t.title for t in page] == ["Read reviews"]


def test_list_paginates_in_sql_with_stable_total(storage, user_id):
    _seed(storage, user_id)
    first, total = storage.list_tasks(user_id, skip=0, limit=3)
    second, total2 = storage.list_tasks(user_id, skip=3, limit=3)
    assert total == total2 == 4
    assert len(first) == 3 and len(second) == 1
    assert {t.id for t in first}.isdisjoint({t.id for t in second})


def test_list_sort_desc_and_invalid_column(storage, user_id):
    _seed(storage, user_id)
    page, _ = storage.list_tasks(user_id, sort_by="title", sort_desc=True)
    assert [t.title for t in page] == sorted((t.title for t in page), reverse=True)
    with pytest.raises(ValueError, match="Cannot sort by"):
        storage.list_tasks(user_id, sort_by="password_hash")


def test_get_user_task_enforces_ownership(storage, user_id):
    other = storage.create_user("mallory", "password123").id
    task = storage.create_task(user_id, "Private", None, "2030-01-01")
    assert storage.get_user_task(user_id, task.id) is not None
    assert storage.get_user_task(other, task.id) is None


def test_completing_and_reopening_manages_completed_at(storage, user_id):
    task = storage.create_task(user_id, "Toggle", None, "2030-01-01")
    done = storage.update_task(task.id, completed=True)
    assert done is not None and done.completed_at is not None
    reopened = storage.update_task(task.id, completed=False)
    assert reopened is not None and reopened.completed_at is None and not reopened.completed


def test_delete_returns_false_for_missing(storage, user_id):
    task = storage.create_task(user_id, "Gone", None, "2030-01-01")
    assert storage.delete_task(task.id) is True
    assert storage.delete_task(task.id) is False
    assert storage.get_task(task.id) is None


def test_deleting_user_cascades_to_tasks(storage, user_id):
    from sqlalchemy import delete, select

    from task_manager_pro.storage.models import TaskModel, UserModel

    storage.create_task(user_id, "Orphan?", None, "2030-01-01")
    with storage._session() as db:
        db.execute(delete(UserModel).where(UserModel.id == user_id))
    with storage._session() as db:
        assert db.scalars(select(TaskModel)).all() == []


def test_get_due_tasks_excludes_completed_and_future(storage, user_id):
    storage.create_task(user_id, "Past", None, "2000-01-01")
    storage.create_task(user_id, "Future", None, "2999-01-01")
    done = storage.create_task(user_id, "Past done", None, "2000-01-02")
    storage.update_task(done.id, completed=True)
    assert [t.title for t in storage.get_due_tasks()] == ["Past"]
    assert [t.title for t in storage.get_due_tasks("2999-12-31")] == ["Past", "Future"]
