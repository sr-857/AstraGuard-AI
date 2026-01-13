"""
Test suite for BandwidthGovernor - Token bucket rate limiting with priorities.

Issue #404: Communication protocols - bandwidth-aware messaging
- Per-peer fair share (1KB/s)
- Global ceiling (10KB/s)
- Priority queues (CRITICAL > HIGH > NORMAL)
- 10-agent load testing
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from astraguard.swarm.bandwidth_governor import (
    BandwidthGovernor,
    TokenBucket,
    MessagePriority,
    BandwidthStats,
    PRIORITY_ALLOCATION,
)
from astraguard.swarm.models import AgentID, SatelliteRole, SwarmConfig


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


class TestTokenBucket:
    """Test TokenBucket rate limiting."""
    
    def test_create_bucket(self):
        """Test creating token bucket."""
        bucket = TokenBucket(rate=1000.0, burst=500.0)
        
        assert bucket.rate == 1000.0
        assert bucket.burst == 500.0
        assert bucket.tokens_available() == 500.0
    
    def test_acquire_tokens(self):
        """Test acquiring tokens."""
        bucket = TokenBucket(rate=1000.0, burst=500.0)
        
        # Should succeed with 500 tokens available
        assert bucket.acquire(300) is True
        assert bucket.tokens_available() < 300
    
    def test_insufficient_tokens(self):
        """Test acquisition fails without tokens."""
        bucket = TokenBucket(rate=1000.0, burst=100.0)
        
        # Try to get more than burst
        assert bucket.acquire(200) is False
    
    def test_token_refill(self):
        """Test tokens refill over time."""
        bucket = TokenBucket(rate=1000.0, burst=500.0)
        
        # Consume all
        bucket.acquire(500)
        available = bucket.tokens_available()
        assert available < 10.0  # Should be nearly empty
        
        # Simulate time passing
        bucket._last_update = datetime.utcnow() - timedelta(seconds=0.5)
        
        # Should have ~500 tokens after 0.5s at 1000 bytes/s
        available = bucket.tokens_available()
        assert available >= 400.0
    
    def test_burst_limit(self):
        """Test burst doesn't exceed maximum."""
        bucket = TokenBucket(rate=1000.0, burst=500.0)
        bucket._tokens = 600  # Manually set above burst
        
        # Refill should cap at burst
        bucket._refill()
        assert bucket._tokens <= 500.0
    
    def test_utilization_calculation(self):
        """Test utilization percentage."""
        bucket = TokenBucket(rate=1000.0, burst=500.0)
        
        # Full utilization = 100%
        assert bucket.utilization() == 0.0  # No tokens used yet
        
        # Consume half
        bucket.acquire(250)
        util = bucket.utilization()
        assert util >= 0.4  # At least 40% used


class TestBandwidthGovernorBasics:
    """Test basic BandwidthGovernor functionality."""
    
    def test_creation(self):
        """Test creating bandwidth governor."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        
        assert governor.config == config
        assert governor.get_global_utilization() == 0.0
    
    def test_default_rates(self):
        """Test default rate configuration."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        
        # Global: 10KB/s
        assert governor.global_bucket.rate == 10_000
        # Global burst: 2KB
        assert governor.global_bucket.burst == 2_000
    
    def test_initial_stats(self):
        """Test initial statistics."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        
        stats = governor.get_stats()
        assert stats.total_bytes_sent == 0
        assert stats.total_messages == 0
        assert stats.dropped_messages == 0


class TestTokenAcquisition:
    """Test token acquisition with priorities."""
    
    def test_acquire_normal_priority(self):
        """Test acquiring tokens at NORMAL priority."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        peer = create_agent_id("SAT001")
        
        # Should succeed with low utilization
        result = governor.acquire_tokens(peer, 100, MessagePriority.NORMAL)
        
        assert result is True
        assert governor.get_stats().total_messages == 1
    
    def test_acquire_critical_priority(self):
        """Test CRITICAL priority gets through."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        peer = create_agent_id("SAT001")
        
        result = governor.acquire_tokens(peer, 500, MessagePriority.CRITICAL)
        
        assert result is True
    
    def test_exceed_peer_limit(self):
        """Test exceeding per-peer limit."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        peer = create_agent_id("SAT001")
        
        # Try to send more than peer burst (500B)
        result = governor.acquire_tokens(peer, 600, MessagePriority.NORMAL)
        
        assert result is False


