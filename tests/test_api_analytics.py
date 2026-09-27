"""
tests/test_api_analytics.py

Integration tests for /api/tasks/stats and /api/tasks/next.
"""

from __future__ import annotations

from datetime import date, timedelta

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


def test_stats_and_next_require_auth(client):
    assert client.get("/api/tasks/stats").status_code in (401, 403)
    assert client.get("/api/tasks/next").status_code in (401, 403)


def test_stats_reflect_created_and_completed_tasks(client, headers):
    today = date.today()
    overdue = create_task(client, headers, "Overdue", (today - timedelta(days=2)).isoformat(), "high")
    create_task(client, headers, "Soon", (today + timedelta(days=2)).isoformat(), "medium")
    done = create_task(client, headers, "Done", (today + timedelta(days=1)).isoformat(), "low")
    client.put(f"/api/tasks/{done['id']}", headers=headers, json={"completed": True})

    stats = client.get("/api/tasks/stats", headers=headers).json()
    assert stats["total"] == 3 and stats["completed"] == 1 and stats["pending"] == 2
    assert stats["overdue"] == 1
    assert stats["completion_rate"] == pytest.approx(1 / 3)
    assert stats["on_time_rate"] == 1.0
    assert stats["by_priority"]["high"]["overdue"] == 1
    assert stats["mean_completion_days"] is not None and stats["mean_completion_days"] >= 0

    # Deleting the overdue task changes the picture.
    client.delete(f"/api/tasks/{overdue['id']}", headers=headers)
    assert client.get("/api/tasks/stats", headers=headers).json()["overdue"] == 0


def test_next_returns_most_urgent_pending_first(client, headers):
    today = date.today()
    create_task(client, headers, "Far low", (today + timedelta(days=60)).isoformat(), "low")
    create_task(client, headers, "Overdue high", (today - timedelta(days=1)).isoformat(), "high")
    create_task(client, headers, "Tomorrow medium", (today + timedelta(days=1)).isoformat(), "medium")
    done = create_task(client, headers, "Done high", (today - timedelta(days=5)).isoformat(), "high")
    client.put(f"/api/tasks/{done['id']}", headers=headers, json={"completed": True})

    body = client.get("/api/tasks/next", headers=headers, params={"limit": 2}).json()
    titles = [t["title"] for t in body["tasks"]]
    assert titles == ["Overdue high", "Tomorrow medium"]
    assert body["tasks"][0]["urgency"] > body["tasks"][1]["urgency"] > 0
    assert body["tasks"][0]["days_until_due"] < 0
    assert "as_of" in body

    assert client.get("/api/tasks/next", headers=headers, params={"limit": 0}).status_code == 422


def test_stats_are_per_user(client, headers):
    create_task(client, headers, "Mine", "2030-01-01")
    other = auth_headers(client, "bob")
    assert client.get("/api/tasks/stats", headers=other).json()["total"] == 0
    assert client.get("/api/tasks/next", headers=other).json()["tasks"] == []


def test_task_named_stats_is_not_shadowed(client, headers):
    """A task ID can never collide with the /stats and /next literals (UUIDs), but
    the literal routes must be registered first so they resolve."""
    r = client.get("/api/tasks/not-a-real-id", headers=headers)
    assert r.status_code == 404


def test_next_calibrated_uses_history_when_enough_completions(client, headers):
    today = date.today()
    # Six tasks completed today, each due 4 days from now → median lead 4 days.
    for i in range(6):
        t = create_task(client, headers, f"done {i}", (today + timedelta(days=4)).isoformat(), "medium")
        client.put(f"/api/tasks/{t['id']}", headers=headers, json={"completed": True})
    create_task(client, headers, "Pending", (today + timedelta(days=2)).isoformat(), "high")

    default = client.get("/api/tasks/next", headers=headers).json()
    assert default["params"]["calibrated"] is False and default["params"]["half_urgency_days"] == 3.0

    body = client.get("/api/tasks/next", headers=headers, params={"calibrated": "true"}).json()
    params = body["params"]
    assert params["calibrated"] is True and params["samples"] == 6
    assert 3.5 <= params["half_urgency_days"] <= 4.5
    assert [t["title"] for t in body["tasks"]] == ["Pending"]
    # Same task, larger horizon → it is "more urgent" under the calibrated curve.
    assert body["tasks"][0]["urgency"] > default["tasks"][0]["urgency"]


def test_next_calibrated_falls_back_with_little_history(client, headers):
    create_task(client, headers, "Only one", "2030-01-01")
    body = client.get("/api/tasks/next", headers=headers, params={"calibrated": "true"}).json()
    assert body["params"]["calibrated"] is False and body["params"]["samples"] == 0
