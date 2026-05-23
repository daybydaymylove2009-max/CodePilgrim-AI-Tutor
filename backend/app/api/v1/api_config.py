from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_api_key, encrypt_api_key, mask_api_key
from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models import ApiUsageLog, User, UserApiConfig
from app.schemas.api_config import (
    ApiConfigCreate,
    ApiConfigResponse,
    ApiConfigUpdate,
    ApiTestRequest,
    ApiTestResponse,
    ApiUsageStats,
)

router = APIRouter(prefix="/api-config", tags=["api-config"])


@router.get("", response_model=ApiConfigResponse)
async def get_api_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(UserApiConfig).where(UserApiConfig.user_id == current_user.id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API config not found")
    try:
        decrypted_key = decrypt_api_key(config.encrypted_api_key)
    except Exception:
        decrypted_key = ""
    return ApiConfigResponse(
        id=config.id,
        provider=config.provider,
        api_key_masked=mask_api_key(decrypted_key),
        api_base_url=config.api_base_url,
        model_name=config.model_name,
        is_active=config.is_active,
        last_tested_at=config.last_tested_at,
        last_test_success=config.last_test_success,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.post("", response_model=ApiConfigResponse)
async def create_api_config(
    data: ApiConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(UserApiConfig).where(UserApiConfig.user_id == current_user.id)
    )
    existing = result.scalar_one_or_none()

    encrypted_key = encrypt_api_key(data.api_key)

    if existing:
        existing.provider = data.provider
        existing.encrypted_api_key = encrypted_key
        if data.api_base_url is not None:
            existing.api_base_url = data.api_base_url
        if data.model_name is not None:
            existing.model_name = data.model_name
        existing.is_active = True
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        config = existing
    else:
        config = UserApiConfig(
            user_id=current_user.id,
            provider=data.provider,
            encrypted_api_key=encrypted_key,
            api_base_url=data.api_base_url,
            model_name=data.model_name,
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)

    return ApiConfigResponse(
        id=config.id,
        provider=config.provider,
        api_key_masked=mask_api_key(data.api_key),
        api_base_url=config.api_base_url,
        model_name=config.model_name,
        is_active=config.is_active,
        last_tested_at=config.last_tested_at,
        last_test_success=config.last_test_success,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.put("", response_model=ApiConfigResponse)
async def update_api_config(
    data: ApiConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(UserApiConfig).where(UserApiConfig.user_id == current_user.id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API config not found")

    if data.provider is not None:
        config.provider = data.provider
    if data.api_key is not None:
        config.encrypted_api_key = encrypt_api_key(data.api_key)
    if data.api_base_url is not None:
        config.api_base_url = data.api_base_url
    if data.model_name is not None:
        config.model_name = data.model_name
    if data.is_active is not None:
        config.is_active = data.is_active
    config.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(config)

    try:
        decrypted_key = decrypt_api_key(config.encrypted_api_key)
    except Exception:
        decrypted_key = ""

    return ApiConfigResponse(
        id=config.id,
        provider=config.provider,
        api_key_masked=mask_api_key(decrypted_key),
        api_base_url=config.api_base_url,
        model_name=config.model_name,
        is_active=config.is_active,
        last_tested_at=config.last_tested_at,
        last_test_success=config.last_test_success,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(UserApiConfig).where(UserApiConfig.user_id == current_user.id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API config not found")
    await db.delete(config)
    await db.commit()


@router.post("/test", response_model=ApiTestResponse)
async def test_api_config(
    request: ApiTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    provider = request.provider
    api_key = request.api_key
    base_url = request.api_base_url
    model_name = request.model_name

    if not api_key or not provider:
        result = await db.execute(
            select(UserApiConfig).where(UserApiConfig.user_id == current_user.id)
        )
        config = result.scalar_one_or_none()
        if not config:
            return ApiTestResponse(success=False, message="No API config found")
        try:
            api_key = decrypt_api_key(config.encrypted_api_key)
        except Exception:
            return ApiTestResponse(success=False, message="Failed to decrypt API key")
        provider = provider or config.provider
        base_url = base_url or config.api_base_url
        model_name = model_name or config.model_name

    start = time.monotonic()
    try:
        if provider == "openai":
            url = f"{(base_url or 'https://api.openai.com/v1').rstrip('/')}/models"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            elapsed = int((time.monotonic() - start) * 1000)
            if resp.status_code == 200:
                _update_test_result(db, current_user.id, True, elapsed)
                return ApiTestResponse(
                    success=True,
                    message="OpenAI API connection successful",
                    latency_ms=elapsed,
                    model=model_name or "gpt-4o",
                )
            else:
                _update_test_result(db, current_user.id, False, elapsed)
                return ApiTestResponse(
                    success=False,
                    message=f"OpenAI API returned status {resp.status_code}",
                    latency_ms=elapsed,
                    model=model_name or "gpt-4o",
                )
        elif provider == "anthropic":
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model_name or "claude-sonnet-4-20250514",
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "Hi"}],
                    },
                )
            elapsed = int((time.monotonic() - start) * 1000)
            if resp.status_code == 200:
                _update_test_result(db, current_user.id, True, elapsed)
                return ApiTestResponse(
                    success=True,
                    message="Anthropic API connection successful",
                    latency_ms=elapsed,
                    model=model_name or "claude-sonnet-4-20250514",
                )
            else:
                _update_test_result(db, current_user.id, False, elapsed)
                return ApiTestResponse(
                    success=False,
                    message=f"Anthropic API returned status {resp.status_code}",
                    latency_ms=elapsed,
                    model=model_name or "claude-sonnet-4-20250514",
                )
        elif provider == "custom":
            url = f"{(base_url or '').rstrip('/')}/models"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            elapsed = int((time.monotonic() - start) * 1000)
            if resp.status_code == 200:
                _update_test_result(db, current_user.id, True, elapsed)
                return ApiTestResponse(
                    success=True,
                    message="Custom API connection successful",
                    latency_ms=elapsed,
                    model=model_name or "gpt-4o",
                )
            else:
                _update_test_result(db, current_user.id, False, elapsed)
                return ApiTestResponse(
                    success=False,
                    message=f"Custom API returned status {resp.status_code}",
                    latency_ms=elapsed,
                    model=model_name or "gpt-4o",
                )
        else:
            return ApiTestResponse(success=False, message=f"Unknown provider: {provider}")
    except Exception as e:
        elapsed = int((time.monotonic() - start) * 1000)
        _update_test_result(db, current_user.id, False, elapsed)
        return ApiTestResponse(success=False, message=f"Connection failed: {str(e)}", latency_ms=elapsed)


async def _update_test_result(db: AsyncSession, user_id: str, success: bool, latency_ms: int):
    result = await db.execute(
        select(UserApiConfig).where(UserApiConfig.user_id == user_id)
    )
    config = result.scalar_one_or_none()
    if config:
        config.last_tested_at = datetime.now(timezone.utc)
        config.last_test_success = success
        await db.commit()


@router.get("/usage", response_model=ApiUsageStats)
async def get_api_usage(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    total_result = await db.execute(
        select(func.count(ApiUsageLog.id)).where(ApiUsageLog.user_id == current_user.id)
    )
    total_calls = total_result.scalar() or 0

    success_result = await db.execute(
        select(func.count(ApiUsageLog.id)).where(
            ApiUsageLog.user_id == current_user.id,
            ApiUsageLog.is_success == True,
        )
    )
    success_calls = success_result.scalar() or 0

    failed_calls = total_calls - success_calls

    avg_latency_result = await db.execute(
        select(func.avg(ApiUsageLog.latency_ms)).where(
            ApiUsageLog.user_id == current_user.id,
            ApiUsageLog.latency_ms.isnot(None),
        )
    )
    avg_latency = avg_latency_result.scalar() or 0.0

    total_tokens_result = await db.execute(
        select(func.sum(ApiUsageLog.tokens_used)).where(
            ApiUsageLog.user_id == current_user.id,
            ApiUsageLog.tokens_used.isnot(None),
        )
    )
    total_tokens = total_tokens_result.scalar() or 0

    recent_result = await db.execute(
        select(ApiUsageLog)
        .where(ApiUsageLog.user_id == current_user.id)
        .order_by(ApiUsageLog.created_at.desc())
        .limit(20)
    )
    recent_logs = recent_result.scalars().all()
    recent_calls = [
        {
            "id": str(log.id),
            "provider": log.provider,
            "endpoint": log.endpoint,
            "model": log.model,
            "is_success": log.is_success,
            "latency_ms": log.latency_ms,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in recent_logs
    ]

    success_rate = (success_calls / total_calls * 100) if total_calls > 0 else 0.0

    return ApiUsageStats(
        total_calls=total_calls,
        success_calls=success_calls,
        failed_calls=failed_calls,
        success_rate=round(success_rate, 2),
        avg_latency_ms=round(float(avg_latency), 2),
        total_tokens=total_tokens,
        recent_calls=recent_calls,
    )
