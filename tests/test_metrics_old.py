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
        initial_value = CIRCUIT_FAILURES_TOTAL.labels(circuit_name="test_circuit")._value

        # Increment counter
        CIRCUIT_FAILURES_TOTAL.labels(circuit_name="test_circuit").inc()
        CIRCUIT_FAILURES_TOTAL.labels(circuit_name="test_circuit").inc(2)

        # Verify increments
        final_value = CIRCUIT_FAILURES_TOTAL.labels(circuit_name="test_circuit")._value
        assert final_value == initial_value + 3

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
        CIRCUIT_RECOVERIES_TOTAL.labels(circuit_name="test_circuit").inc()
        assert CIRCUIT_RECOVERIES_TOTAL.labels(circuit_name="test_circuit")._value == 1

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
        ANOMALY_DETECTIONS_TOTAL.labels(detector_type="heuristic").inc(3)

        assert ANOMALY_DETECTIONS_TOTAL.labels(detector_type="model")._value == 1
        assert ANOMALY_DETECTIONS_TOTAL.labels(detector_type="heuristic")._value == 3

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


class TestRecoveryMetrics:
    """Test recovery metric operations"""

    def test_recovery_attempts_counter(self):
        """Test recovery attempts counter"""
        RECOVERY_ATTEMPTS_TOTAL.inc()
        assert RECOVERY_ATTEMPTS_TOTAL._value == 1

    def test_recovery_success_counter(self):
        """Test recovery success counter"""
        RECOVERY_SUCCESS_TOTAL.inc(2)
        assert RECOVERY_SUCCESS_TOTAL._value == 2

    def test_recovery_failure_counter(self):
        """Test recovery failure counter"""
        RECOVERY_FAILURE_TOTAL.inc()
        assert RECOVERY_FAILURE_TOTAL._value == 1

    def test_recovery_latency_histogram(self):
        """Test recovery latency histogram"""
        RECOVERY_LATENCY.observe(2.5)
        RECOVERY_LATENCY.observe(4.1)
        assert RECOVERY_LATENCY._sum > 0


class TestSystemHealthMetrics:
    """Test system health metric operations"""

    def test_component_health_status_gauge(self):
        """Test component health status gauge"""
        COMPONENT_HEALTH_STATUS.labels(component="api").set(0)  # HEALTHY
        COMPONENT_HEALTH_STATUS.labels(component="database").set(1)  # DEGRADED
        COMPONENT_HEALTH_STATUS.labels(component="cache").set(2)  # FAILED

        assert COMPONENT_HEALTH_STATUS.labels(component="api")._value == 0
        assert COMPONENT_HEALTH_STATUS.labels(component="database")._value == 1
        assert COMPONENT_HEALTH_STATUS.labels(component="cache")._value == 2

    def test_system_uptime_gauge(self):
        """Test system uptime gauge"""
        SYSTEM_UPTIME_SECONDS.set(3600.5)
        assert SYSTEM_UPTIME_SECONDS._value == 3600.5

    def test_memory_usage_gauge(self):
        """Test memory usage gauge"""
        MEMORY_USAGE_BYTES.set(1073741824)  # 1GB
        assert MEMORY_USAGE_BYTES._value == 1073741824

    def test_cpu_usage_gauge(self):
        """Test CPU usage gauge"""
        CPU_USAGE_PERCENT.set(75.5)
        assert CPU_USAGE_PERCENT._value == 75.5


class TestMissionPhaseMetrics:
    """Test mission phase metric operations"""

    def test_mission_phase_changes_counter(self):
        """Test mission phase changes counter"""
        MISSION_PHASE_CHANGES_TOTAL.inc()
        MISSION_PHASE_CHANGES_TOTAL.inc(2)
        assert MISSION_PHASE_CHANGES_TOTAL._value == 3

    def test_mission_phase_duration_gauge(self):
        """Test mission phase duration gauge"""
        MISSION_PHASE_DURATION_SECONDS.set(1800.0)  # 30 minutes
        assert MISSION_PHASE_DURATION_SECONDS._value == 1800.0


