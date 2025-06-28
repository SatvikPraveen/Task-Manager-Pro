"""
utils/session.py

Manages user session persistence using a local JSON file.
Stores and retrieves the username of the currently logged-in user.
Useful for maintaining login state across CLI invocations.
"""

import json
import os
from typing import Optional

# Name of the session file to store the current user session
SESSION_FILE = "session.json"

def save_session(username: str) -> None:
    """
    Saves the current user's session to disk.

    Args:
        username (str): The username to persist in the session file.
    """
    with open(SESSION_FILE, "w") as f:
        json.dump({"username": username}, f)

def load_session() -> Optional[str]:
    """
    Loads the current user's session from disk.

    Returns:
        Optional[str]: The username if a session exists, else None.
    """
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            return json.load(f).get("username")
    return None

def clear_session() -> None:
    """
    Clears the current user session by deleting the session file.
    """
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)