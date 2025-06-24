from typing import Optional

class User:
    def __init__(self, username: str, password: Optional[str]=None):
        self._username = username
        self._password = password # In real apps, hash this!

    @property
    def password(self):
        raise AttributeError("Access to password is restricted.")

    
    @property
    def username(self):
        return self._username
    
    def verify_password(self, password: str) -> bool:
        return self._password == password
    
    def to_dict(self):
        return {
            "username": self._username
        }
    
    def __str__(self):
        return f"User({self.username})"
    
    def __repr__(self):
        return f"<User {self.username}>"