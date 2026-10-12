"""
utils/migration.py

Migration utilities to convert from JSON storage to SQL database.
Safely imports existing data from tasks.json to the SQL database.

Safety rules:

* Only accounts created by *this* run receive tasks. If a username already
  exists in the database it belongs to someone else (or to an earlier run), so
  its JSON tasks are skipped. That also makes re-running the script a no-op
  instead of duplicating every task.
* Each migrated account gets a random one-time password, printed once for the
  operator to hand over. Users replace it with ``PUT /api/users/me/password``.
* ``created_at`` is carried over; completed tasks keep ``completed_at`` empty
  because the JSON store never recorded when they were finished.
"""

import json
import os
import secrets
from datetime import datetime, timezone
from typing import Any, Optional

from task_manager_pro.storage.sql_storage import SQLStorage


def _one_time_password() -> str:
    return secrets.token_urlsafe(18)  # 24 chars, ~144 bits


def _json_created_at(value: Any) -> Optional[datetime]:
    """The CLI stored local wall-clock time as 'YYYY-MM-DD HH:MM:SS'; convert it to UTC."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").astimezone(timezone.utc)
    except ValueError:
        return None


def migrate_json_to_sql(json_file: str = "tasks.json", dry_run: bool = False, storage: Optional[SQLStorage] = None):
    """
    Migrate data from JSON file to SQL database.

    Args:
        json_file (str): Path to tasks.json file
        dry_run (bool): If True, only print what would be migrated
        storage (Optional[SQLStorage]): Target storage; defaults to the configured database.

    Returns:
        dict[str, str]: username -> one-time password for every account created.
    """
    # Check if JSON file exists
    if not os.path.exists(json_file):
        print(f"ℹ️ No {json_file} file found. Starting with empty database.")
        return {}

    # Load JSON data
    try:
        with open(json_file) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"❌ Error: {json_file} is not valid JSON")
        return {}

    print(f"📥 Migrating data from {json_file}...")

    sql_storage = storage or SQLStorage()

    # Migrate users. Only usernames created here may receive tasks below.
    created: dict[str, str] = {}  # username -> user id ("" in a dry run)
    passwords: dict[str, str] = {}
    for user_data in data.get("users", []):
        username = user_data.get("username")
        email = user_data.get("email")

        if not username:
            print("⚠️ Skipping user without username")
            continue
        if username in created:
            continue

        if sql_storage.get_user_by_username(username):
            print(f"  ⚠️ User '{username}' already exists in the database; skipping the account and its tasks")
            continue

        if dry_run:
            print(f"  ✓ Would create user: {username} ({email})")
            created[username] = ""
            continue

        password = _one_time_password()
        try:
            user = sql_storage.create_user(username=username, password=password, email=email)
        except ValueError as e:
            print(f"  ⚠️ {e}; skipping the account and its tasks")
            continue
        if user_data.get("email_reminders_enabled") is False:
            sql_storage.update_user(user.id, email_reminders_enabled=False)
        created[username] = user.id
        passwords[username] = password
        print(f"  ✓ Migrated user: {username}")

    # Migrate tasks
    tasks_migrated = 0
    for task_data in data.get("tasks", []):
        username = task_data.get("user")

        if not username:
            print("⚠️ Skipping task without user association")
            continue
        if username not in created:
            print(f"⚠️ Skipping task - user '{username}' was not created by this migration")
            continue

        title = task_data.get("title")
        description = task_data.get("description", "")
        due_date = task_data.get("due_date")
        completed = bool(task_data.get("completed", False))
        priority = task_data.get("priority", "medium")

        if not title or not due_date:
            print("⚠️ Skipping task without title or due_date")
            continue

        if dry_run:
            print(f"  ✓ Would create task: {title} for {username}")
            continue
        try:
            sql_storage.create_task(
                user_id=created[username],
                title=title,
                description=description,
                due_date=due_date,
                priority=priority,
                completed=completed,
                created_at=_json_created_at(task_data.get("created_at")),
            )
            print(f"  ✓ Migrated task: {title}")
            tasks_migrated += 1
        except Exception as e:
            print(f"  ❌ Error migrating task '{title}': {e}")

    print("\n✅ Migration complete!")
    print(f"  Users migrated: {len(passwords)}")
    print(f"  Tasks migrated: {tasks_migrated}")

    if passwords:
        print("\n🔑 One-time passwords (shown once; hand each to its user, who should set a new one")
        print("   with PUT /api/users/me/password):")
        for username, password in passwords.items():
            print(f"   {username}: {password}")

    return passwords


if __name__ == "__main__":
    import sys

    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    json_file = args[0] if args else "tasks.json"
    dry_run = "--dry-run" in sys.argv

    migrate_json_to_sql(json_file, dry_run=dry_run)
