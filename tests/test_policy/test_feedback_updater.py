"""Feedback policy updater test suite."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from models.feedback import FeedbackEvent, FeedbackLabel
from security_engine.policy_engine import FeedbackPolicyUpdater, process_policy_updates


@pytest.fixture
def mock_memory() -> MagicMock:
    """Mock adaptive memory."""
    memory = MagicMock()
    memory.query_feedback_events.return_value = []
    memory.get_threshold.return_value = 1.0
    return memory


@pytest.fixture
def sample_events() -> list:
    """Sample feedback events."""
    return [
        FeedbackEvent(
            fault_id=f"fault_{i}",
            anomaly_type="power",
            recovery_action="cycle",
            mission_phase="NOMINAL_OPS",
            label=FeedbackLabel.CORRECT if i < 7 else FeedbackLabel.WRONG,
            confidence_score=0.95,
        )
        for i in range(10)
    ]


class TestSuccessRateCalculation:
    """Test empirical success rate computation."""

    def test_success_rate_70_percent(self, sample_events: list) -> None:
        """70% success rate (7 correct out of 10)."""
        updater = FeedbackPolicyUpdater(MagicMock())
        rate = updater._compute_success_rate(sample_events)
        assert rate == 0.7

    def test_success_rate_100_percent(self, mock_memory: MagicMock) -> None:
        """100% success rate."""
        all_correct = [
            FeedbackEvent(
                fault_id="f1",
                anomaly_type="power",
                recovery_action="cycle",
                mission_phase="NOMINAL_OPS",
                label=FeedbackLabel.CORRECT,
                confidence_score=0.95,
            )
            for _ in range(5)
        ]
        updater = FeedbackPolicyUpdater(mock_memory)
        rate = updater._compute_success_rate(all_correct)
        assert rate == 1.0

    def test_success_rate_0_percent(self, mock_memory: MagicMock) -> None:
        """0% success rate (all wrong)."""
        all_wrong = [
            FeedbackEvent(
                fault_id="f1",
                anomaly_type="power",
                recovery_action="cycle",
                mission_phase="NOMINAL_OPS",
                label=FeedbackLabel.WRONG,
                confidence_score=0.95,
            )
            for _ in range(5)
        ]
        updater = FeedbackPolicyUpdater(mock_memory)
        rate = updater._compute_success_rate(all_wrong)
        assert rate == 0.0

    def test_success_rate_empty_list(self, mock_memory: MagicMock) -> None:
        """Empty event list returns 0.0."""
        updater = FeedbackPolicyUpdater(mock_memory)
        rate = updater._compute_success_rate([])
        assert rate == 0.0


class TestThresholdBoosting:
    """Test threshold adjustment for high success rates."""

    def test_threshold_boost_high_success(self, mock_memory: MagicMock) -> None:
        """High success (70%+) boosts threshold."""
        high_success_events = [
            FeedbackEvent(
                fault_id=f"f{i}",
                anomaly_type="power",
                recovery_action="cycle",
                mission_phase="NOMINAL_OPS",
                label=FeedbackLabel.CORRECT,
                confidence_score=0.95,
            )
            for i in range(8)
        ]
        mock_memory.query_feedback_events.return_value = high_success_events

        updater = FeedbackPolicyUpdater(mock_memory)
        stats = updater.update_from_feedback()

        mock_memory.set_threshold.assert_called()
        assert stats["boosted"] == 1
        assert stats["updated"] == 1

    def test_threshold_boost_multiple_patterns(self, mock_memory: MagicMock) -> None:
        """Multiple high-success patterns all boosted."""
        events = [
            FeedbackEvent(
                fault_id=f"f{i}",
                anomaly_type="power" if i < 5 else "thermal",
                recovery_action="cycle" if i < 5 else "cool",
                mission_phase="NOMINAL_OPS",
                label=FeedbackLabel.CORRECT,
                confidence_score=0.95,
            )
            for i in range(10)
        ]
        mock_memory.query_feedback_events.return_value = events

        updater = FeedbackPolicyUpdater(mock_memory)
        stats = updater.update_from_feedback()

        assert stats["boosted"] == 2
        assert stats["updated"] == 2


class TestActionSuppression:
    """Test action suppression for low success rates."""

    def test_action_suppression_low_success(self, mock_memory: MagicMock) -> None:
        """Low success (30%-) suppresses action."""
        low_success_events = [
            FeedbackEvent(
                fault_id=f"f{i}",
                anomaly_type="power",
                recovery_action="cycle",
                mission_phase="NOMINAL_OPS",
                label=FeedbackLabel.WRONG,
                confidence_score=0.95,
            )
            for i in range(4)
        ]
        mock_memory.query_feedback_events.return_value = low_success_events

        updater = FeedbackPolicyUpdater(mock_memory)
        stats = updater.update_from_feedback()

        mock_memory.suppress_action.assert_called_with("cycle", "NOMINAL_OPS")
        assert stats["suppressed"] == 1

    def test_no_suppression_medium_success(self, mock_memory: MagicMock) -> None:
        """Medium success (30-70%) doesn't suppress."""
        medium_events = [
            FeedbackEvent(
                fault_id=f"f{i}",
                anomaly_type="power",
                recovery_action="cycle",
                mission_phase="NOMINAL_OPS",
                label=FeedbackLabel.CORRECT if i < 5 else FeedbackLabel.WRONG,
                confidence_score=0.95,
            )
            for i in range(10)
        ]
        mock_memory.query_feedback_events.return_value = medium_events

        updater = FeedbackPolicyUpdater(mock_memory)
        stats = updater.update_from_feedback()

        mock_memory.suppress_action.assert_not_called()
        assert stats["suppressed"] == 0


