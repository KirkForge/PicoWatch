# feat(telemetry): implement L7 TelemetrySink

**Labels:** enhancement

ADR-002 implementation.

## Scope

- Prometheus metrics endpoint on admin port (default 9091):
  - `picowatch_requests_total{model,blocked,valid}`
  - `picowatch_prompt_score{model,rule}`
  - `picowatch_output_violations_total{model,policy}`
  - `picowatch_scan_duration_seconds{guard_type}`
  - `picowatch_active_scans{guard_type}`
- Structured JSON logging to stdout (compatible with Loki/Datadog/ELK)
- SQLite WAL audit log with 30-day default retention
- OpenTelemetry trace spans (optional `[otel]` extra):
  - `picowatch.request` (root span)
  - `picowatch.prompt_guard.scan` (child span)
  - `picowatch.output_guard.validate` (child span)

## Acceptance Criteria

- [ ] `TelemetrySink` class with `record_prompt_scan()` and `record_validation()`
- [ ] Prometheus `/metrics` endpoint (zero-dep, stdlib rendering)
- [ ] Structured JSON logging to stdout
- [ ] SQLite audit log with WAL mode and checksums
- [ ] Retention policy (configurable, default 30 days)
- [ ] OTel spans work when `[otel]` extra is installed, graceful no-op otherwise

**Depends on:** L5 + L6 (needs data to emit)
