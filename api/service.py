"""
AstraGuard AI REST API Service

FastAPI-based REST API for telemetry ingestion and anomaly detection.
"""

import os
import time
from datetime import datetime, timedelta
from typing import List
from collections import deque
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import FastAPI, HTTPException, status, Depends
from contextlib import asynccontextmanager
import secrets
from pydantic import BaseModel

# Import centralized secrets management
from core.secrets import get_secret, get_secret_masked


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
from api.auth import get_api_key, require_permission, APIKey
from state_machine.state_engine import StateMachine, MissionPhase
from config.mission_phase_policy_loader import MissionPhasePolicyLoader
from anomaly_agent.phase_aware_handler import PhaseAwareAnomalyHandler
from anomaly.anomaly_detector import detect_anomaly, load_model
from classifier.fault_classifier import classify
from core.component_health import get_health_monitor
from memory_engine.memory_store import AdaptiveMemoryStore
from security_engine.predictive_maintenance import (
    get_predictive_maintenance_engine,
    TimeSeriesData,
    PredictionResult
)
from fastapi.responses import Response
from core.metrics import get_metrics_text, get_metrics_content_type
from core.rate_limiter import RateLimiter, RateLimitMiddleware, get_rate_limit_config
from backend.redis_client import RedisClient
import numpy as np

# Observability imports
try:
    from astraguard.observability import (
        startup_metrics_server,
        track_request,
        track_anomaly_detection,
        ANOMALY_DETECTIONS,
        REQUEST_COUNT,
        DETECTION_LATENCY,
    )
    from astraguard.tracing import initialize_tracing, setup_auto_instrumentation, instrument_fastapi, span_anomaly_detection
    from astraguard.logging_config import setup_json_logging, get_logger, log_request, log_detection, log_error
    OBSERVABILITY_ENABLED = True
except ImportError:
    OBSERVABILITY_ENABLED = False
    print("Warning: Observability modules not available. Running without monitoring.")


# Configuration
MAX_ANOMALY_HISTORY_SIZE = 10000  # Maximum number of anomalies to keep in memory

# Global state
state_machine = None
policy_loader = None
phase_aware_handler = None
memory_store = None
predictive_engine = None
latest_telemetry_data = None # Store latest telemetry for dashboard
anomaly_history = deque(maxlen=MAX_ANOMALY_HISTORY_SIZE)  # Bounded deque prevents memory exhaustion
active_faults = {} # Stores active chaos experiments: {fault_type: expiration_timestamp}
start_time = time.time()

# Rate limiting
redis_client = None
telemetry_limiter = None
api_limiter = None


async def initialize_components():
    """Initialize application components (called on startup or in tests)."""
    global state_machine, policy_loader, phase_aware_handler, memory_store, predictive_engine

    if state_machine is None:
        state_machine = StateMachine()
    if policy_loader is None:
        policy_loader = MissionPhasePolicyLoader()
    if phase_aware_handler is None:
        phase_aware_handler = PhaseAwareAnomalyHandler(state_machine, policy_loader)
    if memory_store is None:
        memory_store = AdaptiveMemoryStore()
    if predictive_engine is None:
        predictive_engine = await get_predictive_maintenance_engine(memory_store)


