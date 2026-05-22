from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_\u4e00-\u9fa5]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=100)
    cognitive_style: str = Field(default="visual", pattern="^(visual|auditory|kinesthetic)$")
    interests: list[str] | None = None
    captcha_token: str = Field(..., min_length=1, description="图形验证码通过后获得的token")

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("两次输入的密码不一致")
        return self


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


class CaptchaChallengeResponse(BaseModel):
    captcha_id: str
    background_image: str = Field(description="Base64编码的背景图（含缺口）")
    puzzle_image: str = Field(description="Base64编码的拼图块")
    puzzle_y: int = Field(description="拼图块的Y坐标（固定）")
    width: int = Field(description="背景图宽度")
    height: int = Field(description="背景图高度")
    puzzle_size: int = Field(description="拼图块大小")


class CaptchaVerifyRequest(BaseModel):
    captcha_id: str
    slider_x: int = Field(..., ge=0, description="用户拖动拼图块的X坐标")
    slider_y: int = Field(..., ge=0, description="用户拖动拼图块的Y坐标")


class CaptchaVerifyResponse(BaseModel):
    success: bool
    captcha_token: str | None = None
    message: str | None = None
