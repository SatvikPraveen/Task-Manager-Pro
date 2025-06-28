"""
tests/test_tasks.py

Unit tests for the Task model in the Task Manager PRO application.
Validates task creation, status updates, string representations,
and dictionary conversion functionality using pytest.
"""

import pytest
from task_manager_pro.models.task import Task

def test_task_creation():
    """
    Test basic task initialization with title, description, and due date.
    Ensures fields are correctly assigned and task starts as incomplete.
    """
    task = Task("Read", "Read book", "2025-12-01")
    assert task.title == "Read"
    assert task.description == "Read book"
    assert task.due_date == "2025-12-01"
    assert not task.completed

def test_mark_task_completed():
    """
    Test the mark_complete() method to ensure task status is updated.
    """
    task = Task("Test", "This is a test", "2025-07-01")
    task.mark_complete()
    assert task.completed

def test_task_string_representation():
    """
    Test the string representation (__str__) of a Task instance.
    Ensures task title and status appear in the string output.
    """
    task = Task("Test", "Try string", "2025-01-01")
    assert "Test" in str(task)
    assert "Pending" in str(task)

def test_task_dict_conversion():
    """
    Test the to_dict() method to ensure correct dictionary serialization.
    Validates key fields like title and creation timestamp.
    """
    task = Task("Dict Task", "With dict", "2025-05-01")
    task_dict = task.to_dict()
    assert task_dict["title"] == "Dict Task"
    assert "created_at" in task_dict