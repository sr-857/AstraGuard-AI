"""100% coverage for feedback → memory pinning pipeline."""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock

from security_engine.adaptive_memory import (
    FeedbackPinner,
    process_feedback_after_review,
)
from models.feedback import FeedbackEvent, FeedbackLabel


@pytest.fixture
def mock_memory() -> MagicMock:
    """Create mock AdaptiveMemoryStore."""
    memory = MagicMock()
    memory.pin_event = MagicMock(return_value=None)
    memory.suppress_pattern = MagicMock(return_value=None)
    memory.boost_pattern = MagicMock(return_value=None)
    return memory


class TestWeightMapping:
    """Test FeedbackLabel → weight mapping."""

    def test_weight_correct(self) -> None:
        """CORRECT label has max weight."""
        pinner = FeedbackPinner()
        assert pinner.WEIGHT_MAP[FeedbackLabel.CORRECT] == 10.0

    def test_weight_insufficient(self) -> None:
        """INSUFFICIENT label has medium weight."""
        pinner = FeedbackPinner()
        assert pinner.WEIGHT_MAP[FeedbackLabel.INSUFFICIENT] == 5.0

    def test_weight_wrong(self) -> None:
        """WRONG label has suppression weight."""
        pinner = FeedbackPinner()
        assert pinner.WEIGHT_MAP[FeedbackLabel.WRONG] == 0.1


class TestPinAllFeedback:
    """Test pin_all_feedback() core functionality."""

    def test_no_processed_file(self, mock_memory: MagicMock) -> None:
        """Missing feedback_processed.json returns empty stats."""
        pinner = FeedbackPinner(
            memory=mock_memory, processed_path=Path("nonexistent.json")
        )
        stats = pinner.pin_all_feedback()

        assert stats == {"pinned": 0, "correct": 0, "insufficient": 0, "wrong": 0}
        mock_memory.pin_event.assert_not_called()

    def test_pin_single_correct_event(
        self, tmp_path: Path, mock_memory: MagicMock
    ) -> None:
        """Correct labels get max weight pinning."""
        event = FeedbackEvent(
            fault_id="f001",
            anomaly_type="power",
            recovery_action="cycle",
            label=FeedbackLabel.CORRECT,
            mission_phase="NOMINAL_OPS",
        )

        processed = tmp_path / "feedback_processed.json"
        processed.write_text(json.dumps([json.loads(event.model_dump_json())]))

        pinner = FeedbackPinner(memory=mock_memory, processed_path=processed)
        stats = pinner.pin_all_feedback()

        assert stats == {"pinned": 1, "correct": 1, "insufficient": 0, "wrong": 0}
        mock_memory.pin_event.assert_called_once()
        call_kwargs = mock_memory.pin_event.call_args[1]
        assert call_kwargs["weight"] == 10.0
        assert call_kwargs["event_id"] == "f001"

    def test_pin_insufficient_event(
        self, tmp_path: Path, mock_memory: MagicMock
    ) -> None:
        """INSUFFICIENT label gets medium weight."""
        event = FeedbackEvent(
            fault_id="f002",
            anomaly_type="thermal",
            recovery_action="cooldown",
            label=FeedbackLabel.INSUFFICIENT,
            mission_phase="PAYLOAD_OPS",
        )

        processed = tmp_path / "feedback_processed.json"
        processed.write_text(json.dumps([json.loads(event.model_dump_json())]))

        pinner = FeedbackPinner(memory=mock_memory, processed_path=processed)
        stats = pinner.pin_all_feedback()

        assert stats["insufficient"] == 1
        call_kwargs = mock_memory.pin_event.call_args[1]
        assert call_kwargs["weight"] == 5.0

    def test_pin_wrong_event(self, tmp_path: Path, mock_memory: MagicMock) -> None:
        """WRONG label gets suppression weight."""
        event = FeedbackEvent(
            fault_id="f003",
            anomaly_type="comms",
            recovery_action="reinit",
            label=FeedbackLabel.WRONG,
            mission_phase="SAFE_MODE",
        )

        processed = tmp_path / "feedback_processed.json"
        processed.write_text(json.dumps([json.loads(event.model_dump_json())]))

        pinner = FeedbackPinner(memory=mock_memory, processed_path=processed)
        stats = pinner.pin_all_feedback()

        assert stats["wrong"] == 1
        call_kwargs = mock_memory.pin_event.call_args[1]
        assert call_kwargs["weight"] == 0.1

    def test_pin_multiple_events(self, tmp_path: Path, mock_memory: MagicMock) -> None:
        """Multiple events pinned in sequence."""
        events = [
            FeedbackEvent(
                fault_id=f"f{i:03d}",
                anomaly_type="power",
                recovery_action="cycle",
                label=FeedbackLabel.CORRECT,
                mission_phase="NOMINAL_OPS",
            )
            for i in range(3)
        ]

        processed = tmp_path / "feedback_processed.json"
        processed.write_text(
            json.dumps([json.loads(e.model_dump_json()) for e in events])
        )

        pinner = FeedbackPinner(memory=mock_memory, processed_path=processed)
        stats = pinner.pin_all_feedback()

        assert stats["pinned"] == 3
        assert stats["correct"] == 3
        assert mock_memory.pin_event.call_count == 3

    def test_mixed_labels_stats(self, tmp_path: Path, mock_memory: MagicMock) -> None:
        """Mixed labels accumulate correct stats."""
        events = [
            FeedbackEvent(
                fault_id="f001",
                anomaly_type="power",
                recovery_action="cycle",
                label=FeedbackLabel.CORRECT,
                mission_phase="NOMINAL_OPS",
            ),
            FeedbackEvent(
                fault_id="f002",
                anomaly_type="thermal",
                recovery_action="cooldown",
                label=FeedbackLabel.INSUFFICIENT,
                mission_phase="PAYLOAD_OPS",
            ),
            FeedbackEvent(
                fault_id="f003",
                anomaly_type="comms",
                recovery_action="reinit",
                label=FeedbackLabel.WRONG,
                mission_phase="SAFE_MODE",
            ),
        ]

        processed = tmp_path / "feedback_processed.json"
        processed.write_text(
            json.dumps([json.loads(e.model_dump_json()) for e in events])
        )

        pinner = FeedbackPinner(memory=mock_memory, processed_path=processed)
        stats = pinner.pin_all_feedback()

        assert stats["pinned"] == 3
        assert stats["correct"] == 1
        assert stats["insufficient"] == 1
        assert stats["wrong"] == 1


