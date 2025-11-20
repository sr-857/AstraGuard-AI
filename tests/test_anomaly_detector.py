"""Tests for the anomaly detection module."""
import pytest
from unittest.mock import patch, MagicMock
from anomaly.anomaly_detector import (
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
    # Test with mock numpy
    with patch('numpy.array') as mock_array:
        mock_array.return_value = [[7.9, 0.55, 25.0, 0.1, 3000.0]]
        result = dict_to_features(telemetry)
        assert mock_array.called
        # Verify the values are in the expected order
        args = mock_array.call_args[0][0]
        assert args[0] == 7.9      # voltage
        assert args[1] == 0.55     # current
        assert args[2] == 25.0     # temperature
        assert args[3] == 0.1      # gyro
        assert args[4] == 3000.0   # wheel_speed


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


@patch('anomaly.anomaly_detector.load_model')
def test_detect_anomaly(mock_load_model):
    """Test anomaly detection with mocked model."""
    # Setup mock model
    mock_model = MagicMock()
    mock_model.predict.return_value = [-1]  # -1 indicates anomaly
    mock_model.decision_function.return_value = [-0.5]  # Some score
    mock_load_model.return_value = mock_model
    
    # Import here to avoid loading sklearn during test collection
    from anomaly.anomaly_detector import detect_anomaly
    
    # Test data
    telemetry = {
        "voltage": 7.9,
        "current": 0.55,
        "temperature": 25.0,
        "gyro": 0.1,
        "wheel_speed": 3000.0
    }
    
    # Test detection
    is_anomalous, score = detect_anomaly(telemetry)
    
    # Verify results
    assert isinstance(is_anomalous, bool)
    assert isinstance(score, float)
    mock_load_model.assert_called_once()
    mock_model.predict.assert_called_once()
    mock_model.decision_function.assert_called_once()
