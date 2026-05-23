from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ApiConfigCreate(BaseModel):
    provider: str = Field(..., pattern="^(openai|anthropic|custom)$")
    api_key: str = Field(..., min_length=1, max_length=500)
    api_base_url: str | None = None
    model_name: str | None = None


class ApiConfigUpdate(BaseModel):
    provider: str | None = Field(None, pattern="^(openai|anthropic|custom)$")
    api_key: str | None = Field(None, min_length=1, max_length=500)
    api_base_url: str | None = None
    model_name: str | None = None
    is_active: bool | None = None


class ApiConfigResponse(BaseModel):
    id: uuid.UUID
    provider: str
    api_key_masked: str
    api_base_url: str | None = None
    model_name: str | None = None
    is_active: bool = True
    last_tested_at: datetime | None = None
    last_test_success: bool | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApiTestRequest(BaseModel):
    provider: str | None = None
    api_key: str | None = None
    api_base_url: str | None = None
    model_name: str | None = None


class ApiTestResponse(BaseModel):
    success: bool
    message: str
    latency_ms: int | None = None
    model: str | None = None


class ApiUsageStats(BaseModel):
    total_calls: int = 0
    success_calls: int = 0
    failed_calls: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    total_tokens: int = 0
    recent_calls: list[dict] = []

    model_config = {"from_attributes": True}
