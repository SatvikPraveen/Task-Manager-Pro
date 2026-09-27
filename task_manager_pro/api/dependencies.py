"""
api/dependencies.py

FastAPI dependencies: bearer-token authentication and the repository.

The repository is a process-wide singleton created on first use (not at
import time), and ``get_storage`` is the single override point for tests
that want to bind the API to a different database.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from task_manager_pro.storage.sql_storage import SQLStorage
from task_manager_pro.utils.security import decode_token

bearer_scheme = HTTPBearer(auto_error=True)

_storage: Optional[SQLStorage] = None


def get_storage() -> SQLStorage:
    """Provide the shared :class:`SQLStorage` repository."""
    global _storage
    if _storage is None:
        _storage = SQLStorage()
    return _storage


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """
    Resolve the bearer token to a user ID.

    Raises ``401`` if the token is missing, malformed, expired or of the wrong type.
    """
    payload = decode_token(credentials.credentials)
    if not payload:
        raise _unauthorized("Invalid or expired token")
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise _unauthorized("Could not validate credentials")
    return user_id
