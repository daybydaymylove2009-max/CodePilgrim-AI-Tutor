from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.core.exceptions import NotFoundError
from app.core.pagination import PaginationParams, PaginatedResponse
from app.db.session import get_db
from app.models import KnowledgePoint, KnowledgeState, User
from app.schemas.knowledge import KnowledgePointResponse, KnowledgeStateResponse, LearningPathResponse
from app.services.learning_path import learning_path_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/points", response_model=PaginatedResponse[KnowledgePointResponse])
async def list_knowledge_points(
    topic: str | None = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = select(KnowledgePoint)
    count_query = select(func.count(KnowledgePoint.id))
    if topic:
        query = query.where(KnowledgePoint.topic == topic)
        count_query = count_query.where(KnowledgePoint.topic == topic)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(KnowledgePoint.difficulty).offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(query)
    items = [KnowledgePointResponse.model_validate(kp) for kp in result.scalars().all()]
    return PaginatedResponse.create(items, total, pagination.offset, pagination.limit)


@router.get("/points/{kp_id}", response_model=KnowledgePointResponse)
async def get_knowledge_point(
    kp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(KnowledgePoint).where(KnowledgePoint.id == kp_id))
    kp = result.scalar_one_or_none()
    if not kp:
        raise NotFoundError("Knowledge point", str(kp_id))
    return KnowledgePointResponse.model_validate(kp)


@router.get("/states", response_model=PaginatedResponse[KnowledgeStateResponse])
async def list_knowledge_states(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    count_result = await db.execute(
        select(func.count(KnowledgeState.id)).where(KnowledgeState.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(KnowledgeState)
        .where(KnowledgeState.user_id == current_user.id)
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    items = [KnowledgeStateResponse.model_validate(s) for s in result.scalars().all()]
    return PaginatedResponse.create(items, total, pagination.offset, pagination.limit)


@router.get("/path", response_model=LearningPathResponse)
async def get_learning_path(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return await learning_path_service.get_learning_path(db, current_user.id)


@router.get("/next")
async def get_next_knowledge_point(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    kp_id = await learning_path_service.get_next_kp(db, current_user.id)
    if not kp_id:
        return {"kp_id": None, "message": "All knowledge points mastered or no available path"}
    return {"kp_id": str(kp_id)}


@router.get("/review-plan")
async def get_review_plan(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return await learning_path_service.get_review_plan(db, current_user.id)
