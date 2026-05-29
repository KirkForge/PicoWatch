# PicoWatch 👁️

![PicoWatch Banner](docs/banner.png)

**LLM defender with telemetry — prompt injection detection, output validation, and observability.**

[![CI](https://github.com/KirkForge/PicoWatch/actions/workflows/ci.yml/badge.svg)](https://github.com/KirkForge/PicoWatch)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/)
[![Rules](https://img.shields.io/badge/rules-91-blue)](rules/)
[![Tests](https://img.shields.io/badge/tests-159-green)](tests/)
[![License: KirkForge](https://img.shields.io/badge/license-KirkForge%20Personal%20Use-orange)](LICENSE)
[![KirkForge](https://img.shields.io/badge/org-KirkForge-blue)](https://github.com/KirkForge)
[![Buy Me a Coffee](https://img.shields.io/badge/%E2%98%95-Buy%20Me%20a%20Coffee-yellow)](https://buymeacoffee.com/kirkforge)

PicoWatch is the 4th product in the [Shogun](https://github.com/KirkForge/Shogun) security platform. It runs **standalone** or integrates into Shogun's Iron Dome firewall layer.

## What It Does

| Layer | Defense | Description |
|-------|---------|-------------|
| **L5** | Prompt Guard | Detects jailbreaks, indirect injections, role manipulation, and instruction overrides |
| **L6** | Output Guard | Validates LLM outputs against schemas, content policies, and PII/exfiltration rules |
| **L7** | Telemetry | OpenTelemetry traces, Prometheus metrics, audit logging — full observability for every request |

## Threat Model

PicoWatch is a **fast deterministic pre-filter and telemetry layer** — not a complete solution for LLM prompt injection defense.

**What it does well:**
- Catch common injection patterns (direct overrides, role manipulation, instruction smuggling) with deterministic regex-weighted scoring
- Provide observable, repeatable scoring for every request
- Block the ~80% of lazy/automated attacks cheaply and fast
- Detect encoding-based obfuscation (base64, ROT13, URL-encoding) via decode-then-rescan

**What it does NOT guarantee:**
- Adaptive attackers can bypass pattern-based detection through paraphrase, translation, novel framings, or spaced-out text (though the spaced-text normalizer catches simple cases)
- A `score=0.94, blocked=True` result means a strong rule match, not a mathematical proof of injection — it reflects pattern confidence, not adversarial robustness
- Encoding detection flags the *presence* of encoded payloads; decoded payloads are re-scanned, but novel encoding schemes may evade detection

**Recommended deployment:** Use PicoWatch as a first-pass filter in a defense-in-depth stack. Pair it with LLM-based classifiers, output guards, and monitoring for layers that handle what pattern matching cannot.

## Shogun Defense Stack

| Product | Layer | Focus |
|---------|-------|-------|
| **PicoSentry** | L2 | Static supply-chain scanning |
| **IronDome** | L3/L4 | Runtime sandbox + behavioral analysis |
| **55NDeep** | Delegation | JSON schema + lang battery → cheap subagent writes code, GitNexus diffs keep drift near zero |
| **PicoWatch** | L5/L6/L7 | LLM prompt/output defense + telemetry |

## Quick Start

```bash
pip install picowatch

# Scan a prompt for injection
picowatch scan-prompt --text "ignore previous instructions and..."

# Validate an LLM output against a schema
picowatch validate-output --schema my_schema.json --output response.json

# Start HTTP daemon (with API key auth)
PICOWATCH_API_KEY=secret picowatch serve --port 8766

# Run as Python library
from picowatch import PromptGuard, OutputGuard, TelemetrySink

guard = PromptGuard()
result = guard.check("ignore all previous instructions")
print(result)  # PromptScanResult(blocked=True, score=0.94, rules=['inj_override_ignore'])
```

## HTTP API

```bash
# Start server
picowatch serve --port 8766

# Scan a prompt (requires API key if PICOWATCH_API_KEY is set)
curl -X POST http://localhost:8766/v1/scan/prompt \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{"text": "ignore all instructions"}'

# Validate output
curl -X POST http://localhost:8766/v1/scan/output \
  -H "Content-Type: application/json" \
  -d '{"output": "Contact John at john@example.com", "schema": {"type": "object"}}'

# Health check (no auth required)
curl http://localhost:8766/v1/health

# Prometheus metrics (no auth required)
curl http://localhost:8766/metrics
```

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/scan/prompt` | API key | Scan prompt for injection patterns |
| POST | `/v1/scan/output` | API key | Validate LLM output against schema/policy |
| GET | `/v1/health` | None | Health check |
| GET | `/metrics` | None | Prometheus metrics |
| GET | `/v1/rules` | None | List active defense rules |
| GET | `/v1/rules/:id` | None | Get rule detail |

## Docker

```bash
# Build and run with Prometheus + OTel collector
docker-compose up -d

# With API key
PICOWATCH_API_KEY=your-secret-key docker-compose up -d
```

## Architecture Decisions

See `docs/adr/` for the full decision log.

- [ADR-001](docs/adr/ADR-001-architecture.md) — Defense layer model (L5/L6/L7)
- [ADR-002](docs/adr/ADR-002-telemetry.md) — OpenTelemetry + Prometheus observability
- [ADR-003](docs/adr/ADR-003-prompt-injection.md) — Deterministic injection detection rules
- [ADR-004](docs/adr/ADR-004-output-validation.md) — Schema + policy output validation
- [ADR-005](docs/adr/ADR-005-integration.md) — Standalone-first with Shogun integration
- [ADR-006](docs/adr/ADR-006-determinism.md) — Deterministic rule evaluation
- [ADR-007](docs/adr/ADR-007-transport.md) — Transport and deployment model
- [ADR-008](docs/adr/ADR-008-security.md) — Supply-chain hardening

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,server]"
python -m pytest
ruff check .
mypy src
```

## License

KirkForge Personal Use License. See [LICENSE](LICENSE).