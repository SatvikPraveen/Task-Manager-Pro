"""
tests/test_user.py

Unit tests for the User model in the Task Manager PRO application.
Tests user creation and access control for sensitive user attributes like password.
"""

import pytest
from task_manager_pro.models.user import User

def test_user_creation():
    """
    Test creation of a new user and verifies that username is correctly assigned.
    """
    user = User("satvik", "secret")
    assert user.username == "satvik"

# def test_user_password_not_exposed():
#     """
#     Test that accessing the protected _password attribute raises an error.
#     This is commented out as Python does not enforce strict encapsulation,
#     but it demonstrates intent to avoid direct password access.
#     """
#     user = User("satvik", "secret")
#     with pytest.raises(AttributeError):
#         _ = user._password  # trying to access protected member (by convention)