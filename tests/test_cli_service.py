"""
tests/test_cli_service.py

Tests for the JSON-backed CLI service layer (TaskManager + JSONStorage),
the session helpers and the small CLI utilities. Everything runs inside a
temporary working directory so no files are written into the repository.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from task_manager_pro.models.user import User
from task_manager_pro.services.task_manager import TaskManager
from task_manager_pro.storage.json_storage import JSONStorage
from task_manager_pro.utils import session as session_module
from task_manager_pro.utils.decorators import log_action, require_login
from task_manager_pro.utils.logger_context import LoggerContext


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path, monkeypatch):
    """Run every test in an empty temp directory (tasks.json / session.json live in cwd)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", lambda *_: "")  # never block on prompts
    yield


@pytest.fixture
def manager() -> TaskManager:
    return TaskManager(JSONStorage("tasks.json"))


def _task_ids(manager: TaskManager) -> list[str]:
    return [t["id"] for t in manager.data["tasks"]]


# --------------------------------------------------------------------------- #
# JSONStorage                                                                 #
# --------------------------------------------------------------------------- #
def test_json_storage_initialises_and_roundtrips(tmp_path):
    storage = JSONStorage("store.json")
    assert json.loads((tmp_path / "store.json").read_text()) == {"tasks": [], "users": []}
    storage.save_data({"tasks": [{"id": "1"}], "users": []})
    assert storage.load_data()["tasks"] == [{"id": "1"}]


def test_json_storage_missing_file_returns_empty(tmp_path):
    storage = JSONStorage("store.json")
    (tmp_path / "store.json").unlink()
    assert storage.load_data() == {"users": [], "tasks": []}


# --------------------------------------------------------------------------- #
# Session helpers                                                             #
# --------------------------------------------------------------------------- #
def test_session_save_load_clear():
    assert session_module.load_session() is None
    session_module.save_session("alice")
    assert session_module.load_session() == "alice"
    session_module.clear_session()
    assert session_module.load_session() is None
    session_module.clear_session()  # idempotent


# --------------------------------------------------------------------------- #
# TaskManager                                                                 #
# --------------------------------------------------------------------------- #
def test_login_creates_user_persists_and_restores_session(capsys):
    manager = TaskManager(JSONStorage("tasks.json"))
    manager.login("alice", email="alice@example.com")
    assert manager.current_user is not None and manager.current_user.username == "alice"
    assert "Logged in as alice" in capsys.readouterr().out
    assert session_module.load_session() == "alice"

    # A fresh manager picks the session up from disk.
    again = TaskManager(JSONStorage("tasks.json"))
    assert again.current_user is not None
    assert again.current_user.username == "alice"
    assert again.current_user.email == "alice@example.com"


def test_login_prompts_for_email_when_missing(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "bob@example.com")
    manager = TaskManager(JSONStorage("tasks.json"))
    manager.login("bob")
    assert manager.current_user is not None
    assert manager.current_user.email == "bob@example.com"
    assert manager.data["users"][0]["email"] == "bob@example.com"

    # Second login for an existing user without an email prompts again and saves it.
    manager.data["users"][0]["email"] = None
    manager.storage.save_data(manager.data)
    monkeypatch.setattr("builtins.input", lambda *_: "new@example.com")
    manager.login("bob")
    assert manager.data["users"][0]["email"] == "new@example.com"


def test_task_operations_require_login(manager, capsys):
    manager.add_task("x", "y", "2030-01-01")
    manager.update_task("nope", title="t")
    manager.send_due_reminders()
    manager.toggle_email_reminders()
    out = capsys.readouterr().out
    assert out.count("Please login first") == 4
    assert manager.data["tasks"] == []


