import pytest
from models.task import Task

def test_task_creation():
    task = Task("Read", "Read book", "2025-12-01")
    assert task.title == "Read"
    assert task.description == "Read book"
    assert task.due_date == "2025-12-01"
    assert not task.completed

def test_mark_task_completed():
    task = Task("Test", "This is a test", "2025-07-01")
    task.mark_complete()
    assert task.completed

def test_task_string_representation():
    task = Task("Test", "Try string", "2025-01-01")
    assert "Test" in str(task)
    assert "Pending" in str(task)

def test_task_dict_conversion():
    task = Task("Dict Task", "With dict", "2025-05-01")
    task_dict = task.to_dict()
    assert task_dict["title"] == "Dict Task"
    assert "created_at" in task_dict