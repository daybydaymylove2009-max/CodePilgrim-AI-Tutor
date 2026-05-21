from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from app.core.config import settings


class MasteryLevel(str, Enum):
    UNLEARNED = "unlearned"
    WEAK = "weak"
    SURFACE = "surface"
    LEARNED = "learned"
    MASTERED = "mastered"


@dataclass
class BKTEvidence:
    correct: bool
    response_time_ms: int = 0
    hints_used: int = 0
    hint_level: int = 0

    @property
    def adjusted_correct(self) -> bool:
        if self.hints_used >= 3:
            return False
        if self.hint_level >= 4:
            return False
        if self.correct and self.response_time_ms > 120000:
            return False
        return self.correct


@dataclass
class BKTParams:
    p_l0: float = field(default_factory=lambda: settings.BKT_P_L0)
    p_guess: float = field(default_factory=lambda: settings.BKT_P_G)
    p_slip: float = field(default_factory=lambda: settings.BKT_P_S)
    p_transfer: float = field(default_factory=lambda: settings.BKT_P_T)


class BKTTracker:
    """
    Bayesian Knowledge Tracing — 4-parameter model.

    P(L) = probability the learner has mastered the skill
    P(G) = probability of guessing correctly (without mastery)
    P(S) = probability of slipping (answering incorrectly despite mastery)
    P(T) = probability of transitioning from unlearned to learned

    Update rules:
        After correct answer:
            P(L|correct) = P(L) * (1 - P(S)) / [P(L) * (1 - P(S)) + (1 - P(L)) * P(G)]
        After incorrect answer:
            P(L|incorrect) = P(L) * P(S) / [P(L) * P(S) + (1 - P(L)) * (1 - P(G))]
        After each observation:
            P(L)_new = P(L|evidence) + (1 - P(L|evidence)) * P(T)
    """

    def __init__(self, params: BKTParams | None = None):
        self.params = params or BKTParams()

    def update(self, p_know: float, evidence: BKTEvidence) -> float:
        p_l = p_know
        p_g = self.params.p_guess
        p_s = self.params.p_slip
        p_t = self.params.p_transfer

        effective_correct = evidence.adjusted_correct

        if effective_correct:
            p_l_given_e = p_l * (1 - p_s) / (p_l * (1 - p_s) + (1 - p_l) * p_g)
        else:
            p_l_given_e = p_l * p_s / (p_l * p_s + (1 - p_l) * (1 - p_g))

        p_l_new = p_l_given_e + (1 - p_l_given_e) * p_t

        return min(max(p_l_new, 0.0), 1.0)

    def update_batch(self, p_know: float, evidences: list[BKTEvidence]) -> float:
        p_l = p_know
        for evidence in evidences:
            p_l = self.update(p_l, evidence)
        return p_l

    @staticmethod
    def classify_mastery(p_know: float, independent_rate: float = 0.0, deformation_rate: float = 0.0) -> MasteryLevel:
        if p_know >= 0.85 and independent_rate >= 0.70 and deformation_rate >= 0.50:
            return MasteryLevel.MASTERED
        if p_know >= 0.80 and independent_rate >= 0.70:
            return MasteryLevel.LEARNED
        if p_know >= 0.60:
            return MasteryLevel.SURFACE
        if p_know >= 0.40:
            return MasteryLevel.WEAK
        return MasteryLevel.UNLEARNED

    @staticmethod
    def is_mastery_achieved(p_know: float, independent_rate: float = 0.0) -> bool:
        threshold = settings.BKT_MASTERY_THRESHOLD
        return p_know >= threshold and independent_rate >= 0.70

    def predict_correct_probability(self, p_know: float) -> float:
        p_l = p_know
        p_g = self.params.p_guess
        p_s = self.params.p_slip
        return p_l * (1 - p_s) + (1 - p_l) * p_g

    def estimate_learning_velocity(self, p_know_history: list[float]) -> float:
        if len(p_know_history) < 2:
            return 0.0
        deltas = [p_know_history[i + 1] - p_know_history[i] for i in range(len(p_know_history) - 1)]
        return sum(deltas) / len(deltas)

    def detect_stagnation(self, p_know_history: list[float], window: int = 5, threshold: float = 0.02) -> bool:
        if len(p_know_history) < window:
            return False
        recent = p_know_history[-window:]
        delta = max(recent) - min(recent)
        return delta < threshold

    def detect_regression(self, p_know_history: list[float], window: int = 3) -> bool:
        if len(p_know_history) < window + 1:
            return False
        before_avg = sum(p_know_history[-(window + 1):-1]) / window
        after = p_know_history[-1]
        return after < before_avg - 0.05
