"""
utils/security.py

Security utilities for password hashing and JWT token management.
Provides secure credential handling for authentication.
"""

import bcrypt
from typing import Optional
import jwt
from datetime import datetime, timedelta, timezone
import os


# JWT Configuration
_INSECURE_PLACEHOLDER = "your-secret-key-change-in-production"

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == _INSECURE_PLACEHOLDER:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set (or is still the "
        "placeholder value). Refusing to start with an insecure JWT "
        "signing key. Generate one with `openssl rand -hex 32` and set "
        "it as SECRET_KEY in your environment or .env file."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password (str): Plain text password to hash
        
    Returns:
        str: Hashed password (bcrypt format)
    """
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a bcrypt hash.
    
    Args:
        plain_password (str): Plain text password to verify
        hashed_password (str): Hashed password from database
        
    Returns:
        bool: True if password matches, False otherwise
    """
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data (dict): Data to encode in token (e.g., {"sub": user_id})
        expires_delta (Optional[timedelta]): Token expiration time
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token.
    
    Args:
        token (str): JWT token to decode
        
    Returns:
        Optional[dict]: Decoded payload if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
