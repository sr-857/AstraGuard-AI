import json
from fastapi.testclient import TestClient
from backend.main import create_app
from core.component_health import get_health_monitor, HealthStatus




def test_register_integration():
    with TestClient(create_app()) as client:
        resp = client.post("/monitoring/register", json={"provider": "datadog", "name": "team-a", "config": {}})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "registered"
        assert body["provider"] == "datadog"


def test_datadog_webhook_degraded_component():
    # Simulate a Datadog monitor webhook payload
    payload = {
        "alert_type": "warning",
        "check": "db-connection",
        "text": "High connection latency"
    }
    with TestClient(create_app()) as client:
        resp = client.post("/monitoring/datadog/webhook", json=payload)
        assert resp.status_code == 200
        assert resp.json()["ingested"] == 1

        # Verify the component health was updated (use HealthMonitor's component store)
        from backend.health_monitor import get_health_monitor as get_hm
        health = get_hm().component_health.get_component_health("db-connection")
        assert health.status == HealthStatus.DEGRADED


def test_newrelic_webhook_failure_component():
    payload = {
        "condition_name": "CPU spike",
        "severity": "critical",
        "details": "CPU > 95% for 5m"
    }
    with TestClient(create_app()) as client:
        resp = client.post("/monitoring/newrelic/webhook", json=payload)
        assert resp.status_code == 200
        assert resp.json()["ingested"] == 1

        # Verify using HealthMonitor's component store
        from backend.health_monitor import get_health_monitor as get_hm
        health = get_hm().component_health.get_component_health("CPU spike")
        assert health.status == HealthStatus.FAILED
