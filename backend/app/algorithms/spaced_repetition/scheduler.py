from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from app.core.config import settings


class ReviewPriority(str, Enum):
    P0_OVERDUE = "P0"
    P1_WEAK = "P1"
    P2_SURFACE = "P2"
    P3_LEARNED = "P3"


@dataclass
class SpacedRepetitionItem:
    kp_id: str
    p_know: float
    mastery_level: str
    memory_stability: float = 1.0
    review_interval_days: int = 1
    last_reviewed_at: datetime | None = None
    next_review_at: datetime | None = None
    total_reviews: int = 0
    consecutive_correct: int = 0


class ForgettingCurveModel:
    """
    基于艾宾浩斯遗忘曲线的个性化记忆模型.

    R(t) = e^(-t/S)
    R = 回忆概率, t = 时间间隔, S = 记忆稳定度
    """

    def __init__(self, initial_stability: float = 1.0):
        self.initial_stability = initial_stability

    def recall_probability(self, elapsed_days: float, stability: float) -> float:
        if stability <= 0:
            return 0.0
        return math.exp(-elapsed_days / stability)

    def update_stability(self, current_stability: float, score: float, difficulty: int = 1) -> float:
        difficulty_factor = max(0.5, 1.0 - (difficulty - 1) * 0.1)

        if score >= 0.80:
            success_factor = 1.3 + (score - 0.80) * 2.0
        elif score >= 0.50:
            success_factor = 1.0
        else:
            success_factor = max(0.3, 0.5 + score)

        new_stability = current_stability * success_factor * difficulty_factor
        return max(0.5, min(new_stability, 365.0))

    def next_review_interval(self, stability: float, threshold: float | None = None) -> int:
        threshold = threshold or settings.SPACED_REPETITION_RECALL_THRESHOLD
        if threshold <= 0 or threshold >= 1:
            threshold = 0.85

        interval = -stability * math.log(threshold)
        return max(1, round(interval))


class SpacedRepetitionScheduler:
    """
    间隔重复调度器.

    调度规则:
    - 评分 >= 80%: interval = interval × 2
    - 评分 50-79%: interval 不变
    - 评分 < 50%: interval 重置为 1 天
    """

    def __init__(self):
        self.forgetting_model = ForgettingCurveModel()
        self.initial_interval = settings.SPACED_REPETITION_INITIAL_INTERVAL_DAYS

    def schedule(self, item: SpacedRepetitionItem, score: float, difficulty: int = 1) -> SpacedRepetitionItem:
        item.memory_stability = self.forgetting_model.update_stability(
            item.memory_stability, score, difficulty
        )

        if score >= 0.80:
            item.review_interval_days = item.review_interval_days * 2
            item.consecutive_correct += 1
        elif score >= 0.50:
            item.consecutive_correct = 0
        else:
            item.review_interval_days = self.initial_interval
            item.memory_stability = max(0.5, item.memory_stability * 0.5)
            item.consecutive_correct = 0

        item.total_reviews += 1
        item.last_reviewed_at = datetime.now(timezone.utc)
        item.next_review_at = item.last_reviewed_at + timedelta(days=item.review_interval_days)

        return item

    def get_review_priority(self, item: SpacedRepetitionItem) -> ReviewPriority:
        now = datetime.now(timezone.utc)

        if item.next_review_at and item.next_review_at <= now:
            return ReviewPriority.P0_OVERDUE
        if item.mastery_level in ("unlearned", "weak"):
            return ReviewPriority.P1_WEAK
        if item.mastery_level == "surface":
            return ReviewPriority.P2_SURFACE
        return ReviewPriority.P3_LEARNED

    def get_forgetting_risk(self, item: SpacedRepetitionItem) -> float:
        if item.last_reviewed_at is None:
            return 1.0

        now = datetime.now(timezone.utc)
        elapsed_days = (now - item.last_reviewed_at).total_seconds() / 86400
        recall_prob = self.forgetting_model.recall_probability(elapsed_days, item.memory_stability)
        return 1.0 - recall_prob

    def prioritize_reviews(self, items: list[SpacedRepetitionItem], max_count: int = 5) -> list[SpacedRepetitionItem]:
        priority_order = {
            ReviewPriority.P0_OVERDUE: 0,
            ReviewPriority.P1_WEAK: 1,
            ReviewPriority.P2_SURFACE: 2,
            ReviewPriority.P3_LEARNED: 3,
        }

        def sort_key(item: SpacedRepetitionItem) -> tuple:
            priority = self.get_review_priority(item)
            risk = self.get_forgetting_risk(item)
            return (priority_order.get(priority, 99), -risk)

        sorted_items = sorted(items, key=sort_key)
        return sorted_items[:max_count]

    def generate_daily_plan(
        self, items: list[SpacedRepetitionItem]
    ) -> dict[str, list[SpacedRepetitionItem]]:
        review_items = [i for i in items if self.get_review_priority(i) in (ReviewPriority.P0_OVERDUE, ReviewPriority.P1_WEAK)]
        surface_items = [i for i in items if self.get_review_priority(i) == ReviewPriority.P2_SURFACE]
        challenge_items = [i for i in items if self.get_review_priority(i) == ReviewPriority.P3_LEARNED]

        return {
            "review": self.prioritize_reviews(review_items, max_count=5),
            "surface": self.prioritize_reviews(surface_items, max_count=2),
            "challenge": self.prioritize_reviews(challenge_items, max_count=1),
        }
