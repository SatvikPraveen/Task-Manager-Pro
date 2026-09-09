"""
tests/conftest.py

Shared pytest configuration. Ensures a SECRET_KEY is present before any
test module imports task_manager_pro (which now refuses to import
without one) — this must run before test collection imports the app.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-not-for-production-use")
