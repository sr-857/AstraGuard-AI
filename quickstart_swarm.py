#!/usr/bin/env python3
"""
Quick Start Guide - Issue #397 SwarmConfig Implementation

This file demonstrates usage patterns for the newly implemented swarm models.
Run with: python quickstart_swarm.py
"""

from datetime import datetime
from astraguard.swarm.models import AgentID, SatelliteRole, HealthSummary, SwarmConfig
from astraguard.swarm.serializer import SwarmSerializer
from config.swarm_config import config


def example_agent_creation():
    """Example 1: Creating agent identifiers."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Agent Creation")
    print("=" * 70)
    
    # Using factory method (recommended)
    agent = AgentID.create("astra-v3.0", "SAT-001-A")
    print(f"✓ Created agent: {agent.satellite_serial}")
    print(f"  UUID: {agent.uuid}")
    
    # UUIDs are deterministic
    agent2 = AgentID.create("astra-v3.0", "SAT-001-A")
    print(f"✓ Same input → same UUID: {agent.uuid == agent2.uuid}")


def example_health_telemetry():
    """Example 2: Creating and serializing health telemetry."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Health Telemetry")
    print("=" * 70)
    
    summary = HealthSummary(
        anomaly_signature=[0.1 * i for i in range(32)],
        risk_score=0.75,
        recurrence_score=5.2,
        timestamp=datetime.utcnow(),
    )
    print(f"✓ Created HealthSummary")
    print(f"  Risk Score: {summary.risk_score}")
    print(f"  Recurrence Score: {summary.recurrence_score}")
    print(f"  PCA Dimensions: {len(summary.anomaly_signature)}")


def example_serialization():
    """Example 3: Serialization with compression."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Serialization & Compression")
    print("=" * 70)
    
    serializer = SwarmSerializer(validate=True)
    
    summary = HealthSummary(
        anomaly_signature=[0.1] * 32,
        risk_score=0.5,
        recurrence_score=3.5,
        timestamp=datetime.utcnow(),
    )
    
    # Uncompressed
    uncompressed = serializer.serialize_health(summary, compress=False)
    print(f"✓ JSON Size: {len(uncompressed)} bytes")
    
    # Try compression (if lz4 available)
    try:
        compressed = serializer.serialize_health(summary, compress=True)
        stats = SwarmSerializer.get_compression_stats(
            len(uncompressed), len(compressed)
        )
        print(f"✓ LZ4 Compressed: {len(compressed)} bytes")
        print(f"  Ratio: {stats['compression_ratio']}")
    except ValueError:
        print("✓ LZ4 not available (optional)")
    
    # Roundtrip
    restored = serializer.deserialize_health(uncompressed, compressed=False)
    print(f"✓ Roundtrip successful: {restored.risk_score == summary.risk_score}")


def example_swarm_configuration():
    """Example 4: Swarm configuration with peers."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Swarm Configuration")
    print("=" * 70)
    
    # Create agents
    primary = AgentID.create("astra-v3.0", "SAT-001-A")
    backup = AgentID.create("astra-v3.0", "SAT-002-A")
    standby = AgentID.create("astra-v3.0", "SAT-003-A")
    
    # Create swarm config
    config_obj = SwarmConfig(
        agent_id=primary,
        role=SatelliteRole.PRIMARY,
        constellation_id="astra-v3.0",
        peers=[backup, standby],
        bandwidth_limit_kbps=10,
    )
    
    print(f"✓ Created SwarmConfig")
    print(f"  Agent: {config_obj.agent_id.satellite_serial}")
    print(f"  Role: {config_obj.role.value}")
    print(f"  Peers: {len(config_obj.peers)}")
    print(f"  Bandwidth: {config_obj.bandwidth_limit_kbps} KB/s")


def example_feature_flags():
    """Example 5: Feature flag configuration."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Feature Flag Configuration")
    print("=" * 70)
    
    print(f"Current Config:")
    print(f"  Swarm Enabled: {config.is_swarm_enabled()}")
    print(f"  Schema Validation: {config.SWARM_SCHEMA_VALIDATION}")
    print(f"  Compression: {config.SWARM_COMPRESSION}")
    print(f"  Max Payload: {config.SWARM_MAX_PAYLOAD} bytes")
    
    print(f"\n✓ Enable swarm at runtime:")
    config.enable_swarm_mode()
    print(f"  Swarm Enabled: {config.is_swarm_enabled()}")


def example_jsonschema_validation():
    """Example 6: JSONSchema validation."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: JSONSchema Validation")
    print("=" * 70)
    
    serializer = SwarmSerializer(validate=True)
    
    # Valid data
    valid_data = {
        "anomaly_signature": [0.1] * 32,
        "risk_score": 0.5,
        "recurrence_score": 3.5,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    try:
        serializer.validate_schema(valid_data, "HealthSummary")
        print("✓ Valid HealthSummary passed validation")
    except Exception as e:
        print(f"✗ Validation failed: {e}")
    
    # Invalid data (31-dim instead of 32)
    invalid_data = {
        "anomaly_signature": [0.1] * 31,  # Wrong!
        "risk_score": 0.5,
        "recurrence_score": 3.5,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    try:
        serializer.validate_schema(invalid_data, "HealthSummary")
        print("✗ Invalid data passed (should have failed)")
    except Exception as e:
        print(f"✓ Invalid data rejected (expected)")


def example_error_handling():
    """Example 7: Error handling and constraints."""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Error Handling & Constraints")
    print("=" * 70)
    
    # Risk score bounds
    try:
        bad_summary = HealthSummary(
            anomaly_signature=[0.1] * 32,
            risk_score=1.5,  # Should be [0.0, 1.0]
            recurrence_score=3.5,
            timestamp=datetime.utcnow(),
        )
    except ValueError as e:
        print(f"✓ Risk score validation caught: {str(e)[:50]}...")
    
    # Constellation mismatch
    agent = AgentID.create("astra-v3.0", "SAT-001-A")
    try:
        bad_config = SwarmConfig(
            agent_id=agent,
            role=SatelliteRole.PRIMARY,
            constellation_id="astra-v2.0",  # Mismatch!
        )
    except ValueError as e:
        print(f"✓ Constellation validation caught: {str(e)[:50]}...")
    
    # AgentID immutability
    agent = AgentID.create("astra-v3.0", "SAT-001-A")
    try:
        agent.satellite_serial = "SAT-002-A"  # Try to modify frozen
    except AttributeError:
        print(f"✓ Immutability enforced (frozen dataclass)")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  AstraGuard Swarm Models - Issue #397 Quick Start".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    
    example_agent_creation()
    example_health_telemetry()
    example_serialization()
    example_swarm_configuration()
    example_feature_flags()
    example_jsonschema_validation()
    example_error_handling()
    
    print("\n" + "=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)
    print("\nFor more information, see:")
    print("  - docs/swarm-models.md: Complete specification")
    print("  - tests/swarm/test_models.py: Test suite with examples")
    print("  - benchmarks/state_serialization.py: Performance benchmarks")
    print()


if __name__ == "__main__":
    main()
