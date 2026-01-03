"""
AstraGuard AI REST API Service

FastAPI-based REST API for telemetry ingestion and anomaly detection.
"""

import os
import time
from datetime import datetime
from typing import List
from collections import deque
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.models import (
    TelemetryInput,
    TelemetryBatch,
    AnomalyResponse,
    BatchAnomalyResponse,
    SystemStatus,
    PhaseUpdateRequest,
    PhaseUpdateResponse,
    MemoryStats,
    AnomalyHistoryQuery,
    AnomalyHistoryResponse,
    HealthCheckResponse,
)
from state_machine.state_engine import StateMachine, MissionPhase
from config.mission_phase_policy_loader import MissionPhasePolicyLoader
from anomaly_agent.phase_aware_handler import PhaseAwareAnomalyHandler
from anomaly.anomaly_detector import detect_anomaly, load_model
from classifier.fault_classifier import classify
from core.component_health import get_health_monitor
from memory_engine.memory_store import AdaptiveMemoryStore
import numpy as np


# Configuration
MAX_ANOMALY_HISTORY_SIZE = 10000  # Maximum number of anomalies to keep in memory

# Global state
state_machine = None
policy_loader = None
phase_aware_handler = None
memory_store = None
anomaly_history = deque(maxlen=MAX_ANOMALY_HISTORY_SIZE)  # Bounded deque prevents memory exhaustion
start_time = time.time()


def initialize_components():
    """Initialize application components (called on startup or in tests)."""
    global state_machine, policy_loader, phase_aware_handler, memory_store

    if state_machine is None:
        state_machine = StateMachine()
    if policy_loader is None:
        policy_loader = MissionPhasePolicyLoader()
    if phase_aware_handler is None:
        phase_aware_handler = PhaseAwareAnomalyHandler(state_machine, policy_loader)
    if memory_store is None:
        memory_store = AdaptiveMemoryStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Initialize components
    initialize_components()

    yield

    # Cleanup
    if memory_store:
        memory_store.save()


# Initialize FastAPI app
app = FastAPI(
    title="AstraGuard AI API",
    description="REST API for telemetry ingestion and real-time anomaly detection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration from environment variables
# Security: Never use allow_origins=["*"] with allow_credentials=True in production
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000"
).split(",")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Configured via ALLOWED_ORIGINS env var
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)


@app.get("/", response_model=HealthCheckResponse)
async def root():
    """Root endpoint - health check."""
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now()
    )


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now()
    )


@app.post("/api/v1/telemetry", response_model=AnomalyResponse, status_code=status.HTTP_200_OK)
async def submit_telemetry(telemetry: TelemetryInput):
    """
    Submit single telemetry point for anomaly detection.

    Returns:
        AnomalyResponse with detection results and recommended actions
    """
    try:
        # Convert telemetry to dict
        data = {
            "voltage": telemetry.voltage,
            "temperature": telemetry.temperature,
            "gyro": telemetry.gyro,
            "current": telemetry.current or 0.0,
            "wheel_speed": telemetry.wheel_speed or 0.0,
        }

        # Detect anomaly (uses heuristic if model not loaded)
        is_anomaly, anomaly_score = detect_anomaly(data)

        # Classify fault type
        anomaly_type = classify(data)

        # Get phase-aware decision if anomaly detected
        if is_anomaly:
            decision = phase_aware_handler.handle_anomaly(
                anomaly_type=anomaly_type,
                severity_score=anomaly_score,
                confidence=0.85,
                anomaly_metadata={"telemetry": data}
            )

            response = AnomalyResponse(
                is_anomaly=True,
                anomaly_score=anomaly_score,
                anomaly_type=decision['anomaly_type'],
                severity_score=decision['severity_score'],
                severity_level=decision['policy_decision']['severity'],
                mission_phase=decision['mission_phase'],
                recommended_action=decision['recommended_action'],
                escalation_level=decision['policy_decision']['escalation_level'],
                is_allowed=decision['policy_decision']['is_allowed'],
                allowed_actions=decision['policy_decision']['allowed_actions'],
                should_escalate_to_safe_mode=decision['should_escalate_to_safe_mode'],
                confidence=decision['detection_confidence'],
                reasoning=decision['reasoning'],
                recurrence_count=decision['recurrence_info']['count'],
                timestamp=telemetry.timestamp if telemetry.timestamp else datetime.now()
            )

            # Store in history
            anomaly_history.append(response)

            # Store in memory with embedding (simple feature vector)
            embedding = np.array([
                telemetry.voltage,
                telemetry.temperature,
                abs(telemetry.gyro),
                telemetry.current or 0.0,
                telemetry.wheel_speed or 0.0
            ])
            memory_store.write(
                embedding=embedding,
                metadata={
                    "anomaly_type": anomaly_type,
                    "severity": anomaly_score,
                    "critical": decision['should_escalate_to_safe_mode']
                },
                timestamp=telemetry.timestamp
            )

        else:
            # No anomaly
            response = AnomalyResponse(
                is_anomaly=False,
                anomaly_score=anomaly_score,
                anomaly_type="normal",
                severity_score=0.0,
                severity_level="LOW",
                mission_phase=state_machine.get_current_phase().value,
                recommended_action="NO_ACTION",
                escalation_level="NO_ACTION",
                is_allowed=True,
                allowed_actions=[],
                should_escalate_to_safe_mode=False,
                confidence=0.9,
                reasoning="All telemetry parameters within normal range",
                recurrence_count=0,
                timestamp=telemetry.timestamp if telemetry.timestamp else datetime.now()
            )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anomaly detection failed: {str(e)}"
        ) from e


