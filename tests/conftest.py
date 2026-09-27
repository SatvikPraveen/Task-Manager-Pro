"""
tests/conftest.py

Process-wide test configuration.

The environment is pinned *before* any ``task_manager_pro`` import so that the
cached :class:`~task_manager_pro.config.Settings` sees test values:

* an in-memory SQLite database, so the suite never touches ``tasks.db``;
* ``BCRYPT_ROUNDS=4`` (the minimum) so hashing does not dominate runtime;
* rate limiting disabled, so tests can hammer the auth endpoints;
* a fixed, non-production ``SECRET_KEY``.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-not-for-production-use")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("EMAIL_USER", "")
os.environ.setdefault("EMAIL_PASS", "")
