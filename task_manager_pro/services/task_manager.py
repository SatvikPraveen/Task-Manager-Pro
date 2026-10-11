"""
services/task_manager.py

Defines the TaskManager class, the core controller for managing tasks and users in the CLI application.
Responsible for user authentication, task CRUD operations, reminder notifications, and data persistence.
Uses decorators for logging, JSON/DB storage interface, and optional email reminders for due tasks.
"""

import uuid
from datetime import date, datetime
from typing import Any, Optional

from task_manager_pro.models.task import Task
from task_manager_pro.models.user import User
from task_manager_pro.storage.interface import StorageInterface
from task_manager_pro.utils.decorators import log_action, require_login
from task_manager_pro.utils.emailer import send_email_reminder
from task_manager_pro.utils.session import clear_session, load_session, save_session


def _parse_due(value: Any) -> Optional[date]:
    """Parse a stored or user-supplied 'YYYY-MM-DD' date; ``None`` if it isn't one."""
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def _prompt_email() -> str:
    """Ask for an optional email; returns '' when there is no one to ask (cron, scripts, docker)."""
    try:
        return input("📧 Enter your email (optional, for reminders): ").strip()
    except EOFError:
        return ""


class TaskManager:
    def __init__(self, storage: StorageInterface):
        """
        Initializes the TaskManager with a storage backend.

        Args:
            storage (StorageInterface): Abstract storage handler (e.g., JSON, SQLite).
        """
        self.storage = storage
        self.data = self.storage.load_data()
        username = load_session()  # Restore session if any
        self.current_user: Optional[User] = None
        if username:
            user_data = next((u for u in self.data["users"] if u["username"] == username), None)
            if user_data:
                self.current_user = User.from_dict(user_data)

    def _find_owned_task(self, task_id: str) -> Optional[dict[str, Any]]:
        """
        Returns the task with this ID if it belongs to the current user, else None.

        Every command that reads or changes a single task goes through here, so a
        user can never reach another user's task by guessing or knowing its ID.
        """
        if self.current_user is None:
            return None
        return next(
            (t for t in self.data["tasks"] if t.get("id") == task_id and t.get("user") == self.current_user.username),
            None,
        )

    def _print_due_reminders(self) -> None:
        """
        Checks and prints tasks that are due or overdue.
        Also sends an email reminder if user's email is configured.
        """
        user = self.current_user
        if user is None:
            return
        today = datetime.today().date()
        due_tasks = []
        for t in self.data["tasks"]:
            if t.get("user") != user.username or t.get("completed"):
                continue
            due = _parse_due(t.get("due_date"))
            if due is None:
                print(
                    f"⚠️ Task '{t.get('title')}' has an invalid due date {t.get('due_date')!r}; fix it with update-task"
                )
            elif due <= today:
                due_tasks.append(t)

        if due_tasks:
            print("\n⏰ You have tasks due or overdue:")
            for t in due_tasks:
                print(f"  🔔 {t['title']} — Due: {t['due_date']}")

        # Send optional email reminder, only if the user has them switched on
        if due_tasks and user.email and user.email_reminders_enabled:
            subject = "🔔 Task Due Reminder"
            message = "\n".join([f"{t['title']} — Due: {t['due_date']}" for t in due_tasks])
            if not send_email_reminder(to_email=user.email, subject=subject, body=message):
                print("⚠️ Could not send email reminder (see log for details).")

    @log_action
    def login(self, username: str, email: Optional[str] = None):
        """
        Logs in the user, or creates one if not already registered.

        Args:
            username (str): Username.
            email (Optional[str]): Optional email for reminder setup.
        """
        user_data = next((u for u in self.data["users"] if u["username"] == username), None)

        if user_data:
            self.current_user = User.from_dict(user_data)
            if not user_data.get("email"):
                user_email = email or _prompt_email()
                if user_email:
                    self.current_user._email = user_email
                    user_data["email"] = user_email
                    self.storage.save_data(self.data)
        else:
            self.current_user = User(username, email=email)
            if not email:
                user_email = _prompt_email()
                if user_email:
                    self.current_user._email = user_email
            self.data["users"].append(self.current_user.to_dict())
            self.storage.save_data(self.data)

        save_session(username)
        print(f"✅ Logged in as {self.current_user.username}")
        self._print_due_reminders()

    @log_action
    @require_login
    def add_task(self, title: str, desc: str, due: str):
        """
        Adds a new task for the current user.

        Args:
            title (str): Task title.
            desc (str): Task description.
            due (str): Due date in 'YYYY-MM-DD'.
        """
        assert self.current_user is not None  # guaranteed by @require_login
        if _parse_due(due) is None:
            print(f"❌ Invalid due date {due!r}; use YYYY-MM-DD.")
            return
        task = Task(title, desc, due)
        task.id = uuid.uuid4().hex
        task_dict = task.to_dict()
        task_dict["id"] = task.id
        task_dict["user"] = self.current_user.username

        self.data["tasks"].append(task_dict)
        self.storage.save_data(self.data)
        print(f"✅ Task '{title}' added.")
        print(f"🆔 Task ID: {task.id}")

    @log_action
    @require_login
    def update_task(
        self, task_id: str, title: Optional[str] = None, desc: Optional[str] = None, due: Optional[str] = None
    ):
        """
        Updates an existing task's title, description, or due date.

        Args:
            task_id (str): Unique task identifier.
            title (Optional[str]): New title.
            desc (Optional[str]): New description.
            due (Optional[str]): New due date.
        """
        if due and _parse_due(due) is None:
            print(f"❌ Invalid due date {due!r}; use YYYY-MM-DD.")
            return
        task = self._find_owned_task(task_id)
        if task is None:
            print("❌ Task not found or does not belong to current user.")
            return

        if title:
            task["title"] = title
        if desc:
            task["description"] = desc
        if due:
            task["due_date"] = due
        self.storage.save_data(self.data)
        print(f"🔄 Task '{task_id}' updated successfully.")

    @log_action
    @require_login
    def mark_task_complete(self, task_id: str):
        """
        Marks a task as completed.

        Args:
            task_id (str): Unique task identifier.
        """
        task = self._find_owned_task(task_id)
        if task is None:
            print("❌ Task not found or does not belong to current user.")
            return

        task["completed"] = True
        self.storage.save_data(self.data)
        print(f"✅ Task '{task['title']}' marked as completed.")

    @log_action
    @require_login
    def list_tasks(self, filter_status: str, verbose: bool = False, summary: bool = False):
        """
        Lists tasks based on filter and verbosity settings.

        Args:
            filter_status (str): Filter by status — 'all', 'completed', or 'pending'.
            verbose (bool): Show description for each task.
            summary (bool): Show overall task count breakdown.
        """
        assert self.current_user is not None  # guaranteed by @require_login
        tasks = [t for t in self.data["tasks"] if t.get("user") == self.current_user.username]

        if filter_status == "completed":
            tasks = [t for t in tasks if t["completed"]]
        elif filter_status == "pending":
            tasks = [t for t in tasks if not t["completed"]]

        if not tasks:
            print("📭 No tasks found.")
        else:
            for task in tasks:
                status = "✅" if task["completed"] else "⏳"
                print(f"{status} {task['title']} - Due: {task['due_date']}")
                if verbose:
                    print(f"    📝 {task['description']}")

        if summary:
            total = len(tasks)
            completed = sum(1 for t in tasks if t["completed"])
            pending = total - completed
            print(f"\n📊 Summary:\nTotal: {total} | Completed: {completed} | Pending: {pending}")

        self._print_due_reminders()

    @log_action
    @require_login
    def delete_task(self, task_id: str):
        """
        Deletes a task by ID.

        Args:
            task_id (str): Unique task identifier.
        """
        task = self._find_owned_task(task_id)
        if task is None:
            print("❌ Task not found or does not belong to current user.")
            return

        self.data["tasks"].remove(task)
        self.storage.save_data(self.data)
        print(f"🗑️ Deleted task '{task['title']}'")

    @log_action
    def logout(self):
        """
        Logs out the current user and clears session.
        """
        if self.current_user:
            print(f"👋 Logged out {self.current_user.username}")
            self.current_user = None
            clear_session()
        else:
            print("⚠️ No user is currently logged in.")

    @log_action
    @require_login
    def send_due_reminders(self):
        """
        Triggers due task reminder check and optional email dispatch.
        """
        self._print_due_reminders()

    @log_action
    @require_login
    def toggle_email_reminders(self):
        """
        Toggles email reminder setting for the current user.
        Also updates the setting in persistent storage.
        """
        assert self.current_user is not None  # guaranteed by @require_login
        updated_value = self.current_user.toggle_email_reminders()
        print(f"🔧 Email reminders {'enabled' if updated_value else 'disabled'}.")

        for u in self.data["users"]:
            if u["username"] == self.current_user.username:
                u["email_reminders_enabled"] = updated_value
                break

        self.storage.save_data(self.data)
