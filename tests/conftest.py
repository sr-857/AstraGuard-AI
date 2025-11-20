"""Pytest configuration and fixtures."""
import pytest
import numpy as np
from anomaly.anomaly_detector import train_and_save_model, MODEL_PATH


@pytest.fixture(scope="session", autouse=True)
def ensure_model_exists():
    """Ensure the anomaly detection model is trained before tests run."""
    train_and_save_model()
    assert MODEL_PATH.exists(), "Failed to train and save the model"
    return MODEL_PATH
