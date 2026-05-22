from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.bkt import BKTEvidence, BKTTracker
from app.algorithms.cognitive_load import CognitiveLoadRegulator, CognitiveLoadSignals
from app.algorithms.ercf import ERCFContext, ERCFStage, PersonaStage
from app.core.deps import get_current_active_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models import KnowledgePoint, KnowledgeState, LearningSession, Quiz, QuizAttempt, User
from app.schemas.learning import (
    AIChatRequest,
    AIChatResponse,
    CodeSubmission,
    DailyPlanResponse,
    ExecutionResult,
    LearningSessionResponse,
    MasteryVerificationRequest,
    QuizAttemptResponse,
    QuizSubmission,
)
from app.services.ai_tutor import ai_tutor_service
from app.services.learning_path import learning_path_service
from app.services.sandbox import sandbox

router = APIRouter(prefix="/learning", tags=["learning"])

bkt_tracker = BKTTracker()
cognitive_regulator = CognitiveLoadRegulator()

_active_sessions: dict[str, ERCFContext] = {}


@router.post("/execute", response_model=ExecutionResult)
async def execute_code(
    submission: CodeSubmission,
    current_user: User = Depends(get_current_active_user),
):
    result = await sandbox.execute(submission.code, submission.language)
    return result


@router.post("/submit-code", response_model=LearningSessionResponse)
async def submit_code(
    submission: CodeSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    execution_result = await sandbox.execute(submission.code, submission.language)

    kp_result = await db.execute(select(KnowledgePoint).where(KnowledgePoint.id == submission.kp_id))
    kp = kp_result.scalar_one_or_none()
    if not kp:
        raise NotFoundError("Knowledge point", str(submission.kp_id))

    is_correct = execution_result.success and execution_result.exit_code == 0

    evidence = BKTEvidence(
        correct=is_correct,
        response_time_ms=execution_result.execution_time_ms,
        hints_used=0,
    )

    state = await learning_path_service.update_knowledge_state(db, current_user.id, submission.kp_id, evidence)

    session = LearningSession(
        user_id=current_user.id,
        kp_id=submission.kp_id,
        session_type="code_submission",
        ercf_stage=_active_sessions.get(current_user.id, ERCFContext()).stage.value,
        persona_stage=state.persona_stage,
        code_submitted=submission.code,
        execution_result={
            "stdout": execution_result.stdout,
            "stderr": execution_result.stderr,
            "exit_code": execution_result.exit_code,
        },
        is_correct=is_correct,
        response_time_ms=execution_result.execution_time_ms,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return LearningSessionResponse.model_validate(session)


@router.post("/quiz", response_model=QuizAttemptResponse)
async def submit_quiz(
    submission: QuizSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    quiz_result = await db.execute(select(Quiz).where(Quiz.id == submission.quiz_id))
    quiz = quiz_result.scalar_one_or_none()
    if not quiz:
        raise NotFoundError("Quiz", str(submission.quiz_id))

    is_correct = submission.answer.strip().lower() == quiz.correct_answer.strip().lower()

    state_result = await db.execute(
        select(KnowledgeState).where(
            KnowledgeState.user_id == current_user.id,
            KnowledgeState.kp_id == quiz.kp_id,
        )
    )
    state = state_result.scalar_one_or_none()
    p_before = state.bkt_p_know if state else 0.2

    evidence = BKTEvidence(
        correct=is_correct,
        response_time_ms=submission.response_time_ms,
        hints_used=submission.hint_level_used,
        hint_level=submission.hint_level_used,
    )

    state = await learning_path_service.update_knowledge_state(db, current_user.id, quiz.kp_id, evidence)
    p_after = state.bkt_p_know

    attempt = QuizAttempt(
        user_id=current_user.id,
        quiz_id=submission.quiz_id,
        kp_id=quiz.kp_id,
        answer=submission.answer,
        is_correct=is_correct,
        response_time_ms=submission.response_time_ms,
        hint_level_used=submission.hint_level_used,
        bkt_p_before=p_before,
        bkt_p_after=p_after,
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)

    return QuizAttemptResponse(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        is_correct=attempt.is_correct,
        bkt_p_before=attempt.bkt_p_before,
        bkt_p_after=attempt.bkt_p_after,
        explanation=quiz.explanation,
    )


@router.post("/chat", response_model=AIChatResponse)
async def chat_with_tutor(
    request: AIChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    kp_result = await db.execute(select(KnowledgePoint).where(KnowledgePoint.id == request.kp_id))
    kp = kp_result.scalar_one_or_none()
    if not kp:
        raise NotFoundError("Knowledge point", str(request.kp_id))

    state_result = await db.execute(
        select(KnowledgeState).where(
            KnowledgeState.user_id == current_user.id,
            KnowledgeState.kp_id == request.kp_id,
        )
    )
    state = state_result.scalar_one_or_none()
    p_know = state.bkt_p_know if state else 0.2

    if current_user.id in _active_sessions:
        ercf_context = _active_sessions[current_user.id]
    else:
        persona = PersonaStage(state.persona_stage) if state else PersonaStage.GUIDE
        ercf_context = ERCFContext(persona=persona)
        _active_sessions[current_user.id] = ercf_context

    response = await ai_tutor_service.chat(
        message=request.message,
        kp_id=request.kp_id,
        kp_title=kp.title,
        p_know=p_know,
        context=ercf_context,
    )

    return AIChatResponse(
        session_id=current_user.id,
        assistant_message=response["assistant_message"],
        ercf_stage=response["ercf_stage"],
        persona_stage=response["persona_stage"],
        hint_level=response.get("hint_level"),
        intervention=response.get("intervention"),
    )


@router.post("/verify-mastery")
async def verify_mastery(
    request: MasteryVerificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    execution_result = await sandbox.execute(request.code)

    state_result = await db.execute(
        select(KnowledgeState).where(
            KnowledgeState.user_id == current_user.id,
            KnowledgeState.kp_id == request.kp_id,
        )
    )
    state = state_result.scalar_one_or_none()
    if not state:
        raise NotFoundError("Knowledge state", str(request.kp_id))

    verification_results = {
        "guided": {
            "passed": state.bkt_p_know >= 0.60,
            "description": "照着做：AI引导下能完成代码",
        },
        "independent": {
            "passed": state.bkt_p_know >= 0.80 and state.independent_completion_rate >= 0.60,
            "description": "独立做：无提示独立完成 > 60%",
        },
        "creative": {
            "passed": state.bkt_p_know >= 0.85 and state.independent_completion_rate >= 0.70 and state.deformation_pass_rate >= 0.50,
            "description": "创新做：只有功能需求，无步骤提示，完成 > 50% 功能点",
        },
    }

    level_result = verification_results.get(request.verification_level)
    if not level_result:
        raise NotFoundError("Verification level", request.verification_level)

    if level_result["passed"] and execution_result.success:
        if request.verification_level == "independent":
            state.independent_completion_rate = min(1.0, state.independent_completion_rate + 0.1)
        elif request.verification_level == "creative":
            state.deformation_pass_rate = min(1.0, state.deformation_pass_rate + 0.1)
        await db.commit()

    return {
        "verification_level": request.verification_level,
        "passed": level_result["passed"] and execution_result.success,
        "description": level_result["description"],
        "bkt_p_know": state.bkt_p_know,
        "independent_completion_rate": state.independent_completion_rate,
        "deformation_pass_rate": state.deformation_pass_rate,
        "execution_success": execution_result.success,
    }


@router.get("/daily-plan", response_model=DailyPlanResponse)
async def get_daily_plan(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    plan = await learning_path_service.get_review_plan(db, current_user.id)
    return DailyPlanResponse(**plan)


@router.get("/cognitive-load")
async def assess_cognitive_load(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    recent_sessions_result = await db.execute(
        select(LearningSession)
        .where(LearningSession.user_id == current_user.id)
        .order_by(LearningSession.started_at.desc())
        .limit(10)
    )
    recent_sessions = recent_sessions_result.scalars().all()

    if not recent_sessions:
        return {"load_level": "optimal", "message": "No recent learning data", "actions": [], "suggestions": []}

    total = len(recent_sessions)
    errors = sum(1 for s in recent_sessions if s.is_correct is False)
    hints = sum(s.hints_requested for s in recent_sessions)

    signals = CognitiveLoadSignals(
        error_rate_spike=errors / max(total, 1) > 0.6,
        hint_request_frequency=hints / max(total, 1),
        consecutive_errors=sum(1 for s in recent_sessions[:3] if s.is_correct is False),
        consecutive_correct=sum(1 for s in recent_sessions[:3] if s.is_correct is True),
    )

    regulation = cognitive_regulator.regulate(signals, 0.5)
    return regulation
