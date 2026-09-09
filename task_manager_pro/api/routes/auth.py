"""
api/routes/auth.py

Authentication endpoints for user login, registration, and token refresh.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from task_manager_pro.schemas.user import UserRegister, UserLogin, UserResponse, UserWithToken
from task_manager_pro.storage.sql_storage import SQLStorage
from task_manager_pro.utils.security import create_access_token, decode_token
from datetime import timedelta

router = APIRouter()
storage = SQLStorage()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """
    Register a new user.
    
    Args:
        user_data (UserRegister): User registration data
        
    Returns:
        UserResponse: Newly created user information
        
    Raises:
        HTTPException: 400 if user already exists
    """
    try:
        user = storage.create_user(
            username=user_data.username,
            password=user_data.password,
            email=user_data.email
        )
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            email_reminders_enabled=user.email_reminders_enabled,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=UserWithToken)
async def login(credentials: UserLogin):
    """
    Login user and return access token.
    
    Args:
        credentials (UserLogin): Username and password
        
    Returns:
        UserWithToken: User info with JWT access token
        
    Raises:
        HTTPException: 401 if credentials invalid
    """
    # Verify credentials
    if not storage.verify_user_password(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user
    user = storage.get_user_by_username(credentials.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=access_token_expires
    )
    
    return UserWithToken(
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            email_reminders_enabled=user.email_reminders_enabled,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        ),
        access_token=access_token,
        token_type="bearer",
    )


@router.post("/refresh-token")
async def refresh_token(token: str):
    """
    Refresh an access token.
    
    Args:
        token (str): Current access token
        
    Returns:
        dict: New access token
        
    Raises:
        HTTPException: 401 if token invalid
    """
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    
    user_id = payload.get("sub")
    new_token = create_access_token(
        data={"sub": user_id},
        expires_delta=timedelta(minutes=30)
    )
    
    return {
        "access_token": new_token,
        "token_type": "bearer",
    }
