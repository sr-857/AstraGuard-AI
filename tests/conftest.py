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
        with patch("anomaly.anomaly_detector.load_model") as mock_load_model:
            # Create a mock model
            mock_model = MagicMock()
            mock_model.predict.return_value = [-1]  # Default to anomaly
            mock_model.decision_function.return_value = [-0.5]  # Some score
            mock_load_model.return_value = mock_model

            # Mock the model path
            with patch(
                "anomaly.anomaly_detector.MODEL_PATH", Path("/tmp/mock_model.pkl")
            ):
                yield {"mock_model": mock_model, "mock_load_model": mock_load_model}
