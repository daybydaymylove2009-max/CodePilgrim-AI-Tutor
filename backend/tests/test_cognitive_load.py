import pytest
from app.algorithms.cognitive_load import (
    CognitiveLoadRegulator,
    CognitiveLoadSignals,
    CognitiveLoadLevel,
    RegulationAction,
)


class TestCognitiveLoadAssessment:
    def setup_method(self):
        self.regulator = CognitiveLoadRegulator()

    def test_optimal_load(self):
        signals = CognitiveLoadSignals(
            response_time_change_rate=0.1,
            error_rate_spike=False,
            hint_request_frequency=0.2,
            session_duration_minutes=20,
            consecutive_errors=0,
            consecutive_correct=3,
        )
        load = self.regulator.assess_load(signals)
        assert load == CognitiveLoadLevel.OPTIMAL

    def test_overloaded_from_errors(self):
        signals = CognitiveLoadSignals(
            error_rate_spike=True,
            consecutive_errors=4,
            hint_request_frequency=0.7,
        )
        load = self.regulator.assess_load(signals)
        assert load == CognitiveLoadLevel.OVERLOADED

    def test_overloaded_from_fatigue(self):
        signals = CognitiveLoadSignals(
            session_duration_minutes=50,
            error_rate_spike=True,
            consecutive_errors=3,
        )
        load = self.regulator.assess_load(signals)
        assert load == CognitiveLoadLevel.OVERLOADED

    def test_underloaded_from_fast_progress(self):
        signals = CognitiveLoadSignals(
            response_time_change_rate=-0.4,
            consecutive_correct=6,
            hint_request_frequency=0.05,
        )
        load = self.regulator.assess_load(signals)
        assert load == CognitiveLoadLevel.UNDERLOADED


class TestCognitiveLoadRegulation:
    def setup_method(self):
        self.regulator = CognitiveLoadRegulator()

    def test_overload_triggers_decompose(self):
        signals = CognitiveLoadSignals(
            error_rate_spike=True,
            consecutive_errors=3,
            hint_request_frequency=0.6,
        )
        result = self.regulator.regulate(signals, 0.4)
        assert result["load_level"] == "overloaded"
        assert RegulationAction.DECOMPOSE.value in result["actions"] or RegulationAction.REDUCE_DIFFICULTY.value in result["actions"]

    def test_overload_triggers_break(self):
        signals = CognitiveLoadSignals(
            session_duration_minutes=50,
            consecutive_errors=4,
        )
        result = self.regulator.regulate(signals, 0.3)
        assert result["load_level"] == "overloaded"
        assert RegulationAction.TAKE_BREAK.value in result["actions"]

    def test_underload_triggers_accelerate(self):
        signals = CognitiveLoadSignals(
            response_time_change_rate=-0.4,
            consecutive_correct=6,
            hint_request_frequency=0.05,
        )
        result = self.regulator.regulate(signals, 0.8)
        assert result["load_level"] == "underloaded"
        assert RegulationAction.ACCELERATE.value in result["actions"]

    def test_optimal_maintains(self):
        signals = CognitiveLoadSignals(
            response_time_change_rate=0.1,
            error_rate_spike=False,
            hint_request_frequency=0.2,
            consecutive_errors=0,
            consecutive_correct=2,
        )
        result = self.regulator.regulate(signals, 0.5)
        assert result["load_level"] == "optimal"
        assert RegulationAction.MAINTAIN.value in result["actions"]

    def test_overload_has_suggestions(self):
        signals = CognitiveLoadSignals(
            error_rate_spike=True,
            consecutive_errors=3,
            hint_request_frequency=0.7,
            session_duration_minutes=50,
        )
        result = self.regulator.regulate(signals, 0.3)
        assert len(result["suggestions"]) > 0
