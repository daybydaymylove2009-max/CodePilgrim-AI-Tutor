import math
from datetime import datetime, timedelta, timezone

import pytest
from app.algorithms.spaced_repetition import (
    SpacedRepetitionScheduler,
    SpacedRepetitionItem,
    ForgettingCurveModel,
    ReviewPriority,
)


class TestForgettingCurveModel:
    def setup_method(self):
        self.model = ForgettingCurveModel(initial_stability=1.0)

    def test_recall_at_zero_days(self):
        prob = self.model.recall_probability(0, 1.0)
        assert abs(prob - 1.0) < 0.001

    def test_recall_decreases_over_time(self):
        prob_1d = self.model.recall_probability(1, 1.0)
        prob_5d = self.model.recall_probability(5, 1.0)
        assert prob_1d > prob_5d

    def test_recall_matches_formula(self):
        stability = 5.0
        elapsed = 3.0
        expected = math.exp(-elapsed / stability)
        actual = self.model.recall_probability(elapsed, stability)
        assert abs(actual - expected) < 0.001

    def test_stability_increases_on_success(self):
        new_s = self.model.update_stability(1.0, 0.9, difficulty=1)
        assert new_s > 1.0

    def test_stability_decreases_on_failure(self):
        new_s = self.model.update_stability(1.0, 0.3, difficulty=1)
        assert new_s < 1.0

    def test_difficulty_reduces_stability_growth(self):
        easy = self.model.update_stability(1.0, 0.9, difficulty=1)
        hard = self.model.update_stability(1.0, 0.9, difficulty=5)
        assert easy > hard

    def test_next_review_interval(self):
        interval = self.model.next_review_interval(5.0, 0.85)
        assert interval >= 1
        expected = round(-5.0 * math.log(0.85))
        assert interval == expected


class TestSpacedRepetitionScheduler:
    def setup_method(self):
        self.scheduler = SpacedRepetitionScheduler()

    def _make_item(self, **kwargs) -> SpacedRepetitionItem:
        defaults = {
            "kp_id": "test-kp",
            "p_know": 0.5,
            "mastery_level": "surface",
            "memory_stability": 1.0,
            "review_interval_days": 1,
            "last_reviewed_at": datetime.now(timezone.utc) - timedelta(days=2),
            "next_review_at": datetime.now(timezone.utc) - timedelta(days=1),
            "total_reviews": 3,
            "consecutive_correct": 1,
        }
        defaults.update(kwargs)
        return SpacedRepetitionItem(**defaults)

    def test_high_score_doubles_interval(self):
        item = self._make_item(review_interval_days=4)
        result = self.scheduler.schedule(item, 0.90)
        assert result.review_interval_days == 8

    def test_medium_score_keeps_interval(self):
        item = self._make_item(review_interval_days=4)
        result = self.scheduler.schedule(item, 0.65)
        assert result.review_interval_days == 4

    def test_low_score_resets_interval(self):
        item = self._make_item(review_interval_days=16)
        result = self.scheduler.schedule(item, 0.30)
        assert result.review_interval_days == 1

    def test_overdue_is_p0(self):
        item = self._make_item(next_review_at=datetime.now(timezone.utc) - timedelta(days=1))
        priority = self.scheduler.get_review_priority(item)
        assert priority == ReviewPriority.P0_OVERDUE

    def test_weak_is_p1(self):
        item = self._make_item(mastery_level="weak", next_review_at=datetime.now(timezone.utc) + timedelta(days=1))
        priority = self.scheduler.get_review_priority(item)
        assert priority == ReviewPriority.P1_WEAK

    def test_surface_is_p2(self):
        item = self._make_item(mastery_level="surface", next_review_at=datetime.now(timezone.utc) + timedelta(days=1))
        priority = self.scheduler.get_review_priority(item)
        assert priority == ReviewPriority.P2_SURFACE

    def test_learned_is_p3(self):
        item = self._make_item(mastery_level="learned", next_review_at=datetime.now(timezone.utc) + timedelta(days=5))
        priority = self.scheduler.get_review_priority(item)
        assert priority == ReviewPriority.P3_LEARNED

    def test_forgetting_risk_no_review(self):
        item = self._make_item(last_reviewed_at=None)
        risk = self.scheduler.get_forgetting_risk(item)
        assert risk == 1.0

    def test_forgetting_risk_recent_review(self):
        item = self._make_item(last_reviewed_at=datetime.now(timezone.utc) - timedelta(hours=1))
        risk = self.scheduler.get_forgetting_risk(item)
        assert risk < 0.5

    def test_prioritize_reviews(self):
        items = [
            self._make_item(kp_id="learned", mastery_level="learned", next_review_at=datetime.now(timezone.utc) + timedelta(days=5)),
            self._make_item(kp_id="overdue", mastery_level="surface", next_review_at=datetime.now(timezone.utc) - timedelta(days=1)),
            self._make_item(kp_id="weak", mastery_level="weak", next_review_at=datetime.now(timezone.utc) + timedelta(days=1)),
        ]
        prioritized = self.scheduler.prioritize_reviews(items, max_count=2)
        assert len(prioritized) == 2
        assert prioritized[0].kp_id == "overdue"

    def test_daily_plan_structure(self):
        items = [
            self._make_item(kp_id="overdue", mastery_level="weak", next_review_at=datetime.now(timezone.utc) - timedelta(days=1)),
            self._make_item(kp_id="surface", mastery_level="surface", next_review_at=datetime.now(timezone.utc) + timedelta(days=1)),
            self._make_item(kp_id="learned", mastery_level="learned", next_review_at=datetime.now(timezone.utc) + timedelta(days=5)),
        ]
        plan = self.scheduler.generate_daily_plan(items)
        assert "review" in plan
        assert "surface" in plan
        assert "challenge" in plan
