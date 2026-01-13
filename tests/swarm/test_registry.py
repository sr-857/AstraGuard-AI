"""
Test suite for SwarmRegistry - agent discovery and heartbeat.

Issue #400 tests:
- Peer state management
- Registry operations
- Quorum calculation
- Network partition detection
"""

import pytest
from datetime import datetime, timedelta

from astraguard.swarm.registry import SwarmRegistry, PeerState, HEARTBEAT_TIMEOUT
from astraguard.swarm.models import AgentID, SatelliteRole, HealthSummary, SwarmConfig


def create_agent_id(serial: str) -> AgentID:
    """Create test agent ID."""
    return AgentID.create("astra-v3.0", serial)


def create_config() -> SwarmConfig:
    """Create test SwarmConfig."""
    agent_id = create_agent_id("SAT000")
    peers = {create_agent_id(f"SAT{i:03d}"): SatelliteRole.PRIMARY for i in range(5)}
    return SwarmConfig(
        agent_id=agent_id,
        constellation_id="astra-v3.0",
        role=SatelliteRole.PRIMARY,
        bandwidth_limit_kbps=10,
        peers=peers
    )


class TestPeerState:
    """Test PeerState dataclass."""
    
    def test_peer_creation(self):
        """Test PeerState creation."""
        agent_id = create_agent_id("SAT001")
        now = datetime.utcnow()
        
        peer = PeerState(
            agent_id=agent_id,
            role=SatelliteRole.PRIMARY,
            last_heartbeat=now
        )
        
        assert peer.agent_id == agent_id
        assert peer.is_alive is True
        assert peer.heartbeat_failures == 0
    
    def test_peer_heartbeat_record(self):
        """Test recording heartbeat."""
        agent_id = create_agent_id("SAT001")
        peer = PeerState(
            agent_id=agent_id,
            role=SatelliteRole.PRIMARY,
            last_heartbeat=datetime.utcnow() - timedelta(seconds=100)
        )
        
        health = HealthSummary(
            anomaly_signature=[0.1] * 32,
            risk_score=0.5,
            recurrence_score=3.0,
            timestamp=datetime.utcnow()
        )
        
        peer.record_heartbeat(health)
        
        assert peer.is_alive is True
        assert peer.heartbeat_failures == 0
        assert peer.health_summary == health
    
    def test_peer_timeout(self):
        """Test peer timeout detection."""
        agent_id = create_agent_id("SAT001")
        old_time = datetime.utcnow() - timedelta(seconds=100)
        
        peer = PeerState(
            agent_id=agent_id,
            role=SatelliteRole.PRIMARY,
            last_heartbeat=old_time
        )
        
        assert peer.is_alive is False
    
    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        agent_id = create_agent_id("SAT001")
        peer = PeerState(
            agent_id=agent_id,
            role=SatelliteRole.PRIMARY,
            last_heartbeat=datetime.utcnow()
        )
        
        # No failures: 30s interval
        assert peer.get_next_heartbeat_interval() == 30
        
        # 1 failure: 60s
        peer.record_heartbeat_failure()
        assert peer.get_next_heartbeat_interval() == 60
        
        # 2+ failures: 120s
        peer.record_heartbeat_failure()
        assert peer.get_next_heartbeat_interval() == 120


