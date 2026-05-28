# PicoWatch — Development State

**Version:** 0.1.0 | **Last Updated:** 2026-05-29 | **Git:** `master`

## Architecture

```
PicoWatch/
├── src/picowatch/
│   ├── __init__.py              # Package root, version
│   ├── __main__.py              # CLI entry point
│   ├── cli.py                   # Argparse CLI (scan-prompt, validate-output, serve)
│   ├── prompt_guard/             # L5: Prompt injection detection
│   │   ├── __init__.py
│   │   ├── rules.py             # Rule engine + YAML loader
│   │   ├── normalize.py         # Unicode normalization, encoding detection
│   │   └── scorer.py           # Weighted scoring + threshold logic
│   ├── output_guard/            # L6: Output validation
│   │   ├── __init__.py
│   │   ├── schema_check.py      # JSON Schema validation
│   │   ├── policy.py            # Content policy engine
│   │   └── pii.py              # PII detection + redaction
│   ├── telemetry/                # L7: Observability
│   │   ├── __init__.py
│   │   ├── metrics.py           # Prometheus metrics renderer
│   │   ├── audit.py             # SQLite WAL audit log
│   │   └── traces.py            # OpenTelemetry traces (optional)
│   ├── config.py                # Configuration from env/file/CLI
│   ├── types.py                 # Shared data types
│   └── health.py                # /v1/health endpoint
├── tests/
│   ├── test_cli.py
│   ├── test_prompt_guard.py
│   ├── test_output_guard.py
│   └── test_telemetry.py
├── docs/adr/                    # Architecture Decision Records 001–008
├── rules/                        # Default rule YAML files
│   ├── prompt_injection/
│   └── output_policy/
├── pyproject.toml
├── Dockerfile
└── README.md
```

## Status

| Component | Status | Notes |
|-----------|--------|-------|
| Project scaffold | ✅ | pyproject.toml, CLI skeleton, tests |
| ADR 001–008 | ✅ | Architecture decisions documented |
| L5 PromptGuard | 🔜 | Architecture defined, implementation pending |
| L6 OutputGuard | 🔜 | Architecture defined, implementation pending |
| L7 Telemetry | 🔜 | Architecture defined, implementation pending |
| CI pipeline | 🔜 | ci-cleandev configured |
| Docker | 🔜 | Multi-stage Dockerfile pending |
| Shogun plugin | 🔜 | Adapter pending |

## Integration Points

- **PicoSentry**: PicoWatch's CI self-scans dependencies with PicoSentry
- **IronDome**: PicoWatch's CI self-sandboxes post-install hooks with IronDome
- **55NDeep**: PicoWatch outputs can be verified by 55NDeep delegation
- **Shogun**: PicoWatch loads as L5/L6 filter in Iron Dome firewall
