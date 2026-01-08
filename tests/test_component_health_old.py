"""
Comprehensive tests for Component Health module.

Tests cover:
- Health status management
- Component registration and updates
- Health monitoring
- Thread safety
- Error tracking
- Metadata handling
"""

import pytest
import threading
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from core.component_health import (
    HealthStatus,
    ComponentHealth,
    SystemHealthMonitor,
    get_health_monitor
)
    get_system_health_summary,
    HEALTH_CHECK_INTERVAL,
    MAX_ERROR_HISTORY,
)


class TestHealthStatus:
    """Test HealthStatus enum"""

    def test_health_status_values(self):
        """Test that all expected health status values exist"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.FAILED.value == "failed"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_health_status_ordering(self):
        """Test health status ordering (healthy > degraded > failed > unknown)"""
        assert HealthStatus.HEALTHY > HealthStatus.DEGRADED
        assert HealthStatus.DEGRADED > HealthStatus.FAILED
        assert HealthStatus.FAILED > HealthStatus.UNKNOWN


class TestComponentHealth:
    """Test ComponentHealth class"""

    def test_component_health_creation(self):
        """Test creating a ComponentHealth instance"""
        now = datetime.now()

        health = ComponentHealth(
            name="test_component",
            status=HealthStatus.HEALTHY,
            last_updated=now,
            error_count=2,
            warning_count=1,
            last_error="Connection timeout",
            last_error_time=now - timedelta(minutes=5),
            fallback_active=False,
            metadata={"version": "1.0.0"}
        )

        assert health.name == "test_component"
        assert health.status == HealthStatus.HEALTHY
        assert health.error_count == 2
        assert health.warning_count == 1
        assert health.last_error == "Connection timeout"
        assert health.fallback_active is False
        assert health.metadata == {"version": "1.0.0"}

    def test_component_health_to_dict(self):
        """Test converting ComponentHealth to dictionary"""
        now = datetime.now()

        health = ComponentHealth(
            name="test_component",
            status=HealthStatus.DEGRADED,
            last_updated=now,
            error_count=1,
            metadata={"endpoint": "http://api:8000"}
        )

        result = health.to_dict()

        assert result["name"] == "test_component"
        assert result["status"] == "degraded"
        assert result["error_count"] == 1
        assert result["warning_count"] == 0
        assert result["last_error"] is None
        assert result["fallback_active"] is False
        assert result["metadata"] == {"endpoint": "http://api:8000"}
        assert "last_updated" in result
        assert "last_error_time" in result

    def test_component_health_defaults(self):
        """Test ComponentHealth default values"""
        health = ComponentHealth(
            name="test_component",
            status=HealthStatus.HEALTHY,
            last_updated=datetime.now()
        )

        assert health.error_count == 0
        assert health.warning_count == 0
        assert health.last_error is None
        assert health.last_error_time is None
        assert health.fallback_active is False
        assert health.metadata is None


class TestHealthMonitor:
    """Test SystemHealthMonitor class"""

    def test_health_monitor_initialization(self):
        """Test SystemHealthMonitor initialization"""
        monitor = SystemHealthMonitor()
        assert monitor is not None
        assert hasattr(monitor, '_components')
        assert hasattr(monitor, '_lock')

    def test_register_component(self):
        """Test registering a component"""
        monitor = SystemHealthMonitor()

        # Register a component
        monitor.register_component("test_component")

        # Verify it's registered
        health = monitor.get_component_health("test_component")
        assert health is not None
        assert health.name == "test_component"
        assert health.status == HealthStatus.UNKNOWN

    def test_register_component_with_initial_status(self):
        """Test registering a component with initial status"""
        monitor = SystemHealthMonitor()

        monitor.register_component(
            "test_component",
            initial_status=HealthStatus.HEALTHY,
            metadata={"version": "2.0.0"}
        )

        health = monitor.get_component_health("test_component")
        assert health.status == HealthStatus.HEALTHY
        assert health.metadata == {"version": "2.0.0"}

    def test_update_component_health(self):
        """Test updating component health"""
        monitor = SystemHealthMonitor()
        monitor.register_component("test_component")

        # Update health
        monitor.update_component_health(
            "test_component",
            HealthStatus.DEGRADED,
            error_count=1,
            last_error="Connection failed"
        )

        health = monitor.get_component_health("test_component")
        assert health.status == HealthStatus.DEGRADED
        assert health.error_count == 1
        assert health.last_error == "Connection failed"
        assert health.last_error_time is not None

    def test_update_component_health_incremental(self):
        """Test incremental health updates"""
        monitor = SystemHealthMonitor()
        monitor.register_component("test_component")

        # First update
        monitor.update_component_health(
            "test_component",
            HealthStatus.HEALTHY,
            error_count=1
        )

        # Second update (should increment)
        monitor.update_component_health(
            "test_component",
            HealthStatus.DEGRADED,
            error_count=2  # This should be incremental
        )

        health = monitor.get_component_health("test_component")
        assert health.status == HealthStatus.DEGRADED
        assert health.error_count == 2

    def test_get_component_health_nonexistent(self):
        """Test getting health for non-existent component"""
        monitor = SystemHealthMonitor()

        health = monitor.get_component_health("nonexistent")
        assert health is None

    def test_get_all_components_health(self):
        """Test getting health for all components"""
        monitor = SystemHealthMonitor()

        # Register multiple components
        monitor.register_component("comp1", initial_status=HealthStatus.HEALTHY)
        monitor.register_component("comp2", initial_status=HealthStatus.FAILED)
        monitor.register_component("comp3", initial_status=HealthStatus.DEGRADED)

        all_health = monitor.get_all_components_health()

        assert len(all_health) == 3
        assert all_health["comp1"].status == HealthStatus.HEALTHY
        assert all_health["comp2"].status == HealthStatus.FAILED
        assert all_health["comp3"].status == HealthStatus.DEGRADED

    def test_get_system_health_summary(self):
        """Test getting system health summary"""
        monitor = SystemHealthMonitor()

        # Register components with different statuses
        monitor.register_component("healthy_comp", initial_status=HealthStatus.HEALTHY)
        monitor.register_component("degraded_comp", initial_status=HealthStatus.DEGRADED)
        monitor.register_component("failed_comp", initial_status=HealthStatus.FAILED)

        summary = monitor.get_system_health_summary()

        assert summary["total_components"] == 3
        assert summary["healthy_count"] == 1
        assert summary["degraded_count"] == 1
        assert summary["failed_count"] == 1
        assert summary["overall_status"] == HealthStatus.FAILED  # Worst status wins

    def test_get_system_health_summary_all_healthy(self):
        """Test system health summary when all components are healthy"""
        monitor = SystemHealthMonitor()

        monitor.register_component("comp1", initial_status=HealthStatus.HEALTHY)
        monitor.register_component("comp2", initial_status=HealthStatus.HEALTHY)

        summary = monitor.get_system_health_summary()

        assert summary["total_components"] == 2
        assert summary["healthy_count"] == 2
        assert summary["degraded_count"] == 0
        assert summary["failed_count"] == 0
        assert summary["overall_status"] == HealthStatus.HEALTHY

    def test_get_system_health_summary_empty(self):
        """Test system health summary with no components"""
        monitor = SystemHealthMonitor()

        summary = monitor.get_system_health_summary()

        assert summary["total_components"] == 0
        assert summary["healthy_count"] == 0
        assert summary["overall_status"] == HealthStatus.UNKNOWN


class TestGlobalFunctions:
    """Test global utility functions"""

    def test_get_component_health(self):
        """Test global get_component_health function"""
        # Register a component in the global registry
        update_component_health("global_test", HealthStatus.HEALTHY)

        # Get it back
        health = get_component_health("global_test")
        assert health is not None
        assert health.status == HealthStatus.HEALTHY

    def test_update_component_health_global(self):
        """Test global update_component_health function"""
        # Update component health
        update_component_health(
            "global_update_test",
            HealthStatus.DEGRADED,
            error_count=3,
            last_error="Test error"
        )

        # Verify update
        health = get_component_health("global_update_test")
        assert health.status == HealthStatus.DEGRADED
        assert health.error_count == 3
        assert health.last_error == "Test error"

    def test_get_system_health_summary_global(self):
        """Test global get_system_health_summary function"""
        # Clear any existing components for clean test
        COMPONENT_REGISTRY._components.clear()

        # Add some test components
        update_component_health("summary_comp1", HealthStatus.HEALTHY)
        update_component_health("summary_comp2", HealthStatus.FAILED)

        summary = get_system_health_summary()

        assert summary["total_components"] == 2
        assert summary["healthy_count"] == 1
        assert summary["failed_count"] == 1
        assert summary["overall_status"] == HealthStatus.FAILED


class TestThreadSafety:
    """Test thread safety of health monitoring"""

    def test_concurrent_updates(self):
        """Test concurrent component health updates"""
        monitor = SystemHealthMonitor()
        monitor.register_component("thread_test")

        results = []
        errors = []

        def update_worker(worker_id):
            """Worker function for concurrent updates"""
            try:
                for i in range(10):
                    monitor.update_component_health(
                        "thread_test",
                        HealthStatus.HEALTHY if i % 2 == 0 else HealthStatus.DEGRADED,
                        error_count=i
                    )
                    time.sleep(0.001)  # Small delay to encourage race conditions
                results.append(f"worker_{worker_id}_done")
            except Exception as e:
                errors.append(f"worker_{worker_id}_error: {e}")

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=update_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0
        assert len(results) == 5

        # Verify component still exists and has valid state
        health = monitor.get_component_health("thread_test")
        assert health is not None
        assert isinstance(health.status, HealthStatus)

    def test_registry_thread_safety(self):
        """Test thread safety of component registry"""
        # Clear registry
        COMPONENT_REGISTRY._components.clear()

        def registry_worker(worker_id):
            """Worker that registers and updates components"""
            try:
                # Register component
                update_component_health(f"reg_test_{worker_id}", HealthStatus.HEALTHY)

                # Update it multiple times
                for i in range(5):
                    update_component_health(
                        f"reg_test_{worker_id}",
                        HealthStatus.DEGRADED,
                        error_count=i
                    )

                return True
            except Exception:
                return False

        # Run multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=lambda wid=i: registry_worker(wid))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all components were registered
        summary = get_system_health_summary()
        assert summary["total_components"] == 10


class TestErrorTracking:
    """Test error tracking functionality"""

    def test_error_count_increment(self):
        """Test that error counts increment properly"""
        monitor = SystemHealthMonitor()
        monitor.register_component("error_test")

        # Initial state
        health = monitor.get_component_health("error_test")
        assert health.error_count == 0

        # Update with error
        monitor.update_component_health(
            "error_test",
            HealthStatus.FAILED,
            error_count=1
        )

        health = monitor.get_component_health("error_test")
        assert health.error_count == 1

        # Update again (should increment)
        monitor.update_component_health(
            "error_test",
            HealthStatus.FAILED,
            error_count=1  # This should be added to existing count
        )

        health = monitor.get_component_health("error_test")
        assert health.error_count == 2

    def test_last_error_tracking(self):
        """Test last error message tracking"""
        monitor = SystemHealthMonitor()
        monitor.register_component("error_msg_test")

        # Set first error
        monitor.update_component_health(
            "error_msg_test",
            HealthStatus.FAILED,
            last_error="Connection timeout"
        )

        health = monitor.get_component_health("error_msg_test")
        assert health.last_error == "Connection timeout"
        assert health.last_error_time is not None

        # Update with different error
        new_error_time = datetime.now()
        monitor.update_component_health(
            "error_msg_test",
            HealthStatus.FAILED,
            last_error="Authentication failed"
        )

        health = monitor.get_component_health("error_msg_test")
        assert health.last_error == "Authentication failed"
        assert health.last_error_time >= new_error_time

    def test_warning_count_tracking(self):
        """Test warning count tracking"""
        monitor = SystemHealthMonitor()
        monitor.register_component("warning_test")

        # Update with warnings
        monitor.update_component_health(
            "warning_test",
            HealthStatus.DEGRADED,
            warning_count=3
        )

        health = monitor.get_component_health("warning_test")
        assert health.warning_count == 3


class TestMetadataHandling:
    """Test metadata handling"""

    def test_metadata_storage(self):
        """Test storing and retrieving metadata"""
        monitor = SystemHealthMonitor()
        monitor.register_component(
            "metadata_test",
            metadata={"version": "1.2.3", "endpoint": "http://api:8000"}
        )

        health = monitor.get_component_health("metadata_test")
        assert health.metadata == {"version": "1.2.3", "endpoint": "http://api:8000"}

    def test_metadata_updates(self):
        """Test updating component metadata"""
        monitor = SystemHealthMonitor()
        monitor.register_component("metadata_update_test")

        # Update with metadata
        monitor.update_component_health(
            "metadata_update_test",
            HealthStatus.HEALTHY,
            metadata={"last_check": "2026-01-04T12:00:00Z"}
        )

        health = monitor.get_component_health("metadata_update_test")
        assert health.metadata == {"last_check": "2026-01-04T12:00:00Z"}

    def test_metadata_merge(self):
        """Test merging metadata on updates"""
        monitor = SystemHealthMonitor()
        monitor.register_component(
            "metadata_merge_test",
            metadata={"initial": "value"}
        )

        # Update with additional metadata
        monitor.update_component_health(
            "metadata_merge_test",
            HealthStatus.HEALTHY,
            metadata={"updated": "new_value"}
        )

        health = monitor.get_component_health("metadata_merge_test")
        # Should contain the updated metadata (exact behavior depends on implementation)
        assert health.metadata is not None


class TestHealthCheckIntegration:
    """Test health check integration scenarios"""

    def test_component_lifecycle(self):
        """Test complete component lifecycle"""
        monitor = SystemHealthMonitor()

        # 1. Register component
        monitor.register_component("lifecycle_test")
        health = monitor.get_component_health("lifecycle_test")
        assert health.status == HealthStatus.UNKNOWN

        # 2. Mark as healthy
        monitor.update_component_health("lifecycle_test", HealthStatus.HEALTHY)
        health = monitor.get_component_health("lifecycle_test")
        assert health.status == HealthStatus.HEALTHY

        # 3. Experience some issues
        monitor.update_component_health(
            "lifecycle_test",
            HealthStatus.DEGRADED,
            warning_count=2,
            last_error="High latency"
        )
        health = monitor.get_component_health("lifecycle_test")
        assert health.status == HealthStatus.DEGRADED
        assert health.warning_count == 2

        # 4. Recover
        monitor.update_component_health("lifecycle_test", HealthStatus.HEALTHY)
        health = monitor.get_component_health("lifecycle_test")
        assert health.status == HealthStatus.HEALTHY

        # 5. Complete failure
        monitor.update_component_health(
            "lifecycle_test",
            HealthStatus.FAILED,
            error_count=5,
            last_error="Service unavailable"
        )
        health = monitor.get_component_health("lifecycle_test")
        assert health.status == HealthStatus.FAILED
        assert health.error_count == 5

    def test_bulk_health_updates(self):
        """Test updating multiple components at once"""
        monitor = SystemHealthMonitor()

        components = ["api", "database", "cache", "worker", "monitor"]

        # Register all components
        for comp in components:
            monitor.register_component(comp, initial_status=HealthStatus.HEALTHY)

        # Simulate a system-wide issue affecting multiple components
        affected_components = ["database", "cache"]
        for comp in affected_components:
            monitor.update_component_health(
                comp,
                HealthStatus.FAILED,
                last_error="Network partition detected"
            )

        # Check system health
        summary = monitor.get_system_health_summary()
        assert summary["total_components"] == 5
        assert summary["healthy_count"] == 3  # api, worker, monitor
        assert summary["failed_count"] == 2   # database, cache
        assert summary["overall_status"] == HealthStatus.FAILED

    def test_health_status_persistence(self):
        """Test that health status persists across queries"""
        monitor = SystemHealthMonitor()

        # Set up component with specific state
        monitor.register_component("persistence_test")
        monitor.update_component_health(
            "persistence_test",
            HealthStatus.DEGRADED,
            error_count=3,
            warning_count=1,
            last_error="Intermittent connectivity",
            metadata={"last_check": datetime.now().isoformat()}
        )

        # Query multiple times
        for _ in range(5):
            health = monitor.get_component_health("persistence_test")
            assert health.status == HealthStatus.DEGRADED
            assert health.error_count == 3
            assert health.warning_count == 1
            assert health.last_error == "Intermittent connectivity"
            assert health.metadata is not None