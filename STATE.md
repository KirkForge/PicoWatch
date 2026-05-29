# PicoWatch — Development State

**Version:** 0.6.0 | **Last Updated:** 2026-05-29 | **Git:** `master`

## Architecture

```
PicoWatch/
├── src/picowatch/
│   ├── __init__.py              # Package root, version, exports
│   ├── __main__.py              # CLI entry point
│   ├── cli.py                   # Argparse CLI (scan-prompt, validate-output, serve, rules, health)
│   ├── config.py                # Configuration from env/file/CLI + API key
│   ├── types.py                 # Shared data types (PromptScanResult, ValidationResult, Rule, etc.)
│   ├── health.py                # Health check endpoint
│   ├── server.py                # FastAPI HTTP server (POST scan/prompt, POST scan/output, GET endpoints)
│   ├── shogun/                  # Shogun Iron Dome plugin adapter
│   │   └── __init__.py          # PicoWatchPlugin + WatchGuard protocol
│   ├── prompt_guard/            # L5: Prompt injection detection
│   │   ├── __init__.py          # PromptGuard class
│   │   ├── normalize.py         # Unicode NFKC, whitespace, encoding detection, comment stripping
│   │   ├── rules.py             # YAML rule engine with corpus hashing
│   │   └── scorer.py            # Weighted scoring (max + weighted average)
│   ├── output_guard/            # L6: Output validation
│   │   └── __init__.py          # OutputGuard class (schema check, PII redaction, policy rules)
│   └── telemetry/               # L7: Observability
│       ├── __init__.py
│       ├── metrics.py           # Prometheus metrics (zero-dep text rendering)
│       └── sink.py              # TelemetrySink (JSON logging + SQLite WAL audit)
├── rules/
│   ├── prompt_injection/         # 29 L5 rules across 6 categories
│   │   ├── instruction_override.yaml
│   │   ├── role_manipulation.yaml
│   │   ├── context_injection.yaml
│   │   ├── encoding_attack.yaml
│   │   ├── extraction_attempt.yaml
│   │   └── multi_turn_trap.yaml
│   └── output_policy/            # 16 L6 rules across 4 categories
│       ├── pii_leak.yaml
│       ├── harmful_content.yaml
│       ├── exfiltration.yaml
│       └── format_violation.yaml
├── tests/
│   ├── test_types.py             # Data type tests
│   ├── test_config.py            # Configuration tests
│   ├── test_cli.py               # CLI smoke tests
│   ├── test_prompt_guard.py      # L5 engine tests (normalizer, rule engine, scorer, integration)
│   ├── test_output_guard.py      # L6 validation tests (PII, schema, policy)
│   ├── test_telemetry.py         # L7 telemetry tests (audit, Prometheus)
│   ├── test_rules_corpus.py      # Rule corpus validation (regex, fields, uniqueness)
│   ├── test_determinism.py       # 10-run determinism verification
│   ├── test_server.py            # HTTP server tests (FastAPI, auth, all endpoints)
│   ├── test_ratelimit.py         # Rate limiter tests (sliding window, per-IP)
│   ├── test_otel.py              # OpenTelemetry tracing tests (init, spans, no-op)
│   ├── test_server_integration.py # Server integration tests (dual-port, auth, determinism)
│   └── test_shogun.py            # Shogun plugin tests (init, scan, validate, events, determinism)
├── deploy/
│   ├── prometheus.yml            # Prometheus scrape config
│   └── otel-collector-config.yaml # OpenTelemetry collector config
├── .github/workflows/
│   └── ci.yml                    # CI pipeline (lint, test 3.10-3.13, build, docker)
├── docs/adr/                     # Architecture Decision Records 001–008
├── docs/issues/                  # Issue specs 001–009
├── Dockerfile                    # Multi-stage build (builder → runtime)
├── docker-compose.yml            # PicoWatch + Prometheus + OTel collector
├── pyproject.toml
├── README.md
├── AGENTS.md
├── CHANGELOG.md
├── LICENSE
└── STATE.md
```

## Status

