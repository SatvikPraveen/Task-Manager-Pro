'''
send_reminders.py

This script sends daily email reminders to users who have due or overdue tasks.
Designed to be run as a scheduled job (e.g., via cron).
Ensures reminders are not sent multiple times in a day and logs output for tracking.
'''

import datetime
from task_manager_pro.storage.json_storage import JSONStorage
from task_manager_pro.utils.emailer import send_email_reminder
import sys

# Ensure print statements are immediately flushed (important for cron log visibility)
sys.stdout.reconfigure(line_buffering=True)

# Load stored task/user data from JSON file
storage = JSONStorage("tasks.json")
data = storage.load_data()

# Get today's date for comparison
today = datetime.date.today()
print(f"[{datetime.datetime.now()}] Starting scheduled reminders...\n")

# Flag to track whether any data was updated (to decide if we need to save)
updated = False

# Iterate through all users in the storage
for user_data in data.get("users", []):
    username = user_data["username"]
    email = user_data.get("email")
    reminders_enabled = user_data.get("email_reminders_enabled", False)
    last_reminder_date = user_data.get("last_reminder_date")

    # Skip users without email or if they have reminders disabled
    if not email or not reminders_enabled:
        continue

    # Skip if reminder already sent today
    if last_reminder_date == str(today):
        print(f"[{username}] 💤 Reminder already sent today.")
        continue

    # Filter due/overdue tasks for this user
    due_tasks = [
        t for t in data.get("tasks", [])
        if t["user"] == username
        and not t["completed"]
        and datetime.datetime.strptime(t["due_date"], "%Y-%m-%d").date() <= today
    ]

    # If due tasks exist, send reminder and update last reminder date
    if due_tasks:
        subject = "⏰ Daily Task Reminder"
        body = "\n".join([f"{t['title']} — Due: {t['due_date']}" for t in due_tasks])
        send_email_reminder(to_email=email, subject=subject, body=body)
        print(f"[{username}] 🔔 Reminder sent to {email} for {len(due_tasks)} task(s).")

        user_data["last_reminder_date"] = str(today)
        updated = True
    else:
        print(f"[{username}] ✅ No due tasks.")

# Persist changes only if we updated reminder timestamps
if updated:
    storage.save_data(data)