class TestFileCleanup:
    """Test atomic file cleanup after pinning."""

    def test_cleanup_processed_file(
        self, tmp_path: Path, mock_memory: MagicMock
    ) -> None:
        """processed.json deleted after pinning."""
        event = FeedbackEvent(
            fault_id="f001",
            anomaly_type="power",
            recovery_action="cycle",
            label=FeedbackLabel.CORRECT,
            mission_phase="NOMINAL_OPS",
        )

        processed = tmp_path / "feedback_processed.json"
        processed.write_text(json.dumps([json.loads(event.model_dump_json())]))

        pinner = FeedbackPinner(memory=mock_memory, processed_path=processed)
        pinner.pin_all_feedback()

        assert not processed.exists()

    def test_cleanup_pending_file(self, tmp_path: Path, mock_memory: MagicMock) -> None:
        """pending.json also cleaned up."""
        event = FeedbackEvent(
            fault_id="f001",
            anomaly_type="power",
            recovery_action="cycle",
            label=FeedbackLabel.CORRECT,
            mission_phase="NOMINAL_OPS",
        )

        # Create both files
        processed = tmp_path / "feedback_processed.json"
        processed.write_text(json.dumps([json.loads(event.model_dump_json())]))
        pending = tmp_path / "feedback_pending.json"
        pending.write_text("[]")

        # Change to tmp_path so unlink finds pending.json
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            pinner = FeedbackPinner(memory=mock_memory, processed_path=processed)
            pinner.pin_all_feedback()

            assert not pending.exists()
        finally:
            os.chdir(old_cwd)