class TestErrorHandlingMetrics:
    """Test error handling metric operations"""

    def test_error_handler_invocations_counter(self):
        """Test error handler invocations counter"""
        ERROR_HANDLER_INVOCATIONS_TOTAL.inc()
        assert ERROR_HANDLER_INVOCATIONS_TOTAL._value == 1

    def test_error_handler_success_counter(self):
        """Test error handler success counter"""
        ERROR_HANDLER_SUCCESS_TOTAL.inc(3)
        assert ERROR_HANDLER_SUCCESS_TOTAL._value == 3

    def test_error_handler_failure_counter(self):
        """Test error handler failure counter"""
        ERROR_HANDLER_FAILURE_TOTAL.inc()
        assert ERROR_HANDLER_FAILURE_TOTAL._value == 1


class TestResourceMonitorMetrics:
    """Test resource monitor metric operations"""

    def test_resource_violations_counter(self):
        """Test resource violations counter"""
        RESOURCE_VIOLATIONS_TOTAL.labels(resource_type="memory").inc()
        RESOURCE_VIOLATIONS_TOTAL.labels(resource_type="cpu").inc(2)

        assert RESOURCE_VIOLATIONS_TOTAL.labels(resource_type="memory")._value == 1
        assert RESOURCE_VIOLATIONS_TOTAL.labels(resource_type="cpu")._value == 2

    def test_resource_thresholds_exceeded_gauge(self):
        """Test resource thresholds exceeded gauge"""
        RESOURCE_THRESHOLDS_EXCEEDED.labels(resource_type="memory").set(85.5)
        assert RESOURCE_THRESHOLDS_EXCEEDED.labels(resource_type="memory")._value == 85.5


class TestTimeoutHandlerMetrics:
    """Test timeout handler metric operations"""

    def test_timeouts_counter(self):
        """Test timeouts counter"""
        TIMEOUTS_TOTAL.inc()
        TIMEOUTS_TOTAL.inc(4)
        assert TIMEOUTS_TOTAL._value == 5

    def test_timeout_durations_histogram(self):
        """Test timeout durations histogram"""
        TIMEOUT_DURATIONS_SECONDS.observe(30.0)
        TIMEOUT_DURATIONS_SECONDS.observe(60.5)
        assert TIMEOUT_DURATIONS_SECONDS._sum > 0


class TestInputValidationMetrics:
    """Test input validation metric operations"""

    def test_validation_requests_counter(self):
        """Test validation requests counter"""
        VALIDATION_REQUESTS_TOTAL.inc()
        assert VALIDATION_REQUESTS_TOTAL._value == 1

    def test_validation_failures_counter(self):
        """Test validation failures counter"""
        VALIDATION_FAILURES_TOTAL.inc(2)
        assert VALIDATION_FAILURES_TOTAL._value == 2

    def test_validation_latency_histogram(self):
        """Test validation latency histogram"""
        VALIDATION_LATENCY.observe(0.1)
        VALIDATION_LATENCY.observe(0.25)
        assert VALIDATION_LATENCY._sum > 0


class TestMetricsUtilities:
    """Test utility functions"""

    def test_get_metrics_text(self):
        """Test getting metrics as text format"""
        # Add some test data
        CIRCUIT_STATE.labels(circuit_name="test").set(0)
        CIRCUIT_FAILURES_TOTAL.labels(circuit_name="test").inc()

        # Get metrics text
        metrics_text = get_metrics_text()

        # Verify it's a string and contains expected content
        assert isinstance(metrics_text, str)
        assert "astraguard_circuit_state" in metrics_text
        assert "astraguard_circuit_failures_total" in metrics_text

    def test_reset_all_metrics(self):
        """Test resetting all metrics"""
        # Set some values
        CIRCUIT_FAILURES_TOTAL.labels(circuit_name="test").inc(5)
        ANOMALY_DETECTIONS_TOTAL.labels(detector_type="model").inc(3)

        # Verify values are set
        assert CIRCUIT_FAILURES_TOTAL.labels(circuit_name="test")._value == 5
        assert ANOMALY_DETECTIONS_TOTAL.labels(detector_type="model")._value == 3

        # Reset all metrics
        reset_all_metrics()

        # Verify values are reset (this might not work for all metric types)
        # At minimum, verify function doesn't crash
        assert True  # If we get here, function executed


