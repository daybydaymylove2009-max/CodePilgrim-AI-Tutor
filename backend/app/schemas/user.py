from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=100)
    cognitive_style: str = Field(default="visual", pattern="^(visual|auditory|kinesthetic)$")
    interests: list[str] | None = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    display_name: str
    avatar_url: str | None
    role: str
    cognitive_style: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
