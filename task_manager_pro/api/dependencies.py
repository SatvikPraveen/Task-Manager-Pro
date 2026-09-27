"""
api/dependencies.py

FastAPI dependencies: bearer-token authentication, the repository and the
token denylist.

The repository and the denylist are process-wide singletons created on
first use (not at import time); ``get_storage`` and ``get_token_denylist``
are the override points for tests.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from task_manager_pro.api.state import build_token_denylist
from task_manager_pro.config import get_settings
from task_manager_pro.storage.sql_storage import SQLStorage
from task_manager_pro.utils.security import decode_token
from task_manager_pro.utils.token_denylist import TokenDenylist

bearer_scheme = HTTPBearer(auto_error=True)

_storage: Optional[SQLStorage] = None
_denylist: Optional[TokenDenylist] = None


def get_storage() -> SQLStorage:
    """Provide the shared :class:`SQLStorage` repository."""
    global _storage
    if _storage is None:
        _storage = SQLStorage()
    return _storage


def get_token_denylist() -> TokenDenylist:
    """Provide the shared revoked-token store."""
    global _denylist
    if _denylist is None:
        _denylist = build_token_denylist(get_settings())
    return _denylist


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    denylist: TokenDenylist = Depends(get_token_denylist),
) -> dict[str, Any]:
    """
    Verify the bearer token and return its claims.

    Raises ``401`` if the token is missing, malformed, expired, of the wrong
    type, revoked, or lacks a usable ``sub``.
    """
    payload = decode_token(credentials.credentials)
    if not payload:
        raise _unauthorized("Invalid or expired token")
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise _unauthorized("Could not validate credentials")
    jti = payload.get("jti")
    if isinstance(jti, str) and denylist.is_revoked(jti):
        raise _unauthorized("Token has been revoked")
    return payload


async def get_current_user(payload: dict[str, Any] = Depends(get_token_payload)) -> str:
    """Resolve the bearer token to a user ID."""
    return str(payload["sub"])