class TestSafeThresholdBounds:
    """Test threshold clamping (0.1-2.0)."""

    def test_threshold_min_bound(self, mock_memory: MagicMock) -> None:
        """Threshold clamped at 0.1 minimum."""
        mock_memory.get_threshold.return_value = 0.05
        updater = FeedbackPolicyUpdater(mock_memory)
        updater._adjust_threshold("power", "NOMINAL_OPS", -0.1)

        # Should clamp to 0.1
        call_args = mock_memory.set_threshold.call_args
        assert call_args is not None
        assert call_args[0][2] >= 0.1

    def test_threshold_max_bound(self, mock_memory: MagicMock) -> None:
        """Threshold clamped at 2.0 maximum."""
        mock_memory.get_threshold.return_value = 2.5
        updater = FeedbackPolicyUpdater(mock_memory)
        updater._adjust_threshold("power", "NOMINAL_OPS", 0.5)

        # Should clamp to 2.0
        call_args = mock_memory.set_threshold.call_args
        assert call_args is not None
        assert call_args[0][2] <= 2.0

    def test_threshold_safe_increase(self, mock_memory: MagicMock) -> None:
        """Safe increase within bounds."""
        mock_memory.get_threshold.return_value = 1.0
        updater = FeedbackPolicyUpdater(mock_memory)
        updater._adjust_threshold("power", "NOMINAL_OPS", 0.2)

        call_args = mock_memory.set_threshold.call_args
        assert call_args is not None
        # 1.0 * (1 + 0.2) = 1.2
        assert 1.1 < call_args[0][2] < 1.3


class TestDominantPhaseSelection:
    """Test mission phase aggregation."""

    def test_dominant_phase_selection(self, mock_memory: MagicMock) -> None:
        """Most common phase selected."""
        events = [
            FeedbackEvent(
                fault_id=f"f{i}",
                anomaly_type="power",
                recovery_action="cycle",
                mission_phase="NOMINAL_OPS" if i < 7 else "DEPLOYMENT",
                label=FeedbackLabel.CORRECT,
                confidence_score=0.95,
            )
            for i in range(10)
        ]

        updater = FeedbackPolicyUpdater(mock_memory)
        phase = updater._get_dominant_phase(events)
        assert phase == "NOMINAL_OPS"

    def test_default_phase_empty(self, mock_memory: MagicMock) -> None:
        """Default phase for empty events."""
        updater = FeedbackPolicyUpdater(mock_memory)
        phase = updater._get_dominant_phase([])
        assert phase == "NOMINAL_OPS"


class TestPolicyUpdateIntegration:
    """Test full update workflow."""

    def test_update_from_feedback_no_events(self, mock_memory: MagicMock) -> None:
        """No events returns 0 updates."""
        mock_memory.query_feedback_events.return_value = []

        updater = FeedbackPolicyUpdater(mock_memory)
        stats = updater.update_from_feedback()

        assert stats["updated"] == 0
        assert stats["boosted"] == 0
        assert stats["suppressed"] == 0

    def test_update_from_feedback_mixed_patterns(self, mock_memory: MagicMock) -> None:
        """Mixed success rates update appropriately."""
        events = [
            FeedbackEvent(
                fault_id=f"high_{i}",
                anomaly_type="power",
                recovery_action="cycle",
                mission_phase="NOMINAL_OPS",
                label=FeedbackLabel.CORRECT,
                confidence_score=0.95,
            )
            for i in range(8)
        ] + [
            FeedbackEvent(
                fault_id=f"low_{i}",
                anomaly_type="thermal",
                recovery_action="cool",
                mission_phase="NOMINAL_OPS",
                label=FeedbackLabel.WRONG,
                confidence_score=0.95,
            )
            for i in range(4)
        ]
        mock_memory.query_feedback_events.return_value = events

        updater = FeedbackPolicyUpdater(mock_memory)
        stats = updater.update_from_feedback()

        assert stats["updated"] == 2
        assert stats["boosted"] == 1
        assert stats["suppressed"] == 1

    def test_process_policy_updates_public_api(self, mock_memory: MagicMock) -> None:
        """Public API function works."""
        mock_memory.query_feedback_events.return_value = []
        stats = process_policy_updates(mock_memory)

        assert "updated" in stats
        assert "boosted" in stats
        assert "suppressed" in stats

    def test_process_policy_updates_none_memory(self) -> None:
        """Handles None memory gracefully."""
        stats = process_policy_updates(None)

        assert stats["updated"] == 0
        assert stats["boosted"] == 0
        assert stats["suppressed"] == 0


class TestErrorResilience:
    """Test error handling and edge cases."""

    def test_updater_without_memory(self) -> None:
        """Works without memory backend."""
        updater = FeedbackPolicyUpdater(None)
        stats = updater.update_from_feedback()

        assert stats["updated"] == 0

    def test_missing_memory_methods(self, mock_memory: MagicMock) -> None:
        """Now raises informative error for missing memory methods."""
        memory = MagicMock(spec=[])  # Empty spec = no methods
        updater = FeedbackPolicyUpdater(memory)

        from security_engine.error_handling import MemoryOperationError
        with pytest.raises(MemoryOperationError) as exc_info:
            updater.update_from_feedback()

        assert "Memory backend not available" in str(exc_info.value)
        assert "query_feedback_events" in str(exc_info.value)
