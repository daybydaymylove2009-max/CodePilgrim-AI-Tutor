from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CourseResponse(BaseModel):
    id: uuid.UUID
    title: str
    subtitle: str | None = None
    author: str | None = None
    edition: str | None = None
    publisher: str | None = None
    isbn: str | None = None
    language: str
    description: str | None = None
    cover_url: str | None = None
    total_chapters: int
    difficulty_range: str | None = None
    estimated_hours: float | None = None
    is_active: bool = True
    sort_order: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseChapterResponse(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    part_number: int
    part_title: str | None = None
    chapter_number: int
    chapter_title: str
    description: str | None = None
    estimated_minutes: int | None = None
    difficulty: int
    kp_ids: list[str] | None = None
    learning_objectives: list[str] | None = None
    key_concepts: list[str] | None = None

    model_config = {"from_attributes": True}


class CourseDetailResponse(BaseModel):
    course: CourseResponse
    chapters: list[CourseChapterResponse]
    enrolled: bool = False
    completed_chapters: int = 0
    current_chapter_number: int | None = None


class ChapterDetailResponse(BaseModel):
    chapter: CourseChapterResponse
    knowledge_points: list[dict] = []
    progress: dict | None = None


class CourseEnrollmentRequest(BaseModel):
    course_id: uuid.UUID


class CourseEnrollmentResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    course_id: uuid.UUID
    status: str
    current_chapter_id: uuid.UUID | None = None
    completed_chapters: int
    total_study_minutes: int
    enrolled_at: datetime
    last_studied_at: datetime | None = None

    model_config = {"from_attributes": True}


class ChapterProgressResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    chapter_id: uuid.UUID
    status: str
    study_minutes: int
    mastery_score: float
    notes: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ChapterProgressUpdate(BaseModel):
    status: str | None = None
    study_minutes: int | None = None
    mastery_score: float | None = None
    notes: str | None = None
