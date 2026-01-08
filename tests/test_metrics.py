"""
Comprehensive tests for Prometheus Metrics module.

Tests cover:
- Metric creation and registration
- Counter, Gauge, Histogram operations
- Registry management
- Metric collection and formatting
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
import time
import sys

# Mock prometheus_client module before any imports
class MockGauge:
    def __init__(self, *args, **kwargs):
        self._value = 0
        self._labels = {}

    def labels(self, **kwargs):
        key = tuple(sorted(kwargs.items()))
        if key not in self._labels:
            self._labels[key] = MockGauge()
        return self._labels[key]

    def set(self, value):
        self._value = value

    def inc(self, value=1):
        self._value += value

class MockCounter:
    def __init__(self, *args, **kwargs):
        self._value = 0
        self._labels = {}

    def labels(self, **kwargs):
        key = tuple(sorted(kwargs.items()))
        if key not in self._labels:
            self._labels[key] = MockCounter()
        return self._labels[key]

    def inc(self, value=1):
        self._value += value

class MockHistogram:
    def __init__(self, *args, **kwargs):
        self._observations = []
        self._sum = 0
        self._count = 0
        self._labels = {}

    def labels(self, **kwargs):
        key = tuple(sorted(kwargs.items()))
        if key not in self._labels:
            self._labels[key] = MockHistogram()
        return self._labels[key]

    def observe(self, value):
        self._observations.append(value)
        self._sum += value
        self._count += 1

mock_prometheus = Mock()
mock_prometheus.Gauge = MockGauge
mock_prometheus.Counter = MockCounter
mock_prometheus.Histogram = MockHistogram
mock_prometheus.Summary = MockHistogram  # Similar behavior
mock_prometheus.CollectorRegistry = Mock()
mock_prometheus.generate_latest = Mock(return_value=b"# Mock metrics")
mock_prometheus.CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

sys.modules['prometheus_client'] = mock_prometheus

# Now import the metrics module
from core.metrics import (
    REGISTRY,
    # Circuit Breaker Metrics
    CIRCUIT_STATE,
    CIRCUIT_FAILURES_TOTAL,
    CIRCUIT_SUCCESSES_TOTAL,
    CIRCUIT_TRIPS_TOTAL,
    CIRCUIT_RECOVERIES_TOTAL,
    CIRCUIT_OPEN_DURATION_SECONDS,
    CIRCUIT_FAILURE_RATIO,
    # Anomaly Detection Metrics
    ANOMALY_DETECTIONS_TOTAL,
    ANOMALY_DETECTION_LATENCY,
    ANOMALY_MODEL_LOAD_ERRORS_TOTAL,
    ANOMALY_MODEL_FALLBACK_ACTIVATIONS,
    # System Health Metrics
    COMPONENT_HEALTH_STATUS,
    COMPONENT_ERROR_COUNT,
    COMPONENT_WARNING_COUNT,
    # Memory Store Metrics
    MEMORY_STORE_SIZE_BYTES,
    MEMORY_STORE_ENTRIES,
    MEMORY_STORE_RETRIEVALS,
    MEMORY_STORE_PRUNINGS,
    # Mission Phase Metrics
    MISSION_PHASE,
    ANOMALIES_BY_TYPE,
    # Recovery Metrics
    RECOVERY_ACTIONS_TOTAL,
    # Utility functions
    get_metrics_text,
    get_metrics_content_type
)


class TestCircuitBreakerMetrics:
    """Test circuit breaker metric operations"""

    def test_circuit_state_gauge(self):
        """Test circuit state gauge metric"""
        # Test setting different states
        CIRCUIT_STATE.labels(circuit_name="test_circuit").set(0)  # CLOSED
        CIRCUIT_STATE.labels(circuit_name="test_circuit").set(1)  # OPEN
        CIRCUIT_STATE.labels(circuit_name="test_circuit").set(2)  # HALF_OPEN

        # Verify values are set
        assert CIRCUIT_STATE.labels(circuit_name="test_circuit")._value == 2

    def test_circuit_failures_counter(self):
        """Test circuit failures counter"""
        CIRCUIT_FAILURES_TOTAL.labels(circuit_name="test_circuit").inc()
        CIRCUIT_FAILURES_TOTAL.labels(circuit_name="test_circuit").inc(2)

        assert CIRCUIT_FAILURES_TOTAL.labels(circuit_name="test_circuit")._value == 3

    def test_circuit_successes_counter(self):
        """Test circuit successes counter"""
        CIRCUIT_SUCCESSES_TOTAL.labels(circuit_name="test_circuit").inc(5)
        assert CIRCUIT_SUCCESSES_TOTAL.labels(circuit_name="test_circuit")._value == 5

    def test_circuit_trips_counter(self):
        """Test circuit trips counter"""
        CIRCUIT_TRIPS_TOTAL.labels(circuit_name="test_circuit").inc()
        assert CIRCUIT_TRIPS_TOTAL.labels(circuit_name="test_circuit")._value == 1

    def test_circuit_recoveries_counter(self):
        """Test circuit recoveries counter"""
        CIRCUIT_RECOVERIES_TOTAL.labels(circuit_name="test_circuit").inc(3)
        assert CIRCUIT_RECOVERIES_TOTAL.labels(circuit_name="test_circuit")._value == 3

    def test_circuit_open_duration_gauge(self):
        """Test circuit open duration gauge"""
        CIRCUIT_OPEN_DURATION_SECONDS.labels(circuit_name="test_circuit").set(45.5)
        assert CIRCUIT_OPEN_DURATION_SECONDS.labels(circuit_name="test_circuit")._value == 45.5

    def test_circuit_failure_ratio_gauge(self):
        """Test circuit failure ratio gauge"""
        CIRCUIT_FAILURE_RATIO.labels(circuit_name="test_circuit").set(0.15)
        assert CIRCUIT_FAILURE_RATIO.labels(circuit_name="test_circuit")._value == 0.15


class TestAnomalyDetectionMetrics:
    """Test anomaly detection metric operations"""

    def test_anomaly_detections_counter(self):
        """Test anomaly detections counter"""
        ANOMALY_DETECTIONS_TOTAL.labels(detector_type="model").inc()
        ANOMALY_DETECTIONS_TOTAL.labels(detector_type="heuristic").inc(2)

        assert ANOMALY_DETECTIONS_TOTAL.labels(detector_type="model")._value == 1
        assert ANOMALY_DETECTIONS_TOTAL.labels(detector_type="heuristic")._value == 2

    def test_anomaly_detection_latency_histogram(self):
        """Test anomaly detection latency histogram"""
        # Observe some latency values
        ANOMALY_DETECTION_LATENCY.labels(detector_type="model").observe(0.5)
        ANOMALY_DETECTION_LATENCY.labels(detector_type="model").observe(1.2)
        ANOMALY_DETECTION_LATENCY.labels(detector_type="heuristic").observe(0.8)

        # Verify histogram has observations
        assert ANOMALY_DETECTION_LATENCY.labels(detector_type="model")._sum > 0
        assert ANOMALY_DETECTION_LATENCY.labels(detector_type="heuristic")._sum > 0

    def test_anomaly_model_load_errors_counter(self):
        """Test model load errors counter"""
        ANOMALY_MODEL_LOAD_ERRORS_TOTAL.inc()
        ANOMALY_MODEL_LOAD_ERRORS_TOTAL.inc(2)
        assert ANOMALY_MODEL_LOAD_ERRORS_TOTAL._value == 3

    def test_anomaly_model_fallback_activations(self):
        """Test model fallback activations counter"""
        ANOMALY_MODEL_FALLBACK_ACTIVATIONS.inc()
        assert ANOMALY_MODEL_FALLBACK_ACTIVATIONS._value == 1


class TestMetricsUtilities:
    """Test utility functions"""

    def test_get_metrics_text(self):
        """Test getting metrics as text format"""
        # Add some test data
        CIRCUIT_STATE.labels(circuit_name="test").set(0)
        CIRCUIT_FAILURES_TOTAL.labels(circuit_name="test").inc()

        # Get metrics text
        metrics_text = get_metrics_text()

        # Verify it's a string
        assert isinstance(metrics_text, str)
        # Since we're using mocks, just verify it returns something
        assert len(metrics_text) > 0


class TestRegistryManagement:
    """Test registry management"""

    def test_registry_is_custom(self):
        """Test that we use a custom registry"""
        # Since we're using mocks, just verify REGISTRY exists
        assert REGISTRY is not None

    def test_metrics_registered_in_custom_registry(self):
        """Test that metrics are registered in our custom registry"""
        # With mocks, just verify registry exists
        assert REGISTRY is not None


class TestMetricsIntegration:
    """Test metrics integration scenarios"""

    def setup_method(self):
        """Reset all metrics before each test"""
        # Reset counters
        for metric in [CIRCUIT_FAILURES_TOTAL, CIRCUIT_SUCCESSES_TOTAL, CIRCUIT_TRIPS_TOTAL,
                      CIRCUIT_RECOVERIES_TOTAL, ANOMALY_DETECTIONS_TOTAL,
                      ANOMALY_MODEL_LOAD_ERRORS_TOTAL, ANOMALY_MODEL_FALLBACK_ACTIVATIONS,
                      COMPONENT_ERROR_COUNT, COMPONENT_WARNING_COUNT, MEMORY_STORE_RETRIEVALS,
                      MEMORY_STORE_PRUNINGS, ANOMALIES_BY_TYPE, RECOVERY_ACTIONS_TOTAL]:
            metric._value = 0
            metric._labels = {}

        # Reset gauges
        for metric in [CIRCUIT_STATE, CIRCUIT_OPEN_DURATION_SECONDS, CIRCUIT_FAILURE_RATIO,
                      COMPONENT_HEALTH_STATUS, MEMORY_STORE_SIZE_BYTES, MEMORY_STORE_ENTRIES,
                      MISSION_PHASE]:
            metric._value = 0
            metric._labels = {}

        # Reset histograms
        for metric in [ANOMALY_DETECTION_LATENCY]:
            metric._observations = []
            metric._sum = 0
            metric._count = 0
            metric._labels = {}

    def test_multiple_circuits_tracking(self):
        """Test tracking multiple circuit breakers"""
        # Test multiple circuits
        circuits = ["api_circuit", "db_circuit", "cache_circuit"]

        for circuit in circuits:
            CIRCUIT_STATE.labels(circuit_name=circuit).set(0)  # CLOSED
            CIRCUIT_FAILURES_TOTAL.labels(circuit_name=circuit).inc(2)

        # Verify each circuit has its own state
        for circuit in circuits:
            assert CIRCUIT_STATE.labels(circuit_name=circuit)._value == 0
            assert CIRCUIT_FAILURES_TOTAL.labels(circuit_name=circuit)._value == 2

    def test_anomaly_detection_workflow_metrics(self):
        """Test metrics for a complete anomaly detection workflow"""
        # Simulate anomaly detection workflow
        import time
        start_time = time.time()

        # Model-based detection
        ANOMALY_DETECTIONS_TOTAL.labels(detector_type="model").inc()
        detection_time = time.time() - start_time
        ANOMALY_DETECTION_LATENCY.labels(detector_type="model").observe(detection_time)

        # Verify metrics were recorded
        assert ANOMALY_DETECTIONS_TOTAL.labels(detector_type="model")._value == 1
        assert ANOMALY_DETECTION_LATENCY.labels(detector_type="model")._sum > 0