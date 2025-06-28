"""
models/user.py

Defines the User class used for representing individual users of the task manager.
Includes attributes like username, password, email, and preference for email reminders.
Provides methods for toggling reminder settings and verifying credentials.
Excludes raw password from serialization for safety.
"""

from typing import Optional

class User:
    def __init__(self, username: str, password: Optional[str] = None, email: Optional[str] = None, email_reminders_enabled: bool = True):
        """
        Initializes a User instance.

        Args:
            username (str): Unique username.
            password (Optional[str]): Raw password string (note: should be hashed in production).
            email (Optional[str]): Optional email address.
            email_reminders_enabled (bool): Whether email reminders are enabled.
        """
        self._username = username
        self._password = password  # ⚠️ In production, never store plain text passwords.
        self._email = email
        self._email_reminders_enabled = email_reminders_enabled

    @property
    def password(self):
        """
        Prevents direct access to the password for security reasons.
        Raises:
            AttributeError: Always raised to block access.
        """
        raise AttributeError("Access to password is restricted.")

    @property
    def username(self):
        """Returns the username of the user."""
        return self._username

    @property
    def email(self):
        """Returns the email of the user."""
        return self._email

    @property
    def email_reminders_enabled(self):
        """Returns whether email reminders are currently enabled."""
        return self._email_reminders_enabled

    def toggle_email_reminders(self):
        """
        Toggles the email reminder preference.

        Returns:
            bool: New value of email_reminders_enabled after toggling.
        """
        self._email_reminders_enabled = not self._email_reminders_enabled
        return self._email_reminders_enabled

    def verify_password(self, password: str) -> bool:
        """
        Verifies a password against the stored password.

        Args:
            password (str): Input password string.

        Returns:
            bool: True if the passwords match, False otherwise.
        """
        return self._password == password

    def to_dict(self):
        """
        Serializes user data to a dictionary (excludes password).

        Returns:
            dict: Serialized user data.
        """
        return {
            "username": self._username,
            "email": self._email,
            "email_reminders_enabled": self._email_reminders_enabled
        }

    def __str__(self):
        """Returns a human-readable string representation of the user."""
        return f"User({self.username})"

    def __repr__(self):
        """Returns a formal string representation of the user (for debugging)."""
        return f"<User {self.username}, email={self.email}>"