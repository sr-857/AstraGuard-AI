"""
Tests for Component Health module.
"""

import pytest
from datetime import datetime, timedelta
from core.component_health import (
    HealthStatus,
    ComponentHealth,
    SystemHealthMonitor
)


class TestComponentHealth:
    """Test ComponentHealth dataclass"""

    def test_component_health_creation(self):
        """Test creating a ComponentHealth instance"""
        now = datetime.now()
        health = ComponentHealth(
            name="test_component",
            status=HealthStatus.HEALTHY,
            last_updated=now
        )
        assert health.name == "test_component"
        assert health.status == HealthStatus.HEALTHY
        assert health.last_updated == now
        assert health.error_count == 0
        assert health.warning_count == 0

    def test_component_health_to_dict(self):
        """Test ComponentHealth.to_dict() method"""
        now = datetime.now()
        health = ComponentHealth(
            name="test_component",
            status=HealthStatus.HEALTHY,
            last_updated=now,
            error_count=2,
            last_error="Test error"
        )
        data = health.to_dict()
        assert data["name"] == "test_component"
        assert data["status"] == "healthy"
        assert data["error_count"] == 2
        assert data["last_error"] == "Test error"


class TestSystemHealthMonitor:
    """Test SystemHealthMonitor class"""

    def test_initialization(self):
        """Test SystemHealthMonitor initialization"""
        monitor = SystemHealthMonitor()
        assert monitor._components == {}
        assert monitor._component_lock is not None

    def test_register_component(self):
        """Test registering a component"""
        monitor = SystemHealthMonitor()
        monitor.register_component("test_component")

        health = monitor.get_component_health("test_component")
        assert health is not None
        assert health.name == "test_component"
        assert health.status == HealthStatus.HEALTHY  # Default status

    def test_mark_healthy(self):
        """Test marking component as healthy"""
        monitor = SystemHealthMonitor()
        monitor.register_component("test_component")

        monitor.mark_healthy("test_component")
        health = monitor.get_component_health("test_component")
        assert health.status == HealthStatus.HEALTHY

    def test_get_all_health(self):
        """Test getting all components health"""
        monitor = SystemHealthMonitor()
        monitor.register_component("comp1")
        monitor.register_component("comp2")

        components = monitor.get_all_health()
        assert len(components) == 2
        assert "comp1" in components
        assert "comp2" in components

    def test_get_system_status(self):
        """Test getting system health status"""
        monitor = SystemHealthMonitor()
        monitor.register_component("comp1")
        monitor.register_component("comp2")

        monitor.mark_healthy("comp1")
        monitor.mark_failed("comp2")

        status = monitor.get_system_status()
        assert status["component_counts"]["healthy"] == 1
        assert status["component_counts"]["failed"] == 1
        assert status["component_counts"]["total"] == 2