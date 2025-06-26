import uuid
from typing import Optional
from task_manager_pro.models.task import Task
from task_manager_pro.models.user import User
from task_manager_pro.storage.interface import StorageInterface
from task_manager_pro.utils.decorators import log_action
from task_manager_pro.utils.session import save_session, load_session, clear_session
from datetime import datetime
from task_manager_pro.utils.emailer import send_email_reminder


class TaskManager:
    def __init__(self, storage: StorageInterface):
        self.storage = storage
        self.data = self.storage.load_data()
        username = load_session()
        self.current_user: Optional[User] = None
        if username:
            user_data = next((u for u in self.data["users"] if u["username"] == username), None)
            if user_data:
                self.current_user = User(**user_data)


    def _print_due_reminders(self):
        today = datetime.today().date()
        due_tasks = [
            t for t in self.data["tasks"]
            if t["user"] == self.current_user.username
            and not t["completed"]
            and datetime.strptime(t["due_date"], "%Y-%m-%d").date() <= today
        ]

        if due_tasks:
            print("\n⏰ You have tasks due or overdue:")
            for t in due_tasks:
                print(f"  🔔 {t['title']} — Due: {t['due_date']}")

        # 📬 Optional email reminder
        if due_tasks and self.current_user._email:
            subject = "🔔 Task Due Reminder"
            message = "\n".join([f"{t['title']} — Due: {t['due_date']}" for t in due_tasks])
            try:
                send_email_reminder(
                    to_email=self.current_user._email,
                    subject=subject,
                    body=message
                )
            except Exception as e:
                print(f"⚠️ Could not send email reminder: {e}")


    @log_action
    def login(self, username: str, email: Optional[str] = None):
        # Basic login/creation
        user_data = next((u for u in self.data["users"] if u["username"] == username), None)

        if user_data:
            self.current_user = User(**user_data)
            if "email" not in user_data or not user_data["email"]:
                user_email = input("📧 Enter your email (optional, for reminders): ").strip()
                if user_email:
                    self.current_user._email = user_email
                    user_data["email"] = user_email
                    self.storage.save_data(self.data)
        else:
            self.current_user = User(username, email=email)
            if not email:
                user_email = input("📧 Enter your email (optional, for reminders): ").strip()
                if user_email:
                    self.current_user._email = user_email
            self.data["users"].append(self.current_user.to_dict())
            self.storage.save_data(self.data)

        save_session(username)
        print(f"✅ Logged in as {self.current_user.username}")
        self._print_due_reminders()


    @log_action
    def add_task(self, title: str, desc: str, due: str):
        if not self.current_user:
            print("❌ Please login first.")
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
    def update_task(self, task_id: str, title: str = None, desc: str = None, due: str = None):
        if not self.current_user:
            print("❌ Please login first.")
            return

        for task in self.data["tasks"]:
            if task["id"] == task_id and task["user"] == self.current_user.username:
                if title:
                    task["title"] = title
                if desc:
                    task["description"] = desc
                if due:
                    task["due_date"] = due
                self.storage.save_data(self.data)
                print(f"🔄 Task '{task_id}' updated successfully.")
                return

        print("❌ Task not found or does not belong to current user.")


    @log_action
    def mark_task_complete(self, task_id: str):
        for task in self.data["tasks"]:
            if task["id"] == task_id:
                task["completed"] = True
                self.storage.save_data(self.data)
                print(f"✅ Task '{task['title']}' marked as completed.")
                return
        print("❌ Task not found.")


    @log_action
    def list_tasks(self, filter_status: str, verbose: bool=False, summary: bool=False):
        tasks = self.data["tasks"]
        if self.current_user:
            tasks = [t for t in tasks if t["user"] == self.current_user.username]

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
    def delete_task(self, task_id: str):
        for i, task in enumerate(self.data["tasks"]):
            if task["id"] == task_id:
                deleted = self.data["tasks"].pop(i)
                self.storage.save_data(self.data)
                print(f"🗑️ Deleted task '{deleted['title']}'")
                return
        print("❌ Task not found.")


    @log_action
    def logout(self):
        if self.current_user:
            print(f"👋 Logged out {self.current_user.username}")
            self.current_user = None
            clear_session()
        else:
            print("⚠️ No user is currently logged in.")


    @log_action
    def send_due_reminders(self):
        if not self.current_user:
            print("❌ Please login first.")
            return 
        self._print_due_reminders()


    @log_action
    def toggle_email_reminders(self):
        if not self.current_user:
            print("❌ Please login first.")
            return
        
        updated_value = self.current_user.toggle_email_reminders()
        print(f"🔧 Email reminders {'enabled' if updated_value else 'disabled'}.")

        # Updated stored user data
        for u in self.data["users"]:
            if u["username"] == self.current_user.username:
                u["email_reminders_enabled"] = updated_value
                break
        
        self.storage.save_data(self.data)