class TestSwarmRegistry:
    """Test SwarmRegistry functionality."""
    
    def test_registry_init(self):
        """Test registry initialization."""
        config = create_config()
        registry = SwarmRegistry(config, config.agent_id)
        
        assert registry.agent_id == config.agent_id
        assert config.agent_id in registry.peers
        assert len(registry.peers) == 1
    
    def test_add_peer(self):
        """Test adding peer."""
        config = create_config()
        registry = SwarmRegistry(config, config.agent_id)
        
        peer_id = create_agent_id("SAT001")
        peer_state = PeerState(
            agent_id=peer_id,
            role=SatelliteRole.PRIMARY,
            last_heartbeat=datetime.utcnow()
        )
        
        registry.peers[peer_id] = peer_state
        
        assert len(registry.peers) == 2
        assert registry.get_peer_state(peer_id) == peer_state
    
    def test_get_alive_peers(self):
        """Test getting alive peers."""
        config = create_config()
        registry = SwarmRegistry(config, config.agent_id)
        
        # Add alive peer
        alive_id = create_agent_id("SAT001")
        registry.peers[alive_id] = PeerState(
            agent_id=alive_id,
            role=SatelliteRole.PRIMARY,
            last_heartbeat=datetime.utcnow()
        )
        
        # Add dead peer
        dead_id = create_agent_id("SAT002")
        registry.peers[dead_id] = PeerState(
            agent_id=dead_id,
            role=SatelliteRole.PRIMARY,
            last_heartbeat=datetime.utcnow() - timedelta(seconds=100)
        )
        
        alive = registry.get_alive_peers()
        
        assert config.agent_id in alive
        assert alive_id in alive
        assert dead_id not in alive
        assert len(alive) == 2
    
    def test_quorum_calculation(self):
        """Test quorum size calculation."""
        config = create_config()
        registry = SwarmRegistry(config, config.agent_id)
        
        # 1 peer (self) → quorum = 1
        assert registry.get_quorum_size() == 1
        
        # Add peers up to 4
        for i in range(1, 4):
            peer_id = create_agent_id(f"SAT{i:03d}")
            registry.peers[peer_id] = PeerState(
                agent_id=peer_id,
                role=SatelliteRole.PRIMARY,
                last_heartbeat=datetime.utcnow()
            )
        
        # 4 alive → quorum = 3
        assert registry.get_quorum_size() == 3
    
    def test_peer_health(self):
        """Test retrieving peer health."""
        config = create_config()
        registry = SwarmRegistry(config, config.agent_id)
        
        health = HealthSummary(
            anomaly_signature=[0.1] * 32,
            risk_score=0.5,
            recurrence_score=3.0,
            timestamp=datetime.utcnow()
        )
        
        peer_id = create_agent_id("SAT001")
        registry.peers[peer_id] = PeerState(
            agent_id=peer_id,
            role=SatelliteRole.PRIMARY,
            last_heartbeat=datetime.utcnow(),
            health_summary=health
        )
        
        retrieved = registry.get_peer_health(peer_id)
        assert retrieved == health
    
    def test_registry_stats(self):
        """Test registry statistics."""
        config = create_config()
        registry = SwarmRegistry(config, config.agent_id)
        
        # Add alive peer
        alive_id = create_agent_id("SAT001")
        registry.peers[alive_id] = PeerState(
            agent_id=alive_id,
            role=SatelliteRole.PRIMARY,
            last_heartbeat=datetime.utcnow()
        )
        
        # Add dead peer
        dead_id = create_agent_id("SAT002")
        registry.peers[dead_id] = PeerState(
            agent_id=dead_id,
            role=SatelliteRole.PRIMARY,
            last_heartbeat=datetime.utcnow() - timedelta(seconds=100)
        )
        
        stats = registry.get_registry_stats()
        
        assert stats["total_peers"] == 3
        assert stats["alive_peers"] == 2
        assert stats["dead_peers"] == 1
        assert stats["alive_percentage"] == pytest.approx(66.67, rel=0.01)


