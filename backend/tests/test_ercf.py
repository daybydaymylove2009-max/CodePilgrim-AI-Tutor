import pytest
from app.algorithms.ercf import (
    ERCFController,
    ERCFContext,
    ERCFStage,
    PersonaStage,
    HintLevel,
    PERSONA_MAX_HINT,
)


class TestERCFStageTransition:
    def setup_method(self):
        self.controller = ERCFController()

    def test_start_new_problem(self):
        ctx = ERCFContext(stage=ERCFStage.R3_LOGICAL_DECOMPOSITION)
        new_stage = self.controller.determine_stage(ctx, "start_new_problem")
        assert new_stage == ERCFStage.R1_PROBLEM_INTERPRETATION

    def test_submit_correct_code(self):
        ctx = ERCFContext(stage=ERCFStage.R3_LOGICAL_DECOMPOSITION)
        new_stage = self.controller.determine_stage(ctx, "submit_code", is_correct=True)
        assert ctx.consecutive_correct == 1
        assert ctx.consecutive_errors == 0

    def test_submit_incorrect_code_enters_r4(self):
        ctx = ERCFContext(stage=ERCFStage.R3_LOGICAL_DECOMPOSITION)
        new_stage = self.controller.determine_stage(ctx, "submit_code", is_correct=False)
        assert new_stage == ERCFStage.R4_ERROR_DIAGNOSIS

    def test_request_hint_from_r1(self):
        ctx = ERCFContext(stage=ERCFStage.R1_PROBLEM_INTERPRETATION)
        new_stage = self.controller.determine_stage(ctx, "request_hint")
        assert new_stage == ERCFStage.R3_LOGICAL_DECOMPOSITION

    def test_request_hint_from_r3(self):
        ctx = ERCFContext(stage=ERCFStage.R3_LOGICAL_DECOMPOSITION)
        new_stage = self.controller.determine_stage(ctx, "request_hint")
        assert new_stage == ERCFStage.R5_GUIDED_HINTING

    def test_idle_timeout_triggers_r5(self):
        ctx = ERCFContext(stage=ERCFStage.R2_CONCEPT_IDENTIFICATION)
        new_stage = self.controller.determine_stage(ctx, "idle_timeout")
        assert new_stage == ERCFStage.R5_GUIDED_HINTING

    def test_advance_stage(self):
        ctx = ERCFContext(stage=ERCFStage.R1_PROBLEM_INTERPRETATION)
        new_stage = self.controller.advance_stage(ctx)
        assert new_stage == ERCFStage.R2_CONCEPT_IDENTIFICATION

    def test_advance_from_last_stage(self):
        ctx = ERCFContext(stage=ERCFStage.R5_GUIDED_HINTING)
        new_stage = self.controller.advance_stage(ctx)
        assert new_stage == ERCFStage.R5_GUIDED_HINTING


class TestPersonaProgression:
    def setup_method(self):
        self.controller = ERCFController()

    def test_guide_default(self):
        ctx = ERCFContext(consecutive_correct=0)
        persona = self.controller.determine_persona(ctx, 0.2)
        assert persona == PersonaStage.GUIDE

    def test_collaborator(self):
        ctx = ERCFContext(consecutive_correct=2)
        persona = self.controller.determine_persona(ctx, 0.55)
        assert persona == PersonaStage.COLLABORATOR

    def test_peer(self):
        ctx = ERCFContext(consecutive_correct=3)
        persona = self.controller.determine_persona(ctx, 0.75)
        assert persona == PersonaStage.PEER

    def test_launcher(self):
        ctx = ERCFContext(consecutive_correct=5)
        persona = self.controller.determine_persona(ctx, 0.90)
        assert persona == PersonaStage.LAUNCHER


class TestHintSystem:
    def setup_method(self):
        self.controller = ERCFController()

    def test_hint_within_persona_limit(self):
        ctx = ERCFContext(persona=PersonaStage.GUIDE)
        result = self.controller.get_hint(ctx, HintLevel.L3_SYNTAX)
        assert result["hint_level"] == 3

    def test_hint_exceeds_persona_limit(self):
        ctx = ERCFContext(persona=PersonaStage.PEER)
        result = self.controller.get_hint(ctx, HintLevel.L4_CODE_SNIPPET)
        assert result["hint_level"] <= PERSONA_MAX_HINT[PersonaStage.PEER].value

    def test_hint_skip_level_allows_upgrade_after_three_requests(self):
        ctx = ERCFContext(persona=PersonaStage.PEER, skip_level_requests=2)
        result = self.controller.get_hint(ctx, HintLevel.L4_CODE_SNIPPET)
        assert result["hint_level"] == 4
        assert ctx.skip_level_requests == 0

    def test_hint_skip_level_blocks_before_three_requests(self):
        ctx = ERCFContext(persona=PersonaStage.PEER, skip_level_requests=1)
        result = self.controller.get_hint(ctx, HintLevel.L4_CODE_SNIPPET)
        assert result["hint_level"] <= PERSONA_MAX_HINT[PersonaStage.PEER].value


class TestIntervention:
    def setup_method(self):
        self.controller = ERCFController()

    def test_idle_intervention(self):
        ctx = ERCFContext(idle_seconds=30)
        result = self.controller.should_intervene(ctx)
        assert result["should_intervene"] is True
        assert any(i["type"] == "idle_prompt" for i in result["interventions"])

    def test_stuck_intervention(self):
        ctx = ERCFContext(consecutive_errors=3)
        result = self.controller.should_intervene(ctx)
        assert result["should_intervene"] is True
        assert any(i["type"] == "stuck_intervention" for i in result["interventions"])

    def test_over_reliance_intervention(self):
        ctx = ERCFContext(total_hints_requested=5, consecutive_correct=0)
        result = self.controller.should_intervene(ctx)
        assert result["should_intervene"] is True

    def test_no_intervention(self):
        ctx = ERCFContext(idle_seconds=5, consecutive_errors=0, total_hints_requested=1, consecutive_correct=2)
        result = self.controller.should_intervene(ctx)
        assert result["should_intervene"] is False


class TestSystemPrompt:
    def setup_method(self):
        self.controller = ERCFController()

    def test_prompt_contains_hard_constraints(self):
        ctx = ERCFContext(persona=PersonaStage.GUIDE, stage=ERCFStage.R1_PROBLEM_INTERPRETATION)
        prompt = self.controller.build_system_prompt(ctx, 0.3, "变量与类型")
        assert "不得生成完整可运行的程序代码" in prompt
        assert "变量与类型" in prompt

    def test_prompt_hint_limit_per_persona(self):
        ctx = ERCFContext(persona=PersonaStage.PEER)
        prompt = self.controller.build_system_prompt(ctx, 0.7, "循环")
        assert "L2" in prompt
