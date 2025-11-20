"""Tests for the anomaly detection module."""

import numpy as np
from unittest.mock import patch, MagicMock
from anomaly.anomaly_detector import (
    validate_telemetry,
    dict_to_features,
    detect_anomaly,
)


def test_dict_to_features():
    """Test conversion of telemetry dict to feature array."""
    telemetry = {
        "voltage": 7.9,
        "current": 0.55,
        "temperature": 25.0,
        "gyro": 0.1,
        "wheel_speed": 480.0,
    }
    result = dict_to_features(telemetry)
    # Verify the result is a numpy array with the correct shape and values
    assert isinstance(result, np.ndarray)
    assert result.shape == (1, 5)  # Should be a 2D array with 1 row and 5 columns
    assert np.allclose(result[0], [7.9, 0.55, 25.0, 0.1, 480.0])


def test_validate_telemetry():
    """Test telemetry validation with valid and invalid data."""
    # Test valid telemetry (within normal ranges)
    valid_telemetry = {
        "voltage": 7.9,
        "current": 0.55,
        "temperature": 24.0,
        "gyro": 0.01,
        "wheel_speed": 480.0,
    }
    # Test valid telemetry
    result = validate_telemetry(valid_telemetry)
    assert result["valid"] is True
    assert result["out_of_range"] == []
    assert result["missing_values"] == []
    # Test invalid telemetry (voltage too low)
    invalid_telemetry = valid_telemetry.copy()
    invalid_telemetry["voltage"] = 5.0
    result = validate_telemetry(invalid_telemetry)
    assert result["valid"] is False
    assert "voltage" in result["out_of_range"]
    # Test missing value
    missing_telemetry = valid_telemetry.copy()
    del missing_telemetry["voltage"]
    result = validate_telemetry(missing_telemetry)
    assert result["valid"] is False
    assert "voltage" in result["missing_values"]


@patch("anomaly.anomaly_detector.load_model")
def test_detect_anomaly(mock_load_model):
    """Test anomaly detection with mocked model."""
    # Setup mock model
    mock_model = MagicMock()
    mock_model.predict.return_value = [-1]  # -1 indicates anomaly
    mock_model.decision_function.return_value = [-0.5]  # Some score
    mock_load_model.return_value = mock_model
    # Test data
    telemetry = {
        "voltage": 7.9,
        "current": 0.55,
        "temperature": 25.0,
        "gyro": 0.1,
        "wheel_speed": 3000.0,
    }
    # Test detection
    is_anomalous, score = detect_anomaly(telemetry)
    # Verify results
    assert isinstance(is_anomalous, bool)
    assert isinstance(score, float)
    mock_load_model.assert_called_once()
    mock_model.predict.assert_called_once()
    mock_model.decision_function.assert_called_once()
    assert isinstance(is_anomalous, bool)
    assert isinstance(score, float)
    mock_load_model.assert_called_once()
    mock_model.predict.assert_called_once()
    mock_model.decision_function.assert_called_once()