class TestResonanceUpdates:
    """Test pattern resonance boost/suppress."""

    def test_boost_pattern_correct(
        self, tmp_path: Path, mock_memory: MagicMock
    ) -> None:
        """Correct events boost resonance patterns."""
        event = FeedbackEvent(
            fault_id="f001",
            anomaly_type="power",
            recovery_action="cycle",
            label=FeedbackLabel.CORRECT,
            confidence_score=1.0,
            mission_phase="NOMINAL_OPS",
        )

        processed = tmp_path / "feedback_processed.json"
        processed.write_text(json.dumps([json.loads(event.model_dump_json())]))

        pinner = FeedbackPinner(memory=mock_memory, processed_path=processed)
        pinner.pin_all_feedback()

        mock_memory.boost_pattern.assert_called_once()
        call_args = mock_memory.boost_pattern.call_args
        pattern = call_args[0][0]
        assert pattern == "power:cycle"

    def test_suppress_pattern_wrong(
        self, tmp_path: Path, mock_memory: MagicMock
    ) -> None:
        """Wrong events suppress resonance patterns."""
        event = FeedbackEvent(
            fault_id="f001",
            anomaly_type="power",
            recovery_action="cycle",
            label=FeedbackLabel.WRONG,
            mission_phase="NOMINAL_OPS",
        )

        processed = tmp_path / "feedback_processed.json"
        processed.write_text(json.dumps([json.loads(event.model_dump_json())]))

        pinner = FeedbackPinner(memory=mock_memory, processed_path=processed)
        pinner.pin_all_feedback()

        mock_memory.suppress_pattern.assert_called_once()
        call_args = mock_memory.suppress_pattern.call_args
        pattern = call_args[0][0]
        assert pattern == "power:cycle"

    def test_no_resonance_no_memory(self, tmp_path: Path) -> None:
        """No resonance updates if memory is None."""
        event = FeedbackEvent(
            fault_id="f001",
            anomaly_type="power",
            recovery_action="cycle",
            label=FeedbackLabel.CORRECT,
            mission_phase="NOMINAL_OPS",
        )

        processed = tmp_path / "feedback_processed.json"
        processed.write_text(json.dumps([json.loads(event.model_dump_json())]))

        pinner = FeedbackPinner(memory=None, processed_path=processed)
        stats = pinner.pin_all_feedback()

        # Should still return stats even without memory
        assert stats["pinned"] == 1


class TestProcessFeedbackHook:
    """Test public API integration hook."""

    def test_process_feedback_after_review(
        self, tmp_path: Path, mock_memory: MagicMock
    ) -> None:
        """process_feedback_after_review() calls pin_all_feedback()."""
        event = FeedbackEvent(
            fault_id="f001",
            anomaly_type="power",
            recovery_action="cycle",
            label=FeedbackLabel.CORRECT,
            mission_phase="NOMINAL_OPS",
        )

        processed = tmp_path / "feedback_processed.json"
        processed.write_text(json.dumps([json.loads(event.model_dump_json())]))

        # Patch the path used by FeedbackPinner
        import security_engine.adaptive_memory as am

        original_path = am.Path
        try:
            am.Path = lambda p: (
                processed if str(p) == "feedback_processed.json" else original_path(p)
            )
            stats = process_feedback_after_review(mock_memory)

            assert stats["pinned"] == 1
            mock_memory.pin_event.assert_called_once()
        finally:
            am.Path = original_path


class TestInvalidInput:
    """Test error handling for invalid input."""

    def test_invalid_json_returns_empty(
        self, tmp_path: Path, mock_memory: MagicMock
    ) -> None:
        """Corrupted JSON now raises informative error with actionable suggestions."""
        processed = tmp_path / "feedback_processed.json"
        processed.write_text("invalid json {")

        pinner = FeedbackPinner(memory=mock_memory, processed_path=processed)

        from security_engine.error_handling import FeedbackValidationError
        with pytest.raises(FeedbackValidationError) as exc_info:
            pinner.pin_all_feedback()

        assert "Corrupted feedback file" in str(exc_info.value)
        assert "feedback_processed.json" in str(exc_info.value)
        mock_memory.pin_event.assert_not_called()

    def test_non_list_json_returns_empty(
        self, tmp_path: Path, mock_memory: MagicMock
    ) -> None:
        """Non-list JSON now raises informative error with actionable suggestions."""
        processed = tmp_path / "feedback_processed.json"
        processed.write_text(json.dumps({"not": "list"}))

        pinner = FeedbackPinner(memory=mock_memory, processed_path=processed)

        from security_engine.error_handling import FeedbackValidationError
        with pytest.raises(FeedbackValidationError) as exc_info:
            pinner.pin_all_feedback()

        assert "Feedback format validation failed" in str(exc_info.value)
        assert "Expected list of feedback events" in str(exc_info.value)
        mock_memory.pin_event.assert_not_called()
