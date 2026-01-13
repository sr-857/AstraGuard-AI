"""
Test suite for HealthBroadcaster - periodic health state broadcasting.

Issue #401: Communication protocols - health broadcasting tests
- 30s intervals during normal operation
- Congestion backoff: 30→60→120s
- HMAC verification 100%
- 5-agent constellation delivery rate
- No broadcasts during unchanged health
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from astraguard.swarm.health_broadcaster import HealthBroadcaster, BroadcastMetrics
from astraguard.swarm.models import AgentID, SatelliteRole, HealthSummary, SwarmConfig
from astraguard.swarm.registry import SwarmRegistry
from astraguard.swarm.bus import SwarmMessageBus
from astraguard.swarm.compressor import StateCompressor
from astraguard.swarm.serializer import SwarmSerializer


def create_agent_id(serial: str = "SAT0000") -> AgentID:
    """Create test agent ID."""
    return AgentID.create("astra-v3.0", serial)


def create_config(num_peers: int = 5) -> tuple[SwarmConfig, AgentID]:
    """Create test SwarmConfig."""
    agent_id = create_agent_id("SAT0000")
    peers = {create_agent_id(f"SAT{i:03d}"): SatelliteRole.PRIMARY for i in range(num_peers)}
    return SwarmConfig(
        agent_id=agent_id,
        constellation_id="astra-v3.0",
        role=SatelliteRole.PRIMARY,
        bandwidth_limit_kbps=10,
        peers=peers
    ), agent_id


def create_bus(config: SwarmConfig) -> SwarmMessageBus:
    """Create test bus with serializer."""
    serializer = SwarmSerializer()
    return SwarmMessageBus(config, serializer)


def create_health(risk: float = 0.5) -> HealthSummary:
    """Create test health."""
    return HealthSummary(
        anomaly_signature=[0.1 + i * 0.01 for i in range(32)],
        risk_score=risk,
        recurrence_score=3.0,
        timestamp=datetime.utcnow()
    )


class TestHealthBroadcasterBasics:
    """Test basic broadcaster functionality."""
    
    def test_creation(self):
        """Test creating health broadcaster."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        assert broadcaster.agent_id == agent_id
        assert broadcaster.config == config
        assert broadcaster.metrics is not None
    
    def test_custom_key(self):
        """Test custom private key."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        custom_key = b"secret"
        
        broadcaster = HealthBroadcaster(
            config, agent_id, registry, bus, compressor,
            private_key=custom_key
        )
        
        assert broadcaster.private_key == custom_key
    
    def test_initial_metrics(self):
        """Test initial metrics state."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        metrics = broadcaster.get_metrics()
        assert metrics.total_broadcasts == 0
        assert metrics.successful_broadcasts == 0
        assert metrics.failed_broadcasts == 0


class TestHealthSignatures:
    """Test HMAC signing and verification."""
    
    def test_sign_payload(self):
        """Test HMAC signature generation."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        payload = {
            "agent_id": agent_id.uuid.hex,
            "constellation": "astra-v3.0",
            "compressed_health": "abc123",
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        sig = broadcaster._sign_payload(payload)
        
        assert sig is not None
        assert len(sig) == 64  # SHA256 hex string
    
    def test_verify_valid_signature(self):
        """Test verifying valid HMAC signature."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        payload = {
            "agent_id": agent_id.uuid.hex,
            "constellation": "astra-v3.0",
            "compressed_health": "abc123",
            "timestamp": datetime.utcnow().isoformat(),
        }
        payload["signature"] = broadcaster._sign_payload(payload)
        
        is_valid = HealthBroadcaster.verify_signature(payload, broadcaster.private_key)
        assert is_valid is True
    
    def test_verify_invalid_signature(self):
        """Test rejecting invalid HMAC signature."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        payload = {
            "agent_id": agent_id.uuid.hex,
            "constellation": "astra-v3.0",
            "compressed_health": "abc123",
            "timestamp": datetime.utcnow().isoformat(),
            "signature": "invalid_sig_123"
        }
        
        is_valid = HealthBroadcaster.verify_signature(payload, broadcaster.private_key)
        assert is_valid is False
    
    def test_verify_fails_with_wrong_key(self):
        """Test verification fails with different key."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        payload = {
            "agent_id": agent_id.uuid.hex,
            "constellation": "astra-v3.0",
            "compressed_health": "abc123",
            "timestamp": datetime.utcnow().isoformat(),
        }
        payload["signature"] = broadcaster._sign_payload(payload)
        
        wrong_key = b"wrong_key"
        is_valid = HealthBroadcaster.verify_signature(payload, wrong_key)
        assert is_valid is False


