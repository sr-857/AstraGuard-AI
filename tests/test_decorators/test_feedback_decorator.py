"""100% coverage test suite for @log_feedback decorator and thread safety."""
import pytest
import json
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

from security_engine.decorators import log_feedback, ThreadSafeFeedbackStore
from models.feedback import FeedbackEvent, FeedbackLabel


class TestThreadSafeFeedbackStore:
    """Test ThreadSafeFeedbackStore atomic operations."""

    def test_append_single_event(self):
        """Store can append and retrieve single event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            event = FeedbackEvent(
                fault_id="f1",
                anomaly_type="test",
                recovery_action="test_action",
                mission_phase="NOMINAL_OPS",
                label=FeedbackLabel.CORRECT,
            )
            store.append(event)

            data = json.loads((Path(tmpdir) / "test.json").read_text())
            assert len(data) == 1
            assert data[0]["fault_id"] == "f1"

    def test_append_multiple_events(self):
        """Store preserves multiple appends."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            for i in range(5):
                event = FeedbackEvent(
                    fault_id=f"f{i}",
                    anomaly_type="test",
                    recovery_action="test_action",
                    mission_phase="NOMINAL_OPS",
                    label=FeedbackLabel.CORRECT,
                )
                store.append(event)

            data = json.loads((Path(tmpdir) / "test.json").read_text())
            assert len(data) == 5

    def test_load_corrupted_json_creates_new(self):
        """Corrupted JSON is treated as empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.json"
            path.write_text("invalid json {")
            store = ThreadSafeFeedbackStore(path)
            event = FeedbackEvent(
                fault_id="f1",
                anomaly_type="test",
                recovery_action="test_action",
                mission_phase="NOMINAL_OPS",
                label=FeedbackLabel.CORRECT,
            )
            store.append(event)

            data = json.loads(path.read_text())
            assert len(data) == 1


class TestLogFeedbackDecorator:
    """Test @log_feedback decorator functionality."""

    def test_decorator_preserves_return_true(self):
        """Decorator returns True when function returns True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                @log_feedback("f1", "test")
                def success():
                    return True

                result = success()
                assert result is True

    def test_decorator_preserves_return_false(self):
        """Decorator returns False when function returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                @log_feedback("f1", "test")
                def failure():
                    return False

                result = failure()
                assert result is False

    def test_decorator_preserves_return_none(self):
        """Decorator returns None when function returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                @log_feedback("f1", "test")
                def no_return():
                    pass

                result = no_return()
                assert result is None

    @pytest.mark.parametrize("return_value", [True, False, None, "string", 42, []])
    def test_all_return_types_preserved(self, return_value):
        """Decorator never modifies return values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                @log_feedback("f1", "test")
                def dummy():
                    return return_value

                result = dummy()
                assert result == return_value

    def test_decorator_captures_feedback_success(self):
        """Successful execution logs FeedbackEvent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                @log_feedback("f1", "test_type")
                def success():
                    return True

                success()
                data = json.loads((Path(tmpdir) / "test.json").read_text())
                assert len(data) == 1
                assert data[0]["fault_id"] == "f1"
                assert data[0]["anomaly_type"] == "test_type"

    def test_decorator_confidence_success(self):
        """Successful execution sets confidence_score to 1.0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                @log_feedback("f1", "test")
                def success():
                    return True

                success()
                data = json.loads((Path(tmpdir) / "test.json").read_text())
                assert data[0]["confidence_score"] == 1.0

    def test_decorator_confidence_failure(self):
        """Failed execution sets confidence_score to 0.5."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                @log_feedback("f1", "test")
                def failure():
                    return False

                failure()
                data = json.loads((Path(tmpdir) / "test.json").read_text())
                assert data[0]["confidence_score"] == 0.5

    def test_decorator_with_args(self):
        """Decorator works with function arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                @log_feedback("f1", "test")
                def with_args(a, b, c=None):
                    return a + b

                result = with_args(1, 2, c=3)
                assert result == 3

    def test_decorator_error_non_blocking(self):
        """Decorator errors don't prevent exception propagation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                @log_feedback("f1", "test")
                def raises_error():
                    raise ValueError("Test error")

                with pytest.raises(ValueError):
                    raises_error()

    def test_decorator_default_mission_phase(self):
        """Decorator uses NOMINAL_OPS as default mission_phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                @log_feedback("f1", "test")
                def dummy():
                    return True

                dummy()
                data = json.loads((Path(tmpdir) / "test.json").read_text())
                assert data[0]["mission_phase"] == "NOMINAL_OPS"

    def test_decorator_label_correct(self):
        """Label set to correct on success."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                @log_feedback("f1", "test")
                def success():
                    return True

                success()
                data = json.loads((Path(tmpdir) / "test.json").read_text())
                assert data[0]["label"] == "correct"

    def test_decorator_label_wrong(self):
        """Label set to wrong on failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                @log_feedback("f1", "test")
                def failure():
                    return False

                failure()
                data = json.loads((Path(tmpdir) / "test.json").read_text())
                assert data[0]["label"] == "wrong"


class TestThreadSafety:
    """Test concurrent access patterns."""

    def test_concurrent_appends(self):
        """Multiple threads can safely append events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")

            def append_events(thread_id):
                for i in range(10):
                    event = FeedbackEvent(
                        fault_id=f"f{thread_id}_{i}",
                        anomaly_type="test",
                        recovery_action="test_action",
                        mission_phase="NOMINAL_OPS",
                        label=FeedbackLabel.CORRECT,
                    )
                    store.append(event)

            threads = [
                threading.Thread(target=append_events, args=(tid,))
                for tid in range(5)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            data = json.loads((Path(tmpdir) / "test.json").read_text())
            assert len(data) == 50

    def test_decorator_concurrent_calls(self):
        """Decorator maintains atomicity under concurrent load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                @log_feedback("f1", "test")
                def dummy():
                    return True

                threads = [
                    threading.Thread(target=dummy) for _ in range(20)
                ]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

                data = json.loads((Path(tmpdir) / "test.json").read_text())
                assert len(data) == 20

class TestLoadNonListJSON:
    """Test edge case where JSON file contains non-list data."""

    def test_load_dict_json_returns_empty(self):
        """_load() returns empty list when JSON is a dict, not list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.json"
            # Write a dict instead of list to JSON
            path.write_text('{"key": "value"}')
            store = ThreadSafeFeedbackStore(path)
            
            # When we append, it should treat the file as empty
            event = FeedbackEvent(
                fault_id="f1",
                anomaly_type="test",
                recovery_action="test_action",
                mission_phase="NOMINAL_OPS",
                label=FeedbackLabel.CORRECT,
            )
            store.append(event)

            # File should now contain a list with one event
            data = json.loads(path.read_text())
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["fault_id"] == "f1"

    def test_load_string_json_returns_empty(self):
        """_load() returns empty list when JSON is a string, not list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.json"
            # Write a string JSON value
            path.write_text('"just a string"')
            store = ThreadSafeFeedbackStore(path)
            
            event = FeedbackEvent(
                fault_id="f2",
                anomaly_type="test",
                recovery_action="test_action",
                mission_phase="NOMINAL_OPS",
                label=FeedbackLabel.CORRECT,
            )
            store.append(event)

            data = json.loads(path.read_text())
            assert isinstance(data, list)
            assert len(data) == 1


class TestDecoratorExceptionHandling:
    """Test exception handling paths in decorator."""

    def test_decorator_function_exception_logs_feedback(self):
        """When decorated function raises, feedback still logged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                @log_feedback("f_error", "error_type")
                def raises_runtime_error():
                    raise RuntimeError("Intentional error")

                with pytest.raises(RuntimeError):
                    raises_runtime_error()

                # Check that error feedback was logged
                data = json.loads((Path(tmpdir) / "test.json").read_text())
                assert len(data) == 1
                assert data[0]["fault_id"] == "f_error"
                assert data[0]["label"] == "wrong"
                assert data[0]["confidence_score"] == 0.0

    def test_decorator_exception_with_mission_phase_attribute(self):
        """Exception path extracts mission_phase from first arg."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                class MockState:
                    mission_phase = "PAYLOAD_OPS"

                @log_feedback("f_mission", "test")
                def error_with_state(state):
                    raise ValueError("Test")

                with pytest.raises(ValueError):
                    error_with_state(MockState())

                data = json.loads((Path(tmpdir) / "test.json").read_text())
                assert len(data) == 1
                assert data[0]["mission_phase"] == "PAYLOAD_OPS"

    def test_decorator_exception_invalid_mission_phase_defaults(self):
        """Invalid mission_phase in exception path defaults to NOMINAL_OPS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                class MockState:
                    mission_phase = "INVALID_PHASE"

                @log_feedback("f_invalid", "test")
                def error_with_invalid_state(state):
                    raise ValueError("Test")

                with pytest.raises(ValueError):
                    error_with_invalid_state(MockState())

                data = json.loads((Path(tmpdir) / "test.json").read_text())
                assert data[0]["mission_phase"] == "NOMINAL_OPS"

    def test_decorator_exception_with_nested_error_on_feedback_logging(self):
        """When exception occurs and feedback logging also fails, exception still propagates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):
                # Make store.append fail to simulate feedback logging error
                store.append = lambda x: (_ for _ in ()).throw(IOError("Disk full"))

                @log_feedback("f_nested", "test")
                def raises_then_fails_feedback():
                    raise ValueError("Original error")

                # Should raise the original ValueError, not the IOError
                with pytest.raises(ValueError):
                    raises_then_fails_feedback()

    def test_decorator_with_none_mission_phase_attribute(self):
        """Mission phase None is handled in exception path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                class MockState:
                    mission_phase = None

                @log_feedback("f_none", "test")
                def error_with_none_phase(state):
                    raise ValueError("Test")

                with pytest.raises(ValueError):
                    error_with_none_phase(MockState())

                data = json.loads((Path(tmpdir) / "test.json").read_text())
                assert data[0]["mission_phase"] == "NOMINAL_OPS"

    def test_decorator_success_with_valid_mission_phases(self):
        """Success path handles all valid mission phases correctly."""
        valid_phases = ["LAUNCH", "DEPLOYMENT", "NOMINAL_OPS", "PAYLOAD_OPS", "SAFE_MODE"]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ThreadSafeFeedbackStore(Path(tmpdir) / "test.json")
            with patch("security_engine.decorators._pending_store", store):

                class MockState:
                    def __init__(self, phase):
                        self.mission_phase = phase

                for phase in valid_phases:
                    @log_feedback("f_phase", "test")
                    def success_with_phase(state):
                        return True

                    success_with_phase(MockState(phase))

                data = json.loads((Path(tmpdir) / "test.json").read_text())
                assert len(data) == len(valid_phases)
                for i, phase in enumerate(valid_phases):
                    assert data[i]["mission_phase"] == phase