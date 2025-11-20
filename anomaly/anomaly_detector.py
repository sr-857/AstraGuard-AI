#!/usr/bin/env python3
# Anomaly Detection Module for AstraGuard AI
"""
This module implements machine learning-based anomaly detection using
Isolation Forest algorithm to identify unusual telemetry patterns.

Author: Subhajit Roy
"""

import os
import pickle
from typing import Tuple

import numpy as np
from sklearn.ensemble import IsolationForest

# Constants
MODEL_PATH = os.path.join(os.path.dirname(__file__), "anomaly_if.pkl")
FEATURE_ORDER = ["voltage", "current", "temperature", "gyro", "wheel_speed"]
NORMAL_RANGES = {
    "voltage": (7.8, 8.0),
    "current": (0.5, 0.6),
    "temperature": (20, 28),
    "gyro": (-0.05, 0.05),
    "wheel_speed": (470, 490),
}


def synthesize_normal(n_samples: int = 1000) -> np.ndarray:
    """Generate synthetic normal telemetry data for training.

    Args:
        n_samples: Number of samples to generate

    Returns:
        numpy array of shape (n_samples, 5) with normal telemetry data
    """
    np.random.seed(42)  # For reproducible training data

    # Generate normal telemetry based on realistic CubeSat parameters
    voltage = np.random.normal(7.9, 0.03, n_samples)
    current = np.random.normal(0.55, 0.01, n_samples)
    temperature = np.random.normal(24, 0.4, n_samples)
    gyro = np.random.normal(0, 0.015, n_samples)
    wheel_speed = np.random.normal(480, 4, n_samples)
    X = np.vstack([voltage, current, temperature, gyro, wheel_speed]).T
    return X


def train_and_save_model() -> None:
    """Train Isolation Forest model on normal data and save to disk."""
    print("Training anomaly detection model...")

    # Generate training data
    X_train = synthesize_normal(2000)

    # Train Isolation Forest model
    model = IsolationForest(
        contamination=0.01,  # Expected anomaly rate
        random_state=42,
        n_estimators=100,
        max_samples="auto",
    )
    model.fit(X_train)

    # Save model
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"Model saved to {MODEL_PATH}")
    print(f"Training completed with {X_train.shape[0]} samples")


def load_model() -> IsolationForest:
    """Load trained model from disk, training if necessary.

    Returns:
        Trained Isolation Forest model
    """
    if not os.path.exists(MODEL_PATH):
        train_and_save_model()

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    return model


def dict_to_features(telemetry_dict: dict) -> np.ndarray:
    """Convert telemetry dictionary to feature array in correct order.

    Args:
        telemetry_dict: Dictionary with telemetry values

    Returns:
        numpy array of shape (1, 5) with features in correct order
    """
    features = []
    for feature_name in FEATURE_ORDER:
        value = telemetry_dict.get(feature_name, 0)
        if value is None:
            value = 0  # Will be detected as anomalous
        features.append(float(value))
    return np.array(features).reshape(1, -1)


def detect_anomaly(telemetry_sample: dict) -> Tuple[bool, float]:
    """Detect if telemetry sample is anomalous.

    Args:
        telemetry_sample: Dictionary containing telemetry values

    Returns:
        Tuple of (is_anomalous, anomaly_score)
        - is_anomalous: True if sample is anomalous
        - anomaly_score: Lower values indicate more anomalous (negative = anomaly)
    """
    try:
        model = load_model()
        X = dict_to_features(telemetry_sample)

        # Get anomaly score and prediction
        anomaly_score = model.decision_function(X)[0]
        prediction = model.predict(X)[0]  # -1 for anomaly, 1 for normal

        is_anomalous = prediction == -1

        return bool(is_anomalous), float(anomaly_score)

    except Exception as e:
        print(f"Error in anomaly detection: {e}")
        # Default to anomalous on error for safety
        return True, -1.0


def validate_telemetry(telemetry_dict: dict) -> dict:
    """Validate telemetry values against expected ranges.

    Args:
        telemetry_dict: Dictionary with telemetry values

    Returns:
        Dictionary with validation results
    """
    validation_results = {"valid": True, "out_of_range": [], "missing_values": []}

    for feature, (min_val, max_val) in NORMAL_RANGES.items():
        value = telemetry_dict.get(feature)

        if value is None:
            validation_results["missing_values"].append(feature)
            validation_results["valid"] = False
        elif not (min_val <= value <= max_val):
            validation_results["out_of_range"].append(feature)
            validation_results["valid"] = False

    return validation_results


def main() -> None:
    """Main function to train and test the anomaly detection model."""
    try:
        # Train model
        train_and_save_model()

        # Test with some samples
        print("\nTesting anomaly detection:")

        # Normal sample
        normal_sample = {
            "voltage": 7.9,
            "current": 0.55,
            "temperature": 24,
            "gyro": 0.01,
            "wheel_speed": 480,
        }

        is_anom, score = detect_anomaly(normal_sample)
        print(f"Normal sample - Anomalous: {is_anom}, Score: {score:.3f}")

        # Anomalous sample
        anomalous_sample = {
            "voltage": 6.5,  # Low voltage
            "current": 0.55,
            "temperature": 24,
            "gyro": 0.01,
            "wheel_speed": 480,
        }

        is_anom, score = detect_anomaly(anomalous_sample)
        print(f"Anomalous sample - Anomalous: {is_anom}, Score: {score:.3f}")

    except Exception as e:
        print(f"Error in main: {e}")


if __name__ == "__main__":
    main()
