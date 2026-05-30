# PicoWatch — Development State

**Version:** 0.7.0 | **Last Updated:** 2026-05-30 | **Maturity:** Pre-1.0 beta

## What PicoWatch IS

- A **deterministic pre-filter** for LLM prompt injection and output validation
- A **telemetry layer** (OTel, Prometheus, audit logging) for LLM interactions
- A standalone tool that also integrates with PicoShogun as a plugin
- Part of the **Pico Security Series** (PicoSentry → PicoDome → PicoWatch → PicoShogun)

## What PicoWatch is NOT

- A complete LLM security solution (it's a fast pre-filter, not an adaptive classifier)
- Production-hardened (pre-1.0, APIs may change)
- A replacement for human review of flagged content
- "Enterprise-grade" until proven in real deployments

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
│   ├── ratelimit.py             # Per-IP sliding window rate limiter
│   ├── shogun/                  # PicoShogun plugin adapter (directory name kept for import compat)
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
│       ├── otel.py              # OpenTelemetry tracing
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
│   ├── test_types.py
│   ├── test_config.py
│   ├── test_cli.py
│   ├── test_prompt_guard.py
│   ├── test_output_guard.py
│   ├── test_telemetry.py
│   ├── test_rules_corpus.py
│   ├── test_determinism.py
│   ├── test_ratelimit.py
│   ├── test_server.py
│   ├── test_server_integration.py
│   ├── test_shogun.py
│   └── test_otel.py
├── deploy/
│   ├── prometheus.yml
│   └── otel-collector-config.yaml
├── .github/workflows/
│   └── ci.yml
├── docs/adr/                     # ADR 001–008
├── docs/issues/                  # Issue specs 001–009
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── picowatch.toml
```

## Component Status

| Component | Status | Notes |
|-----------|--------|-------|
| Project scaffold | ✅ | pyproject.toml, CLI, tests, venv |
| L5 PromptGuard | ✅ | Rule engine, normalizer, scorer, 59 rules |
| L6 OutputGuard | ✅ | Schema validation, PII redaction (16 patterns), 32 rules |
| L7 Telemetry | ✅ | SQLite WAL audit, Prometheus metrics, JSON logging |
| CLI | ✅ | scan-prompt, validate-output, serve, rules, health |
| HTTP server | ✅ | POST /v1/scan/prompt, POST /v1/scan/output, GET health/metrics/rules |
| API key auth | ✅ | X-API-Key header or Bearer token |
| Rate limiting | ✅ | Per-IP sliding window, 429 + Retry-After |
| Admin port | ✅ | Separate 9091 port for health/metrics/rules |
| Determinism | ✅ | 10-run verification passes, random.seed(0) guard |
| PicoShogun plugin | ✅ | WatchGuard protocol, event bus, 17 tests |
| Docker | ✅ | Multi-stage Dockerfile + docker-compose |
| CI | ✅ | GitHub Actions (lint, test, build, docker) |
| Audit integrity | ✅ | HMAC-SHA256 checksums, verify_audit_integrity() |
| Config permissions | ✅ | Warns on group/world-readable config |
| Input size limits | ✅ | 1MB max, HTTP 413 on oversize |
| OTel tracing | ✅ | Server endpoints emit spans |
| SBOM in CI | 🔶 | CycloneDX script exists but SLSA provenance is aspirational, not real |
| PyPI publishing | 🔶 | Workflow exists but no published release yet |
| Real-world testing | ❌ | No production deployments known |

## Test Results

```
243 tests passed
- test_types: 10
- test_config: 8
- test_cli: 2
- test_prompt_guard: 45
- test_output_guard: 29
- test_telemetry: 8
- test_rules_corpus: 6
- test_determinism: 3
- test_ratelimit: 10
- test_server: 55
- test_shogun: 17
- test_otel: 16
- test_server_integration: 29
```

## Known Gaps

1. **No production deployments** — PicoWatch has not been tested under real LLM traffic
2. **Pattern-based detection only** — novel/paraphrased attacks will bypass rules
3. **SLSA provenance is scripted but not verified** — the CI generates SBOM and digest, but no external verifier confirms them
4. **No rate-limit persistence** — in-memory only, resets on restart
5. **Helm chart is scaffolded** — not tested in real Kubernetes deployments

## Integration Points

- **PicoSentry**: PicoWatch's CI self-scans dependencies (if PicoSentry is available)
- **PicoDome**: PicoWatch's CI self-sandboxes post-install hooks (if PicoDome is available)
- **PicoShogun**: PicoWatch loads as L5/L6 filter in PicoShogun's firewall
