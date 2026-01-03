# AstraGuard-AI Production Observability Deployment Guide

## Quick Reference

| Component | Port | URL | Purpose |
|-----------|------|-----|---------|
| AstraGuard API | 8000 | http://localhost:8000 | REST API + /metrics endpoint |
| Prometheus | 9091 | http://localhost:9091 | Metrics storage & queries |
| Grafana | 3000 | http://localhost:3000 | Dashboards & visualization |
| Jaeger | 16686 | http://localhost:16686 | Distributed tracing UI |
| Redis | 6379 | localhost:6379 | Cache & session storage |

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Git

## Installation

### Step 1: Install Dependencies

```bash
# Install Python packages (including observability modules)
pip install -r requirements.txt
```

**Key observability packages installed:**
- `prometheus-client` - Metrics collection
- `opentelemetry-api/sdk` - Tracing framework
- `opentelemetry-exporter-jaeger` - Jaeger integration
- `structlog` + `python-json-logger` - JSON structured logging

### Step 2: Start Production Stack

```bash
# Start all services (astra-guard, redis, prometheus, grafana, jaeger, exporters)
docker-compose -f docker-compose.prod.yml up -d

# Verify services are running
docker-compose -f docker-compose.prod.yml ps
```

Expected output:
```
NAME                COMMAND                  SERVICE             STATUS      PORTS
astra-guard         "python run_api.py"      astra-guard         Up 2 min    0.0.0.0:8000->8000/tcp, 0.0.0.0:9090->9090/tcp
prometheus          "/bin/prometheus..."    prometheus          Up 2 min    0.0.0.0:9091->9090/tcp
grafana             "/run.sh"                grafana             Up 1 min    0.0.0.0:3000->3000/tcp
jaeger              "/go/bin/all-in-one"    jaeger              Up 1 min    0.0.0.0:16686->16686/tcp
redis               "redis-server ..."      redis               Up 2 min    0.0.0.0:6379->6379/tcp
redis-exporter      "/bin/redis_exporter"   redis-exporter      Up 2 min    0.0.0.0:9121->9121/tcp
node-exporter       "/bin/node_exporter"    node-exporter       Up 2 min    0.0.0.0:9100->9100/tcp
```

### Step 3: Verify Metrics Collection

```bash
# Check that Prometheus is scraping targets
curl -s http://localhost:9091/api/v1/targets | jq '.data.activeTargets[].labels.job'

# Query metrics directly
curl http://localhost:9090/metrics | grep astra_
```

### Step 4: Access Dashboards

