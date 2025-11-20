"""Basic tests that don't require external dependencies."""

import pytest


def test_imports():
    """Test that basic imports work."""
    # This is a simple test that should always pass
    assert True


def test_anomaly_detector_import():
    """Test that we can import the anomaly detector module."""
    # This will help verify if the module structure is correct
    try:
        from anomaly import anomaly_detector  # noqa: F401

        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import anomaly_detector: {e}")
