from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ERCFStage(str, Enum):
    R1_PROBLEM_INTERPRETATION = "R1"
    R2_CONCEPT_IDENTIFICATION = "R2"
    R3_LOGICAL_DECOMPOSITION = "R3"
    R4_ERROR_DIAGNOSIS = "R4"
    R5_GUIDED_HINTING = "R5"


class PersonaStage(str, Enum):
    GUIDE = "guide"
    COLLABORATOR = "collaborator"
    PEER = "peer"
    LAUNCHER = "launcher"


class HintLevel(int, Enum):
    L1_CONCEPT = 1
    L2_DIRECTION = 2
    L3_SYNTAX = 3
    L4_CODE_SNIPPET = 4
    L5_FULL_EXPLANATION = 5


PERSONA_MAX_HINT = {
    PersonaStage.GUIDE: HintLevel.L5_FULL_EXPLANATION,
    PersonaStage.COLLABORATOR: HintLevel.L3_SYNTAX,
    PersonaStage.PEER: HintLevel.L2_DIRECTION,
    PersonaStage.LAUNCHER: HintLevel.L1_CONCEPT,
}

ERCF_STAGE_PROMPTS: dict[ERCFStage, dict[str, str]] = {
    ERCFStage.R1_PROBLEM_INTERPRETATION: {
        "purpose": "引导学习者理解题目要求",
        "prompt_template": (
            "让我们先理解这个问题在问什么...\n"
            "这个例子中，输入是什么？期望输出是什么？\n"
            "你能用自己的话复述一下题目要求吗？"
        ),
        "completion_criteria": "学习者能正确描述问题的输入输出和约束条件",
    },
    ERCFStage.R2_CONCEPT_IDENTIFICATION: {
        "purpose": "帮助识别解决问题所需的知识概念",
        "prompt_template": (
            "解决这个问题需要用到哪些知识点？\n"
            "你还记得'{concept}'怎么用吗？\n"
            "哪些已学过的知识可能对这个问题有帮助？"
        ),
        "completion_criteria": "学习者能识别出解决问题所需的核心概念",
    },
    ERCFStage.R3_LOGICAL_DECOMPOSITION: {
        "purpose": "引导将大问题分解为小步骤",
        "prompt_template": (
            "让我们把这个问题拆成几步...\n"
            "第一步：{step1}；第二步：{step2}；第三步：{step3}\n"
            "你觉得每一步应该怎么实现？"
        ),
        "completion_criteria": "学习者能将问题分解为可执行的子步骤",
    },
    ERCFStage.R4_ERROR_DIAGNOSIS: {
        "purpose": "帮助诊断代码中的错误",
        "prompt_template": (
            "这里的循环好像多跑了一次...\n"
            "注意！索引是从0开始的...\n"
            "检查一下{error_area}，看看是不是有什么问题？"
        ),
        "completion_criteria": "学习者能定位错误并理解错误原因",
    },
    ERCFStage.R5_GUIDED_HINTING: {
        "purpose": "提供增量式提示而非直接给答案",
        "prompt_template": {
            HintLevel.L1_CONCEPT: "想想用什么来{action}...",
            HintLevel.L2_DIRECTION: "可能需要用到{concept}来{action}...",
            HintLevel.L3_SYNTAX: "试试用 {syntax}...",
            HintLevel.L4_CODE_SNIPPET: "你可以这样写：{snippet}",
            HintLevel.L5_FULL_EXPLANATION: "让我详细解释一下这个概念：{explanation}",
        },
        "completion_criteria": "学习者基于提示独立完成代码编写",
    },
}


@dataclass
class ERCFContext:
    stage: ERCFStage = ERCFStage.R1_PROBLEM_INTERPRETATION
    persona: PersonaStage = PersonaStage.GUIDE
    current_hint_level: HintLevel = HintLevel.L1_CONCEPT
    consecutive_errors: int = 0
    consecutive_correct: int = 0
    idle_seconds: int = 0
    total_hints_requested: int = 0
    skip_level_requests: int = 0