1. **Grafana** (http://localhost:3000)
   - Default credentials: `admin` / `admin`
   - Datasource automatically configured: Prometheus @ http://prometheus:9090
   - Dashboards auto-provisioned:
     - **Service Health** - Request rate, latency, errors, connections
     - **Reliability & Resilience** - Circuit breaker, retry, recovery metrics
     - **Anomaly Detection** - Detection rate, accuracy, false positives

2. **Prometheus** (http://localhost:9091)
   - Query interface at `/graph`
   - Alert rules at `/alerts`
   - Targets at `/targets`

3. **Jaeger** (http://localhost:16686)
   - Service search for `astra-guard`
   - Trace visualization
   - Latency analysis

## Configuration

### Environment Variables

```bash
# Logging
export ENABLE_JSON_LOGGING=true
export LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Jaeger Tracing
export JAEGER_HOST=jaeger
export JAEGER_PORT=6831
export OTEL_EXPORTER_JAEGER_ENDPOINT=http://jaeger:14268/api/traces

# Metrics
export PROMETHEUS_PORT=9090

# Application
export ENVIRONMENT=production
export APP_VERSION=1.0.0
```

### Prometheus Configuration

Edit `prometheus.yml` to customize:
- **Scrape intervals**: Global default 15s
- **Alert rules**: Add rules for SLOs, error rates, latency thresholds
- **Data retention**: 7 days (configurable)

Example custom alert rule:

```yaml
groups:
  - name: astraGuard
    rules:
      - alert: AnomalyDetectionSpike
        expr: rate(astra_anomalies_detected_total[5m]) > 1.0
        for: 2m
        annotations:
          summary: "High anomaly detection rate"
```

### Grafana Dashboards

Pre-built dashboards available in `grafana/dashboards/`:

1. **service-health.json**
   - Request rate (requests/sec)
   - Error rate (5-minute)
   - P50/P95/P99 latency
   - Active connections
   - Error breakdown by type

2. **reliability-resilience.json**
   - Circuit breaker state (CLOSED/OPEN/HALF_OPEN)
   - State transition rate
   - Retry rate by endpoint
   - Recovery time histogram (chaos experiments)
   - Recovery actions success rate

3. **anomaly-detection.json**
   - Detection rate by severity
   - False positive rate
   - Detection latency percentiles
   - Model accuracy over time
   - Hourly anomaly distribution

To add custom dashboards:
1. Create JSON in `grafana/dashboards/`
2. Restart Grafana: `docker-compose -f docker-compose.prod.yml restart grafana`

## API Integration

### Automatic Instrumentation

The API automatically instruments:
- **HTTP requests** (via FastAPI middleware)
- **Anomaly detection** (track_request + span_anomaly_detection)
- **Errors** (auto-logged with context)
- **Cache operations** (Redis auto-instrumented)

### Manual Instrumentation

Add observability to custom code:

```python
from astraguard.observability import track_request, ANOMALY_DETECTIONS
from astraguard.tracing import span_anomaly_detection
from astraguard.logging_config import get_logger, log_detection

logger = get_logger(__name__)

# Track request + anomaly detection
with track_request("custom_operation"):
    with span_anomaly_detection(data_size=1000, model_name="custom_v1"):
        result = process_data(data)
        
        # Record metrics
        if is_anomaly(result):
            ANOMALY_DETECTIONS.labels(severity="critical").inc()
            log_detection(
                logger,
                severity="CRITICAL",
                detected_type="custom_anomaly",
                confidence=0.95
            )
        
        return result
```

## Testing

### Unit Tests

```bash
# Run observability tests
pytest tests/test_observability.py -v

# With coverage
pytest tests/test_observability.py --cov=astraguard.observability --cov-report=html
```

### Integration Test

```bash
# Generate sample telemetry
curl -X POST http://localhost:8000/api/v1/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "voltage": 12.5,
    "temperature": 45.0,
    "gyro": 0.1,
    "current": 5.0,
    "wheel_speed": 10.5
  }'

# Check metrics (should see astra_anomalies_detected_total incremented)
curl http://localhost:8000/metrics | grep astra_anomalies_detected_total
```

### Load Test with Observability

```bash
# Using Apache Bench
ab -n 1000 -c 10 http://localhost:8000/health

# Then check Prometheus for spike in request rate:
# curl 'http://localhost:9091/api/v1/query?query=rate(astra_http_requests_total[1m])'
```

## Monitoring

### Key Metrics to Watch

| Metric | Alert Threshold | SLO Target |
|--------|-----------------|------------|
| Error Rate | > 5% | < 0.1% |
| P95 Latency | > 1.0s | < 500ms |
| Availability | < 99.9% | 99.9%+ |
| Circuit Breaker State | OPEN (any) | CLOSED |
| False Positive Rate | > 10% | < 5% |
| Recovery Time (median) | > 60s | < 30s |

### Alert Rules

Recommended alerts (enable in prometheus.yml):

```yaml
# Service Health
- alert: HighErrorRate
  expr: rate(astra_http_requests_total{status="500"}[5m]) > 0.05

- alert: HighLatency
  expr: histogram_quantile(0.95, rate(astra_http_request_duration_seconds_bucket[5m])) > 1.0

# Reliability
- alert: CircuitBreakerOpen
  expr: astra_circuit_breaker_state > 0

- alert: RetryExhaustion
  expr: rate(astra_retry_attempts_total{outcome="exhausted"}[5m]) > 0.01

# Anomaly Detection
- alert: AnomalyDetectionSpike
  expr: rate(astra_anomalies_detected_total[5m]) > 1.0

- alert: HighFalsePositiveRate
  expr: rate(astra_false_positives_total[5m]) / (rate(astra_anomalies_detected_total[5m]) + 0.0001) > 0.1
```

## Troubleshooting

### Prometheus Not Scraping Metrics

```bash
# Check target status
curl http://localhost:9091/api/v1/targets | jq '.data.activeTargets'

# Check logs
docker-compose -f docker-compose.prod.yml logs prometheus

# Verify astra-guard metrics endpoint
curl http://astra-guard:9090/metrics
```

### Jaeger Not Receiving Traces

```bash
# Check Jaeger connectivity
docker-compose -f docker-compose.prod.yml logs jaeger

# Verify Jaeger UDP endpoint
telnet localhost 6831

# Check for trace data
curl http://localhost:16686/api/traces?service=astra-guard
```

### Redis Exporter Not Working

```bash
# Check Redis connection
redis-cli -h localhost ping

# Check exporter logs
docker-compose -f docker-compose.prod.yml logs redis-exporter

# Test metrics endpoint
curl http://localhost:9121/metrics | head -20
```

### High Memory Usage

```bash
# Check Prometheus retention settings in docker-compose.prod.yml:
# PROMETHEUS_ARGS: "--storage.tsdb.retention.time=7d"

# Lower retention if needed:
# PROMETHEUS_ARGS: "--storage.tsdb.retention.time=3d"

# Restart Prometheus
docker-compose -f docker-compose.prod.yml up -d prometheus
```

## Performance Tuning

### Optimize Scrape Intervals

For high-traffic environments:

```yaml
# prometheus.yml
global:
  scrape_interval: 30s      # Increase to 30s for less load
  evaluation_interval: 60s  # Increase evaluation interval
```

### Enable Sampling in Jaeger

```yaml
# In docker-compose.prod.yml, add to JAEGER environment:
SAMPLING_TYPE: "probabilistic"
SAMPLING_PARAM: "0.1"  # Sample 10% of traces
```

### Reduce Log Verbosity

```bash
export LOG_LEVEL=WARNING  # Instead of INFO
```

## Backup & Recovery

### Backup Prometheus Data

```bash
# Stop Prometheus
docker-compose -f docker-compose.prod.yml stop prometheus

# Backup volume
docker run --rm -v astra-guard_prometheus-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/prometheus-backup.tar.gz /data

# Start Prometheus
docker-compose -f docker-compose.prod.yml up -d prometheus
```

### Backup Grafana Dashboards

```bash
# Export all dashboards
docker-compose -f docker-compose.prod.yml exec grafana grafana-cli \
  admin export-dashboard-json dashboards

# Or manually export from UI: Dashboard > ... > Export
```

## Scaling

For production deployments with multiple instances:

1. **Prometheus Federation**: Set up multiple Prometheus instances scraping different targets
2. **Grafana High Availability**: Use external PostgreSQL backend
3. **Jaeger Distributed**: Use Cassandra/Elasticsearch backend (vs all-in-one)

Example multi-instance prometheus.yml:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'astra-guard-1'
    static_configs:
      - targets: ['astra-guard-1:9090']
  
  - job_name: 'astra-guard-2'
    static_configs:
      - targets: ['astra-guard-2:9090']
```

## Support & Documentation

- [Prometheus Docs](https://prometheus.io/docs/)
- [Grafana Docs](https://grafana.com/docs/grafana/)
- [Jaeger Docs](https://www.jaegertracing.io/docs/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)

## Issue #20 Completion Checklist

- ✅ Prometheus metrics collection (observability.py)
- ✅ OpenTelemetry + Jaeger tracing (tracing.py)
- ✅ Structured JSON logging (logging_config.py)
- ✅ Production Docker stack (docker-compose.prod.yml)
- ✅ Prometheus configuration (prometheus.yml)
- ✅ Grafana dashboards (3 pre-built)
- ✅ API integration (api/service.py)
- ✅ Requirements updated (requirements.txt)
- ✅ Comprehensive tests (test_observability.py)
- ✅ Documentation (OBSERVABILITY.md, this guide)

---

**Last Updated**: 2026-01-04
**Status**: Production Ready ✅
**Enterprise Observability**: 3-Pillars Implemented
