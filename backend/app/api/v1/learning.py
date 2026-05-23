from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.bkt import BKTEvidence, BKTTracker
from app.algorithms.cognitive_load import CognitiveLoadRegulator, CognitiveLoadSignals
from app.algorithms.ercf import ERCFContext, ERCFStage, PersonaStage
from app.core.config import settings
from app.core.crypto import decrypt_api_key
from app.core.deps import get_current_active_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models import ApiUsageLog, KnowledgePoint, KnowledgeState, LearningSession, Quiz, QuizAttempt, User, UserApiConfig
from app.schemas.learning import (
    AIChatRequest,
    AIChatResponse,
    CodeAnnotationRequest,
    CodeAnnotationResponse,
    CodeSubmission,
    DailyPlanResponse,
    ExecutionResult,
    KnowledgeExplanationRequest,
    KnowledgeExplanationResponse,
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


async def _get_user_api_config(db: AsyncSession, user_id: str) -> dict | None:
    result = await db.execute(
        select(UserApiConfig).where(
            UserApiConfig.user_id == user_id,
            UserApiConfig.is_active == True,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        return None
    try:
        decrypted_key = decrypt_api_key(config.encrypted_api_key)
    except Exception:
        return None
    return {
        "provider": config.provider,
        "api_key": decrypted_key,
        "api_base_url": config.api_base_url,
        "model_name": config.model_name,
    }


async def _log_api_usage(
    db: AsyncSession,
    user_id: str,
    provider: str,
    endpoint: str,
    model: str | None,
    success: bool,
    latency_ms: int | None,
    error: str | None = None,
    tokens: int | None = None,
):
    log = ApiUsageLog(
        user_id=user_id,
        provider=provider,
        endpoint=endpoint,
        model=model,
        is_success=success,
        latency_ms=latency_ms,
        error_message=error,
        tokens_used=tokens,
    )
    db.add(log)
    await db.commit()


@router.post("/execute", response_model=ExecutionResult)
async def execute_code(
    submission: CodeSubmission,
    current_user: User = Depends(get_current_active_user),
):
    result = await sandbox.execute(
        submission.code,
        submission.language,
        stdin=submission.stdin,
        user_id=current_user.id,
    )
    return result


@router.get("/execution-history")
async def get_execution_history(
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
):
    return sandbox.get_history(current_user.id, limit)


@router.post("/submit-code", response_model=LearningSessionResponse)
async def submit_code(
    submission: CodeSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    execution_result = await sandbox.execute(
        submission.code,
        submission.language,
        stdin=submission.stdin,
        user_id=current_user.id,
    )

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

    api_config = await _get_user_api_config(db, current_user.id)
    start = time.monotonic()
    try:
        response = await ai_tutor_service.chat(
            message=request.message,
            kp_id=request.kp_id,
            kp_title=kp.title,
            p_know=p_know,
            context=ercf_context,
            api_config=api_config,
        )
        elapsed = int((time.monotonic() - start) * 1000)
        provider = api_config["provider"] if api_config else "system"
        model = api_config.get("model_name") if api_config else None
        await _log_api_usage(db, current_user.id, provider, "/chat", model, True, elapsed)
    except Exception as e:
        elapsed = int((time.monotonic() - start) * 1000)
        provider = api_config["provider"] if api_config else "system"
        model = api_config.get("model_name") if api_config else None
        await _log_api_usage(db, current_user.id, provider, "/chat", model, False, elapsed, error=str(e))
        response = {
            "assistant_message": f"⚠️ AI 导师暂不可用。当前未配置个人 API 密钥，无法提供智能对话辅导。\n\n你可以：\n1. 前往「API 设置」页面配置你的个人 API 密钥\n2. 继续通过代码运行和知识点浏览进行自主学习\n\n其他功能（代码执行、课程学习、知识图谱等）均可正常使用。",
            "ercf_stage": ercf_context.stage.value,
            "persona_stage": ercf_context.persona.value,
            "hint_level": ercf_context.current_hint_level.value,
            "intervention": None,
        }

    return AIChatResponse(
        session_id=current_user.id,
        assistant_message=response["assistant_message"],
        ercf_stage=response["ercf_stage"],
        persona_stage=response["persona_stage"],
        hint_level=response.get("hint_level"),
        intervention=response.get("intervention"),
    )


@router.post("/annotate-code", response_model=CodeAnnotationResponse)
async def annotate_code(
    request: CodeAnnotationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    kp_title = None
    if request.kp_id:
        kp_result = await db.execute(select(KnowledgePoint).where(KnowledgePoint.id == request.kp_id))
        kp = kp_result.scalar_one_or_none()
        if kp:
            kp_title = kp.title

    api_config = await _get_user_api_config(db, current_user.id)
    start = time.monotonic()
    try:
        result = await ai_tutor_service.annotate_code(
            code=request.code,
            language=request.language,
            kp_title=kp_title,
            api_config=api_config,
        )
        elapsed = int((time.monotonic() - start) * 1000)
        provider = api_config["provider"] if api_config else "system"
        model = api_config.get("model_name") if api_config else None
        await _log_api_usage(db, current_user.id, provider, "/annotate-code", model, True, elapsed)
    except Exception as e:
        elapsed = int((time.monotonic() - start) * 1000)
        provider = api_config["provider"] if api_config else "system"
        model = api_config.get("model_name") if api_config else None
        await _log_api_usage(db, current_user.id, provider, "/annotate-code", model, False, elapsed, error=str(e))
        result = {
            "annotated_code": request.code,
            "explanation": "代码注解功能需要 AI API 支持。请前往「API 设置」配置你的个人 API 密钥以启用此功能。",
            "key_concepts": [],
        }
    return CodeAnnotationResponse(**result)


@router.post("/explain-knowledge", response_model=KnowledgeExplanationResponse)
async def explain_knowledge(
    request: KnowledgeExplanationRequest,
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

    api_config = await _get_user_api_config(db, current_user.id)
    has_any_api = api_config or settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY

    if has_any_api:
        start = time.monotonic()
        try:
            result = await ai_tutor_service.explain_knowledge(
                kp_title=kp.title,
                kp_description=kp.description if hasattr(kp, "description") else None,
                p_know=p_know,
                api_config=api_config,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            provider = api_config["provider"] if api_config else "system"
            model = api_config.get("model_name") if api_config else None
            await _log_api_usage(db, current_user.id, provider, "/explain-knowledge", model, True, elapsed)
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            provider = api_config["provider"] if api_config else "system"
            model = api_config.get("model_name") if api_config else None
            await _log_api_usage(db, current_user.id, provider, "/explain-knowledge", model, False, elapsed, error=str(e))
            result = _build_db_fallback_explanation(kp, p_know)
            result["_ai_unavailable"] = True
    else:
        result = _build_db_fallback_explanation(kp, p_know)

    result["kp_id"] = request.kp_id
    return KnowledgeExplanationResponse(**result)


def _build_db_fallback_explanation(kp: KnowledgePoint, p_know: float) -> dict:
    level = "入门" if p_know < 0.3 else "进阶" if p_know < 0.7 else "深入"
    explanation = kp.description or f"这是关于「{kp.title}」的知识点。当前掌握程度：{level}。"
    if kp.learning_objectives:
        explanation += "\n\n学习目标：\n" + "\n".join(f"• {obj}" for obj in kp.learning_objectives)

    key_points = []
    if kp.learning_objectives:
        key_points = [f"掌握：{obj}" for obj in kp.learning_objectives[:4]]

    code_example = ""
    if kp.code_examples and len(kp.code_examples) > 0:
        code_example = kp.code_examples[0]

    common_mistakes = [
        "未充分理解核心概念就急于编写代码",
        "忽略边界条件和异常处理",
        "缺乏对底层原理的深入理解",
    ]

    return {
        "title": kp.title,
        "explanation": explanation,
        "key_points": key_points,
        "code_example": code_example,
        "common_mistakes": common_mistakes,
    }


@router.post("/verify-mastery")
async def verify_mastery(
    request: MasteryVerificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    execution_result = await sandbox.execute(
        request.code,
        user_id=current_user.id,
    )

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
