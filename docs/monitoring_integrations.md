# Monitoring Integrations (Issue #183)

This document describes the pluggable monitoring integrations implemented as a proof-of-concept.

## Overview

- New package: `backend.monitoring_integrations`
- Purpose: Allow AstraGuard to ingest alerts and events from external monitoring systems (Datadog, New Relic).
- Extensible: add adapters implementing `MonitoringAdapter.parse_payload` and optionally override `ingest`.

## Current adapters

- `DatadogAdapter` — parses common Datadog webhook shapes.
- `NewRelicAdapter` — parses common New Relic webhook shapes.

## Endpoints

- `POST /monitoring/register` — Register integration config (in-memory PoC).
  - payload: `{ "provider": "datadog", "name": "team-a", "config": {...} }`

- `POST /monitoring/{provider}/webhook` — Generic webhook endpoint for supported providers.
  - Example: `POST /monitoring/datadog/webhook` with Datadog monitor payload.

## Behavior

- Alerts are normalized by adapters to a common shape and then ingested into AstraGuard's `HealthMonitor`.
- Severity mapping:
  - critical/error -> `mark_failed`
  - warning/degraded -> `mark_degraded`
  - info/other -> `mark_healthy`

## How to extend

1. Create adapter that inherits from `MonitoringAdapter`.
2. Implement `parse_payload(self, payload)` returning list of normalized alerts.
3. Optionally override `ingest` to perform custom ingestion logic.
4. Register adapter in `backend/monitoring_integrations/router.py` `_ADAPTERS` map.

## Testing

Unit tests added: `tests/test_monitoring_integrations.py`

## Next steps

- Add persistent integration storage (DB) and authentication for webhooks
- Add more adapters and richer normalization
- Add metrics and observability for ingestion
- Add e2e examples and integration tests with real webhook payload samples
