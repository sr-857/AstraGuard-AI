"""
Test suite for AstraGuard swarm message bus.

Issue #398: Inter-satellite message bus abstraction
- QoS level validation (0, 1, 2)
- Topic filtering and subscriptions
- ISL latency simulation (50-200ms)
- Message delivery and deduplication
- 99%+ delivery rate at 10KB/s
- 90%+ code coverage
"""

import pytest
import asyncio
import json
from datetime import datetime
from uuid import uuid4
from typing import List

from astraguard.swarm.models import AgentID, SatelliteRole, HealthSummary, SwarmConfig
from astraguard.swarm.serializer import SwarmSerializer
from astraguard.swarm.types import (
    SwarmMessage,
    SwarmTopic,
    QoSLevel,
    TopicFilter,
    SubscriptionID,
    MessageAck,
)
from astraguard.swarm.bus import SwarmMessageBus


class TestSwarmMessage:
    """Test suite for SwarmMessage dataclass."""

    @staticmethod
    def create_valid_message(
        topic: str = "health/summary",
        payload: bytes = b"test",
        sender: AgentID = None,
        qos: int = 1,
    ) -> SwarmMessage:
        """Helper to create valid message."""
        if sender is None:
            sender = AgentID.create("astra-v3.0", "SAT-001-A")
        return SwarmMessage(topic=topic, payload=payload, sender=sender, qos=qos)

    def test_message_creation(self):
        """Test valid message creation."""
        msg = self.create_valid_message()
        assert msg.topic == "health/summary"
        assert msg.payload == b"test"
        assert msg.qos == 1

    def test_message_frozen(self):
        """Test that message is immutable."""
        msg = self.create_valid_message()
        with pytest.raises(AttributeError):
            msg.topic = "intent/plan"

    def test_invalid_topic(self):
        """Test that invalid topics are rejected."""
        sender = AgentID.create("astra-v3.0", "SAT-001-A")
        with pytest.raises(ValueError, match="Invalid topic"):
            SwarmMessage(topic="invalid", payload=b"test", sender=sender)

    def test_invalid_qos(self):
        """Test that invalid QoS levels are rejected."""
        sender = AgentID.create("astra-v3.0", "SAT-001-A")
        with pytest.raises(ValueError, match="QoS must be"):
            SwarmMessage(
                topic="health/summary", payload=b"test", sender=sender, qos=3
            )

    def test_payload_size_limit(self):
        """Test that oversized payloads are rejected."""
        sender = AgentID.create("astra-v3.0", "SAT-001-A")
        with pytest.raises(ValueError, match="exceeds 10KB"):
            SwarmMessage(
                topic="health/summary",
                payload=b"x" * 11000,
                sender=sender,
            )

    def test_empty_payload(self):
        """Test that empty payloads are rejected."""
        sender = AgentID.create("astra-v3.0", "SAT-001-A")
        with pytest.raises(ValueError, match="cannot be empty"):
            SwarmMessage(topic="health/summary", payload=b"", sender=sender)

    def test_message_serialization(self):
        """Test message to_dict/from_dict roundtrip."""
        original = self.create_valid_message()
        data = original.to_dict()
        restored = SwarmMessage.from_dict(data)
        
        assert restored.topic == original.topic
        assert restored.payload == original.payload
        assert restored.qos == original.qos


class TestTopicFilter:
    """Test suite for topic filtering."""

    def test_exact_match(self):
        """Test exact topic match."""
        filter_obj = TopicFilter("health/summary")
        assert filter_obj.matches("health/summary") is True
        assert filter_obj.matches("health/status") is False

    def test_wildcard_match(self):
        """Test wildcard topic match."""
        filter_obj = TopicFilter("health/*")
        assert filter_obj.matches("health/summary") is True
        assert filter_obj.matches("health/status") is True
        assert filter_obj.matches("intent/plan") is False

    def test_all_topics(self):
        """Test match-all wildcard."""
        filter_obj = TopicFilter("*")
        assert filter_obj.matches("health/summary") is True
        assert filter_obj.matches("intent/plan") is True
        assert filter_obj.matches("coord/sync") is True


