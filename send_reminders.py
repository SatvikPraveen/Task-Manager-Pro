# send_reminders.py
import datetime
from storage.json_storage import JSONStorage
from utils.emailer import send_email_reminder

storage = JSONStorage("tasks.json")
data = storage.load_data()

today = datetime.date.today()
print(f"[{datetime.datetime.now()}] Starting scheduled reminders...\n")

for user_data in data.get("users", []):
    username = user_data["username"]
    email = user_data.get("email")
    reminders_enabled = user_data.get("email_reminders_enabled", False)

    if not email or not reminders_enabled:
        continue

    due_tasks = [
        t for t in data.get("tasks", [])
        if t["user"] == username
        and not t["completed"]
        and datetime.datetime.strptime(t["due_date"], "%Y-%m-%d").date() <= today
    ]

    if due_tasks:
        subject = "⏰ Daily Task Reminder"
        body = "\n".join([f"{t['title']} — Due: {t['due_date']}" for t in due_tasks])
        send_email_reminder(to_email=email, subject=subject, body=body)
        print(f"[{username}] 🔔 Reminder sent to {email} for {len(due_tasks)} task(s).")
    else:
        print(f"[{username}] ✅ No due tasks.")