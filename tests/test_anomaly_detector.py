import pytest
from anomaly.anomaly_detector import detect_anomaly


def test_anomaly_detector_normal():
    state = {
        "voltage": 7.9,
        "current": 0.55,
        "temperature": 24.0,
        "gyro": 0.01,
        "wheel_speed": 480,
    }
    is_anomalous, score = detect_anomaly(state)
    assert is_anomalous in [True, False]
    assert isinstance(score, float)


def test_anomaly_detector_fault():
    state = {
        "voltage": 6.2,
        "current": 0.55,
        "temperature": 36.4,
        "gyro": 0.12,
        "wheel_speed": None,
    }
    is_anomalous, score = detect_anomaly(state)
    assert is_anomalous in [True, False]
    assert isinstance(score, float)