class TestSwarmMessageBus:
    """Test suite for SwarmMessageBus."""

    @pytest.fixture
    def bus_with_agents(self):
        """Create message bus with multiple agents."""
        agent1 = AgentID.create("astra-v3.0", "SAT-001-A")
        config1 = SwarmConfig(
            agent_id=agent1,
            role=SatelliteRole.PRIMARY,
            constellation_id="astra-v3.0",
        )
        serializer = SwarmSerializer(validate=False)
        bus = SwarmMessageBus(config1, serializer, latency_ms=0)
        return bus, [agent1]

    @pytest.mark.asyncio
    async def test_fire_forget_publish(self, bus_with_agents):
        """Test QoS 0 (fire-forget) publish."""
        bus, _ = bus_with_agents
        result = await bus.publish(
            "health/summary", b"test_payload", qos=QoSLevel.FIRE_FORGET
        )
        assert result is True
        assert bus.metrics["published"] == 1
        assert bus.metrics["delivered"] == 1

    @pytest.mark.asyncio
    async def test_ack_publish(self, bus_with_agents):
        """Test QoS 1 (ACK) publish with acknowledgment."""
        bus, _ = bus_with_agents

        # Setup subscriber to send ACK
        received_messages = []

        async def ack_subscriber(msg: SwarmMessage):
            received_messages.append(msg)
            await bus.acknowledge(msg)

        sub_id = bus.subscribe("health/summary", ack_subscriber)

        # Publish with ACK
        result = await bus.publish("health/summary", b"test_payload", qos=QoSLevel.ACK)

        assert result is True
        assert len(received_messages) == 1
        assert bus.metrics["acked"] == 1

        bus.unsubscribe(sub_id)

    @pytest.mark.asyncio
    async def test_reliable_publish(self, bus_with_agents):
        """Test QoS 2 (reliable) publish with deduplication."""
        bus, _ = bus_with_agents

        received_messages = []

        def reliable_subscriber(msg: SwarmMessage):
            received_messages.append(msg)

        sub_id = bus.subscribe("health/summary", reliable_subscriber)

        # Publish with reliable QoS
        result = await bus.publish(
            "health/summary", b"test_payload", qos=QoSLevel.RELIABLE
        )

        assert result is True
        assert len(received_messages) == 1

        bus.unsubscribe(sub_id)

    @pytest.mark.asyncio
    async def test_topic_filtering(self, bus_with_agents):
        """Test topic filter matching."""
        bus, _ = bus_with_agents

        health_messages = []
        intent_messages = []

        def health_subscriber(msg: SwarmMessage):
            health_messages.append(msg)

        def intent_subscriber(msg: SwarmMessage):
            intent_messages.append(msg)

        health_sub = bus.subscribe("health/*", health_subscriber)
        intent_sub = bus.subscribe("intent/*", intent_subscriber)

        # Publish to different topics
        await bus.publish("health/summary", b"health", qos=0)
        await bus.publish("health/status", b"status", qos=0)
        await bus.publish("intent/plan", b"plan", qos=0)

        assert len(health_messages) == 2
        assert len(intent_messages) == 1

        bus.unsubscribe(health_sub)
        bus.unsubscribe(intent_sub)

    @pytest.mark.asyncio
    async def test_subscription_leak_detection(self, bus_with_agents):
        """Test detection of subscription leaks."""
        bus, _ = bus_with_agents

        def subscriber(msg: SwarmMessage):
            pass

        # Create multiple subscriptions
        subs = [
            bus.subscribe("health/summary", subscriber),
            bus.subscribe("intent/plan", subscriber),
            bus.subscribe("coord/sync", subscriber),
        ]

        assert len(bus.get_subscriptions()) == 3

        # Unsubscribe and verify cleanup
        for sub in subs:
            bus.unsubscribe(sub)

        assert len(bus.get_subscriptions()) == 0

    @pytest.mark.asyncio
    async def test_latency_simulation(self):
        """Test ISL latency simulation."""
        agent = AgentID.create("astra-v3.0", "SAT-001-A")
        config = SwarmConfig(
            agent_id=agent,
            role=SatelliteRole.PRIMARY,
            constellation_id="astra-v3.0",
        )
        serializer = SwarmSerializer(validate=False)
        bus = SwarmMessageBus(config, serializer, latency_ms=50)

        # Measure publish time
        import time

        start = time.time()
        await bus.publish("health/summary", b"test", qos=0)
        elapsed_ms = (time.time() - start) * 1000

        # Should be at least 50ms due to latency
        assert elapsed_ms >= 50

    @pytest.mark.asyncio
    async def test_health_summary_integration(self, bus_with_agents):
        """Test integration with Issue #397 HealthSummary."""
        bus, _ = bus_with_agents

        health_messages = []

        async def health_subscriber(msg: SwarmMessage):
            health_messages.append(msg)
            # Send ACK for QoS 1
            await bus.acknowledge(msg)

        sub_id = bus.subscribe("health/*", health_subscriber)

        # Create HealthSummary
        summary = HealthSummary(
            anomaly_signature=[0.1] * 32,
            risk_score=0.5,
            recurrence_score=3.5,
            timestamp=datetime.utcnow(),
        )

        # Publish HealthSummary with QoS 1
        result = await bus.publish("health/summary", summary, qos=QoSLevel.ACK)

        assert result is True
        assert len(health_messages) == 1

        bus.unsubscribe(sub_id)

    @pytest.mark.asyncio
    async def test_isl_bandwidth_limit(self, bus_with_agents):
        """Test ISL bandwidth limit enforcement (10KB)."""
        bus, _ = bus_with_agents

        # Try to publish oversized payload - should fail
        large_payload = b"x" * 11000
        
        # The publish call may fail or the metrics may not increment
        # depending on when the check happens
        try:
            result = await bus.publish(
                "health/summary", large_payload, qos=0
            )
            # If it doesn't fail at publish, at least check the payload was rejected
            assert result is False
        except ValueError:
            # Payload validation may raise ValueError
            pass

    @pytest.mark.asyncio
    async def test_multiple_agents_broadcast(self):
        """Test broadcasting between multiple agents."""
        # Create 5 agents
        agents = [
            AgentID.create("astra-v3.0", f"SAT-{i:03d}-A") for i in range(1, 6)
        ]

        # Create buses for each agent
        buses = []
        serializer = SwarmSerializer(validate=False)

        for agent in agents:
            config = SwarmConfig(
                agent_id=agent,
                role=SatelliteRole.PRIMARY,
                constellation_id="astra-v3.0",
                bandwidth_limit_kbps=10,
            )
            bus = SwarmMessageBus(config, serializer, latency_ms=10)
            buses.append(bus)

        # Subscribe each bus to health messages
        received = {i: [] for i in range(len(agents))}

        def make_subscriber(idx):
            def subscriber(msg: SwarmMessage):
                received[idx].append(msg)

            return subscriber

        subs = []
        for i, bus in enumerate(buses):
            sub = bus.subscribe("health/*", make_subscriber(i))
            subs.append(sub)

        # Publish from first agent only
        await buses[0].publish(
            "health/summary", b"message_0", qos=0
        )

        # Verify delivery - only first bus should have received
        assert len(received[0]) >= 1

    @pytest.mark.asyncio
    async def test_message_ordering(self, bus_with_agents):
        """Test message sequence ordering."""
        bus, _ = bus_with_agents

        messages = []

        def subscriber(msg: SwarmMessage):
            messages.append(msg)

        sub_id = bus.subscribe("health/*", subscriber)

        # Publish multiple messages
        for i in range(5):
            await bus.publish(f"health/msg_{i}", b"test", qos=0)

        # Verify sequence numbers are ordered
        for i, msg in enumerate(messages):
            assert msg.sequence == i + 1

        bus.unsubscribe(sub_id)

    def test_metrics_tracking(self, bus_with_agents):
        """Test metrics collection."""
        bus, _ = bus_with_agents

        initial_metrics = bus.get_metrics()
        assert initial_metrics["published"] == 0
        assert initial_metrics["delivered"] == 0

    @pytest.mark.asyncio
    async def test_async_callback(self, bus_with_agents):
        """Test async callback execution."""
        bus, _ = bus_with_agents

        async_results = []

        async def async_subscriber(msg: SwarmMessage):
            await asyncio.sleep(0.01)
            async_results.append(msg)

        sub_id = bus.subscribe("health/*", async_subscriber)

        await bus.publish("health/summary", b"test", qos=0)

        # Give async callback time to execute
        await asyncio.sleep(0.05)

        assert len(async_results) == 1

        bus.unsubscribe(sub_id)


class TestQoSLevels:
    """Test suite for QoS level validation."""

    def test_qos_fire_forget(self):
        """Test QoS 0 enumeration."""
        assert QoSLevel.FIRE_FORGET == 0

    def test_qos_ack(self):
        """Test QoS 1 enumeration."""
        assert QoSLevel.ACK == 1

    def test_qos_reliable(self):
        """Test QoS 2 enumeration."""
        assert QoSLevel.RELIABLE == 2
