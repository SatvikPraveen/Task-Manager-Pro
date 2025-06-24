from functools import wraps
from datetime import datetime


def log_action(func):
    """
    Logs every decorated function call with a timestamp and function name.
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
    Assumes the class has 'current_user' attribute.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            print("❌ Please login to perform this action.")
            return
        return func(self, *args, **kwargs)
    return wrapper