class TestHealthDelta:
    """Test unchanged health optimization."""
    
    def test_first_broadcast(self):
        """Test first broadcast always sends."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        health = create_health(0.5)
        should_broadcast = broadcaster._should_broadcast(health)
        
        assert should_broadcast is True
    
    def test_unchanged_health_skipped(self):
        """Test unchanged health doesn't broadcast."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        health = create_health(0.5)
        
        # First call broadcasts
        broadcaster._should_broadcast(health)
        broadcaster._last_health_hash = broadcaster._hash_health(health)
        
        # Second call with same health doesn't
        should_broadcast = broadcaster._should_broadcast(health)
        assert should_broadcast is False
    
    def test_changed_health_broadcasts(self):
        """Test changed health triggers broadcast."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        health1 = create_health(0.3)
        broadcaster._last_health_hash = broadcaster._hash_health(health1)
        
        health2 = create_health(0.8)
        
        should_broadcast = broadcaster._should_broadcast(health2)
        assert should_broadcast is True


class TestHealthHashing:
    """Test health delta detection."""
    
    def test_hash_consistency(self):
        """Test hashing is consistent."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        health = create_health(0.5)
        hash1 = broadcaster._hash_health(health)
        hash2 = broadcaster._hash_health(health)
        
        assert hash1 == hash2
    
    def test_hash_differs_for_changes(self):
        """Test hash differs for changed health."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        health1 = create_health(0.3)
        health2 = create_health(0.8)
        
        hash1 = broadcaster._hash_health(health1)
        hash2 = broadcaster._hash_health(health2)
        
        assert hash1 != hash2


class TestCongestionBackoff:
    """Test congestion detection and backoff."""
    
    def test_normal_interval(self):
        """Test normal broadcast interval is 30s."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        broadcaster._adjust_broadcast_interval(0.0)
        assert broadcaster._current_interval == 30.0
    
    def test_medium_congestion_60s(self):
        """Test medium congestion (>70%) → 60s interval."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        broadcaster._adjust_broadcast_interval(0.75)
        assert broadcaster._current_interval == 60.0
    
    def test_severe_congestion_120s(self):
        """Test severe congestion (>85%) → 120s interval."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        broadcaster._adjust_broadcast_interval(0.90)
        assert broadcaster._current_interval == 120.0
    
    def test_threshold_70_percent(self):
        """Test exact 70% threshold."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        # Just below
        broadcaster._adjust_broadcast_interval(0.69)
        assert broadcaster._current_interval == 30.0
        
        # Just above
        broadcaster._adjust_broadcast_interval(0.71)
        assert broadcaster._current_interval == 60.0
    
    def test_threshold_85_percent(self):
        """Test exact 85% threshold."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        # Just below
        broadcaster._adjust_broadcast_interval(0.84)
        assert broadcaster._current_interval == 60.0
        
        # Just above
        broadcaster._adjust_broadcast_interval(0.86)
        assert broadcaster._current_interval == 120.0


class TestBroadcastMetrics:
    """Test metrics tracking."""
    
    def test_update_on_success(self):
        """Test metrics update on successful broadcast."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        broadcaster._update_metrics(success=True, latency_ms=10.5)
        
        assert broadcaster.metrics.total_broadcasts == 1
        assert broadcaster.metrics.successful_broadcasts == 1
        assert broadcaster.metrics.average_latency_ms == pytest.approx(10.5, rel=0.01)
    
    def test_update_on_failure(self):
        """Test metrics update on failed broadcast."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        broadcaster._update_metrics(success=False, latency_ms=0.0)
        
        assert broadcaster.metrics.total_broadcasts == 1
        assert broadcaster.metrics.failed_broadcasts == 1
    
    def test_delivery_rate(self):
        """Test delivery rate calculation."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        # Initial rate
        rate = broadcaster.get_delivery_rate()
        assert rate == 0.0
        
        # After broadcasts
        broadcaster.metrics.total_broadcasts = 10
        broadcaster.metrics.successful_broadcasts = 9
        broadcaster.metrics.skipped_broadcasts = 0
        
        rate = broadcaster.get_delivery_rate()
        assert rate == pytest.approx(0.9, rel=0.01)


class TestIntegration:
    """Integration tests with full stack."""
    
    def test_broadcaster_with_registry(self):
        """Test broadcaster integration with registry."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        # Registry should have agent
        assert agent_id in registry.peers
        
        # Can get health from registry
        health = registry.get_peer_health(agent_id)
        assert health is None or isinstance(health, HealthSummary)
    
    def test_full_chain_signature(self):
        """Test full signature chain works."""
        config, agent_id = create_config()
        registry = SwarmRegistry(config, agent_id)
        bus = create_bus(config)
        compressor = StateCompressor()
        
        broadcaster = HealthBroadcaster(config, agent_id, registry, bus, compressor)
        
        # Full message chain
        payload = {
            "agent_id": agent_id.uuid.hex,
            "constellation": "astra-v3.0",
            "compressed_health": "xyz789",
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Sign
        payload["signature"] = broadcaster._sign_payload(payload)
        
        # Verify with same broadcaster key
        assert HealthBroadcaster.verify_signature(payload, broadcaster.private_key)
        
        # Verify fails with different key
        assert not HealthBroadcaster.verify_signature(payload, b"wrong")
