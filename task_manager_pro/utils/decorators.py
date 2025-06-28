"""
utils/decorators.py

Provides function decorators to enhance functionality of CLI actions.
Includes logging of function calls and enforcement of login requirements.
"""

from functools import wraps
from datetime import datetime


def log_action(func):
    """
    Logs every decorated function call with a timestamp and function name.

    Args:
        func (Callable): The function being decorated.

    Returns:
        Callable: Wrapped function with logging functionality.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        func_name = func.__name__.replace("_", " ").title()
        print(f"[{timestamp}] ▶ Executing: {func_name}")
        result = func(*args, **kwargs)
        print(f"[{timestamp}] ✔ Completed: {func_name}")
        return result
    return wrapper


def require_login(func):
    """
    Prevents execution if no user is logged in.
    Assumes the class has a 'current_user' attribute.

    Args:
        func (Callable): The function being decorated.

    Returns:
        Callable: Wrapped function that checks login status before execution.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            print("❌ Please login to perform this action.")
            return
        return func(self, *args, **kwargs)
    return wrapper