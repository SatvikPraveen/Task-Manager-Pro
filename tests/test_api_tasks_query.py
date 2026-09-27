"""
tests/test_api_tasks_query.py

API-level tests for filtering, sorting, pagination metadata, ownership
isolation and token refresh.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from task_manager_pro.api.main import app
from task_manager_pro.storage.database import Base, engine
from tests.helpers import auth_headers, create_task


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def headers(client):
    return auth_headers(client, "alice")


def _seed(client, headers):
    create_task(client, headers, "Write paper", "2030-01-10", "high", "draft intro")
    create_task(client, headers, "Run experiments", "2030-01-05", "medium")
    create_task(client, headers, "Buy milk", "2030-01-01", "low", "2 litres")


def test_list_filters_by_priority_and_search(client, headers):
    _seed(client, headers)
    r = client.get("/api/tasks", headers=headers, params={"priority": "high"})
    assert r.status_code == 200
    assert [t["title"] for t in r.json()["tasks"]] == ["Write paper"]

    r = client.get("/api/tasks", headers=headers, params={"q": "milk"})
    assert [t["title"] for t in r.json()["tasks"]] == ["Buy milk"]


def test_list_due_window_and_validation(client, headers):
    _seed(client, headers)
    r = client.get("/api/tasks", headers=headers, params={"due_after": "2030-01-02", "due_before": "2030-01-06"})
    assert [t["title"] for t in r.json()["tasks"]] == ["Run experiments"]

    r = client.get("/api/tasks", headers=headers, params={"due_after": "2030-01-06", "due_before": "2030-01-02"})
    assert r.status_code == 422

    r = client.get("/api/tasks", headers=headers, params={"due_before": "not-a-date"})
    assert r.status_code == 422


def test_list_sorting_and_page_metadata(client, headers):
    _seed(client, headers)
    r = client.get("/api/tasks", headers=headers, params={"sort_by": "title", "sort_desc": "true", "limit": 2})
    body = r.json()
    assert [t["title"] for t in body["tasks"]] == ["Write paper", "Run experiments"]
    assert body == {**body, "total": 3, "page": 1, "page_size": 2, "pages": 2}

    r = client.get(
        "/api/tasks", headers=headers, params={"sort_by": "title", "sort_desc": "true", "limit": 2, "skip": 2}
    )
    assert [t["title"] for t in r.json()["tasks"]] == ["Buy milk"]
    assert r.json()["page"] == 2

    r = client.get("/api/tasks", headers=headers, params={"sort_by": "password_hash"})
    assert r.status_code == 422


def test_tasks_are_isolated_between_users(client, headers):
    task = create_task(client, headers, "Secret", "2030-01-01")
    other = auth_headers(client, "bob")

    assert client.get(f"/api/tasks/{task['id']}", headers=other).status_code == 404
    assert client.put(f"/api/tasks/{task['id']}", headers=other, json={"title": "pwned"}).status_code == 404
    assert client.delete(f"/api/tasks/{task['id']}", headers=other).status_code == 404
    assert client.get("/api/tasks", headers=other).json()["total"] == 0
    # Owner still sees the untouched task.
    assert client.get(f"/api/tasks/{task['id']}", headers=headers).json()["title"] == "Secret"


def test_create_rejects_blank_title_and_bad_date(client, headers):
    r = client.post("/api/tasks", headers=headers, json={"title": "   ", "due_date": "2030-01-01"})
    assert r.status_code == 422
    r = client.post("/api/tasks", headers=headers, json={"title": "x", "due_date": "2030-13-01"})
    assert r.status_code == 422


def test_reopening_task_clears_completed_at(client, headers):
    task = create_task(client, headers, "Toggle", "2030-01-01")
    done = client.put(f"/api/tasks/{task['id']}", headers=headers, json={"completed": True}).json()
    assert done["completed"] and done["completed_at"] is not None
    reopened = client.put(f"/api/tasks/{task['id']}", headers=headers, json={"completed": False}).json()
    assert not reopened["completed"] and reopened["completed_at"] is None


def test_refresh_token_uses_bearer_header(client, headers):
    r = client.post("/api/auth/refresh-token", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in"] > 0
    # The new token is usable.
    assert client.get("/api/users/me", headers={"Authorization": f"Bearer {body['access_token']}"}).status_code == 200
    # No header → 401/403 from the bearer scheme, never a 422 asking for a query param.
    assert client.post("/api/auth/refresh-token").status_code in (401, 403)


def test_login_response_includes_expiry(client, headers):
    r = client.post("/api/auth/login", json={"username": "alice", "password": "securepass123"})
    assert r.status_code == 200
    assert r.json()["expires_in"] == 30 * 60