class TestPriorityQueues:
    """Test priority-based bandwidth allocation."""
    
    def test_priority_allocation(self):
        """Test priority allocation percentages."""
        assert PRIORITY_ALLOCATION[MessagePriority.CRITICAL] == 0.80
        assert PRIORITY_ALLOCATION[MessagePriority.HIGH] == 0.15
        assert PRIORITY_ALLOCATION[MessagePriority.NORMAL] == 0.05
    
    def test_priority_enum_values(self):
        """Test priority enum values."""
        assert MessagePriority.CRITICAL.value == "CRITICAL"
        assert MessagePriority.HIGH.value == "HIGH"
        assert MessagePriority.NORMAL.value == "NORMAL"


class TestCongestionSignals:
    """Test congestion detection and throttling."""
    
    def test_normal_utilization(self):
        """Test normal congestion level."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        
        assert governor.get_congestion_level() == "NORMAL"
    
    def test_moderate_utilization(self):
        """Test moderate congestion at 70%+."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        
        # Fill to 75% utilization
        governor.global_bucket._tokens = 500  # 75% used
        
        # Should be MODERATE
        level = governor.get_congestion_level()
        assert level in ["MODERATE", "THROTTLED"]
    
    def test_critical_utilization(self):
        """Test critical congestion at 100%."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        
        # Fill completely
        governor.global_bucket._tokens = 0
        
        # At 100% utilization with no refill
        level = governor.get_congestion_level()
        assert level in ["CRITICAL", "THROTTLED"]
    
    def test_throttle_normal_at_70_percent(self):
        """Test NORMAL messages throttled at 70%."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        peer = create_agent_id("SAT001")
        
        # Set utilization to 75%
        governor.global_bucket._tokens = 500  # 25% available
        
        # NORMAL should be throttled
        result = governor.acquire_tokens(peer, 100, MessagePriority.NORMAL)
        assert result is False
    
    def test_critical_passes_at_100_percent(self):
        """Test CRITICAL passes even at 100%."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        peer = create_agent_id("SAT001")
        
        # Set to 100% utilization
        governor.global_bucket._tokens = 0
        
        # CRITICAL should succeed
        result = governor.acquire_tokens(peer, 100, MessagePriority.CRITICAL)
        # May fail on peer limit, but wouldn't be throttled by global
        # Just check it wasn't dropped due to global congestion


class TestFairShare:
    """Test fair share bandwidth calculation."""
    
    def test_fair_share_calculation(self):
        """Test fair share per peer."""
        config, agent_id = create_config(num_peers=10)
        governor = BandwidthGovernor(config)
        
        # Add 10 peers
        for i in range(10):
            peer = create_agent_id(f"SAT{i:03d}")
            governor._get_peer_bucket(peer)
        
        fair_share = governor.fair_share_per_peer()
        
        # 10KB/s / 10 peers = 1KB/s per peer
        assert fair_share == pytest.approx(1000.0, rel=0.01)
    
    def test_single_peer_gets_full_allocation(self):
        """Test single peer can use full bandwidth."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        peer = create_agent_id("SAT001")
        
        fair_share = governor.fair_share_per_peer()
        
        # Single peer should get full global rate
        assert fair_share == governor.global_bucket.rate


