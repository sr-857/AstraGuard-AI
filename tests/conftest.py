"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Skip tests if sklearn is not available
try:
    import sklearn  # noqa: F401
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

pytest_plugins = []

# Only add the mock_anomaly_detector fixture if sklearn is available
if SKLEARN_AVAILABLE:

    # Mock the model loading in the anomaly detector module
    @pytest.fixture(autouse=True)
    def mock_anomaly_detector():
        """Mock the anomaly detector module to avoid loading real models."""
        with patch("anomaly.anomaly_detector.load_model", MagicMock()), patch(
            "anomaly.anomaly_detector.detect_anomaly", MagicMock(return_value=(False, 0.05))
        ):
            yield