"""
models/task.py

Defines the Task class representing an individual task in the task manager.
Includes attributes like title, description, due date, and completion status.
Supports serialization to/from dictionary for storage.
"""

from datetime import datetime
from typing import Optional

class Task:
    def __init__(self, title: str, description: str, due_date: str, completed: bool = False):
        """
        Initializes a Task instance.

        Args:
            title (str): Title of the task.
            description (str): Optional description.
            due_date (str): Due date in 'YYYY-MM-DD' format.
            completed (bool): Completion status. Default is False.
        """
        self._title = title
        self._description = description
        self._due_date = datetime.strptime(due_date, "%Y-%m-%d")
        self._completed = completed
        self._created_at = datetime.now()
        self._id: Optional[str] = None  # Will be assigned after creation

    @property
    def id(self) -> Optional[str]:
        """Returns the task ID."""
        return self._id

    @id.setter
    def id(self, value: str):
        """Sets the task ID."""
        self._id = value

    @property
    def title(self):
        return self._title

    @property
    def description(self):
        return self._description

    @property
    def due_date(self):
        """Returns due date as a formatted string."""
        return self._due_date.strftime("%Y-%m-%d")

    @property
    def completed(self):
        return self._completed

    def mark_complete(self):
        """Marks the task as completed."""
        self._completed = True

    def to_dict(self):
        """
        Converts the task to a dictionary format for JSON serialization.
        """
        return {
            "id": self._id,
            "title": self._title,
            "description": self._description,
            "due_date": self.due_date,
            "completed": self._completed,
            "created_at": self._created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

    @staticmethod
    def from_dict(data: dict):
        """
        Creates a Task object from a dictionary.

        Args:
            data (dict): Dictionary with task data.

        Returns:
            Task: A Task object reconstructed from the dictionary.
        """
        task = Task(
            title=data["title"],
            description=data["description"],
            due_date=data["due_date"],
            completed=data.get("completed", False)
        )
        task.id = data.get("id")
        return task

    def __str__(self):
        return f"{self._title} - Due: {self._due_date} - {'Done' if self.completed else 'Pending'}"

    def __repr__(self):
        return f"<Task {self.title}>"