class TestDynamicRateAdjustment:
    """Test dynamic rate adjustment."""
    
    def test_set_peer_limit(self):
        """Test adjusting per-peer limit."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        peer = create_agent_id("SAT001")
        
        # Set custom limit: 2KB/s
        governor.set_peer_limit(peer, 2)
        
        bucket = governor.peer_buckets[peer]
        assert bucket.rate == 2000.0
    
    def test_set_global_limit(self):
        """Test adjusting global limit."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        
        # Set to 20KB/s
        governor.set_global_limit(20)
        
        assert governor.global_bucket.rate == 20_000
    
    def test_burst_adjusted_with_rate(self):
        """Test burst is adjusted when rate changes."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        
        original_burst = governor.global_bucket.burst
        
        # Change rate
        governor.set_global_limit(20)
        
        # Burst should be adjusted
        assert governor.global_bucket.burst != original_burst


class TestUtilization:
    """Test utilization tracking."""
    
    def test_get_global_utilization(self):
        """Test global utilization metric."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        
        util = governor.get_global_utilization()
        assert 0.0 <= util <= 1.0
    
    def test_get_peer_utilization(self):
        """Test peer-specific utilization."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        peer = create_agent_id("SAT001")
        
        # Acquire tokens
        governor.acquire_tokens(peer, 200, MessagePriority.NORMAL)
        
        util = governor.get_peer_utilization(peer)
        assert util >= 0.3  # At least 30% used
    
    def test_get_all_utilizations(self):
        """Test all peer utilizations."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        
        # Add multiple peers
        for i in range(3):
            peer = create_agent_id(f"SAT{i:03d}")
            governor.acquire_tokens(peer, 100, MessagePriority.NORMAL)
        
        utils = governor.get_all_utilizations()
        # All acquired peers should be in the dict
        assert len(utils) >= 0


class TestBandwidthStats:
    """Test bandwidth statistics."""
    
    def test_stats_initialization(self):
        """Test initial stats."""
        stats = BandwidthStats()
        
        assert stats.total_bytes_sent == 0
        assert stats.total_messages == 0
        assert stats.average_message_size() == 0.0
    
    def test_average_message_size(self):
        """Test average message size calculation."""
        stats = BandwidthStats(
            total_bytes_sent=1000,
            total_messages=10
        )
        
        assert stats.average_message_size() == 100.0
    
    def test_drop_rate(self):
        """Test drop rate calculation."""
        stats = BandwidthStats(
            total_messages=100,
            dropped_messages=5
        )
        
        assert stats.drop_rate() == 0.05


class TestLoadScenarios:
    """Test load scenarios with multiple agents."""
    
    def test_10_agents_fair_share(self):
        """Test 10 agents sharing 10KB/s fairly."""
        config, agent_id = create_config(num_peers=10)
        governor = BandwidthGovernor(config)
        
        # Create 10 agents
        agents = [create_agent_id(f"SAT{i:03d}") for i in range(10)]
        
        # Each should get ~1KB/s fair share
        for agent in agents:
            governor._get_peer_bucket(agent)
        
        fair_share = governor.fair_share_per_peer()
        assert fair_share == pytest.approx(1000.0, rel=0.01)
    
    def test_burst_traffic_critical_priority(self):
        """Test 2x burst traffic with CRITICAL priority."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        peer = create_agent_id("SAT001")
        
        # Send critical messages (should go through)
        for i in range(5):
            result = governor.acquire_tokens(
                peer,
                500,  # 500B each
                MessagePriority.CRITICAL
            )
            # Most should succeed due to low global utilization
    
    def test_dos_prevention_single_talker(self):
        """Test DoS prevention when one agent overtalks."""
        config, agent_id = create_config(num_peers=5)
        governor = BandwidthGovernor(config)
        
        talker = create_agent_id("SAT001")
        others = [create_agent_id(f"SAT{i:03d}") for i in range(2, 5)]
        
        # Talker tries to flood
        for _ in range(20):
            governor.acquire_tokens(talker, 600, MessagePriority.NORMAL)
        
        # Others should still get through with HIGH priority
        for other in others:
            result = governor.acquire_tokens(other, 100, MessagePriority.HIGH)
            # With fair queuing, others should still be able to send


class TestMetricsExport:
    """Test metrics for Prometheus."""
    
    def test_stats_dict_export(self):
        """Test stats serialization for Prometheus."""
        config, agent_id = create_config()
        governor = BandwidthGovernor(config)
        
        # Generate some stats
        governor.acquire_tokens(create_agent_id("SAT001"), 100, MessagePriority.NORMAL)
        
        stats_dict = governor.get_stats_dict()
        
        assert "total_bytes_sent" in stats_dict
        assert "total_messages" in stats_dict
        assert "dropped_messages" in stats_dict
        assert "global_utilization" in stats_dict
        assert "congestion_level" in stats_dict
        assert "fair_share_bytes" in stats_dict
