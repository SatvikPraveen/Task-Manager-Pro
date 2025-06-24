from datetime import datetime
from typing import Optional

class Task:
    def __init__(self, title: str, description: str, due_date: str, completed: bool=False):
        self._title = title
        self._description = description
        self._due_date = datetime.strptime(due_date, "%Y-%m-%d") # You can convert it to datetime.date in logic layer
        self._completed = completed
        self._created_at = datetime.now()
        self._id: Optional[str] = None # ID will be sent after creation

    @property
    def id(self) -> Optional[str]:
        return self._id
    
    @id.setter
    def id(self, value:str):
        self._id = value

    @property
    def title(self):
        return self._title
    
    @property
    def description(self):
        return self._description
    
    @property
    def due_date(self):
        return self._due_date.strftime("%Y-%m-%d")
    
    @property
    def completed(self):
        return self._completed

    def mark_complete(self):
        self._completed = True

    def to_dict(self):
        return {
            "id": self._id,
            "title": self._title,
            "description": self._description,
            "due_date": self.due_date,
            "completed": self._completed,
            "created_at": self._created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

    @staticmethod
    def from_dict(data:dict):
        task= Task(
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