"""
storage/json_storage.py

Implements the JSONStorage class, a concrete storage backend for Task Manager PRO.
Persists tasks and users data to a local JSON file (default: tasks.json).
Implements the StorageInterface to support load and save operations.
"""

import json
import os
import tempfile
from typing import Any

from task_manager_pro.storage.interface import StorageInterface


class CorruptDataError(ValueError):
    """The data file exists but is not valid JSON of the expected shape."""


class JSONStorage(StorageInterface):
    def __init__(self, filename: str = "tasks.json") -> None:
        """
        Initializes the JSONStorage instance.

        Args:
            filename (str): Name of the JSON file to store task and user data.
        """
        self.filename = filename
        if not os.path.exists(self.filename):
            self._initialize_file()

    def _initialize_file(self) -> None:
        """
        Creates an empty JSON file with initial structure if it doesn't exist.
        """
        with open(self.filename, "w") as f:
            json.dump({"tasks": [], "users": []}, f)

    def load_data(self) -> dict[str, Any]:
        """
        Loads and returns the data from the JSON file.

        Returns:
            Dict[str, Any]: Dictionary containing user and task data.
        """
        try:
            with open(self.filename) as f:
                data = json.load(f)
        except FileNotFoundError:
            return {"users": [], "tasks": []}
        except json.JSONDecodeError as exc:
            raise CorruptDataError(f"{self.filename} is not valid JSON ({exc}); fix or remove it") from exc
        if not isinstance(data, dict):
            raise CorruptDataError(f"{self.filename} must contain a JSON object with 'users' and 'tasks'")
        data.setdefault("users", [])
        data.setdefault("tasks", [])
        return data

    def save_data(self, data: dict[str, Any]) -> None:
        """
        Saves the provided data dictionary to the JSON file.

        Args:
            data (Dict[str, Any]): Dictionary containing updated task and user data.
        """
        # Write a temp file in the same directory and atomically swap it in, so a
        # crash mid-write can never leave a truncated tasks.json behind.
        directory = os.path.dirname(os.path.abspath(self.filename))
        fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tasks-", suffix=".json.tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.filename)
        except BaseException:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
