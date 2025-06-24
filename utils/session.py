import json
import os
from typing import Optional

SESSION_FILE = "session.json"

def save_session(username: str) -> None:
    with open(SESSION_FILE, "w") as f:
        json.dump({"username": username}, f)

def load_session() -> Optional[str]:
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            return json.load(f).get("username")
    return None

def clear_session() -> None:
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)