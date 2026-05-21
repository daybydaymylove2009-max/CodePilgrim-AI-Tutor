import pytest
from app.algorithms.bkt import BKTTracker, BKTParams, BKTEvidence, MasteryLevel


class TestBKTEvidence:
    def test_adjusted_correct_simple_correct(self):
        e = BKTEvidence(correct=True, response_time_ms=5000, hints_used=0)
        assert e.adjusted_correct is True

    def test_adjusted_correct_too_many_hints(self):
        e = BKTEvidence(correct=True, response_time_ms=5000, hints_used=3)
        assert e.adjusted_correct is False

    def test_adjusted_correct_high_hint_level(self):
        e = BKTEvidence(correct=True, response_time_ms=5000, hints_used=1, hint_level=4)
        assert e.adjusted_correct is False

    def test_adjusted_correct_too_slow(self):
        e = BKTEvidence(correct=True, response_time_ms=130000, hints_used=0)
        assert e.adjusted_correct is False

    def test_adjusted_correct_incorrect(self):
        e = BKTEvidence(correct=False, response_time_ms=1000, hints_used=0)
        assert e.adjusted_correct is False


class TestBKTTracker:
    def setup_method(self):
        self.tracker = BKTTracker(BKTParams(p_l0=0.2, p_guess=0.25, p_slip=0.15, p_transfer=0.1))

    def test_initial_update_correct(self):
        p = self.tracker.update(0.2, BKTEvidence(correct=True))
        assert p > 0.2

    def test_initial_update_incorrect(self):
        p = self.tracker.update(0.2, BKTEvidence(correct=False))
        assert p < 0.2

    def test_consecutive_correct_increases(self):
        p = 0.2
        for _ in range(5):
            p = self.tracker.update(p, BKTEvidence(correct=True))
        assert p > 0.8

    def test_consecutive_incorrect_decreases(self):
        p = 0.8
        for _ in range(3):
            p = self.tracker.update(p, BKTEvidence(correct=False))
        assert p < 0.8

    def test_bounded_probability(self):
        p = 0.2
        for _ in range(100):
            p = self.tracker.update(p, BKTEvidence(correct=True))
        assert p <= 1.0

        p = 0.8
        for _ in range(100):
            p = self.tracker.update(p, BKTEvidence(correct=False))
        assert p >= 0.0

    def test_batch_update(self):
        evidences = [BKTEvidence(correct=True)] * 5
        p = self.tracker.update_batch(0.2, evidences)
        assert p > 0.8

    def test_mixed_evidence(self):
        evidences = [
            BKTEvidence(correct=True),
            BKTEvidence(correct=False),
            BKTEvidence(correct=True),
        ]
        p = self.tracker.update_batch(0.2, evidences)
        assert 0.2 < p < 1.0

    def test_predict_correct_probability(self):
        prob = self.tracker.predict_correct_probability(0.5)
        expected = 0.5 * (1 - 0.15) + (1 - 0.5) * 0.25
        assert abs(prob - expected) < 0.001

    def test_learning_velocity(self):
        history = [0.2, 0.3, 0.4, 0.5, 0.6]
        velocity = self.tracker.estimate_learning_velocity(history)
        assert velocity > 0

    def test_stagnation_detected(self):
        history = [0.5, 0.5, 0.5, 0.5, 0.5]
        assert self.tracker.detect_stagnation(history) is True

    def test_no_stagnation(self):
        history = [0.2, 0.3, 0.4, 0.5, 0.6]
        assert self.tracker.detect_stagnation(history) is False

    def test_regression_detected(self):
        history = [0.5, 0.6, 0.7, 0.4]
        assert self.tracker.detect_regression(history) is True

    def test_no_regression(self):
        history = [0.5, 0.6, 0.7, 0.8]
        assert self.tracker.detect_regression(history) is False


class TestMasteryLevel:
    def test_unlearned(self):
        assert BKTTracker.classify_mastery(0.1) == MasteryLevel.UNLEARNED

    def test_weak(self):
        assert BKTTracker.classify_mastery(0.45) == MasteryLevel.WEAK

    def test_surface(self):
        assert BKTTracker.classify_mastery(0.65) == MasteryLevel.SURFACE

    def test_learned(self):
        assert BKTTracker.classify_mastery(0.82, independent_rate=0.75) == MasteryLevel.LEARNED

    def test_mastered(self):
        assert BKTTracker.classify_mastery(0.90, independent_rate=0.80, deformation_rate=0.60) == MasteryLevel.MASTERED

    def test_mastery_achieved(self):
        assert BKTTracker.is_mastery_achieved(0.90, 0.80) is True

    def test_mastery_not_achieved(self):
        assert BKTTracker.is_mastery_achieved(0.70, 0.50) is False
