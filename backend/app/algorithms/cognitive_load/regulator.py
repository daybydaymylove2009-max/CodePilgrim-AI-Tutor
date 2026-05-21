from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CognitiveLoadLevel(str, Enum):
    UNDERLOADED = "underloaded"
    OPTIMAL = "optimal"
    OVERLOADED = "overloaded"


class RegulationAction(str, Enum):
    ACCELERATE = "accelerate"
    MAINTAIN = "maintain"
    DECOMPOSE = "decompose"
    REDUCE_DIFFICULTY = "reduce_difficulty"
    INSERT_PRACTICE = "insert_practice"
    TAKE_BREAK = "take_break"


@dataclass
class CognitiveLoadSignals:
    response_time_change_rate: float = 0.0
    error_rate_spike: bool = False
    hint_request_frequency: float = 0.0
    session_duration_minutes: float = 0.0
    consecutive_errors: int = 0
    consecutive_correct: int = 0
    idle_seconds: int = 0


class CognitiveLoadRegulator:
    """
    认知负荷调节器.

    实时监测并调节学习者的认知负荷：
    - 过载 → 拆分知识点、插入实践环节、降低难度
    - 适中 → 维持当前节奏，适度挑战
    - 空闲 → 加速推进、增加挑战、引入新概念

    反馈周期：每5分钟评估一次
    """

    def __init__(self):
        self.fatigue_threshold_minutes = 45.0
        self.error_spike_threshold = 0.6
        self.idle_threshold_seconds = 30
        self.acceleration_threshold_rate = -0.3

    def assess_load(self, signals: CognitiveLoadSignals) -> CognitiveLoadLevel:
        overload_signals = 0

        if signals.error_rate_spike:
            overload_signals += 2
        if signals.consecutive_errors >= 3:
            overload_signals += 2
        if signals.hint_request_frequency > 0.5:
            overload_signals += 1
        if signals.response_time_change_rate > 0.5:
            overload_signals += 1
        if signals.session_duration_minutes > self.fatigue_threshold_minutes:
            overload_signals += 1

        underload_signals = 0
        if signals.response_time_change_rate < self.acceleration_threshold_rate:
            underload_signals += 1
        if signals.consecutive_correct >= 5:
            underload_signals += 2
        if signals.hint_request_frequency < 0.1 and signals.consecutive_correct >= 3:
            underload_signals += 1

        if overload_signals >= 3:
            return CognitiveLoadLevel.OVERLOADED
        if underload_signals >= 2:
            return CognitiveLoadLevel.UNDERLOADED
        return CognitiveLoadLevel.OPTIMAL

    def regulate(self, signals: CognitiveLoadSignals, current_p_know: float) -> dict:
        load_level = self.assess_load(signals)

        if load_level == CognitiveLoadLevel.OVERLOADED:
            return self._handle_overload(signals, current_p_know)
        if load_level == CognitiveLoadLevel.UNDERLOADED:
            return self._handle_underload(signals, current_p_know)
        return self._handle_optimal(signals, current_p_know)

    def _handle_overload(self, signals: CognitiveLoadSignals, p_know: float) -> dict:
        actions = []

        if signals.session_duration_minutes > self.fatigue_threshold_minutes:
            actions.append(RegulationAction.TAKE_BREAK)

        if signals.consecutive_errors >= 3:
            actions.append(RegulationAction.REDUCE_DIFFICULTY)

        if signals.error_rate_spike or signals.hint_request_frequency > 0.5:
            actions.append(RegulationAction.DECOMPOSE)

        if not actions:
            actions.append(RegulationAction.INSERT_PRACTICE)

        return {
            "load_level": load_level.value if (load_level := CognitiveLoadLevel.OVERLOADED) else "overloaded",
            "actions": [a.value for a in actions],
            "message": "检测到你有些吃力，让我们调整一下节奏。",
            "suggestions": self._generate_overload_suggestions(signals),
        }

    def _handle_underload(self, signals: CognitiveLoadSignals, p_know: float) -> dict:
        actions = [RegulationAction.ACCELERATE]

        if p_know >= 0.70:
            actions.append(RegulationAction.MAINTAIN)

        return {
            "load_level": "underloaded",
            "actions": [a.value for a in actions],
            "message": "你学得很快！让我们尝试更有挑战性的内容。",
            "suggestions": [
                "尝试更高难度的变体题",
                "跳过已掌握的基础练习",
                "挑战综合应用题",
            ],
        }

    def _handle_optimal(self, signals: CognitiveLoadSignals, p_know: float) -> dict:
        return {
            "load_level": "optimal",
            "actions": [RegulationAction.MAINTAIN.value],
            "message": "当前学习节奏很好，继续保持！",
            "suggestions": [],
        }

    def _generate_overload_suggestions(self, signals: CognitiveLoadSignals) -> list[str]:
        suggestions = []
        if signals.consecutive_errors >= 3:
            suggestions.append("回到更基础的概念复习一下")
        if signals.hint_request_frequency > 0.5:
            suggestions.append("试试从不同角度理解这个概念")
        if signals.session_duration_minutes > self.fatigue_threshold_minutes:
            suggestions.append("休息一下，疲劳时学习效果会下降")
        if signals.response_time_change_rate > 0.5:
            suggestions.append("放慢节奏，不必急于完成")
        return suggestions or ["拆分当前问题为更小的步骤"]