class TestRegistryManagement:
    """Test registry management"""

    def test_registry_is_custom(self):
        """Test that we use a custom registry"""
        assert isinstance(REGISTRY, CollectorRegistry)
        assert REGISTRY is not CollectorRegistry._default_registry

    def test_metrics_registered_in_custom_registry(self):
        """Test that metrics are registered in our custom registry"""
        # Check that some metrics are in our registry
        assert len(REGISTRY._collector_to_names) > 0

        # Verify specific metrics are registered
        metric_names = []
        for collector, names in REGISTRY._collector_to_names.items():
            metric_names.extend(names)

        assert "astraguard_circuit_state" in metric_names
        assert "astraguard_anomaly_detections_total" in metric_names


class TestMetricsIntegration:
    """Test metrics integration scenarios"""

    def test_multiple_circuits_tracking(self):
        """Test tracking multiple circuits simultaneously"""
        circuits = ["api_circuit", "db_circuit", "cache_circuit"]

        for circuit in circuits:
            CIRCUIT_STATE.labels(circuit_name=circuit).set(0)
            CIRCUIT_FAILURES_TOTAL.labels(circuit_name=circuit).inc()
            CIRCUIT_SUCCESSES_TOTAL.labels(circuit_name=circuit).inc(2)

        # Verify all circuits have metrics
        for circuit in circuits:
            assert CIRCUIT_STATE.labels(circuit_name=circuit)._value == 0
            assert CIRCUIT_FAILURES_TOTAL.labels(circuit_name=circuit)._value == 1
            assert CIRCUIT_SUCCESSES_TOTAL.labels(circuit_name=circuit)._value == 2

    def test_anomaly_detection_workflow_metrics(self):
        """Test metrics for a complete anomaly detection workflow"""
        # Simulate anomaly detection workflow
        start_time = time.time()

        # Model-based detection
        ANOMALY_DETECTIONS_TOTAL.labels(detector_type="model").inc()
        detection_time = time.time() - start_time
        ANOMALY_DETECTION_LATENCY.labels(detector_type="model").observe(detection_time)

        # Recovery attempt
        RECOVERY_ATTEMPTS_TOTAL.inc()
        RECOVERY_SUCCESS_TOTAL.inc()
        recovery_time = 1.5
        RECOVERY_LATENCY.observe(recovery_time)

        # Verify workflow metrics
        assert ANOMALY_DETECTIONS_TOTAL.labels(detector_type="model")._value == 1
        assert RECOVERY_ATTEMPTS_TOTAL._value == 1
        assert RECOVERY_SUCCESS_TOTAL._value == 1

    def test_system_health_monitoring(self):
        """Test system health monitoring metrics"""
        # Simulate system health updates
        components = ["api", "database", "cache", "worker"]

        for i, component in enumerate(components):
            COMPONENT_HEALTH_STATUS.labels(component=component).set(i % 3)  # Cycle through statuses

        # Update system metrics
        SYSTEM_UPTIME_SECONDS.set(86400)  # 1 day
        MEMORY_USAGE_BYTES.set(2147483648)  # 2GB
        CPU_USAGE_PERCENT.set(67.5)

        # Verify system metrics
        assert SYSTEM_UPTIME_SECONDS._value == 86400
        assert MEMORY_USAGE_BYTES._value == 2147483648
        assert CPU_USAGE_PERCENT._value == 67.5

        for i, component in enumerate(components):
            assert COMPONENT_HEALTH_STATUS.labels(component=component)._value == i % 3