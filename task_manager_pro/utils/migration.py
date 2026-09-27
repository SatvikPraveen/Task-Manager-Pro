"""
utils/migration.py

Migration utilities to convert from JSON storage to SQL database.
Safely imports existing data from tasks.json to SQLite database.
"""

import json
import os

from task_manager_pro.storage.sql_storage import SQLStorage


def migrate_json_to_sql(json_file: str = "tasks.json", dry_run: bool = False):
    """
    Migrate data from JSON file to SQL database.

    Args:
        json_file (str): Path to tasks.json file
        dry_run (bool): If True, only print what would be migrated
    """
    # Check if JSON file exists
    if not os.path.exists(json_file):
        print(f"ℹ️ No {json_file} file found. Starting with empty database.")
        return

    # Load JSON data
    try:
        with open(json_file) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"❌ Error: {json_file} is not valid JSON")
        return

    print(f"📥 Migrating data from {json_file}...")

    # Initialize SQL storage
    sql_storage = SQLStorage()

    # Migrate users
    users_migrated = 0
    if "users" in data:
        for user_data in data["users"]:
            username = user_data.get("username")
            email = user_data.get("email")

            if not username:
                print("⚠️ Skipping user without username")
                continue

            # Generate a default password hash (user should reset on first login)
            default_password = f"{username}@temp123"

            if dry_run:
                print(f"  ✓ Would create user: {username} ({email})")
            else:
                try:
                    sql_storage.create_user(username=username, password=default_password, email=email)
                    print(f"  ✓ Migrated user: {username}")
                    users_migrated += 1
                except ValueError as e:
                    print(f"  ⚠️ {e}")

    # Migrate tasks
    tasks_migrated = 0
    if "tasks" in data:
        for task_data in data["tasks"]:
            user_id = None
            username = task_data.get("user")

            if not username:
                print("⚠️ Skipping task without user association")
                continue

            # Find user by username
            user = sql_storage.get_user_by_username(username)
            if not user:
                print(f"⚠️ Skipping task - user '{username}' not found")
                continue

            user_id = user.id
            title = task_data.get("title")
            description = task_data.get("description", "")
            due_date = task_data.get("due_date")
            completed = task_data.get("completed", False)
            priority = task_data.get("priority", "medium")

            if not title or not due_date:
                print("⚠️ Skipping task without title or due_date")
                continue

            if dry_run:
                print(f"  ✓ Would create task: {title} for {username}")
            else:
                try:
                    task = sql_storage.create_task(
                        user_id=user_id, title=title, description=description, due_date=due_date, priority=priority
                    )
                    if completed:
                        sql_storage.update_task(task.id, completed=True)

                    print(f"  ✓ Migrated task: {title}")
                    tasks_migrated += 1
                except Exception as e:
                    print(f"  ❌ Error migrating task '{title}': {e}")

    print("\n✅ Migration complete!")
    print(f"  Users migrated: {users_migrated}")
    print(f"  Tasks migrated: {tasks_migrated}")

    if not dry_run:
        print("\n💡 Note: Default passwords set to '<username>@temp123'")
        print("   Users should change their password on first login.")


if __name__ == "__main__":
    import sys

    json_file = sys.argv[1] if len(sys.argv) > 1 else "tasks.json"
    dry_run = "--dry-run" in sys.argv

    migrate_json_to_sql(json_file, dry_run=dry_run)
