"""
Distributed Resilience Coordinator for cluster-wide consensus.

Provides:
- Leader election coordination
- State publishing to cluster
- Vote collection and majority voting
- Quorum-based consensus decisions
- Multi-instance synchronization
"""

import asyncio
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import Counter
from backend.redis_client import RedisClient

logger = logging.getLogger(__name__)


@dataclass
class ConsensusDecision:
    """Consensus decision from cluster quorum."""
    
    circuit_state: str  # e.g., "CLOSED", "OPEN", "HALF_OPEN"
    fallback_mode: str  # e.g., "PRIMARY", "HEURISTIC", "SAFE"
    leader_instance: str  # Instance ID of current leader
    quorum_met: bool  # Whether quorum threshold was met
    voting_instances: int  # Number of instances that voted
    consensus_strength: float  # Percentage agreement (0.0 - 1.0)

    def dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class DistributedResilienceCoordinator:
    """Cluster-wide resilience state coordination via Redis.
    
    Responsibilities:
    - Lead cluster-wide state synchronization
    - Coordinate leader election
    - Collect votes from all instances
    - Apply majority voting for circuit/fallback decisions
    - Publish local state changes
    - Maintain quorum requirements
    """

    def __init__(
        self,
        redis_client: RedisClient,
        health_monitor,
        recovery_orchestrator=None,
        fallback_manager=None,
        quorum_threshold: float = 0.5,  # >50% for consensus
    ):
        """Initialize distributed coordinator.
        
        Args:
            redis_client: RedisClient instance for communication
            health_monitor: HealthMonitor for local state
            recovery_orchestrator: Recovery orchestrator for actions
            fallback_manager: FallbackManager for mode changes
            quorum_threshold: Minimum fraction for quorum (default: >50%)
        """
        self.redis = redis_client
        self.health = health_monitor
        self.recovery = recovery_orchestrator
        self.fallback = fallback_manager
        self.quorum_threshold = quorum_threshold

        # Instance identification
        self.instance_id = f"astra-{uuid.uuid4().hex[:8]}"
        self.is_leader = False

        # Background tasks
        self._running = False
        self._state_publisher_task = None
        self._leader_renewal_task = None
        self._vote_collector_task = None

        # Metrics
        self.election_wins = 0
        self.consensus_decisions = 0
        self.last_consensus_time = None

        logger.info(f"Initialized DistributedResilienceCoordinator: {self.instance_id}")

    async def startup(self):
        """Initialize distributed coordination.
        
        Attempts leader election and starts background tasks.
        """
        if not self.redis.connected:
            logger.error("Redis not connected, cannot start coordinator")
            return

        # Attempt leader election
        self.is_leader = await self.redis.leader_election(self.instance_id)
        if self.is_leader:
            self.election_wins += 1
            logger.info(f"Instance {self.instance_id} elected as LEADER")
        else:
            logger.info(f"Instance {self.instance_id} running as FOLLOWER")

        # Start background tasks
        self._running = True
        self._state_publisher_task = asyncio.create_task(self._state_publisher())
        self._leader_renewal_task = asyncio.create_task(self._leader_renewal())
        self._vote_collector_task = asyncio.create_task(self._vote_collector())

        logger.info("Distributed coordination started")

    async def shutdown(self):
        """Gracefully shutdown coordination."""
        self._running = False

        # Cancel and await background tasks with proper exception handling
        tasks_to_cancel = [
            ("state_publisher", self._state_publisher_task),
            ("leader_renewal", self._leader_renewal_task),
            ("vote_collector", self._vote_collector_task),
        ]

        for task_name, task in tasks_to_cancel:
            if task:
                try:
                    task.cancel()
                    await task
                except asyncio.CancelledError:
                    logger.debug(f"Task {task_name} cancelled successfully")
                except Exception as e:
                    logger.warning(f"Error during {task_name} shutdown: {e}")
                finally:
                    # Clear task reference
                    if task_name == "state_publisher":
                        self._state_publisher_task = None
                    elif task_name == "leader_renewal":
                        self._leader_renewal_task = None
                    elif task_name == "vote_collector":
                        self._vote_collector_task = None

        logger.info("Distributed coordination stopped")

    async def _state_publisher(self, interval: int = 5):
        """Continuously publish local state to cluster.
        
        Args:
            interval: Publication interval in seconds
        """
        while self._running:
            try:
                # Get local state
                local_state = await self.health.get_comprehensive_state()

                # Add instance metadata
                state_payload = {
                    "instance_id": self.instance_id,
                    "is_leader": self.is_leader,
                    "timestamp": datetime.utcnow().isoformat(),
                    "state": local_state,
                }

                # Publish to cluster
                await self.redis.publish_state(
                    "astra:resilience:state", state_payload
                )

                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"State publisher error: {e}")
                await asyncio.sleep(interval)

    async def _leader_renewal(self, interval: int = 15):
        """Renew leadership TTL if leader.
        
        Args:
            interval: Renewal interval in seconds
        """
        while self._running:
            try:
                if self.is_leader:
                    renewed = await self.redis.renew_leadership(
                        self.instance_id, ttl=30
                    )
                    if not renewed:
                        logger.warning(f"Lost leadership: {self.instance_id}")
                        self.is_leader = False
                    else:
                        logger.debug("Leadership renewed")
                else:
                    # Try to become leader if not already
                    self.is_leader = await self.redis.leader_election(
                        self.instance_id, ttl=30
                    )
                    if self.is_leader:
                        self.election_wins += 1
                        logger.info(f"Became leader: {self.instance_id}")

                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Leader renewal error: {e}")
                await asyncio.sleep(interval)

    async def _vote_collector(self, interval: int = 5):
        """Collect and register cluster votes.
        
        Args:
            interval: Collection interval in seconds
        """
        while self._running:
            try:
                # Get local state for voting
                local_state = await self.health.get_comprehensive_state()

                # Create vote
                vote = {
                    "circuit_breaker_state": local_state.get("circuit_state", "UNKNOWN"),
                    "fallback_mode": local_state.get("fallback_mode", "PRIMARY"),
                    "health_score": local_state.get("health_score", 0.0),
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # Register vote
                await self.redis.register_vote(self.instance_id, vote, ttl=30)

                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Vote collector error: {e}")
                await asyncio.sleep(interval)

    async def get_cluster_consensus(self) -> ConsensusDecision:
        """Get quorum-based consensus decision from cluster.
        
        Collects votes from all instances and applies majority voting.
        Requires >50% quorum for valid consensus.
        
        Returns:
            ConsensusDecision with cluster consensus
        """
        try:
            # Get all votes
            votes = await self.redis.get_cluster_votes()

            if not votes:
                logger.warning("No votes available for consensus")
                return ConsensusDecision(
                    circuit_state="UNKNOWN",
                    fallback_mode="SAFE",
                    leader_instance="",
                    quorum_met=False,
                    voting_instances=0,
                    consensus_strength=0.0,
                )

            # Extract state values
            circuit_votes = [
                v.get("circuit_breaker_state", "UNKNOWN") for v in votes.values()
            ]
            fallback_votes = [v.get("fallback_mode", "PRIMARY") for v in votes.values()]

            # Majority voting
            circuit_consensus = self._majority_vote(circuit_votes)
            fallback_consensus = self._majority_vote(fallback_votes)

            # Get leader
            leader = await self.redis.get_leader()

            # Calculate quorum
            num_votes = len(votes)
            quorum_met = num_votes >= len(votes) / 2 + 1  # Majority: >50%

            # Calculate consensus strength
            if circuit_consensus != "SPLIT_BRAIN":
                circuit_strength = (
                    sum(1 for v in circuit_votes if v == circuit_consensus) / num_votes
                )
            else:
                circuit_strength = 0.0

            decision = ConsensusDecision(
                circuit_state=circuit_consensus,
                fallback_mode=fallback_consensus,
                leader_instance=leader or "NONE",
                quorum_met=quorum_met,
                voting_instances=num_votes,
                consensus_strength=circuit_strength,
            )

            self.consensus_decisions += 1
            self.last_consensus_time = datetime.utcnow()

            logger.debug(
                f"Consensus: circuit={circuit_consensus}, "
                f"fallback={fallback_consensus}, quorum={quorum_met}, "
                f"strength={circuit_strength:.2%}, votes={num_votes}"
            )

            return decision
        except Exception as e:
            logger.error(f"Failed to get cluster consensus: {e}")
            return ConsensusDecision(
                circuit_state="UNKNOWN",
                fallback_mode="SAFE",
                leader_instance="",
                quorum_met=False,
                voting_instances=0,
                consensus_strength=0.0,
            )

    def _majority_vote(self, votes: List[str]) -> str:
        """Apply majority voting to list of votes.
        
        Returns most common vote if it has >50% agreement.
        Otherwise returns "SPLIT_BRAIN" to indicate conflict.
        
        Args:
            votes: List of vote values
            
        Returns:
            Most common vote or "SPLIT_BRAIN"
        """
        if not votes:
            return "UNKNOWN"

        # Count votes
        counter = Counter(votes)
        most_common_vote, count = counter.most_common(1)[0]

        # Check for majority (>50%)
        majority_threshold = len(votes) / 2
        if count > majority_threshold:
            logger.debug(f"Majority vote: {most_common_vote} ({count}/{len(votes)})")
            return most_common_vote
        else:
            logger.warning(f"No majority consensus: {dict(counter)}")
            return "SPLIT_BRAIN"

    async def get_cluster_health(self) -> Dict[str, Any]:
        """Get aggregated health status of entire cluster.
        
        Returns:
            Dict with cluster health metrics
        """
        try:
            all_health = await self.redis.get_all_instance_health()
            if not all_health:
                return {"instances": 0, "healthy": 0, "degraded": 0, "failed": 0}

            # Categorize health
            healthy = sum(
                1
                for h in all_health.values()
                if h.get("health_score", 0) >= 0.8
            )
            degraded = sum(
                1
                for h in all_health.values()
                if 0.5 <= h.get("health_score", 0) < 0.8
            )
            failed = sum(
                1 for h in all_health.values() if h.get("health_score", 0) < 0.5
            )

            return {
                "instances": len(all_health),
                "healthy": healthy,
                "degraded": degraded,
                "failed": failed,
                "health_states": all_health,
            }
        except Exception as e:
            logger.error(f"Failed to get cluster health: {e}")
            return {"instances": 0, "healthy": 0, "degraded": 0, "failed": 0}

    async def get_metrics(self) -> Dict[str, Any]:
        """Get coordinator metrics.
        
        Returns:
            Dict with coordination metrics
        """
        return {
            "instance_id": self.instance_id,
            "is_leader": self.is_leader,
            "election_wins": self.election_wins,
            "consensus_decisions": self.consensus_decisions,
            "last_consensus_time": (
                self.last_consensus_time.isoformat()
                if self.last_consensus_time
                else None
            ),
            "running": self._running,
        }

    async def apply_consensus_decision(self, decision: ConsensusDecision) -> bool:
        """Apply consensus decision to local instance.
        
        Updates fallback mode based on consensus if quorum met.
        
        Args:
            decision: ConsensusDecision to apply
            
        Returns:
            True if applied, False otherwise
        """
        if not decision.quorum_met:
            logger.warning("Cannot apply decision: quorum not met")
            return False

        try:
            # Apply fallback mode change if different
            if self.fallback and decision.fallback_mode != "PRIMARY":
                logger.info(f"Applying consensus fallback mode: {decision.fallback_mode}")
                await self.fallback.cascade(decision.fallback_mode)
                return True

            return True
        except Exception as e:
            logger.error(f"Failed to apply consensus decision: {e}")
            return False
