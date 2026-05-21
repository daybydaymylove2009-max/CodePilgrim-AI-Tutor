from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CodeSubmission(BaseModel):
    code: str = Field(..., min_length=1, max_length=50000)
    kp_id: uuid.UUID
    language: str = Field(default="python", pattern="^(python|javascript)$")


class ExecutionResult(BaseModel):
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    execution_time_ms: int = 0
    memory_used_mb: float = 0.0
    error_type: str | None = None
    error_message: str | None = None


class QuizSubmission(BaseModel):
    quiz_id: uuid.UUID
    answer: str
    response_time_ms: int = 0
    hint_level_used: int = 0


class QuizAttemptResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    is_correct: bool
    bkt_p_before: float
    bkt_p_after: float
    explanation: str | None

    model_config = {"from_attributes": True}


class AIChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class AIChatRequest(BaseModel):
    kp_id: uuid.UUID
    message: str
    session_id: uuid.UUID | None = None


class AIChatResponse(BaseModel):
    session_id: uuid.UUID
    assistant_message: str
    ercf_stage: str
    persona_stage: str
    hint_level: int | None
    intervention: dict | None


class LearningSessionResponse(BaseModel):
    id: uuid.UUID
    kp_id: uuid.UUID
    session_type: str
    ercf_stage: str
    persona_stage: str
    is_correct: bool | None
    cognitive_load_score: float | None
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class DailyPlanResponse(BaseModel):
    review_items: list[dict]
    new_items: list[dict]
    challenge_items: list[dict]


class MasteryVerificationRequest(BaseModel):
    kp_id: uuid.UUID
    verification_level: str = Field(..., pattern="^(guided|independent|creative)$")
    code: str
