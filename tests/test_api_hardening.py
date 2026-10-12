"""
tests/test_api_hardening.py

Regression tests for API/storage defects found in the October 2026 review:
long passwords vs bcrypt's 72-byte limit, atomic token revocation, duplicate
registration races, time-zone handling of dates and timestamps, clearing
nullable fields, LIKE-wildcard escaping and the JWT algorithm allow-list.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import sessionmaker

from task_manager_pro.api.main import app
from task_manager_pro.config import Settings
from task_manager_pro.schemas.task import TaskResponse
from task_manager_pro.storage import sql_storage as sql_storage_module
from task_manager_pro.storage.database import Base, engine, make_engine
from task_manager_pro.storage.sql_storage import SQLStorage
from task_manager_pro.utils.security import verify_password_dummy
from task_manager_pro.utils.token_denylist import InMemoryTokenDenylist
from tests.helpers import auth_headers, create_task, register

LONG_PASSWORD = "p" * 100  # > 72 bytes


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# --------------------------------------------------------------------------- #
# Passwords and bcrypt's 72-byte limit                                        #
# --------------------------------------------------------------------------- #
def test_register_rejects_passwords_bcrypt_would_truncate(client):
    r = client.post("/api/auth/register", json={"username": "longpw", "password": LONG_PASSWORD})
    assert r.status_code == 422
    assert "72 bytes" in r.text
    # Multi-byte characters count by bytes, not characters: 25 x 3 bytes = 75.
    r = client.post("/api/auth/register", json={"username": "longpw", "password": "€" * 25})
    assert r.status_code == 422


def test_long_password_login_does_not_reveal_which_usernames_exist(client):
    register(client, "alice")
    known = client.post("/api/auth/login", json={"username": "alice", "password": LONG_PASSWORD})
    unknown = client.post("/api/auth/login", json={"username": "nobody", "password": LONG_PASSWORD})
    assert known.status_code == unknown.status_code == 401
    assert known.json() == unknown.json()


def test_dummy_verify_accepts_any_length():
    verify_password_dummy(LONG_PASSWORD)  # must not raise


# --------------------------------------------------------------------------- #
# Token revocation is atomic                                                  #
# --------------------------------------------------------------------------- #
def test_revoke_reports_only_the_first_caller():
    denylist = InMemoryTokenDenylist()
    assert denylist.revoke("jti-1", 60) is True
    assert denylist.revoke("jti-1", 60) is False
    assert denylist.revoke("expired", 0) is False


def test_concurrent_revocations_of_one_token_have_one_winner():
    denylist = InMemoryTokenDenylist()
    results: list[bool] = []
    barrier = threading.Barrier(16)

    def worker() -> None:
        barrier.wait()
        results.append(denylist.revoke("shared-jti", 60))

    threads = [threading.Thread(target=worker) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(True) == 1


def test_refresh_with_revoked_token_issues_nothing(client):
    headers = auth_headers(client)
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    r = client.post("/api/auth/refresh-token", headers=headers)
    assert r.status_code == 401
    assert "access_token" not in r.json()


# --------------------------------------------------------------------------- #
# Duplicate registration race                                                 #
# --------------------------------------------------------------------------- #
def test_register_race_maps_unique_violation_to_value_error(tmp_path, monkeypatch):
    """Another request inserts the same username between the existence check and our insert."""
    file_engine = make_engine(f"sqlite:///{tmp_path / 'race.db'}", echo=False)
    Base.metadata.create_all(file_engine)
    storage = SQLStorage(sessionmaker(bind=file_engine), create_tables=False)

    real_hash = sql_storage_module.hash_password
    raced = False

    def hash_then_race(password: str) -> str:
        nonlocal raced
        if not raced:
            raced = True
            storage.create_user("alice", "otherpassword")  # the competing request wins
        return real_hash(password)

    monkeypatch.setattr(sql_storage_module, "hash_password", hash_then_race)
    with pytest.raises(ValueError, match="already exists"):
        storage.create_user("alice", "password123")
    file_engine.dispose()


# --------------------------------------------------------------------------- #
# Time zones                                                                  #
# --------------------------------------------------------------------------- #
def _task_row(**overrides):
    now = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    row = {
        "id": "t1",
        "user_id": "u1",
        "title": "x",
        "description": None,
        "due_date": datetime(2026, 10, 11, tzinfo=timezone.utc),
        "priority": "medium",
        "completed": False,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }
    row.update(overrides)
    return row


def test_due_date_survives_a_non_utc_database_session():
    # PostgreSQL returns UTC midnight in the session zone, e.g. 2026-10-10T20:00-04:00.
    shifted = datetime(2026, 10, 11, tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-4)))
    assert str(TaskResponse.model_validate(_task_row(due_date=shifted)).due_date) == "2026-10-11"


def test_naive_timestamps_are_returned_as_utc(client):
    headers = auth_headers(client)
    task = create_task(client, headers, "Write", "2030-01-01")
    for field in ("created_at", "updated_at"):
        parsed = datetime.fromisoformat(task[field].replace("Z", "+00:00"))
        assert parsed.utcoffset() == timedelta(0), task[field]
    me = client.get("/api/users/me", headers=headers).json()
    assert datetime.fromisoformat(me["created_at"].replace("Z", "+00:00")).utcoffset() == timedelta(0)


# --------------------------------------------------------------------------- #
# Clearing nullable fields                                                    #
# --------------------------------------------------------------------------- #
def test_null_clears_task_description_but_not_required_fields(client):
    headers = auth_headers(client)
    task = create_task(client, headers, "Write", "2030-01-01", description="draft")
    r = client.put(f"/api/tasks/{task['id']}", headers=headers, json={"description": None})
    assert r.status_code == 200 and r.json()["description"] is None
    for field in ("title", "due_date", "priority", "completed"):
        r = client.put(f"/api/tasks/{task['id']}", headers=headers, json={field: None})
        assert r.status_code == 422, field


def test_null_removes_user_email(client):
    headers = auth_headers(client, email="alice@example.com")
    r = client.put("/api/users/me", headers=headers, json={"email": None})
    assert r.status_code == 200 and r.json()["email"] is None
    r = client.put("/api/users/me", headers=headers, json={"email_reminders_enabled": None})
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# Search treats LIKE wildcards literally                                      #
# --------------------------------------------------------------------------- #
def test_search_wildcards_are_literal(client):
    headers = auth_headers(client)
    create_task(client, headers, "discount 50 off", "2030-01-01")
    create_task(client, headers, "save 50% now", "2030-01-02")
    create_task(client, headers, "snake_case rename", "2030-01-03")

    def titles(q: str) -> list[str]:
        r = client.get("/api/tasks", headers=headers, params={"q": q})
        assert r.status_code == 200, r.text
        return sorted(t["title"] for t in r.json()["tasks"])

    assert titles("50%") == ["save 50% now"]
    assert titles("_") == ["snake_case rename"]


# --------------------------------------------------------------------------- #
# Configuration                                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("algorithm", ["none", "RS256", "hs256"])
def test_jwt_algorithm_must_be_hmac(algorithm):
    with pytest.raises(ValidationError):
        Settings(secret_key="k" * 40, jwt_algorithm=algorithm)
