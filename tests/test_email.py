# test_email.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.emailer import send_email_reminder

send_email_reminder(
    to_email="satvikpraveen786@gmail.com",
    subject="Test Reminder",
    body="This is a test email from Task Manager PRO!"
)