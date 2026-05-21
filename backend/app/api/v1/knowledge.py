from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import KnowledgePoint, KnowledgeState, User
from app.schemas.knowledge import KnowledgePointResponse, KnowledgeStateResponse, LearningPathResponse
from app.services.learning_path import learning_path_service
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/points", response_model=list[KnowledgePointResponse])
async def list_knowledge_points(
    topic: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(KnowledgePoint)
    if topic:
        query = query.where(KnowledgePoint.topic == topic)
    query = query.order_by(KnowledgePoint.difficulty)
    result = await db.execute(query)
    return [KnowledgePointResponse.model_validate(kp) for kp in result.scalars().all()]


@router.get("/points/{kp_id}", response_model=KnowledgePointResponse)
async def get_knowledge_point(
    kp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(KnowledgePoint).where(KnowledgePoint.id == kp_id))
    kp = result.scalar_one_or_none()
    if not kp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge point not found")
    return KnowledgePointResponse.model_validate(kp)


@router.get("/states", response_model=list[KnowledgeStateResponse])
async def list_knowledge_states(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(KnowledgeState).where(KnowledgeState.user_id == current_user.id)
    )
    return [KnowledgeStateResponse.model_validate(s) for s in result.scalars().all()]


@router.get("/path", response_model=LearningPathResponse)
async def get_learning_path(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await learning_path_service.get_learning_path(db, current_user.id)


@router.get("/next")
async def get_next_knowledge_point(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kp_id = await learning_path_service.get_next_kp(db, current_user.id)
    if not kp_id:
        return {"kp_id": None, "message": "All knowledge points mastered or no available path"}
    return {"kp_id": str(kp_id)}


@router.get("/review-plan")
async def get_review_plan(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await learning_path_service.get_review_plan(db, current_user.id)