class ERCFController:
    """
    ERCF (EduMate Reasoning Control Framework) 推理控制器.

    五阶段推理框架，控制AI导师的教学引导流程：
    R1 问题解析 → R2 概念识别 → R3 逻辑分解 → R4 错误诊断 → R5 引导提示

    结合角色渐进模型 (Persona Progression)：
    Guide → Collaborator → Peer → Launcher
    """

    def __init__(self):
        self.stage_prompts = ERCF_STAGE_PROMPTS

    def determine_stage(self, context: ERCFContext, learner_action: str, is_correct: bool | None = None) -> ERCFStage:
        if learner_action == "start_new_problem":
            return ERCFStage.R1_PROBLEM_INTERPRETATION

        if learner_action == "submit_code":
            if is_correct is True:
                context.consecutive_errors = 0
                context.consecutive_correct += 1
                if context.stage == ERCFStage.R4_ERROR_DIAGNOSIS:
                    return ERCFStage.R5_GUIDED_HINTING
                return context.stage
            else:
                context.consecutive_correct = 0
                context.consecutive_errors += 1
                return ERCFStage.R4_ERROR_DIAGNOSIS

        if learner_action == "request_hint":
            if context.stage in (ERCFStage.R1_PROBLEM_INTERPRETATION, ERCFStage.R2_CONCEPT_IDENTIFICATION):
                return ERCFStage.R3_LOGICAL_DECOMPOSITION
            return ERCFStage.R5_GUIDED_HINTING

        if learner_action == "identify_concept":
            return ERCFStage.R2_CONCEPT_IDENTIFICATION

        if learner_action == "decompose":
            return ERCFStage.R3_LOGICAL_DECOMPOSITION

        if learner_action == "idle_timeout":
            return ERCFStage.R5_GUIDED_HINTING

        return context.stage

    def advance_stage(self, context: ERCFContext) -> ERCFStage:
        stage_order = list(ERCFStage)
        current_idx = stage_order.index(context.stage)
        if current_idx < len(stage_order) - 1:
            return stage_order[current_idx + 1]
        return context.stage

    def get_hint(self, context: ERCFContext, hint_level: HintLevel | None = None) -> dict[str, Any]:
        max_hint = PERSONA_MAX_HINT.get(context.persona, HintLevel.L1_CONCEPT)
        requested_level = hint_level or context.current_hint_level

        if requested_level.value > max_hint.value:
            context.skip_level_requests += 1
            if context.skip_level_requests >= 3:
                context.skip_level_requests = 0
            else:
                requested_level = max_hint

        context.current_hint_level = requested_level
        context.total_hints_requested += 1

        stage_data = self.stage_prompts.get(ERCFStage.R5_GUIDED_HINTING, {})
        prompt_templates = stage_data.get("prompt_template", {})

        if isinstance(prompt_templates, dict):
            template = prompt_templates.get(requested_level, "再想想...")
        else:
            template = str(prompt_templates)

        return {
            "stage": context.stage.value,
            "persona": context.persona.value,
            "hint_level": requested_level.value,
            "prompt_template": template,
            "max_hint_for_persona": max_hint.value,
        }

    def determine_persona(self, context: ERCFContext, p_know: float) -> PersonaStage:
        if p_know >= 0.85 and context.consecutive_correct >= 5:
            return PersonaStage.LAUNCHER
        if p_know >= 0.70 and context.consecutive_correct >= 3:
            return PersonaStage.PEER
        if p_know >= 0.50 and context.consecutive_correct >= 2:
            return PersonaStage.COLLABORATOR
        return PersonaStage.GUIDE

    def should_intervene(self, context: ERCFContext) -> dict[str, Any]:
        interventions = []

        if context.idle_seconds >= 30:
            interventions.append({
                "type": "idle_prompt",
                "message": "看起来你在这里停了一会儿，需要一点提示吗？",
                "action": "offer_hint",
            })

        if context.consecutive_errors >= 3:
            interventions.append({
                "type": "stuck_intervention",
                "message": "连续几次都遇到了困难，让我们换个角度来看这个问题。",
                "action": "change_approach",
            })

        if context.total_hints_requested >= 5 and context.consecutive_correct == 0:
            interventions.append({
                "type": "over_reliance_warning",
                "message": "你似乎在频繁请求提示，试试先自己思考一下？",
                "action": "encourage_independence",
            })

        return {
            "should_intervene": len(interventions) > 0,
            "interventions": interventions,
            "persona": context.persona.value,
            "stage": context.stage.value,
        }

    def build_system_prompt(self, context: ERCFContext, p_know: float, kp_title: str) -> str:
        persona_descriptions = {
            PersonaStage.GUIDE: "你是一位耐心的引路者（Guide），详细讲解每一步，解释为什么这样做。",
            PersonaStage.COLLABORATOR: "你是一位协作者（Collaborator），与学习者共同完成，引导而非指令。",
            PersonaStage.PEER: "你是一位同伴（Peer），平等讨论，提出问题，分享思路。",
            PersonaStage.LAUNCHER: "你是一位发射者（Launcher），观察者角色，仅在完成后复盘。",
        }

        stage_descriptions = {
            ERCFStage.R1_PROBLEM_INTERPRETATION: "当前处于R1阶段：问题解析。引导学习者理解题目要求。",
            ERCFStage.R2_CONCEPT_IDENTIFICATION: "当前处于R2阶段：概念识别。帮助识别所需知识概念。",
            ERCFStage.R3_LOGICAL_DECOMPOSITION: "当前处于R3阶段：逻辑分解。引导将问题分解为小步骤。",
            ERCFStage.R4_ERROR_DIAGNOSIS: "当前处于R4阶段：错误诊断。帮助定位和理解代码错误。",
            ERCFStage.R5_GUIDED_HINTING: "当前处于R5阶段：引导提示。提供增量式提示，不给完整答案。",
        }

        hard_constraints = """
【硬性约束 - 绝对禁止】
1. 不得生成完整可运行的程序代码
2. 不得写出"复制粘贴即可运行"的解决方案
3. 不得跳过推理过程直接给出答案
4. 不得替学习者完成代码编写
5. 每次提示必须是增量式的、引导性的
"""

        max_hint = PERSONA_MAX_HINT.get(context.persona, HintLevel.L1_CONCEPT)
        hint_constraint = f"\n【提示等级限制】当前角色阶段允许的最高提示等级：L{max_hint.value}\n"

        return f"""你是 CodePilgrim 的 AI 编程导师，正在教授知识点：{kp_title}

学习者掌握度：{p_know:.1%}

{persona_descriptions.get(context.persona, persona_descriptions[PersonaStage.GUIDE])}

{stage_descriptions.get(context.stage, "")}

{hard_constraints}
{hint_constraint}
请根据以上框架引导学习者。"""
