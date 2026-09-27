"""
utils/security.py

Password hashing and JWT helpers.

All tunables (bcrypt cost, signing key, algorithm, default lifetime) come from
:mod:`task_manager_pro.config` and are read at call time, so a process can be
reconfigured (e.g. in tests) without re-importing this module.

Tokens carry the standard registered claims ``sub``, ``iat``, ``exp`` and
``jti`` plus a ``type`` claim ("access") so that future token kinds (refresh,
API keys) cannot be confused with access tokens.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt

from task_manager_pro.config import get_settings

ACCESS_TOKEN_TYPE = "access"

# A fixed, valid bcrypt hash used to keep login timing constant when the
# username does not exist (see ``verify_password_dummy``). Generated once at
# cost 12 from a random password that is not retained anywhere.
_DUMMY_HASH = "$2b$12$pqAQgiQNyc54kVPCDImXe.QsYDOLlwDQRNc5AqgabyNZtAL0LtRTi"


def hash_password(password: str) -> str:
    """Hash ``password`` with bcrypt at the configured work factor."""
    rounds = get_settings().bcrypt_rounds
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return ``True`` if ``plain_password`` matches the bcrypt ``hashed_password``."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        # Malformed hash stored in the database; treat as non-matching.
        return False


def verify_password_dummy(plain_password: str) -> None:
    """
    Burn the same amount of CPU as a real verification.

    Called on login when the username is unknown so that the response time does
    not reveal whether an account exists (timing-based user enumeration).
    """
    bcrypt.checkpw(plain_password.encode("utf-8"), _DUMMY_HASH.encode("utf-8"))


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.

    Args:
        data: Claims to embed (must include ``sub``).
        expires_delta: Lifetime override; defaults to ``ACCESS_TOKEN_EXPIRE_MINUTES``.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    lifetime = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    to_encode: Dict[str, Any] = dict(data)
    to_encode.update(
        {
            "iat": now,
            "exp": now + lifetime,
            "jti": uuid.uuid4().hex,
            "type": ACCESS_TOKEN_TYPE,
        }
    )
    return jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT.

    Returns the payload, or ``None`` if the signature, expiry or token type is
    invalid. Callers never see the underlying ``jwt`` exceptions.
    """
    settings = get_settings()
    try:
        payload: Dict[str, Any] = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError:
        return None
    if payload.get("type", ACCESS_TOKEN_TYPE) != ACCESS_TOKEN_TYPE:
        return None
    return payload