@app.post("/api/v1/telemetry/batch", response_model=BatchAnomalyResponse)
async def submit_telemetry_batch(batch: TelemetryBatch):
    """
    Submit batch of telemetry points for anomaly detection.

    Returns:
        BatchAnomalyResponse with aggregated results
    """
    results = []
    anomalies_detected = 0

    for telemetry in batch.telemetry:
        result = await submit_telemetry(telemetry)
        results.append(result)
        if result.is_anomaly:
            anomalies_detected += 1

    return BatchAnomalyResponse(
        total_processed=len(results),
        anomalies_detected=anomalies_detected,
        results=results
    )


@app.get("/api/v1/status", response_model=SystemStatus)
async def get_status():
    """Get system health and status."""
    health_monitor = get_health_monitor()
    components = health_monitor.get_all_health()

    return SystemStatus(
        status="healthy" if all(
            c.get("status") == "HEALTHY" for c in components.values()
        ) else "degraded",
        mission_phase=state_machine.get_current_phase().value,
        components=components,
        uptime_seconds=time.time() - start_time,
        timestamp=datetime.now()
    )


@app.get("/api/v1/phase", response_model=dict)
async def get_phase():
    """Get current mission phase."""
    current_phase = state_machine.get_current_phase()
    constraints = phase_aware_handler.get_phase_constraints(current_phase)

    return {
        "phase": current_phase.value,
        "description": state_machine.get_phase_description(current_phase),
        "constraints": constraints,
        "history": state_machine.get_phase_history(),
        "timestamp": datetime.now()
    }


@app.post("/api/v1/phase", response_model=PhaseUpdateResponse)
async def update_phase(request: PhaseUpdateRequest):
    """Update mission phase."""
    try:
        target_phase = MissionPhase(request.phase.value)

        if request.force:
            # Force transition (e.g., emergency SAFE_MODE)
            if target_phase == MissionPhase.SAFE_MODE:
                result = state_machine.force_safe_mode()
            else:
                result = state_machine.set_phase(target_phase)
        else:
            # Normal transition with validation
            result = state_machine.set_phase(target_phase)

        return PhaseUpdateResponse(
            success=result['success'],
            previous_phase=result['previous_phase'],
            new_phase=result['new_phase'],
            message=result['message'],
            timestamp=datetime.now()
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Phase transition failed: {str(e)}"
        ) from e


@app.get("/api/v1/memory/stats", response_model=MemoryStats)
async def get_memory_stats():
    """Query memory store statistics."""
    stats = memory_store.get_stats()

    return MemoryStats(
        total_events=stats['total_events'],
        critical_events=stats['critical_events'],
        avg_age_hours=stats['avg_age_hours'],
        max_recurrence=stats['max_recurrence'],
        timestamp=datetime.now()
    )


@app.get("/api/v1/history/anomalies", response_model=AnomalyHistoryResponse)
async def get_anomaly_history(
    start_time: datetime = None,
    end_time: datetime = None,
    limit: int = 100,
    severity_min: float = None
):
    """Retrieve anomaly history with optional filtering."""
    # Convert deque to list for filtering operations
    filtered = list(anomaly_history)

    # Filter by time range
    if start_time:
        filtered = [a for a in filtered if a.timestamp >= start_time]
    if end_time:
        filtered = [a for a in filtered if a.timestamp <= end_time]

    # Filter by severity
    if severity_min is not None:
        filtered = [a for a in filtered if a.severity_score >= severity_min]

    # Apply limit (get last N items)
    filtered = filtered[-limit:] if len(filtered) > limit else filtered

    return AnomalyHistoryResponse(
        count=len(filtered),
        anomalies=filtered,
        start_time=start_time,
        end_time=end_time
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