class TestNetworkPartition:
    """Test network partition scenarios."""
    
    def test_partition_detection(self):
        """Test detecting network partitions."""
        config = create_config()
        registry = SwarmRegistry(config, config.agent_id)
        
        now = datetime.utcnow()
        
        # Add 2 alive peers
        for i in range(1, 3):
            peer_id = create_agent_id(f"SAT{i:03d}")
            registry.peers[peer_id] = PeerState(
                agent_id=peer_id,
                role=SatelliteRole.PRIMARY,
                last_heartbeat=now
            )
        
        # Add 2 dead peers
        for i in range(3, 5):
            peer_id = create_agent_id(f"SAT{i:03d}")
            registry.peers[peer_id] = PeerState(
                agent_id=peer_id,
                role=SatelliteRole.PRIMARY,
                last_heartbeat=now - timedelta(seconds=100)
            )
        
        alive = registry.get_alive_peers()
        
        # Should have self + 2 alive
        assert len(alive) == 3
        assert config.agent_id in alive
    
    def test_partial_quorum(self):
        """Test quorum with partial connectivity."""
        config = create_config()
        registry = SwarmRegistry(config, config.agent_id)
        
        now = datetime.utcnow()
        
        # 3 alive, 2 dead (out of 5)
        for i in range(1, 4):
            peer_id = create_agent_id(f"SAT{i:03d}")
            registry.peers[peer_id] = PeerState(
                agent_id=peer_id,
                role=SatelliteRole.PRIMARY,
                last_heartbeat=now
            )
        
        for i in range(4, 6):
            peer_id = create_agent_id(f"SAT{i:03d}")
            registry.peers[peer_id] = PeerState(
                agent_id=peer_id,
                role=SatelliteRole.PRIMARY,
                last_heartbeat=now - timedelta(seconds=100)
            )
        
        alive = registry.get_alive_peers()
        quorum = registry.get_quorum_size()
        
        # 4 alive (self + 3), quorum = 3
        assert len(alive) == 4
        assert quorum == 3


class TestScalability:
    """Test with large peer counts."""
    
    def test_many_peers(self):
        """Test with 50 peers."""
        agent_id = create_agent_id("SAT0000")
        peers = {create_agent_id(f"SAT{i:04d}"): SatelliteRole.PRIMARY for i in range(50)}
        config = SwarmConfig(
            agent_id=agent_id,
            constellation_id="astra-v3.0",
            role=SatelliteRole.PRIMARY,
            bandwidth_limit_kbps=10,
            peers=peers
        )
        
        registry = SwarmRegistry(config, agent_id)
        
        now = datetime.utcnow()
        
        # Add 49 more peers
        for i in range(1, 50):
            peer_id = create_agent_id(f"SAT{i:04d}")
            registry.peers[peer_id] = PeerState(
                agent_id=peer_id,
                role=SatelliteRole.PRIMARY,
                last_heartbeat=now
            )
        
        assert registry.get_peer_count() == 50
        alive = registry.get_alive_peers()
        assert len(alive) == 50
        assert registry.get_quorum_size() == 26
    
    def test_large_stats(self):
        """Test stats with 50 peers."""
        agent_id = create_agent_id("SAT0000")
        peers = {create_agent_id(f"SAT{i:04d}"): SatelliteRole.PRIMARY for i in range(50)}
        config = SwarmConfig(
            agent_id=agent_id,
            constellation_id="astra-v3.0",
            role=SatelliteRole.PRIMARY,
            bandwidth_limit_kbps=10,
            peers=peers
        )
        
        registry = SwarmRegistry(config, agent_id)
        
        now = datetime.utcnow()
        
        # Add 30 alive, 19 dead
        for i in range(1, 31):
            peer_id = create_agent_id(f"SAT{i:04d}")
            registry.peers[peer_id] = PeerState(
                agent_id=peer_id,
                role=SatelliteRole.PRIMARY,
                last_heartbeat=now
            )
        
        for i in range(31, 50):
            peer_id = create_agent_id(f"SAT{i:04d}")
            registry.peers[peer_id] = PeerState(
                agent_id=peer_id,
                role=SatelliteRole.PRIMARY,
                last_heartbeat=now - timedelta(seconds=100)
            )
        
        stats = registry.get_registry_stats()
        
        assert stats["total_peers"] == 50
        assert stats["alive_peers"] == 31
        assert stats["dead_peers"] == 19
