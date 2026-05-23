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
        api_config: dict | None = None,
    ) -> dict[str, Any]:
        system_prompt = self.ercf.build_system_prompt(context, p_know, kp_title)

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        raw_response = await self._call_llm(messages, api_config=api_config)

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

    async def _call_llm(self, messages: list[dict[str, str]], api_config: dict | None = None) -> str:
        if api_config:
            provider = api_config.get("provider", "")
            api_key = api_config.get("api_key", "")
            base_url = api_config.get("api_base_url", "")
            model = api_config.get("model_name", "")
            if provider == "openai" and api_key:
                return await self._call_openai(messages, api_key=api_key, base_url=base_url or "https://api.openai.com/v1", model=model or "gpt-4o")
            elif provider == "anthropic" and api_key:
                return await self._call_anthropic(messages, api_key=api_key, model=model or "claude-sonnet-4-20250514")
            elif provider == "custom" and api_key:
                return await self._call_openai(messages, api_key=api_key, base_url=base_url, model=model or "gpt-4o")
        if settings.OPENAI_API_KEY:
            return await self._call_openai(messages)
        if settings.ANTHROPIC_API_KEY:
            return await self._call_anthropic(messages)
        return self._fallback_response(messages)

    async def _call_openai(self, messages: list[dict[str, str]], api_key: str | None = None, base_url: str = "https://api.openai.com/v1", model: str | None = None) -> str:
        key = api_key or settings.OPENAI_API_KEY
        url = f"{base_url.rstrip('/')}/chat/completions"
        mdl = model or settings.OPENAI_MODEL
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": mdl,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1000,
                },
            )
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def _call_anthropic(self, messages: list[dict[str, str]], api_key: str | None = None, model: str | None = None) -> str:
        key = api_key or settings.ANTHROPIC_API_KEY
        mdl = model or settings.ANTHROPIC_MODEL
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
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": mdl,
                    "max_tokens": 1000,
                    "system": system_msg,
                    "messages": chat_messages,
                },
            )
            data = response.json()
            return data["content"][0]["text"]

    async def annotate_code(
        self,
        code: str,
        language: str = "python",
        kp_title: str | None = None,
        api_config: dict | None = None,
    ) -> dict[str, Any]:
        prompt = (
            f"你是一位编程教学专家。请对以下{language}代码进行注解和讲解：\n\n"
            f"```{language}\n{code}\n```\n\n"
        )
        if kp_title:
            prompt += f"相关知识点：{kp_title}\n\n"
        prompt += (
            "请按以下格式返回（必须是合法JSON）：\n"
            "{\n"
            '  "annotated_code": "添加了详细中文注释的代码",\n'
            '  "explanation": "代码整体逻辑的讲解，2-4句话",\n'
            '  "key_concepts": ["涉及的核心概念1", "核心概念2"]\n'
            "}\n\n"
            "要求：\n"
            "1. annotated_code 中每行关键代码上方添加 # 注释\n"
            "2. 注释要解释为什么这样做，而不仅仅是做了什么\n"
            "3. key_concepts 最多5个\n"
            "4. 只返回JSON，不要其他文字"
        )

        messages = [
            {"role": "system", "content": "你是编程教学专家，擅长用简洁的中文解释代码。只返回JSON格式。"},
            {"role": "user", "content": prompt},
        ]

        raw = await self._call_llm(messages, api_config=api_config)
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            result = json.loads(cleaned)
            return {
                "annotated_code": result.get("annotated_code", code),
                "explanation": result.get("explanation", ""),
                "key_concepts": result.get("key_concepts", []),
            }
        except (json.JSONDecodeError, KeyError):
            return {
                "annotated_code": code,
                "explanation": raw[:300] if raw else "代码注解生成失败",
                "key_concepts": [],
            }

    async def explain_knowledge(
        self,
        kp_title: str,
        kp_description: str | None = None,
        p_know: float = 0.0,
        api_config: dict | None = None,
    ) -> dict[str, Any]:
        level = "入门" if p_know < 0.3 else "进阶" if p_know < 0.7 else "深入"
        depth_guide = {
            "入门": "从基础概念出发，用类比和直观示例建立认知框架，强调'为什么'而非'怎么做'",
            "进阶": "在已有概念基础上深入实现原理、性能特征和生产实践，连接理论与工程",
            "深入": "聚焦底层机制、边界情况、性能优化和架构设计，提供专家级洞察",
        }
        prompt = (
            f"你是一位拥有10年以上工业生产级开发经验的编程教学专家。请为以下知识点生成专业级教学解说：\n\n"
            f"知识点：{kp_title}\n"
        )
        if kp_description:
            prompt += f"知识范围：{kp_description}\n"
        prompt += (
            f"学习者当前掌握程度：{level}（p_know={p_know:.2f}）\n"
            f"讲解策略：{depth_guide[level]}\n\n"
            "请按以下格式返回（必须是合法JSON）：\n"
            "{\n"
            '  "title": "知识点标题",\n'
            '  "explanation": "专业级详细讲解，5-8段，包含：1)核心概念与设计哲学 2)底层机制与实现原理 3)生产环境最佳实践 4)性能特征与权衡 5)与其他技术的关联",\n'
            '  "key_points": ["要点1：包含具体技术细节", "要点2：包含生产级注意事项", "要点3：包含性能或安全考量", "要点4：包含常见陷阱"],\n'
            '  "code_example": "生产级代码示例，15-30行，包含错误处理、类型标注、注释说明，反映真实工程实践",\n'
            '  "common_mistakes": ["生产环境常见错误1：具体描述及后果", "生产环境常见错误2：具体描述及修复方案", "生产环境常见错误3：具体描述及预防措施"]\n'
            "}\n\n"
            "要求：\n"
            "1. 讲解必须达到企业工业生产级深度，不能停留在入门玩具级\n"
            "2. 每段讲解必须有具体的技术细节，禁止空泛描述\n"
            "3. code_example 必须是生产级代码：包含错误处理、类型标注、边界检查\n"
            "4. key_points 每条必须包含可操作的技术细节\n"
            "5. common_mistakes 必须描述生产环境真实踩坑场景\n"
            "6. 只返回JSON，不要其他文字"
        )

        messages = [
            {"role": "system", "content": "你是一位拥有10年以上工业生产级开发经验的编程教学专家。你的讲解必须深入底层原理、包含生产级最佳实践、覆盖性能和安全考量。禁止浅尝辄止的入门级描述。只返回JSON格式。"},
            {"role": "user", "content": prompt},
        ]

        raw = await self._call_llm(messages, api_config=api_config)
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            result = json.loads(cleaned)
            return {
                "title": result.get("title", kp_title),
                "explanation": result.get("explanation", ""),
                "key_points": result.get("key_points", []),
                "code_example": result.get("code_example", ""),
                "common_mistakes": result.get("common_mistakes", []),
            }
        except (json.JSONDecodeError, KeyError):
            return {
                "title": kp_title,
                "explanation": raw[:500] if raw else "知识点解说生成失败",
                "key_points": [],
                "code_example": "",
                "common_mistakes": [],
            }

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