| Component | Status | Notes |
|-----------|--------|-------|
| Project scaffold | ✅ | pyproject.toml, CLI, tests, venv |
| ADR 001–008 | ✅ | Architecture decisions documented |
| L5 PromptGuard | ✅ | Rule engine, normalizer, scorer, 59 rules (6 categories) |
| L6 OutputGuard | ✅ | Schema validation, PII detection/redaction (16 patterns), 32 rules, feedback loop |
| L7 Telemetry | ✅ | SQLite WAL audit, Prometheus metrics, JSON logging |
| CLI | ✅ | scan-prompt, validate-output, serve, rules, health |
| FastAPI HTTP server | ✅ | POST /v1/scan/prompt, POST /v1/scan/output, GET health/metrics/rules |
| API key auth | ✅ | X-API-Key header or Bearer token on POST endpoints |
| Default rules | ✅ | 59 prompt injection (6 categories) + 32 output policy (4 categories) = 91 total |
| Test suite | ✅ | 236 tests passing |
| Determinism verification | ✅ | 10-run determinism test passes |
| CI pipeline | ✅ | GitHub Actions (lint, test 3.10-3.13, build, docker) |
| Docker | ✅ | Multi-stage Dockerfile + docker-compose (PicoWatch + Prometheus + OTel) |
| Shogun plugin | ✅ | PicoWatchPlugin + WatchGuard protocol, event bus, 17 tests |
| OTel tracing | ✅ | init_tracing(), trace_prompt_scan(), trace_output_validation() in server endpoints; 16 OTel tests |
| Admin port (ADR-007) | ✅ | Separate 9091 port for health/metrics/rules; integration tests |
| Rate limiting (ADR-008) | ✅ | Per-IP sliding window, 429 + Retry-After |
| TOML config file | ✅ | picowatch.toml search path: ., ~/.config/, /etc/ |
| Request ID auto-gen (ADR-002) | ✅ | Auto-generates req-{uuid} if not provided |
| Prometheus histograms (ADR-002) | ✅ | picowatch_prompt_score, picowatch_scan_duration_seconds |
| mypy strict | ✅ | 18 source files, 0 errors |
| PyPI publishing | ✅ | Trusted Publishing workflow in `.github/workflows/publish.yml` |

## Test Results

```
236 tests PASSED in 73.17s
- test_types: 10/10 ✅
- test_config: 8/8 ✅
- test_cli: 2/2 ✅
- test_prompt_guard: 45/45 ✅
- test_output_guard: 29/29 ✅
- test_telemetry: 8/8 ✅
- test_rules_corpus: 6/6 ✅
- test_determinism: 3/3 ✅
- test_ratelimit: 10/10 ✅
- test_server: 55/55 ✅
- test_shogun: 17/17 ✅
- test_otel: 16/16 ✅
- test_server_integration: 29/29 ✅
```

## HTTP API

### Main port (8766)
```
POST /v1/scan/prompt     → PromptScanResult   (auth: API key)
POST /v1/scan/output     → ValidationResult   (auth: API key)
GET  /v1/health          → HealthStatus       (no auth)
GET  /metrics            → Prometheus text    (no auth)
GET  /v1/rules           → List[Rule]         (no auth)
GET  /v1/rules/:id       → Rule detail        (no auth)
```

### Admin port (9091, ADR-007)
```
GET  /v1/health          → HealthStatus       (no auth)
GET  /metrics            → Prometheus text    (no auth)
GET  /v1/rules           → List[Rule]         (no auth)
GET  /v1/rules/:id       → Rule detail        (no auth)
```

Auth: Set `PICOWATCH_API_KEY` env var. POST endpoints require `X-API-Key` header or `Bearer` token.

## CLI Usage

```bash
# Scan a prompt for injection
picowatch scan-prompt --text "ignore all previous instructions"
# → {"blocked": true, "score": 0.9, "verdict": "block", "rules_matched": [...]}

# Validate an LLM output
picowatch validate-output --schema schema.json --output response.json

# Verify determinism (runs twice, compares)
picowatch --verify-determinism scan-prompt --text "You are now DAN"

# Start HTTP daemon
picowatch serve --port 8766

# List active rules
picowatch rules

# Health check
picowatch health
```

## Docker

```bash
# Build and run
docker-compose up -d

# With API key
PICOWATCH_API_KEY=your-secret-key docker-compose up -d

# Test endpoint
curl http://localhost:8766/v1/health
curl -X POST http://localhost:8766/v1/scan/prompt \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{"text": "ignore all instructions"}'
```

## Integration Points

- **PicoSentry**: PicoWatch's CI self-scans dependencies with PicoSentry
- **IronDome**: PicoWatch's CI self-sandboxes post-install hooks with IronDome
- **55NDeep**: PicoWatch outputs can be verified by 55NDeep delegation
- **Shogun**: PicoWatch loads as L5/L6 filter in Iron Dome firewall