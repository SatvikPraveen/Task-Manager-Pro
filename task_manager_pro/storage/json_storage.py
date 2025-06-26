import json
import os
from typing import Dict, Any
from task_manager_pro.storage.interface import StorageInterface

class JSONStorage(StorageInterface):
    def __init__(self, filename="tasks.json"):
        self.filename = filename
        if not os.path.exists(self.filename):
            self._initialize_file()

    def _initialize_file(self):
        with open(self.filename, "w") as f:
            json.dump({"tasks": [], "users": []}, f)

    def load_data(self) -> Dict[str, Any]:
        try:
            with open(self.filename, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"users": [], "tasks": []}
    
    def save_data(self, data):
        with open(self.filename, "w") as f:
            json.dump(data, f, indent=4)
