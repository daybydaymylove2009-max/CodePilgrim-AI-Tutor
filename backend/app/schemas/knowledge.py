from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgePointResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    topic: str
    difficulty: int
    irt_b_param: float | None
    prerequisites: list[dict] | None
    learning_objectives: list[str] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeStateResponse(BaseModel):
    id: uuid.UUID
    kp_id: uuid.UUID
    bkt_p_know: float
    mastery_level: str
    independent_completion_rate: float
    deformation_pass_rate: float
    total_attempts: int
    correct_attempts: int
    last_reviewed_at: datetime | None
    next_review_at: datetime | None
    review_interval_days: int
    persona_stage: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class LearningPathNode(BaseModel):
    kp_id: uuid.UUID
    title: str
    difficulty: int
    mastery_level: str
    bkt_p_know: float
    is_unlocked: bool
    is_current: bool


class LearningPathResponse(BaseModel):
    nodes: list[LearningPathNode]
    total_kps: int
    mastered_count: int
    current_kp_id: uuid.UUID | None
