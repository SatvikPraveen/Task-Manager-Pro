"""
tests/helpers.py

Small helpers shared by the API test modules.
"""

from __future__ import annotations

from typing import Optional

from fastapi.testclient import TestClient

DEFAULT_PASSWORD = "securepass123"


def register(
    client: TestClient, username: str = "testuser", password: str = DEFAULT_PASSWORD, email: Optional[str] = None
) -> dict:
    payload: dict = {"username": username, "password": password}
    if email:
        payload["email"] = email
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def login(client: TestClient, username: str = "testuser", password: str = DEFAULT_PASSWORD) -> str:
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(
    client: TestClient, username: str = "testuser", password: str = DEFAULT_PASSWORD, email: Optional[str] = None
) -> dict[str, str]:
    """Register (idempotently) and log in, returning a bearer header."""
    resp = client.post(
        "/api/auth/register", json={"username": username, "password": password, **({"email": email} if email else {})}
    )
    assert resp.status_code in (201, 400), resp.text
    return {"Authorization": f"Bearer {login(client, username, password)}"}


def create_task(
    client: TestClient,
    headers: dict[str, str],
    title: str,
    due_date: str,
    priority: str = "medium",
    description: Optional[str] = None,
) -> dict:
    resp = client.post(
        "/api/tasks",
        headers=headers,
        json={"title": title, "due_date": due_date, "priority": priority, "description": description},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
