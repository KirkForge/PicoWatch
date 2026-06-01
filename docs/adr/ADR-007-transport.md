# ADR-007: Transport & Deployment Model

**Status:** Accepted

**Context:**

PicoWatch needs to accept prompt/output inspection requests. It must work as a CLI tool, a Python library, an HTTP service, and a PicoPicoShogun plugin. The transport layer must be flexible without adding complexity.

Options considered:
- **HTTP only** — requires running a server
- **Library only** — no daemon mode
- **Library + optional HTTP daemon** — maximum flexibility

**Decision:**

**Library-first with optional HTTP daemon.** Same architecture as MCP and PicoShogun's API server.

### Transport Modes

| Mode | Use Case | Transport |
|------|----------|-----------|
| **CLI** | One-shot scans, CI pipelines | stdin/argv → stdout (JSON) |
| **Library** | Python integration | Direct function calls |
| **HTTP daemon** | Microservice, PicoShogun remote | FastAPI on configurable port |
| **PicoShogun plugin** | Integrated PicoShogun firewall | In-process Python adapter |

### HTTP API (when running as daemon)

```
POST /v1/scan/prompt     → PromptScanResult
POST /v1/scan/output     → ValidationResult
GET  /v1/health          → HealthStatus
GET  /metrics             → Prometheus text format
GET  /v1/rules            → List active rules
GET  /v1/rules/:id        → Get rule detail
```

Auth: API key via `X-API-Key` header or Bearer token. No auth required for `/health` and `/metrics`.

### Configuration

All modes read from:
1. Environment variables (`PICOWATCH_*`)
2. Config file (`picowatch.toml` or `picowatch.yaml`)
3. CLI flags (highest priority)

Key settings:
- `PICOWATCH_RULES_DIR`: path to rule YAML files (default: bundled rules)
- `PICOWATCH_THRESHOLD_BLOCK`: score threshold for blocking (default: 0.7)
- `PICOWATCH_THRESHOLD_WARN`: score threshold for warning (default: 0.4)
- `PICOWATCH_OTEL_ENDPOINT`: OpenTelemetry OTLP endpoint (optional)
- `PICOWATCH_AUDIT_RETENTION_DAYS`: SQLite audit log retention (default: 30)
- `PICOWATCH_ADMIN_PORT`: Prometheus metrics port (default: 9091)

### Deployment

- **Single binary**: `pip install picowatch` → `picowatch` CLI
- **Docker**: `Dockerfile` with multi-stage build (like PicoSentry like PicoSentry/PicoDome)
- **Kubernetes**: Helm chart with readiness/liveness probes on `/v1/health`

**Consequences:**

✅ Positive: Library-first means zero overhead for Python integrations.
✅ Positive: HTTP daemon uses FastAPI — standard, async, OpenAPI docs auto-generated.
✅ Positive: Same config model across all transport modes.
⚠️ Negative: HTTP daemon adds FastAPI + uvicorn as dependencies (only for daemon mode).
