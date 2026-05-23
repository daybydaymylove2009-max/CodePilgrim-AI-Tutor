from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.models import (
    Course, CourseChapter, CourseEnrollment, ChapterProgress,
    KnowledgePoint, KnowledgeState, User,
)
from app.schemas.course import (
    CourseResponse, CourseChapterResponse, CourseDetailResponse,
    ChapterDetailResponse, CourseEnrollmentRequest, CourseEnrollmentResponse,
    ChapterProgressResponse, ChapterProgressUpdate,
)

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseResponse])
async def list_courses(
    language: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = select(Course).where(Course.is_active == True).order_by(Course.sort_order)
    if language:
        query = query.where(Course.language == language)
    result = await db.execute(query)
    return [CourseResponse.model_validate(c) for c in result.scalars().all()]


@router.get("/{course_id}", response_model=CourseDetailResponse)
async def get_course_detail(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Course).where(Course.id == str(course_id)))
    course = result.scalar_one_or_none()
    if not course:
        raise NotFoundError("Course", str(course_id))

    ch_result = await db.execute(
        select(CourseChapter)
        .where(CourseChapter.course_id == str(course_id))
        .order_by(CourseChapter.chapter_number)
    )
    chapters = [CourseChapterResponse.model_validate(ch) for ch in ch_result.scalars().all()]

    enrollment = None
    enr_result = await db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.user_id == current_user.id,
            CourseEnrollment.course_id == str(course_id),
        )
    )
    enrollment = enr_result.scalar_one_or_none()

    current_chapter_number = None
    if enrollment and enrollment.current_chapter_id:
        ch_r = await db.execute(
            select(CourseChapter.chapter_number).where(CourseChapter.id == enrollment.current_chapter_id)
        )
        row = ch_r.scalar_one_or_none()
        if row:
            current_chapter_number = row

    return CourseDetailResponse(
        course=CourseResponse.model_validate(course),
        chapters=chapters,
        enrolled=enrollment is not None,
        completed_chapters=enrollment.completed_chapters if enrollment else 0,
        current_chapter_number=current_chapter_number,
    )


@router.get("/{course_id}/chapters/{chapter_id}", response_model=ChapterDetailResponse)
async def get_chapter_detail(
    course_id: uuid.UUID,
    chapter_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(CourseChapter).where(
            CourseChapter.id == str(chapter_id),
            CourseChapter.course_id == str(course_id),
        )
    )
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise NotFoundError("Chapter", str(chapter_id))

    knowledge_points = []
    if chapter.kp_ids:
        kp_result = await db.execute(
            select(KnowledgePoint).where(KnowledgePoint.id.in_(chapter.kp_ids))
        )
        for kp in kp_result.scalars().all():
            ks_result = await db.execute(
                select(KnowledgeState).where(
                    KnowledgeState.user_id == current_user.id,
                    KnowledgeState.kp_id == kp.id,
                )
            )
            ks = ks_result.scalar_one_or_none()
            knowledge_points.append({
                "id": str(kp.id),
                "title": kp.title,
                "description": kp.description,
                "difficulty": kp.difficulty,
                "learning_objectives": kp.learning_objectives,
                "code_examples": kp.code_examples,
                "mastery_level": ks.mastery_level if ks else "unlearned",
                "bkt_p_know": ks.bkt_p_know if ks else 0.0,
            })

    progress = None
    prog_result = await db.execute(
        select(ChapterProgress).where(
            ChapterProgress.user_id == current_user.id,
            ChapterProgress.chapter_id == str(chapter_id),
        )
    )
    prog = prog_result.scalar_one_or_none()
    if prog:
        progress = ChapterProgressResponse.model_validate(prog).model_dump()

    return ChapterDetailResponse(
        chapter=CourseChapterResponse.model_validate(chapter),
        knowledge_points=knowledge_points,
        progress=progress,
    )


@router.post("/enroll", response_model=CourseEnrollmentResponse)
async def enroll_course(
    data: CourseEnrollmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Course).where(Course.id == str(data.course_id)))
    course = result.scalar_one_or_none()
    if not course:
        raise NotFoundError("Course", str(data.course_id))

    existing = await db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.user_id == current_user.id,
            CourseEnrollment.course_id == str(data.course_id),
        )
    )
    existing_enrollment = existing.scalar_one_or_none()
    if existing_enrollment:
        return CourseEnrollmentResponse.model_validate(existing_enrollment)

    first_chapter = await db.execute(
        select(CourseChapter)
        .where(CourseChapter.course_id == str(data.course_id))
        .order_by(CourseChapter.chapter_number)
        .limit(1)
    )
    first_ch = first_chapter.scalar_one_or_none()

    enrollment = CourseEnrollment(
        user_id=current_user.id,
        course_id=str(data.course_id),
        current_chapter_id=first_ch.id if first_ch else None,
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return CourseEnrollmentResponse.model_validate(enrollment)


@router.get("/enrollments", response_model=list[CourseEnrollmentResponse])
async def list_enrollments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(CourseEnrollment).where(CourseEnrollment.user_id == current_user.id)
    )
    return [CourseEnrollmentResponse.model_validate(e) for e in result.scalars().all()]


@router.put("/chapters/{chapter_id}/progress", response_model=ChapterProgressResponse)
async def update_chapter_progress(
    chapter_id: uuid.UUID,
    data: ChapterProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(ChapterProgress).where(
            ChapterProgress.user_id == current_user.id,
            ChapterProgress.chapter_id == str(chapter_id),
        )
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = ChapterProgress(
            user_id=current_user.id,
            chapter_id=str(chapter_id),
            started_at=datetime.now(timezone.utc),
        )
        db.add(progress)
        await db.flush()

    if data.status is not None:
        progress.status = data.status
        if data.status == "completed":
            progress.completed_at = datetime.now(timezone.utc)
    if data.study_minutes is not None:
        progress.study_minutes = data.study_minutes
    if data.mastery_score is not None:
        progress.mastery_score = data.mastery_score
    if data.notes is not None:
        progress.notes = data.notes

    await db.commit()
    await db.refresh(progress)
    return ChapterProgressResponse.model_validate(progress)
