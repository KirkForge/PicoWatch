# ADR-002: Telemetry & Observability Stack

**Status:** Accepted

**Context:**

LLM interactions are a black box in most deployments. Without structured observability, it's impossible to detect abuse patterns, measure defense effectiveness, or comply with audit requirements. PicoWatch needs a telemetry story that works standalone and integrates with existing monitoring stacks.

Options considered:
- **Custom metrics endpoint** — simple but proprietary
- **OpenTelemetry (OTel)** — industry standard, vendor-neutral, huge ecosystem
- **Structured logging only** — insufficient for time-series analysis and alerting

**Decision:**

Use **OpenTelemetry** for traces + Prometheus for metrics, with structured logging as the baseline.

### Traces (OpenTelemetry)

Every LLM request/response cycle is a span. Child spans for each defense check:

```
picowatch.request (root span)
├── picowatch.prompt_guard.scan
├── picowatch.output_guard.validate
└── picowatch.telemetry.emit
```

Span attributes:
- `picowatch.request.id`: unique request ID
- `picowatch.prompt.blocked`: boolean
- `picowatch.prompt.score`: 0.0–1.0 injection score
- `picowatch.prompt.rules_matched`: list of rule IDs
- `picowatch.output.valid`: boolean
- `picowatch.output.violations`: list of policy violation IDs
- `picowatch.model`: model identifier
- `picowatch.latency_ms`: end-to-end latency

### Metrics (Prometheus)

Exposed on a separate admin port (default 9091):

| Metric | Type | Labels |
|--------|------|--------|
| `picowatch_requests_total` | counter | `model`, `blocked`, `valid` |
| `picowatch_prompt_score` | histogram | `model`, `rule` |
| `picowatch_output_violations_total` | counter | `model`, `policy` |
| `picowatch_scan_duration_seconds` | histogram | `guard_type` |
| `picowatch_active_scans` | gauge | `guard_type` |

### Structured Logging

JSON to stdout, compatible with Loki/Datadog/ELK:

```json
{
  "timestamp": "2026-05-29T12:00:00Z",
  "level": "warn",
  "event": "prompt.blocked",
  "request_id": "req-abc123",
  "score": 0.94,
  "rules": ["injection_role_override", "instruction_override"],
  "model": "gpt-4o",
  "latency_ms": 2.1
}
```

### Audit Log

SQLite WAL database for persistent audit trail. 30-day retention by default. Every blocked prompt and violated output is recorded with full context.

### Dependency Strategy

- **Core** (no OTel): Structured logging + SQLite audit. Works everywhere.
- **Optional** (`[otel]`): OpenTelemetry SDK + OTLP exporter. `pip install picowatch[otel]`
- **Prometheus**: Always available on admin port. No extra deps — pure stdlib metric rendering.

**Consequences:**

✅ Positive: Full observability without mandatory external dependencies.
✅ Positive: Prometheus metrics are zero-dep, always available.
✅ Positive: OTel traces integrate with Jaeger, Zipkin, Datadog, Honeycomb.
⚠️ Negative: SQLite audit log needs retention policy (default 30 days).
⚠️ Negative: OTel adds dependency weight when enabled; kept optional.
