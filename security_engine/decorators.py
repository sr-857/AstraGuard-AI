"""Thread-safe decorator for automatic feedback event capture."""

from functools import wraps
from typing import Callable, Any, Optional, TypeVar
from datetime import datetime
import json
import threading
import logging
from pathlib import Path

from models.feedback import FeedbackEvent, FeedbackLabel

logger = logging.getLogger(__name__)

# Type variable for generic callable
F = TypeVar("F", bound=Callable[..., Any])


class ThreadSafeFeedbackStore:
    """Atomic pending events storage with thread-safe operations."""

    def __init__(self, path: Path = Path("feedback_pending.json")):
        self.path = path
        self.lock = threading.Lock()

    def append(self, event: FeedbackEvent) -> None:
        """Thread-safely append event to pending store."""
        with self.lock:
            try:
                pending = self._load()
            except (FileNotFoundError, json.JSONDecodeError):
                pending = []
            pending.append(json.loads(event.model_dump_json()))
            self._dump(pending)

    def _load(self) -> list[Any]:
        """Load pending events from disk."""
        with open(self.path, "r") as f:
            data = json.loads(f.read())
            if isinstance(data, list):
                return data
            return []

    def _dump(self, events: list[Any]) -> None:
        """Write pending events to disk (compact format)."""
        with open(self.path, "w") as f:
            json.dump(events, f, separators=(",", ":"))


_pending_store = ThreadSafeFeedbackStore()


def log_feedback(fault_id: str, anomaly_type: str = "unknown") -> Callable[[F], F]:
    """Decorator: Auto-capture recovery action → FeedbackEvent → pending store.

    Args:
        fault_id: Identifier for the fault being recovered from
        anomaly_type: Type of anomaly (e.g., "power_subsystem", "thermal")

    Returns:
        Decorator function that wraps recovery actions

    Example:
        @log_feedback(fault_id="power_loss_", anomaly_type="power_subsystem")
        def emergency_power_cycle(system_state):
            return True  # Recovery success
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result: Any = None  # Initialize result
            error_to_raise: Optional[Exception] = None

            try:
                # Extract mission_phase from first arg if it has the attribute
                mission_phase = "NOMINAL_OPS"
                if args and hasattr(args[0], "mission_phase"):
                    mp = args[0].mission_phase
                    # Ensure mission_phase is a string (handle mock objects)
                    mission_phase = str(mp) if mp else "NOMINAL_OPS"
                    # Validate against allowed values
                    if mission_phase not in (
                        "LAUNCH",
                        "DEPLOYMENT",
                        "NOMINAL_OPS",
                        "PAYLOAD_OPS",
                        "SAFE_MODE",
                    ):
                        mission_phase = "NOMINAL_OPS"

                # Execute the wrapped recovery function
                result = func(*args, **kwargs)
                success = result is True if isinstance(result, bool) else True

                # Auto-create pending FeedbackEvent
                event = FeedbackEvent(
                    fault_id=fault_id,
                    anomaly_type=anomaly_type,
                    recovery_action=func.__name__,
                    mission_phase=mission_phase,
                    label=FeedbackLabel.CORRECT if success else FeedbackLabel.WRONG,
                    confidence_score=1.0 if success else 0.5,
                    operator_notes=None,
                )

                _pending_store.append(event)
                # Silent logging - don't spam console

            except Exception as e:
                # Capture ANY exception but continue to feedback logging attempt
                error_to_raise = e
                # Only log specific exception types to avoid noise
                if isinstance(e, (IOError, json.JSONDecodeError, TypeError)):
                    logger.debug(f"Function {func.__name__} raised exception: {type(e).__name__}: {e}")

                # Try to log failure feedback even if function raised
                try:
                    mission_phase = "NOMINAL_OPS"
                    if args and hasattr(args[0], "mission_phase"):
                        mp = args[0].mission_phase
                        mission_phase = str(mp) if mp else "NOMINAL_OPS"
                        if mission_phase not in (
                            "LAUNCH",
                            "DEPLOYMENT",
                            "NOMINAL_OPS",
                            "PAYLOAD_OPS",
                            "SAFE_MODE",
                        ):
                            mission_phase = "NOMINAL_OPS"

                    event = FeedbackEvent(
                        fault_id=fault_id,
                        anomaly_type=anomaly_type,
                        recovery_action=func.__name__,
                        mission_phase=mission_phase,
                        label=FeedbackLabel.WRONG,  # Failure to execute
                        confidence_score=0.0,
                        operator_notes=None,
                    )
                    _pending_store.append(event)
                except (IOError, json.JSONDecodeError) as e:
                    # Non-blocking: log but don't raise feedback logging errors
                    logger.debug(
                        f"Failed to log feedback for {func.__name__}: "
                        f"{type(e).__name__}: {e}"
                    )

            if error_to_raise:
                raise error_to_raise

            return result  # Never break recovery flow

        return wrapper  # type: ignore[return-value]

    return decorator
