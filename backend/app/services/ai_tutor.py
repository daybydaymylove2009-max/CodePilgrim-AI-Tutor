from __future__ import annotations

import json
import uuid
from typing import Any

import httpx

from app.core.config import settings
from app.algorithms.ercf import ERCFController, ERCFContext, ERCFStage, PersonaStage, HintLevel
from app.algorithms.bkt import BKTTracker
from app.algorithms.cognitive_load import CognitiveLoadRegulator, CognitiveLoadSignals


class AITutorService:
    """
    AI 对话导师服务.

    集成 ERCF 推理框架 + 角色渐进模型 + 输出守卫.
    支持 OpenAI 和 Anthropic 两种 LLM 后端.
    """

    def __init__(self):
        self.ercf = ERCFController()
        self.bkt = BKTTracker()
        self.cognitive_regulator = CognitiveLoadRegulator()

    async def chat(
        self,
        message: str,
        kp_id: uuid.UUID,
        kp_title: str,
        p_know: float,
        context: ERCFContext,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        system_prompt = self.ercf.build_system_prompt(context, p_know, kp_title)

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        raw_response = await self._call_llm(messages)

        guarded_response = self._apply_output_guard(raw_response, context)

        new_stage = self.ercf.determine_stage(context, "submit_code", None)
        new_persona = self.ercf.determine_persona(context, p_know)

        context.stage = new_stage
        context.persona = new_persona

        return {
            "assistant_message": guarded_response,
            "ercf_stage": context.stage.value,
            "persona_stage": context.persona.value,
            "hint_level": context.current_hint_level.value,
            "intervention": self.ercf.should_intervene(context) if context.idle_seconds >= 30 else None,
        }

    async def _call_llm(self, messages: list[dict[str, str]]) -> str:
        if settings.OPENAI_API_KEY:
            return await self._call_openai(messages)
        if settings.ANTHROPIC_API_KEY:
            return await self._call_anthropic(messages)
        return self._fallback_response(messages)

    async def _call_openai(self, messages: list[dict[str, str]]) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENAI_MODEL,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1000,
                },
            )
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def _call_anthropic(self, messages: list[dict[str, str]]) -> str:
        system_msg = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                chat_messages.append(m)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.ANTHROPIC_MODEL,
                    "max_tokens": 1000,
                    "system": system_msg,
                    "messages": chat_messages,
                },
            )
            data = response.json()
            return data["content"][0]["text"]

    def _fallback_response(self, messages: list[dict[str, str]]) -> str:
        last_user_msg = messages[-1]["content"] if messages else ""
        return f"我听到了你的问题。让我们一步步来思考：你能先用自己的话描述一下你想实现什么吗？"

    def _apply_output_guard(self, response: str, context: ERCFContext) -> str:
        response = self._check_prs_compliance(response, context)
        response = self._check_lscp_safety(response, context)
        return response

    def _check_prs_compliance(self, response: str, context: ERCFContext) -> str:
        lines = response.split("\n")
        code_block_count = 0
        in_code_block = False
        code_lines: list[str] = []

        for line in lines:
            if line.strip().startswith("```"):
                if in_code_block:
                    in_code_block = False
                    code_block_count += 1
                else:
                    in_code_block = True
                continue
            if in_code_block:
                code_lines.append(line)

        if code_block_count > 0 and len(code_lines) > 5:
            return (
                "让我换个方式来引导你思考：\n\n"
                "与其直接给你完整代码，不如我们一步步来：\n"
                "1. 首先，想想你需要什么数据结构来存储信息\n"
                "2. 然后，考虑用什么控制结构来处理逻辑\n"
                "3. 最后，想想如何组织代码使其更清晰\n\n"
                "你想先从哪一步开始？"
            )

        return response

    def _check_lscp_safety(self, response: str, context: ERCFContext) -> str:
        max_hint = {
            PersonaStage.GUIDE: 5,
            PersonaStage.COLLABORATOR: 3,
            PersonaStage.PEER: 2,
            PersonaStage.LAUNCHER: 1,
        }.get(context.persona, 1)

        code_indicators = ["def ", "class ", "for ", "while ", "if ", "return "]
        code_count = sum(1 for indicator in code_indicators if indicator in response)

        if code_count > max_hint:
            return (
                "我注意到你可能在寻找更直接的答案，但让我先引导你思考：\n\n"
                "你能描述一下你期望程序做什么吗？"
                "从描述开始，我们再逐步转化为代码。"
            )

        return response


ai_tutor_service = AITutorService()