def _check_credential_security():
    """
    Check and warn about insecure credential configurations at startup.

    Security Checks:
    1. Warn if METRICS_USER/METRICS_PASSWORD are not set
    2. Warn if using common/weak credentials
    3. Set global flag if using defaults
    """
    global _USING_DEFAULT_CREDENTIALS

    metrics_user = get_secret("metrics_user")
    metrics_password = get_secret("metrics_password")

    # Check if credentials are set
    if not metrics_user or not metrics_password:
        print("\n" + "=" * 70)
        print("⚠️  SECURITY WARNING: Metrics authentication not configured!")
        print("=" * 70)
        print("METRICS_USER and METRICS_PASSWORD environment variables are not set.")
        print("The /metrics endpoint will return HTTP 500 until configured.")
        print()
        print("To fix this:")
        print("  1. Set environment variables:")
        print("     export METRICS_USER=your_username")
        print("     export METRICS_PASSWORD=your_secure_password")
        print("  2. Or add to .env file:")
        print("     METRICS_USER=your_username")
        print("     METRICS_PASSWORD=your_secure_password")
        print("=" * 70 + "\n")
        return

    # List of weak/common credentials to warn about
    weak_credentials = [
        ("admin", "admin"),
        ("admin", "password"),
        ("root", "root"),
        ("admin", "12345"),
        ("admin", "123456"),
        ("user", "user"),
        ("test", "test"),
    ]

    # Check for weak credentials
    for weak_user, weak_pass in weak_credentials:
        if metrics_user == weak_user and metrics_password == weak_pass:
            _USING_DEFAULT_CREDENTIALS = True
            print("\n" + "=" * 70)
            print("🔴 CRITICAL SECURITY WARNING: Using default/weak credentials!")
            print("=" * 70)
            print(f"Detected credentials: {get_secret_masked('metrics_user')}/{get_secret_masked('metrics_password')}")
            print()
            print("⚠️  THESE CREDENTIALS ARE PUBLICLY KNOWN AND INSECURE!")
            print()
            print("IMMEDIATE ACTION REQUIRED:")
            print("  1. Change credentials before deploying to production")
            print("  2. Use strong, randomly-generated passwords (20+ characters)")
            print("  3. Consider using secrets management (Vault, AWS Secrets Manager)")
            print()
            print("Generate secure password:")
            print("  python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
            print("=" * 70 + "\n")
            break

    # Check for short passwords
    if len(metrics_password) < 12:
        print("\n" + "=" * 70)
        print("⚠️  WARNING: Weak password detected!")
        print("=" * 70)
        print(f"Password length: {len(metrics_password)} characters")
        print("Recommended minimum: 16 characters")
        print()
        print("Consider using a stronger password:")
        print("  python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
        print("=" * 70 + "\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global redis_client, telemetry_limiter, api_limiter

    # Security: Check credentials at startup
    _check_credential_security()

    # Initialize components
    await initialize_components()
    
    # Pre-load anomaly detection model async
    await load_model()

    # Initialize rate limiting
    try:
        redis_url = get_secret("redis_url")
        redis_client = RedisClient(redis_url=redis_url)
        await redis_client.connect()

        # Get rate limit configurations
        rate_configs = get_rate_limit_config()

        # Create rate limiters
        telemetry_limiter = RateLimiter(
            redis_client.redis,
            "telemetry",
            rate_configs["telemetry"][0],  # rate_per_second
            rate_configs["telemetry"][1]   # burst_capacity
        )
        api_limiter = RateLimiter(
            redis_client.redis,
            "api",
            rate_configs["api"][0],  # rate_per_second
            rate_configs["api"][1]   # burst_capacity
        )

        # Add rate limiting middleware after initialization
        if telemetry_limiter and api_limiter:
            app.add_middleware(RateLimitMiddleware, telemetry_limiter=telemetry_limiter, api_limiter=api_limiter)

        print("✅ Rate limiting initialized successfully")
    except Exception as e:
        print(f"⚠️  Warning: Rate limiting initialization failed: {e}")
        print("Rate limiting will be disabled")

    # Initialize observability (if available)
    if OBSERVABILITY_ENABLED:
        try:
            logger = get_logger(__name__)
            setup_json_logging(log_level=get_secret("log_level", "INFO"))
            initialize_tracing()
            setup_auto_instrumentation()
            instrument_fastapi(app)
            startup_metrics_server(port=9090)
            logger.info("event", "observability_initialized", service="astra-guard", version="1.0.0")
        except Exception as e:
            print(f"Warning: Observability initialization failed: {e}")

    yield

    # Cleanup
    if memory_store:
        memory_store.save()
    if redis_client:
        await redis_client.close()


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
ALLOWED_ORIGINS = get_secret("allowed_origins").split(",")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Configured via ALLOWED_ORIGINS env var
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# Rate limiting middleware will be added in lifespan after initialization

security = HTTPBasic()

# Credential validation flag (set during startup)
_USING_DEFAULT_CREDENTIALS = False

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Validate HTTP Basic Auth credentials for metrics endpoint.

    Security Notes:
    - Credentials MUST be set via METRICS_USER and METRICS_PASSWORD env vars
    - Default credentials trigger startup warning but are allowed for development
    - Use secrets.compare_digest for timing-attack resistance

    Args:
        credentials: HTTP Basic Auth credentials from request

    Returns:
        Username if valid

    Raises:
        HTTPException 401: Invalid credentials
        HTTPException 500: Credentials not configured
    """
    correct_username = get_secret("metrics_user")
    correct_password = get_secret("metrics_password")

    # Security: Require credentials to be explicitly set
    if not correct_username or not correct_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Metrics authentication not configured. Set METRICS_USER and METRICS_PASSWORD environment variables.",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = correct_username.encode("utf8")
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = correct_password.encode("utf8")
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# ============================================================================
# Helper Functions
# ============================================================================

def check_chaos_injection(fault_type: str) -> bool:
    """Check if a chaos fault is currently active."""
    if fault_type in active_faults:
        expiration = active_faults[fault_type]
        if time.time() > expiration:
            del active_faults[fault_type]
            return False
        return True
    return False


def cleanup_expired_faults():
    """Clean up expired chaos faults."""
    current_time = time.time()
    expired = [k for k, v in active_faults.items() if current_time > v]
    for k in expired:
        del active_faults[k]


def inject_chaos_fault(fault_type: str, duration_seconds: int) -> dict:
    """Inject a chaos fault for the specified duration."""
    expiration = time.time() + duration_seconds
    active_faults[fault_type] = expiration
    return {
        "status": "injected",
        "fault": fault_type,
        "expires_at": expiration
    }


def create_response(status: str, data: dict = None, **kwargs) -> dict:
    """Create a standardized API response with timestamp."""
    response = {
        "status": status,
        "timestamp": datetime.now()
    }
    if data:
        response.update(data)
    response.update(kwargs)
    return response


def process_telemetry_batch(telemetry_list: list) -> dict:
    """Process a batch of telemetry data and return aggregated results."""
    processed_count = 0
    anomalies_detected = 0

    for telemetry in telemetry_list:
        try:
            # Process individual telemetry (extracted from submit_telemetry logic)
            processed_count += 1

            # Check for anomalies
            anomaly_score = anomaly_detector.detect_anomaly(telemetry)
            if anomaly_score > 0.7:
                anomalies_detected += 1

                # Store anomaly
                anomaly = AnomalyEvent(
                    timestamp=datetime.now(),
                    metric=telemetry.get('metric', 'unknown'),
                    value=telemetry.get('value', 0.0),
                    severity_score=anomaly_score,
                    context=telemetry
                )
                anomaly_history.append(anomaly)

        except Exception as e:
            logger.error(f"Failed to process telemetry: {e}")
            continue
    return {
        "processed": processed_count,
        "anomalies_detected": anomalies_detected
    }
# ============================================================================
# API Endpoints
# ============================================================================
@app.get("/", response_model=HealthCheckResponse)
async def root():
    """Root endpoint - health check."""
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now()
    )


@app.get("/metrics", tags=["monitoring"])
async def get_metrics():
    """
    Prometheus metrics endpoint.
    
    Returns Prometheus-formatted metrics including:
    - HTTP request count and latency
    - Anomaly detection metrics
    - Circuit breaker state
    - Retry attempts
    - Recovery actions
    """
    if not OBSERVABILITY_ENABLED:
        return {"error": "Observability not enabled"}
    
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from starlette.responses import Response
    
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now()
    )


@app.get("/metrics")
async def metrics(username: str = Depends(get_current_username)):
    """Prometheus metrics endpoint."""
    return Response(
        content=get_metrics_text(), 
        media_type=get_metrics_content_type()
    )


@app.post("/api/v1/telemetry", response_model=AnomalyResponse, status_code=status.HTTP_200_OK)
async def submit_telemetry(telemetry: TelemetryInput, api_key: APIKey = Depends(get_api_key)):
    """
    Submit single telemetry point for anomaly detection.

    Requires API key authentication with 'write' permission.

    Returns:
        AnomalyResponse with detection results and recommended actions
    """
    request_start = time.time()
    
    # CHAOS INJECTION HOOK
    # 1. Network Latency Injection
    if check_chaos_injection("network_latency"):
        time.sleep(2.0)  # Simulate 2s latency

    # 2. Model Loader Failure Injection
    if check_chaos_injection("model_loader"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chaos Injection: Model Loader Failed"
        )
    
    try:
        if OBSERVABILITY_ENABLED:
            with track_request("anomaly_detection"):
                with span_anomaly_detection(data_size=1, model_name="detector_v1"):
                    response = await _process_telemetry(telemetry, request_start)
        else:
            response = await _process_telemetry(telemetry, request_start)

        if OBSERVABILITY_ENABLED and response.is_anomaly:
            logger = get_logger(__name__)
            ANOMALY_DETECTIONS.labels(severity=response.severity_level.lower()).inc()
            log_detection(
                logger,
                severity=response.severity_level,
                detected_type=response.anomaly_type,
                confidence=response.confidence,
                instance_id="telemetry"
            )

        return response

    except Exception as e:
        if OBSERVABILITY_ENABLED:
            logger = get_logger(__name__)
            log_error(logger, e, {"endpoint": "/api/v1/telemetry"})
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anomaly detection failed: {str(e)}"
        ) from e


async def _process_telemetry(telemetry: TelemetryInput, request_start: float) -> AnomalyResponse:
    """Internal telemetry processing logic."""
    # Convert telemetry to dict
    data = {
        "voltage": telemetry.voltage,
        "temperature": telemetry.temperature,
        "gyro": telemetry.gyro,
        "current": telemetry.current or 0.0,
        "wheel_speed": telemetry.wheel_speed or 0.0,
    }

    # Update global latest telemetry
    global latest_telemetry_data
    latest_telemetry_data = {
        "data": data,
        "timestamp": datetime.now()
    }

    # Detect anomaly (uses heuristic if model not loaded)
    is_anomaly, anomaly_score = await detect_anomaly(data)

    # Classify fault type
    anomaly_type = classify(data)

    # Predictive Maintenance: Add training data and check for predictions
    predictive_actions = []
    if predictive_engine:
        try:
            # Create time-series data point
            ts_data = TimeSeriesData(
                timestamp=datetime.now(),
                cpu_usage=telemetry.cpu_usage or 0.0,
                memory_usage=telemetry.memory_usage or 0.0,
                network_latency=telemetry.network_latency or 0.0,
                disk_io=telemetry.disk_io or 0.0,
                error_rate=telemetry.error_rate or 0.0,
                response_time=telemetry.response_time or 0.0,
                active_connections=telemetry.active_connections or 0,
                failure_occurred=is_anomaly
            )

            # Add training data
            await predictive_engine.add_training_data(ts_data)

            # Check for failure predictions
            predictions = await predictive_engine.predict_failures(ts_data)

            if predictions:
                logger.info(f"Predictive maintenance: {len(predictions)} failure predictions made")

                # Trigger preventive actions
                actions = await predictive_engine.trigger_preventive_actions(predictions)
                predictive_actions = actions

                # Log predictions for monitoring
                for prediction in predictions:
                    logger.warning(f"PREDICTED FAILURE: {prediction.failure_type.value} "
                                 f"at {prediction.predicted_time} (prob: {prediction.probability:.2f})")

        except Exception as e:
            logger.error(f"Predictive maintenance failed: {e}")
            # Don't fail the request if predictive maintenance fails

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

    # Record latency in observability (if enabled)
    if OBSERVABILITY_ENABLED:
        elapsed_ms = (time.time() - request_start) * 1000
        DETECTION_LATENCY.observe(elapsed_ms / 1000.0)

    return response


@app.get("/api/v1/telemetry/latest")
async def get_latest_telemetry(api_key: APIKey = Depends(get_api_key)):
    """Get the most recent telemetry data point."""
    if latest_telemetry_data is None:
        return create_response("no_data", {"data": None, "message": "No telemetry received yet"})
    return create_response("success", latest_telemetry_data)


@app.post("/api/v1/telemetry/batch", response_model=BatchAnomalyResponse)
async def submit_telemetry_batch(batch: TelemetryBatch, api_key: APIKey = Depends(get_api_key)):
    """
    Submit batch of telemetry points for anomaly detection.

    Requires API key authentication with 'write' permission.

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
async def get_status(api_key: APIKey = Depends(get_api_key)):
    """Get system health and status.

    Requires API key authentication with 'read' permission.
    """
    health_monitor = get_health_monitor()
    components = health_monitor.get_all_health()

    # CHAOS INJECTION HOOK: Redis Failure
    if check_chaos_injection("redis_failure"):
        # Simulate Redis being down/degraded
        if "memory_store" in components:
            components["memory_store"]["status"] = "DEGRADED"
            components["memory_store"]["details"] = "ConnectionRefusedError: Chaos Injection"

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
async def get_phase(api_key: APIKey = Depends(get_api_key)):
    """Get current mission phase.

    Requires API key authentication with 'read' permission.
    """
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
async def update_phase(request: PhaseUpdateRequest, api_key: APIKey = Depends(require_permission("write"))):
    """Update mission phase.

    Requires API key authentication with 'write' permission.
    """
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
async def get_memory_stats(api_key: APIKey = Depends(get_api_key)):
    """Query memory store statistics.

    Requires API key authentication with 'read' permission.
    """
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
    api_key: str = Depends(get_api_key),
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


@app.post("/api/v1/chaos/inject")
async def inject_fault(request: ChaosRequest, api_key: APIKey = Depends(require_permission("admin"))):
    """Trigger a chaos experiment."""
    return inject_chaos_fault(request.fault_type, request.duration_seconds)



class AnalysisRequest(BaseModel):
    anomaly_id: str
    context: dict = {}

class AnalysisResponse(BaseModel):
    anomaly_id: str
    analysis: str
    recommendation: str
    confidence: float


class UplinkCommand(BaseModel):
    target_id: str
    command: str
    params: dict = {}

class UplinkResponse(BaseModel):
    status: str
    ack_id: str
    message: str
    timestamp: datetime

@app.post("/api/v1/uplink", response_model=UplinkResponse)
async def send_uplink_command(cmd: UplinkCommand, api_key: APIKey = Depends(require_permission("write"))):
    """
    Send a command to a specific satellite or system.
    """
    # Simulate transmission delay
    time.sleep(0.8)

    ack_id = secrets.token_hex(4).upper()
    
    # Simple logic to generate response based on command
    if cmd.command.upper() == "REBOOT":
        msg = f"Reboot sequence initiated for {cmd.target_id}. Estimated downtime: 45s."
    elif cmd.command.upper() == "DIAGNOSTICS":
        msg = f"Diagnostics running on {cmd.target_id}. Report will be downlinked in T+120s."
    elif cmd.command.upper() == "DEPLOY":
        msg = f"Actuator deployment command acknowledged for {cmd.target_id}. Monitoring telemetry."
    else:
        msg = f"Command '{cmd.command}' queued for uplink to {cmd.target_id}."

    return UplinkResponse(
        status="sent",
        ack_id=ack_id,
        message=msg,
        timestamp=datetime.now()
    )

@app.post("/api/v1/analysis/investigate", response_model=AnalysisResponse)
async def investigate_anomaly(request: AnalysisRequest, api_key: APIKey = Depends(get_api_key)):
    """
    AI-powered anomaly investigation (Mocked for MVP).
    Analyzes telemetry context to provide explanations and recommendations.
    """
    # Simulate processing delay (AI thinking)
    time.sleep(1.5)
    
    context = request.context
    metric = context.get('metric', 'Unknown')
    value = context.get('value', 'N/A')
    
    # Heuristic-based "Generative" responses
    if "Temp" in metric:
        analysis = f"Thermal analysis indicates a rapid temperature excursion to {value}. This pattern is consistent with obstructed radiator flow or sensor bias drift."
        recommendation = "1. Verify radiator louver positions. \n2. Check thermal sensor redundancy. \n3. Initiate cooling cycle if temp > 85°C."
        confidence = 0.92
    elif "Voltage" in metric or "Current" in metric:
        analysis = f"Power subsystem detected instability ({value}). The fluctuations suggest a potential short-circuit on the secondary bus or battery cell degradation."
        recommendation = "1. Isolate non-essential loads. \n2. Switch to backup battery logic. \n3. Monitor bus voltage for impedance changes."
        confidence = 0.88
    elif "Gyro" in metric:
        analysis = "Attitude control system (ACS) reporting gyroscopic drift beyond nominal bounds. Likely caused by reaction wheel saturation or solar pressure torque."
        recommendation = "1. Momentum dumping maneuver required. \n2. recalibrate star trackers. \n3. Switch to magnetorquer-only control temporarily."
        confidence = 0.85
    else:
        analysis = f"Unusual pattern detected in {metric} ({value}). Correlation with historical anomalies suggests a transient single-event upset (SEU) in the telemetry encoder."
        recommendation = "1. Acknowledge and monitor for recurrence. \n2. Perform soft reset of telemetry unit if persists > 5min."
        confidence = 0.75

    return AnalysisResponse(
        anomaly_id=request.anomaly_id,
        analysis=analysis,
        recommendation=recommendation,
        confidence=confidence
    )

@app.get("/api/v1/chaos/status")
async def get_chaos_status(api_key: APIKey = Depends(get_api_key)):
    """Get active chaos experiments."""
    cleanup_expired_faults()
    return create_response("success", {
        "active_faults": list(active_faults.keys()),
        "details": active_faults
    })



@app.get("/api/v1/replay/session")
async def get_replay_session(incident_type: str = "VOLTAGE_SPIKE", api_key: APIKey = Depends(get_api_key)):
    """
    Generate a synthetic replay session (60 seconds) for a given incident type.
    """
    # Generate 60 points (1 per second)
    replay_data = []
    base_time = datetime.now() - timedelta(minutes=5)
    
    for i in range(60):
        t = base_time + timedelta(seconds=i)
        
        # Default nominal values
        voltage = 3.6
        temp = 45.0
        gyro = 0.001
        
        # Inject anomalies based on scenario and time (peak at 30s)
        progress = i / 60.0
        
        if incident_type == "VOLTAGE_SPIKE":
            if 20 < i < 40:
                voltage += 1.5 * np.sin((i - 20) * 0.3) # Spike usage
        elif incident_type == "THERMAL_RUNAWAY":
             if i > 15:
                 temp += (i - 15) * 1.5 # Linear increase
        elif incident_type == "GYRO_DRIFT":
             if i > 10:
                 gyro += (i - 10) * 0.05
        
        replay_data.append({
            "timestamp": t.isoformat(),
            "voltage": float(voltage),
            "temperature": float(temp),
            "gyro": float(gyro),
            "current": 2.1,
            "wheel_speed": 4500.0,
            "anomaly_score": 0.8 if (20 < i < 40) else 0.1 # Mock score
        })
        
    return create_response("success", {
        "incident": incident_type,
        "frames": replay_data
    })


# ============================================================================
# Predictive Maintenance Endpoints
# ============================================================================

@app.post("/api/v1/predictive/train")
async def train_predictive_models(api_key: APIKey = Depends(require_permission("admin"))):
    """
    Train predictive maintenance models using collected telemetry data.
    """
    if not predictive_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Predictive maintenance engine not initialized"
        )

    try:
        # Train models
        metrics = await predictive_engine.train_models()

        return create_response("training_completed", {
            "metrics": metrics
        })

    except Exception as e:
        logger.error(f"Model training failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model training failed: {str(e)}"
        )

@app.get("/api/v1/predictive/status")
async def get_predictive_status(api_key: APIKey = Depends(get_api_key)):
    """
    Get the status of the predictive maintenance system.
    """
    if not predictive_engine:
        return create_response("not_initialized", {
            "message": "Predictive maintenance engine not available"
        })

    try:
        # Get basic stats
        training_data_count = len(predictive_engine.training_data)

        return create_response("active", {
            "training_data_points": training_data_count,
            "models_trained": len(predictive_engine.models),
            "last_prediction": getattr(predictive_engine, '_last_prediction_time', None)
        })

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return create_response("error", {
            "message": str(e)
        })

@app.post("/api/v1/predictive/predict")
async def get_predictions(telemetry: TelemetryInput, api_key: APIKey = Depends(get_api_key)):
    """
    Get failure predictions for current telemetry data.
    """
    if not predictive_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Predictive maintenance engine not initialized"
        )

    try:
        # Create time-series data
        ts_data = TimeSeriesData(
            timestamp=datetime.now(),
            cpu_usage=telemetry.cpu_usage or 0.0,
            memory_usage=telemetry.memory_usage or 0.0,
            network_latency=telemetry.network_latency or 0.0,
            disk_io=telemetry.disk_io or 0.0,
            error_rate=telemetry.error_rate or 0.0,
            response_time=telemetry.response_time or 0.0,
            active_connections=telemetry.active_connections or 0,
            failure_occurred=False  # We're predicting, not reporting actual failure
        )

        # Get predictions
        predictions = await predictive_engine.predict_failures(ts_data)

        # Convert to serializable format
        prediction_data = []
        for pred in predictions:
            prediction_data.append({
                "failure_type": pred.failure_type.value,
                "probability": pred.probability,
                "predicted_time": pred.predicted_time.isoformat(),
                "confidence": pred.confidence,
                "features_used": pred.features_used,
                "model_used": pred.model_used.value,
                "preventive_actions": pred.preventive_actions
            })

        return create_response("success", {
            "predictions": prediction_data
        })

    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
