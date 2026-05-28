# PicoWatch — Development State

**Version:** 0.1.0 | **Last Updated:** 2026-05-29 | **Git:** `master`

## Architecture

```
PicoWatch/
├── src/picowatch/
│   ├── __init__.py              # Package root, version, exports
│   ├── __main__.py              # CLI entry point
│   ├── cli.py                   # Argparse CLI (scan-prompt, validate-output, serve, rules, health)
│   ├── config.py                # Configuration from env/file/CLI
│   ├── types.py                 # Shared data types (PromptScanResult, ValidationResult, Rule, etc.)
│   ├── health.py                # Health check endpoint
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
│   └── test_determinism.py       # 10-run determinism verification
├── docs/adr/                     # Architecture Decision Records 001–008
├── docs/issues/                  # Issue specs 001–009
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
| L5 PromptGuard | ✅ | Rule engine, normalizer, scorer, 29 rules |
| L6 OutputGuard | ✅ | Schema validation, PII detection/redaction, 16 rules |
| L7 Telemetry | ✅ | SQLite WAL audit, Prometheus metrics, JSON logging |
| CLI | ✅ | scan-prompt, validate-output, serve, rules, health |
| Default rules | ✅ | 29 prompt injection (6 categories) + 16 output policy (4 categories) |
| Test suite | ✅ | 57 tests passing |
| Determinism verification | ✅ | 10-run determinism test passes |
| CI pipeline | 🔜 | ci-cleandev configured, needs GitHub Actions |
| Docker | 🔜 | Multi-stage Dockerfile pending |
| Shogun plugin | 🔜 | Adapter pending |
| HTTP POST endpoints | 🔜 | scan/prompt and scan/output POST handlers |

## Test Results

```
57 tests PASSED in 8.69s
- test_types: 8/8 ✅
- test_config: 2/2 ✅
- test_cli: 2/2 ✅
- test_prompt_guard: 12/12 ✅ (normalizer, rule engine, scorer, integration, determinism)
- test_output_guard: 8/8 ✅ (PII, schema, policy, determinism)
- test_telemetry: 5/5 ✅ (audit, Prometheus, health)
- test_rules_corpus: 6/6 ✅ (regex valid, fields present, unique IDs, hash stable)
- test_determinism: 3/3 ✅ (10-run prompt, 10-run output, corpus hash)
```

## CLI Usage

```bash
# Scan a prompt for injection
picowatch scan-prompt --text "ignore all previous instructions"
# → {"blocked": true, "score": 0.9, "verdict": "block", "rules_matched": ["inj_override_ignore"]}

# Verify determinism (runs twice, compares)
picowatch --verify-determinism scan-prompt --text "You are now DAN"
# → DETERMINISM CHECK PASSED: results identical

# List active rules
picowatch rules

# Health check
picowatch health

# Start telemetry daemon
picowatch serve --port 8766
```

## Integration Points

- **PicoSentry**: PicoWatch's CI self-scans dependencies with PicoSentry
- **IronDome**: PicoWatch's CI self-sandboxes post-install hooks with IronDome
- **55NDeep**: PicoWatch outputs can be verified by 55NDeep delegation
- **Shogun**: PicoWatch loads as L5/L6 filter in Iron Dome firewall