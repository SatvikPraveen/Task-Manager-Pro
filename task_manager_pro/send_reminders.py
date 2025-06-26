# send_reminders.py
import datetime
from task_manager_pro.storage.json_storage import JSONStorage
from task_manager_pro.utils.emailer import send_email_reminder
import sys

# Ensure print statements are flushed immediately (for cron logs)
sys.stdout.reconfigure(line_buffering=True)

storage = JSONStorage("tasks.json")
data = storage.load_data()

today = datetime.date.today()
print(f"[{datetime.datetime.now()}] Starting scheduled reminders...\n")

updated = False  # Track if we modify anything

for user_data in data.get("users", []):
    username = user_data["username"]
    email = user_data.get("email")
    reminders_enabled = user_data.get("email_reminders_enabled", False)
    last_reminder_date = user_data.get("last_reminder_date")

    if not email or not reminders_enabled:
        continue

    # Skip if already reminded today
    if last_reminder_date == str(today):
        print(f"[{username}] 💤 Reminder already sent today.")
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

        user_data["last_reminder_date"] = str(today)
        updated = True
    else:
        print(f"[{username}] ✅ No due tasks.")

if updated:
    storage.save_data(data)