def test_add_update_complete_list_delete_cycle(manager, capsys):
    manager.login("alice", email="alice@example.com")
    manager.add_task("Write", "the paper", "2030-01-01")
    manager.add_task("Read", "the reviews", "2030-02-01")
    first, second = _task_ids(manager)
    assert all(t["user"] == "alice" for t in manager.data["tasks"])

    manager.update_task(first, title="Write v2", desc="revised", due="2030-01-15")
    updated = next(t for t in manager.data["tasks"] if t["id"] == first)
    assert (updated["title"], updated["description"], updated["due_date"]) == ("Write v2", "revised", "2030-01-15")

    manager.update_task("missing-id", title="zzz")
    assert "not found" in capsys.readouterr().out

    manager.mark_task_complete(second)
    assert next(t for t in manager.data["tasks"] if t["id"] == second)["completed"] is True
    manager.mark_task_complete("missing-id")
    assert "Task not found" in capsys.readouterr().out

    capsys.readouterr()
    manager.list_tasks("completed", verbose=True, summary=True)
    out = capsys.readouterr().out
    assert "Read" in out and "Write v2" not in out and "the reviews" in out
    assert "Total: 1 | Completed: 1 | Pending: 0" in out

    manager.list_tasks("pending")
    out = capsys.readouterr().out
    assert "Write v2" in out and "Read" not in out

    manager.delete_task(first)
    assert _task_ids(manager) == [second]
    manager.delete_task(first)
    assert "Task not found" in capsys.readouterr().out

    # Persisted to disk.
    assert [t["id"] for t in JSONStorage("tasks.json").load_data()["tasks"]] == [second]


def test_list_tasks_empty_and_reminders_for_due_tasks(manager, capsys):
    manager.login("alice", email="alice@example.com")
    manager.list_tasks("all")
    assert "No tasks found" in capsys.readouterr().out

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    manager.add_task("Overdue", "late", yesterday)
    capsys.readouterr()
    manager.send_due_reminders()
    out = capsys.readouterr().out
    assert "tasks due or overdue" in out and "Overdue" in out


def test_toggle_email_reminders_and_logout(manager, capsys):
    manager.login("alice", email="alice@example.com")
    assert manager.current_user is not None
    assert manager.current_user.email_reminders_enabled is True
    manager.toggle_email_reminders()
    assert manager.current_user.email_reminders_enabled is False
    assert manager.data["users"][0]["email_reminders_enabled"] is False
    assert "disabled" in capsys.readouterr().out

    manager.logout()
    assert manager.current_user is None and session_module.load_session() is None
    manager.logout()
    assert "No user is currently logged in" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# User model                                                                  #
# --------------------------------------------------------------------------- #
def test_user_model_behaviour():
    user = User("carol", "secret", "c@example.com")
    with pytest.raises(AttributeError):
        _ = user.password
    assert user.verify_password("secret") and not user.verify_password("nope")
    assert user.toggle_email_reminders() is False
    assert user.to_dict() == {"username": "carol", "email": "c@example.com", "email_reminders_enabled": False}
    assert "password" not in user.to_dict()
    assert str(user) == "User(carol)" and "carol" in repr(user)


# --------------------------------------------------------------------------- #
# Decorators and LoggerContext                                                #
# --------------------------------------------------------------------------- #
def test_decorators(capsys):
    class Thing:
        current_user = None

        @require_login
        def act(self):
            return "acted"

        @log_action
        def logged(self, value):
            return value * 2

    thing = Thing()
    assert thing.act() is None
    assert "Please login" in capsys.readouterr().out
    thing.current_user = object()
    assert thing.act() == "acted"
    assert thing.logged(21) == 42
    out = capsys.readouterr().out
    assert "Executing: Logged" in out and "Completed: Logged" in out


def test_logger_context_success_and_error(tmp_path, capsys):
    log_file = tmp_path / "ctx.log"
    with LoggerContext("doing work", log_file=str(log_file)) as ctx:
        ctx.log("half way")
    with pytest.raises(RuntimeError), LoggerContext("failing", log_file=str(log_file)):
        raise RuntimeError("boom")
    content = log_file.read_text()
    assert "Starting: doing work" in content and "half way" in content and "Finished: doing work" in content
    assert "Error during: failing" in content and "boom" in content
    assert "Session ended" in content
    with pytest.raises(RuntimeError):
        LoggerContext("x", log_file=str(log_file))._write_log("not opened")
