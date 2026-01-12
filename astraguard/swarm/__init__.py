"""
AstraGuard Swarm Module - Multi-Agent Intelligence Framework

Provides data models, serialization, and orchestration for distributed
satellite constellation operations with bandwidth-constrained ISL links.

Issue #397: Data models and serialization foundation
Issue #398: Inter-satellite message bus abstraction
"""

from astraguard.swarm.models import (
    AgentID,
    SatelliteRole,
    HealthSummary,
    SwarmConfig,
)
from astraguard.swarm.serializer import SwarmSerializer
from astraguard.swarm.types import (
    SwarmMessage,
    SwarmTopic,
    QoSLevel,
    TopicFilter,
    SubscriptionID,
    MessageAck,
    IntentMessage,
    PriorityEnum,
)
from astraguard.swarm.bus import SwarmMessageBus
from astraguard.swarm.compressor import StateCompressor, CompressionStats
from astraguard.swarm.registry import SwarmRegistry, PeerState
from astraguard.swarm.health_broadcaster import HealthBroadcaster, BroadcastMetrics
from astraguard.swarm.intent_broadcaster import IntentBroadcaster, IntentStats
from astraguard.swarm.reliable_delivery import ReliableDelivery, SentMsg, DeliveryStats, AckStatus
from astraguard.swarm.bandwidth_governor import BandwidthGovernor, TokenBucket, MessagePriority, BandwidthStats
from astraguard.swarm.leader_election import LeaderElection, ElectionState, ElectionMetrics

__all__ = [
    # Models (Issue #397)
    "AgentID",
    "SatelliteRole",
    "HealthSummary",
    "SwarmConfig",
    # Serialization (Issue #397)
    "SwarmSerializer",
    # Message types (Issue #398)
    "SwarmMessage",
    "SwarmTopic",
    "QoSLevel",
    "TopicFilter",
    "SubscriptionID",
    "MessageAck",
    # Intent types (Issue #402)
    "IntentMessage",
    "PriorityEnum",
    # Message bus (Issue #398)
    "SwarmMessageBus",
    # Compression (Issue #399)
    "StateCompressor",
    "CompressionStats",
    # Registry (Issue #400)
    "SwarmRegistry",
    "PeerState",
    # Health Broadcasting (Issue #401)
    "HealthBroadcaster",
    "BroadcastMetrics",
    # Intent Broadcasting (Issue #402)
    "IntentBroadcaster",
    "IntentStats",
    # Reliable Delivery (Issue #403)
    "ReliableDelivery",
    "SentMsg",
    "DeliveryStats",
    "AckStatus",
    # Bandwidth Governor (Issue #404)
    "BandwidthGovernor",
    "TokenBucket",
    "MessagePriority",
    "BandwidthStats",
    # Leader Election (Issue #405)
    "LeaderElection",
    "ElectionState",
    "ElectionMetrics",
]
