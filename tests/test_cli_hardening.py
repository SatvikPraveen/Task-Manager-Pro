"""
tests/test_cli_hardening.py

Regression tests for CLI, reminder-job and JSON→SQL migration defects found in
the October 2026 review, plus the password-change endpoint the migration's
one-time passwords rely on.
"""

from __future__ import annotations

import io
import json
import os
import runpy
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from task_manager_pro.api.main import app
from task_manager_pro.services import task_manager as task_manager_module
from task_manager_pro.services.task_manager import TaskManager
from task_manager_pro.storage.database import Base, engine, make_engine
from task_manager_pro.storage.json_storage import CorruptDataError, JSONStorage
from task_manager_pro.storage.sql_storage import SQLStorage
from task_manager_pro.utils import emailer as emailer_module
from task_manager_pro.utils.migration import migrate_json_to_sql
from tests.helpers import DEFAULT_PASSWORD, auth_headers

YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path, monkeypatch):
    """tasks.json / session.json live in cwd; keep them in a temp dir."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", lambda *_: "")
    yield


def _write_store(users: list[dict], tasks: list[dict]) -> None:
    with open("tasks.json", "w") as f:
        json.dump({"users": users, "tasks": tasks}, f)


def _task(user: str, title: str, due: str, **extra) -> dict:
    return {
        "id": f"id-{title}",
        "user": user,
        "title": title,
        "description": "",
        "due_date": due,
        "completed": False,
    } | extra


# --------------------------------------------------------------------------- #
# Stored user records with extra keys                                         #
# --------------------------------------------------------------------------- #
def test_extra_keys_in_user_record_do_not_lock_the_user_out(capsys):
    """send_reminders writes last_reminder_date; the CLI must still load that user."""
    _write_store([{"username": "al", "email": None, "last_reminder_date": "2026-10-01"}], [])
    manager = TaskManager(JSONStorage("tasks.json"))
    manager.login("al")
    manager.list_tasks("all")
    assert "Logged in as al" in capsys.readouterr().out
    assert TaskManager(JSONStorage("tasks.json")).current_user.username == "al"  # session restore path


# --------------------------------------------------------------------------- #
# Email reminders respect the user's setting and report failures              #
# --------------------------------------------------------------------------- #
def _manager_with_due_task(reminders_enabled: bool) -> TaskManager:
    _write_store(
        [{"username": "al", "email": "al@example.com", "email_reminders_enabled": reminders_enabled}],
        [_task("al", "Overdue", YESTERDAY)],
    )
    manager = TaskManager(JSONStorage("tasks.json"))
    manager.login("al")
    return manager


def test_disabled_reminders_send_no_email(monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(task_manager_module, "send_email_reminder", lambda **kw: sent.append(kw["to_email"]) or True)
    manager = _manager_with_due_task(reminders_enabled=False)
    manager.list_tasks("all")
    manager.send_due_reminders()
    assert sent == []


def test_enabled_reminders_send_and_report_failure(monkeypatch, capsys):
    sent: list[str] = []
    monkeypatch.setattr(task_manager_module, "send_email_reminder", lambda **kw: sent.append(kw["to_email"]) or False)
    _manager_with_due_task(reminders_enabled=True)
    assert sent == ["al@example.com"]  # login sends
    assert "Could not send email reminder" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# Due-date validation                                                         #
# --------------------------------------------------------------------------- #
def test_invalid_due_dates_are_rejected_not_stored(capsys):
    manager = TaskManager(JSONStorage("tasks.json"))
    manager.login("al")
    manager.add_task("Bad", "x", "tomorrow")
    assert manager.data["tasks"] == []
    manager.add_task("Good", "x", "2030-01-01")
    (task_id,) = [t["id"] for t in manager.data["tasks"]]
    manager.update_task(task_id, due="31/12/2030")
    assert manager.data["tasks"][0]["due_date"] == "2030-01-01"
    assert capsys.readouterr().out.count("Invalid due date") == 2


def test_a_corrupt_due_date_row_does_not_crash_listing(capsys):
    _write_store([{"username": "al"}], [_task("al", "Broken", "tomorrow"), _task("al", "Fine", "2030-01-01")])
    manager = TaskManager(JSONStorage("tasks.json"))
    manager.login("al")
    manager.list_tasks("all")
    out = capsys.readouterr().out
    assert "Fine" in out and "invalid due date" in out


# --------------------------------------------------------------------------- #
# JSON storage                                                                #
# --------------------------------------------------------------------------- #
def test_corrupt_json_raises_a_clear_error():
    with open("tasks.json", "w") as f:
        f.write("")
    with pytest.raises(CorruptDataError, match="not valid JSON"):
        JSONStorage("tasks.json").load_data()
    with open("tasks.json", "w") as f:
        f.write("[]")
    with pytest.raises(CorruptDataError):
        JSONStorage("tasks.json").load_data()


def test_cli_exits_cleanly_on_corrupt_json(monkeypatch, capsys):
    from task_manager_pro import cli

    with open("tasks.json", "w") as f:
        f.write("{truncated")
    monkeypatch.setattr("sys.argv", ["task-manager", "list-tasks"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1
    assert "not valid JSON" in capsys.readouterr().out


def test_missing_top_level_keys_default_to_empty():
    with open("tasks.json", "w") as f:
        json.dump({"users": []}, f)
    assert JSONStorage("tasks.json").load_data()["tasks"] == []


def test_save_is_atomic_and_leaves_no_temp_files():
    storage = JSONStorage("tasks.json")
    storage.save_data({"users": [{"username": "al"}], "tasks": []})
    assert storage.load_data()["users"] == [{"username": "al"}]
    assert sorted(os.listdir(".")) == ["tasks.json"]


# --------------------------------------------------------------------------- #
# Login without a terminal                                                    #
# --------------------------------------------------------------------------- #
def test_login_without_stdin_does_not_crash(monkeypatch):
    def eof(*_):
        raise EOFError

    monkeypatch.setattr("builtins.input", eof)
    manager = TaskManager(JSONStorage("tasks.json"))
    manager.login("carol")
    manager.login("carol")  # existing user without email: prompts again
    assert manager.current_user.username == "carol"


def test_login_uses_given_email_for_existing_user():
    manager = TaskManager(JSONStorage("tasks.json"))
    manager.login("carol")
    manager.login("carol", email="carol@example.com")
    assert manager.data["users"][0]["email"] == "carol@example.com"


# --------------------------------------------------------------------------- #
# send_reminders cron job                                                     #
# --------------------------------------------------------------------------- #
def _run_reminder_job(monkeypatch, *, delivered: bool) -> list[str]:
    sent: list[str] = []
    monkeypatch.setattr(emailer_module, "send_email_reminder", lambda **kw: sent.append(kw["to_email"]) or delivered)
    monkeypatch.setattr("sys.stdout", io.StringIO())
    runpy.run_module("task_manager_pro.send_reminders", run_name="__main__")
    return sent


def test_reminder_job_records_only_delivered_reminders(monkeypatch):
    _write_store(
        [{"username": "al", "email": "al@example.com", "email_reminders_enabled": True}],
        [_task("al", "Overdue", YESTERDAY)],
    )
    assert _run_reminder_job(monkeypatch, delivered=False) == ["al@example.com"]
    assert "last_reminder_date" not in JSONStorage("tasks.json").load_data()["users"][0]

    _run_reminder_job(monkeypatch, delivered=True)
    assert JSONStorage("tasks.json").load_data()["users"][0]["last_reminder_date"] == date.today().isoformat()


def test_reminder_job_skips_bad_rows_and_serves_other_users(monkeypatch):
    _write_store(
        [
            {"username": "al", "email": "al@example.com", "email_reminders_enabled": True},
            {"username": "bo", "email": "bo@example.com", "email_reminders_enabled": True},
        ],
        [_task("al", "Broken", "tomorrow"), _task("bo", "Overdue", YESTERDAY)],
    )
    assert _run_reminder_job(monkeypatch, delivered=True) == ["bo@example.com"]


# --------------------------------------------------------------------------- #
# JSON → SQL migration                                                        #
# --------------------------------------------------------------------------- #
@pytest.fixture
def sql_storage() -> SQLStorage:
    mem_engine = make_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(mem_engine)
    return SQLStorage(sessionmaker(bind=mem_engine), create_tables=False)


def _json_export() -> str:
    _write_store(
        [{"username": "alice", "email": "a@example.com"}, {"username": "bob"}],
        [
            _task("alice", "Write", "2030-01-01", created_at="2026-01-02 09:30:00"),
            _task("alice", "Done", "2026-01-05", completed=True),
            _task("bob", "Bob's", "2030-01-01"),
        ],
    )
    return "tasks.json"


def test_migration_uses_random_one_time_passwords(sql_storage, capsys):
    passwords = migrate_json_to_sql(_json_export(), storage=sql_storage)
    assert set(passwords) == {"alice", "bob"}
    assert len(set(passwords.values())) == 2
    assert not sql_storage.verify_user_password("alice", "alice@temp123")
    assert sql_storage.verify_user_password("alice", passwords["alice"])
    assert "@temp123" not in capsys.readouterr().out


def test_migration_never_attaches_tasks_to_an_existing_account(sql_storage):
    existing = sql_storage.create_user("alice", "someone-elses-password")
    migrate_json_to_sql(_json_export(), storage=sql_storage)
    assert sql_storage.get_user_tasks(existing.id) == []
    bob = sql_storage.get_user_by_username("bob")
    assert [t.title for t in sql_storage.get_user_tasks(bob.id)] == ["Bob's"]


def test_migration_rerun_does_not_duplicate(sql_storage):
    migrate_json_to_sql(_json_export(), storage=sql_storage)
    assert migrate_json_to_sql("tasks.json", storage=sql_storage) == {}
    alice = sql_storage.get_user_by_username("alice")
    assert len(sql_storage.get_user_tasks(alice.id)) == 2


def test_migration_keeps_history_honest(sql_storage):
    migrate_json_to_sql(_json_export(), storage=sql_storage)
    alice = sql_storage.get_user_by_username("alice")
    tasks = {t.title: t for t in sql_storage.get_user_tasks(alice.id)}
    assert tasks["Done"].completed is True and tasks["Done"].completed_at is None
    assert tasks["Write"].created_at.replace(tzinfo=None).date() == date(2026, 1, 2)


# --------------------------------------------------------------------------- #
# Password change endpoint                                                    #
# --------------------------------------------------------------------------- #
@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


def test_change_password(client):
    headers = auth_headers(client, "alice")
    url = "/api/users/me/password"
    wrong = client.put(url, headers=headers, json={"current_password": "nope-nope", "new_password": "brand-new-pw"})
    assert wrong.status_code == 400
    ok = client.put(url, headers=headers, json={"current_password": DEFAULT_PASSWORD, "new_password": "brand-new-pw"})
    assert ok.status_code == 204
    login = client.post("/api/auth/login", json={"username": "alice", "password": "brand-new-pw"})
    assert login.status_code == 200
    old = client.post("/api/auth/login", json={"username": "alice", "password": DEFAULT_PASSWORD})
    assert old.status_code == 401
    too_long = client.put(url, headers=headers, json={"current_password": "brand-new-pw", "new_password": "x" * 80})
    assert too_long.status_code == 422
