"""
tests/test_api.py

Comprehensive tests for the FastAPI REST API endpoints.
Tests authentication, task CRUD, and user management.
"""

import pytest
from fastapi.testclient import TestClient

from task_manager_pro.api.main import app
from task_manager_pro.storage.database import Base, engine


@pytest.fixture(autouse=True)
def clean_db():
    """Clean database before each test."""
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    # Create all tables fresh
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup after test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Provide FastAPI test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test GET / root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "🎯 Task Manager PRO API"


def test_health_check(client):
    """Test GET /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


# Authentication Tests
def test_register_user(client):
    """Test user registration."""
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "password": "securepass123",
            "email": "test@example.com",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data


def test_register_duplicate_user(client):
    """Test duplicate user registration fails."""
    # Register first user
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "password": "securepass123",
            "email": "test@example.com",
        },
    )

    # Try to register again
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "password": "differentpass",
            "email": "different@example.com",
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_login_valid_credentials(client):
    """Test login with valid credentials."""
    # Register
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "password": "securepass123",
            "email": "test@example.com",
        },
    )

    # Login
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "securepass123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "testuser"


def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    # Register
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "password": "securepass123",
            "email": "test@example.com",
        },
    )

    # Try login with wrong password
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]


# Task Tests
def test_create_task_authenticated(client):
    """Test creating a task as authenticated user."""
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "password": "securepass123",
            "email": "test@example.com",
        },
    )

    login_resp = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "securepass123",
        },
    )
    token = login_resp.json()["access_token"]

    # Create task
    response = client.post(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Learn FastAPI",
            "description": "Complete the tutorial",
            "due_date": "2025-12-31",
            "priority": "high",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Learn FastAPI"
    assert data["priority"] == "high"
    assert not data["completed"]


def test_create_task_unauthenticated(client):
    """Test creating a task without authentication."""
    response = client.post(
        "/api/tasks",
        json={
            "title": "Test",
            "description": "Test",
            "due_date": "2025-12-31",
        },
    )
    assert response.status_code == 401  # Unauthorized (no credentials)


def test_list_tasks(client):
    """Test listing tasks."""
    # Setup
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "password": "securepass123",
        },
    )

    login_resp = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "securepass123"},
    )
    token = login_resp.json()["access_token"]

    # Create multiple tasks
    for i in range(3):
        client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": f"Task {i + 1}",
                "description": f"Desc {i + 1}",
                "due_date": "2025-12-31",
            },
        )

    # List tasks
    response = client.get(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["tasks"]) == 3


def test_list_tasks_paginated(client):
    """Test task pagination."""
    # Setup
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "password": "securepass123",
        },
    )

    login_resp = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "securepass123"},
    )
    token = login_resp.json()["access_token"]

    # Create 15 tasks
    for i in range(15):
        client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": f"Task {i + 1}",
                "description": f"Desc {i + 1}",
                "due_date": "2025-12-31",
            },
        )

    # Get page 1 (limit 10)
    response = client.get(
        "/api/tasks?skip=0&limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 15
    assert len(data["tasks"]) == 10
    assert data["page"] == 1


def test_get_task_detail(client):
    """Test getting task details."""
    # Setup
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "password": "securepass123",
        },
    )

    login_resp = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "securepass123"},
    )
    token = login_resp.json()["access_token"]

    # Create task
    create_resp = client.post(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Test Task",
            "description": "Test Description",
            "due_date": "2025-12-31",
        },
    )
    task_id = create_resp.json()["id"]

    # Get task
    response = client.get(
        f"/api/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["description"] == "Test Description"


def test_update_task(client):
    """Test updating a task."""
    # Setup
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "password": "securepass123",
        },
    )

    login_resp = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "securepass123"},
    )
    token = login_resp.json()["access_token"]

    # Create task
    create_resp = client.post(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Original Title",
            "description": "Original",
            "due_date": "2025-12-31",
        },
    )
    task_id = create_resp.json()["id"]

    # Update task
    response = client.put(
        f"/api/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Updated Title",
            "completed": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["completed"] is True


def test_delete_task(client):
    """Test deleting a task."""
    # Setup
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "password": "securepass123",
        },
    )

    login_resp = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "securepass123"},
    )
    token = login_resp.json()["access_token"]

    # Create task
    create_resp = client.post(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "To Delete",
            "description": "Delete me",
            "due_date": "2025-12-31",
        },
    )
    task_id = create_resp.json()["id"]

    # Delete task
    response = client.delete(
        f"/api/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


# User Tests
def test_get_current_user(client):
    """Test getting current user profile."""
    # Setup
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "password": "securepass123",
            "email": "test@example.com",
        },
    )

    login_resp = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "securepass123"},
    )
    token = login_resp.json()["access_token"]

    # Get user
    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


def test_toggle_email_reminders(client):
    """Test toggling email reminders."""
    # Setup
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "password": "securepass123",
        },
    )

    login_resp = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "securepass123"},
    )
    token = login_resp.json()["access_token"]

    # Check initial state
    resp1 = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    initial_state = resp1.json()["email_reminders_enabled"]

    # Toggle
    response = client.post(
        "/api/users/me/toggle-reminders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email_reminders_enabled"] != initial_state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
