"""
utils/emailer.py

Provides functionality for sending email reminders to users about due tasks.
Uses SMTP with STARTTLS and reads credentials from a .env file for secure configuration.
"""

import os
import smtplib
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables (e.g., email credentials, SMTP server details)
load_dotenv()

EMAIL_ADDRESS = os.environ.get("EMAIL_USER")            # Sender's email address
EMAIL_PASSWORD = os.environ.get("EMAIL_PASS")           # Sender's email password or app-specific password
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")  # Default SMTP server
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))       # Port for STARTTLS (default: 587)


def send_email_reminder(to_email: str, subject: str, body: str):
    """
    Sends an email reminder using SMTP.

    Args:
        to_email (str): Recipient's email address.
        subject (str): Subject line of the email.
        body (str): Main body content of the email.
    """
    try:
        # Construct the email message
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Establish connection to the SMTP server using STARTTLS
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)  # Login using credentials
            server.send_message(msg)  # Send the email

        print(f"📧 Email reminder sent to {to_email}!")

    except Exception as e:
        # Handle and display any errors encountered
        print(f"❌ Failed to send email: {e}")