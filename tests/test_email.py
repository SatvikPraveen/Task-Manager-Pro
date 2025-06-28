"""
tests/test_email.py

Test script for verifying the email reminder functionality.
Directly calls the send_email_reminder utility to ensure SMTP configuration,
authentication, and email dispatch are working as expected.
Intended for manual testing only, not automated unit tests.
"""

import sys
import os

# Add the project root directory to the Python path
# Ensures relative imports from task_manager_pro module work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the email reminder function
from task_manager_pro.utils.emailer import send_email_reminder

# Send a test email to verify that the system is configured correctly
send_email_reminder(
    to_email="satvikpraveen786@gmail.com",
    subject="Test Reminder",
    body="This is a test email from Task Manager PRO!"
)