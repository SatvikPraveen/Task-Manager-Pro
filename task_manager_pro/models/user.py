from typing import Optional

class User:
    def __init__(self, username: str, password: Optional[str]=None, email: Optional[str]=None, email_reminders_enabled: bool=True):
        self._username = username
        self._password = password # In real apps, hash this!
        self._email = email
        self._email_reminders_enabled = email_reminders_enabled

    @property
    def password(self):
        raise AttributeError("Access to password is restricted.")

    
    @property
    def username(self):
        return self._username
    
    @property
    def email(self):
        return self._email
    
    @property
    def email_reminders_enabled(self):
        return self._email_reminders_enabled
    
    def toggle_email_reminders(self):
        self._email_reminders_enabled = not self._email_reminders_enabled
        return self._email_reminders_enabled
    
    def verify_password(self, password: str) -> bool:
        return self._password == password
    
    def to_dict(self):
        return {
            "username": self._username,
            "email": self._email,
            "email_reminders_enabled": self._email_reminders_enabled
        }
    
    def __str__(self):
        return f"User({self.username})"
    
    def __repr__(self):
        return f"<User {self.username}, email={self.email}>"