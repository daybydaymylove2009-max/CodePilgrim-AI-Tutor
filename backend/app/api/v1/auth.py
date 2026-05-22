from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.core.exceptions import AppError, ConflictError, UnauthorizedError
from app.core.security import verify_password, get_password_hash, create_access_token
from app.db.session import get_db
from app.models import User
from app.schemas.user import (
    CaptchaChallengeResponse,
    CaptchaVerifyRequest,
    CaptchaVerifyResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
)
from app.services.security import captcha_service, anti_abuse_service
from loguru import logger

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


@router.get("/captcha/challenge", response_model=CaptchaChallengeResponse)
async def get_captcha_challenge():
    challenge = await captcha_service.create_challenge()
    return CaptchaChallengeResponse(**challenge)


@router.post("/captcha/verify", response_model=CaptchaVerifyResponse)
async def verify_captcha(data: CaptchaVerifyRequest):
    result = await captcha_service.verify_captcha(data.captcha_id, data.slider_position)
    if result["success"]:
        return CaptchaVerifyResponse(
            success=True,
            captcha_token=result["captcha_token"],
        )
    return CaptchaVerifyResponse(
        success=False,
        message=result.get("message", "验证失败"),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = _get_client_ip(request)

    ip_check = await anti_abuse_service.check_ip_rate(client_ip)
    if not ip_check["allowed"]:
        raise AppError(
            code="RATE_LIMITED",
            message=ip_check["reason"],
            status_code=429,
            detail={"retry_after": ip_check.get("retry_after")},
        )

    if not await captcha_service.validate_token(user_data.captcha_token):
        raise AppError(
            code="CAPTCHA_INVALID",
            message="验证码无效或已过期，请重新完成滑块验证",
            status_code=400,
        )

    suspicious = await anti_abuse_service.detect_suspicious(
        username=user_data.username,
        email=user_data.email,
        client_ip=client_ip,
    )
    if suspicious["action"] == "review":
        logger.warning(
            f"Registration blocked (review required): username={user_data.username}, "
            f"ip={client_ip}, risk_score={suspicious['risk_score']}, flags={suspicious['flags']}"
        )
        raise AppError(
            code="REGISTRATION_REVIEW",
            message="注册信息需要人工审核，请稍后再试或联系管理员",
            status_code=403,
            detail={"risk_score": suspicious["risk_score"], "flags": suspicious["flags"]},
        )
    if suspicious["action"] == "extra_verify":
        logger.warning(
            f"Suspicious registration detected: username={user_data.username}, "
            f"ip={client_ip}, risk_score={suspicious['risk_score']}"
        )

    existing = await db.execute(
        select(User).where((User.username == user_data.username) | (User.email == user_data.email))
    )
    if existing.scalar_one_or_none():
        raise ConflictError("用户名或邮箱已被注册")

    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        display_name=user_data.display_name,
        cognitive_style=user_data.cognitive_style,
        interests=user_data.interests,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await anti_abuse_service.record_registration(client_ip)

    logger.info(f"User registered: {user.username} ({user.id}) from IP={client_ip}")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == credentials.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise UnauthorizedError("用户名或密码错误")

    token = create_access_token({"sub": str(user.id)})
    logger.info(f"User logged in: {user.username}")
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return UserResponse.model_validate(current_user)
