import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="learner")
    cognitive_style: Mapped[str] = mapped_column(String(20), default="visual")
    interests: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    knowledge_states = relationship("KnowledgeState", back_populates="user", cascade="all, delete-orphan")
    learning_sessions = relationship("LearningSession", back_populates="user", cascade="all, delete-orphan")


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    irt_b_param: Mapped[float | None] = mapped_column(Float, nullable=True)
    prerequisites: Mapped[list | None] = mapped_column(JSON, nullable=True)
    learning_objectives: Mapped[list | None] = mapped_column(JSON, nullable=True)
    code_examples: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    knowledge_states = relationship("KnowledgeState", back_populates="knowledge_point")
    edges_from = relationship(
        "KnowledgeEdge", foreign_keys="KnowledgeEdge.from_kp_id", back_populates="from_kp", cascade="all, delete-orphan"
    )
    edges_to = relationship(
        "KnowledgeEdge", foreign_keys="KnowledgeEdge.to_kp_id", back_populates="to_kp", cascade="all, delete-orphan"
    )


class KnowledgeEdge(Base):
    __tablename__ = "knowledge_edges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_kp_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_points.id", ondelete="CASCADE"))
    to_kp_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_points.id", ondelete="CASCADE"))
    relation_type: Mapped[str] = mapped_column(String(50), default="prerequisite")

    from_kp = relationship("KnowledgePoint", foreign_keys=[from_kp_id], back_populates="edges_from")
    to_kp = relationship("KnowledgePoint", foreign_keys=[to_kp_id], back_populates="edges_to")


class KnowledgeState(Base):
    __tablename__ = "knowledge_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    kp_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_points.id", ondelete="CASCADE"))
    bkt_p_know: Mapped[float] = mapped_column(Float, default=0.2)
    bkt_p_guess: Mapped[float] = mapped_column(Float, default=0.25)
    bkt_p_slip: Mapped[float] = mapped_column(Float, default=0.15)
    bkt_p_transfer: Mapped[float] = mapped_column(Float, default=0.1)
    mastery_level: Mapped[str] = mapped_column(String(20), default="unlearned")
    independent_completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    deformation_pass_rate: Mapped[float] = mapped_column(Float, default=0.0)
    total_attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    memory_stability: Mapped[float] = mapped_column(Float, default=1.0)
    review_interval_days: Mapped[int] = mapped_column(Integer, default=1)
    persona_stage: Mapped[str] = mapped_column(String(20), default="guide")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="knowledge_states")
    knowledge_point = relationship("KnowledgePoint", back_populates="knowledge_states")


class LearningSession(Base):
    __tablename__ = "learning_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    kp_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_points.id", ondelete="CASCADE"))
    session_type: Mapped[str] = mapped_column(String(30), default="guided")
    ercf_stage: Mapped[str] = mapped_column(String(30), default="R1")
    persona_stage: Mapped[str] = mapped_column(String(20), default="guide")
    hint_level_used: Mapped[int] = mapped_column(Integer, default=0)
    code_submitted: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hints_requested: Mapped[int] = mapped_column(Integer, default=0)
    cognitive_load_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_messages: Mapped[list | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="learning_sessions")


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kp_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_points.id", ondelete="CASCADE"))
    question_type: Mapped[str] = mapped_column(String(30), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list | None] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    irt_difficulty_b: Mapped[float | None] = mapped_column(Float, nullable=True)
    irt_discrimination_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    hint_levels: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    quiz_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"))
    kp_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_points.id", ondelete="CASCADE"))
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    hint_level_used: Mapped[int] = mapped_column(Integer, default=0)
    bkt_p_before: Mapped[float] = mapped_column(Float, default=0.0)
    bkt_p_after: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
