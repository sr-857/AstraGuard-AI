"""
AstraGuard AI - Autonomous Fault Detection & Recovery System for CubeSats

This package provides real-time telemetry monitoring, anomaly detection,
and autonomous recovery capabilities for CubeSat spacecraft.
"""

__version__ = "1.0.0"
__author__ = "Subhajit Roy"
__email__ = "your.email@example.com"

# Import key components for easier access
from .telemetry import TelemetryStream  # noqa: F401

__all__ = ["TelemetryStream"]
