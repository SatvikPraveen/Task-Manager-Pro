"""
storage/json_storage.py

Implements the JSONStorage class, a concrete storage backend for Task Manager PRO.
Persists tasks and users data to a local JSON file (default: tasks.json).
Implements the StorageInterface to support load and save operations.
"""

import json
import os
from typing import Dict, Any
from task_manager_pro.storage.interface import StorageInterface

class JSONStorage(StorageInterface):
    def __init__(self, filename="tasks.json"):
        """
        Initializes the JSONStorage instance.

        Args:
            filename (str): Name of the JSON file to store task and user data.
        """
        self.filename = filename
        if not os.path.exists(self.filename):
            self._initialize_file()

    def _initialize_file(self):
        """
        Creates an empty JSON file with initial structure if it doesn't exist.
        """
        with open(self.filename, "w") as f:
            json.dump({"tasks": [], "users": []}, f)

    def load_data(self) -> Dict[str, Any]:
        """
        Loads and returns the data from the JSON file.

        Returns:
            Dict[str, Any]: Dictionary containing user and task data.
        """
        try:
            with open(self.filename, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"users": [], "tasks": []}
    
    def save_data(self, data):
        """
        Saves the provided data dictionary to the JSON file.

        Args:
            data (Dict[str, Any]): Dictionary containing updated task and user data.
        """
        with open(self.filename, "w") as f:
            json.dump(data, f, indent=4)