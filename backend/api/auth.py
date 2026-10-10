"""
Authentication API Router: Sign-Up, Login, Profile, and Token Refresh endpoints.
"""
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from models.user import User
from schemas.auth_schemas import TokenResponse, UserLoginRequest, UserOut, UserSignUpRequest
from services.auth_service import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

TOKEN_EXPIRE_MINUTES = 120  # 2 hours access token


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserSignUpRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user account with validated email and PBKDF2-hashed password.
    """
    normalized_email = payload.email.strip().lower()

    # Check if email is already registered
    existing_user = (
        await db.execute(select(User).where(User.email == normalized_email))
    ).scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    hashed_pw = hash_password(payload.password)
    user = User(
        email=normalized_email,
        hashed_password=hashed_pw,
        full_name=payload.full_name.strip() if payload.full_name else None,
        role="patient",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("New user registered: %s (id=%s)", user.email, user.id)

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        expires_in_minutes=TOKEN_EXPIRE_MINUTES,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=TOKEN_EXPIRE_MINUTES,
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user credentials and issue a signed JWT access token.
    """
    normalized_email = payload.email.strip().lower()

    user = (
        await db.execute(select(User).where(User.email == normalized_email))
    ).scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        logger.warning("Failed login attempt for email: %s", normalized_email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Please contact support.",
        )

    user.last_login_at = datetime.utcnow()
    await db.commit()

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        expires_in_minutes=TOKEN_EXPIRE_MINUTES,
    )

    logger.info("User logged in successfully: %s", user.email)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=TOKEN_EXPIRE_MINUTES,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Fetch the currently authenticated user's profile details.
    """
    return UserOut.model_validate(current_user)
