"""
utils/emailer.py

SMTP email delivery for task reminders (STARTTLS).

Credentials and server details come from :mod:`task_manager_pro.config`.
The transport is injectable so tests can assert on the message that would be
sent without touching the network.
"""

from __future__ import annotations

import logging
import smtplib
from collections.abc import Callable
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from task_manager_pro.config import get_settings

logger = logging.getLogger(__name__)

SMTPFactory = Callable[[str, int], smtplib.SMTP]


def build_message(sender: str, to_email: str, subject: str, body: str) -> MIMEMultipart:
    """Construct the MIME message for a plain-text reminder."""
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    return msg


def send_email_reminder(
    to_email: str,
    subject: str,
    body: str,
    *,
    smtp_factory: Optional[SMTPFactory] = None,
) -> bool:
    """
    Send a reminder email.

    Returns ``True`` on success, ``False`` if email is not configured or the
    transport failed. Failures are logged rather than raised because reminders
    are best-effort side effects of other operations.
    """
    settings = get_settings()
    if not settings.email_configured:
        logger.warning("Email not configured: EMAIL_USER and EMAIL_PASS must be set")
        return False

    sender = settings.email_user or ""
    password = settings.email_pass.get_secret_value() if settings.email_pass else ""
    factory: SMTPFactory = smtp_factory or smtplib.SMTP

    try:
        msg = build_message(sender, to_email, subject, body)
        with factory(settings.smtp_server, settings.smtp_port) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        logger.info("Email reminder sent to %s", to_email)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)
        return False
