"""Tests for the anomaly detection module."""
import numpy as np
import pytest
from anomaly.anomaly_detector import (
    detect_anomaly,
    validate_telemetry,
    dict_to_features
)


def test_dict_to_features():
    """Test conversion of telemetry dict to feature array."""
    telemetry = {
        "voltage": 7.9,
        "current": 0.55,
        "temperature": 25.0,
        "gyro": 0.1,
        "wheel_speed": 3000.0
    }
    expected = np.array([[7.9, 0.55, 25.0, 0.1, 3000.0]])
    result = dict_to_features(telemetry)
    np.testing.assert_array_almost_equal(result, expected)


def test_validate_telemetry():
    """Test telemetry validation with valid and invalid data."""
    # Test valid telemetry
    valid_telemetry = {
        "voltage": 7.9,
        "current": 0.55,
        "temperature": 25.0,
        "gyro": 0.1,
        "wheel_speed": 3000.0
    }
    result = validate_telemetry(valid_telemetry)
    assert result["is_valid"] is True
    
    # Test invalid telemetry (voltage too low)
    invalid_telemetry = valid_telemetry.copy()
    invalid_telemetry["voltage"] = 5.0
    result = validate_telemetry(invalid_telemetry)
    assert result["is_valid"] is False
    assert "voltage" in result["errors"]


# This is a basic test - in a real scenario, we'd mock the model
# or use a test fixture with pre-trained weights
def test_detect_anomaly():
    """Test anomaly detection with basic input validation."""
    # Create a test telemetry sample
    telemetry = {
        "voltage": 7.9,
        "current": 0.55,
        "temperature": 25.0,
        "gyro": 0.1,
        "wheel_speed": 3000.0
    }
    
    # Just test that the function runs and returns expected types
    is_anomalous, score = detect_anomaly(telemetry)
    assert isinstance(is_anomalous, bool)
    assert isinstance(score, float)
