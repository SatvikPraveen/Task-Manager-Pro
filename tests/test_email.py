"""
tests/test_email.py

Unit tests for the SMTP reminder helper. The transport is replaced with an
in-memory fake so no network access happens.
"""

from __future__ import annotations

import smtplib

import pytest

from task_manager_pro.config import reset_settings
from task_manager_pro.utils.emailer import build_message, send_email_reminder


class FakeSMTP:
    """Records the calls a real ``smtplib.SMTP`` would receive."""

    instances: list[FakeSMTP] = []

    def __init__(self, host: str, port: int) -> None:
        self.host, self.port = host, port
        self.calls: list[str] = []
        self.sent = []
        FakeSMTP.instances.append(self)

    def __enter__(self) -> FakeSMTP:
        return self

    def __exit__(self, *exc) -> None:  # type: ignore[no-untyped-def]
        self.calls.append("close")

    def starttls(self) -> None:
        self.calls.append("starttls")

    def login(self, user: str, password: str) -> None:
        self.calls.append(f"login:{user}")

    def send_message(self, msg) -> None:  # type: ignore[no-untyped-def]
        self.calls.append("send")
        self.sent.append(msg)


class FailingSMTP(FakeSMTP):
    def login(self, user: str, password: str) -> None:
        raise smtplib.SMTPAuthenticationError(535, b"bad credentials")


@pytest.fixture
def email_env(monkeypatch):
    monkeypatch.setenv("EMAIL_USER", "sender@example.com")
    monkeypatch.setenv("EMAIL_PASS", "app-password")
    monkeypatch.setenv("SMTP_SERVER", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "2525")
    reset_settings()
    FakeSMTP.instances.clear()
    yield
    reset_settings()


def test_build_message_headers():
    msg = build_message("a@example.com", "b@example.com", "Subject", "Body text")
    assert msg["From"] == "a@example.com"
    assert msg["To"] == "b@example.com"
    assert msg["Subject"] == "Subject"
    assert "Body text" in msg.as_string()


def test_send_returns_false_when_unconfigured(monkeypatch):
    monkeypatch.setenv("EMAIL_USER", "")
    monkeypatch.setenv("EMAIL_PASS", "")
    reset_settings()
    try:
        assert send_email_reminder("x@example.com", "s", "b", smtp_factory=FakeSMTP) is False
        assert FakeSMTP.instances == []
    finally:
        reset_settings()


def test_send_uses_starttls_login_and_send(email_env):
    ok = send_email_reminder("to@example.com", "Reminder", "Do the thing", smtp_factory=FakeSMTP)
    assert ok is True
    (smtp,) = FakeSMTP.instances
    assert (smtp.host, smtp.port) == ("smtp.example.com", 2525)
    assert smtp.calls == ["starttls", "login:sender@example.com", "send", "close"]
    assert smtp.sent[0]["To"] == "to@example.com"


def test_send_swallows_transport_errors(email_env):
    assert send_email_reminder("to@example.com", "s", "b", smtp_factory=FailingSMTP) is False
