"""
Pydantic Request & Response Schemas for Authentication and User Accounts.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserSignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: str | None = Field(None, min_length=2, max_length=200)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str | None = None
    role: str = "patient"
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserOut
