# PicoWatch — Development State

**Version:** 1.0.1 | **Last Updated:** 2026-06-01 | **Tag:** v1.0.1 (at commit e80e39d)

## What PicoWatch IS

A **deterministic regex-weighted pre-filter** for LLM prompt injection and output validation, with a telemetry layer (audit logging, Prometheus metrics, optional OTel tracing). Runs standalone via CLI/HTTP or as a PicoShogun plugin.

## What PicoWatch is NOT

- A complete LLM security solution — it's a fast pattern matcher, not an adaptive classifier
- Battle-tested in production — no known real-world deployments
- A replacement for LLM-based classifiers or human review of flagged content
- "Enterprise-grade" anything

## Architecture

```
src/picowatch/
├── __init__.py              # Package root, version 1.0.1, public exports
├── __main__.py              # CLI entry point (delegates to cli.main)
├── cli.py                   # Argparse CLI: scan-prompt, validate-output, serve, rules, health
├── config.py                # Config from env > TOML file > defaults; assert_secure() gate
├── types.py                 # Frozen dataclasses: PromptScanResult, ValidationResult, Rule, HealthStatus, Verdict
├── health.py                # health_check() factory for HealthStatus
├── server.py                # FastAPI app factory + admin app factory + run_server()
├── ratelimit.py             # Per-IP sliding window rate limiter (thread-safe, in-memory)
├── picoshogun/              # PicoShogun plugin adapter
│   └── __init__.py          # PicoWatchPlugin + WatchGuard Protocol
├── prompt_guard/            # L5: Prompt injection detection
│   ├── __init__.py          # PromptGuard class (orchestrates normalize → evaluate → score)
│   ├── normalize.py         # Unicode NFKC, whitespace, spaced-text, separator-punct collapse, comments, encoding decode+rescan
│   ├── rules.py             # RuleEngine: loads YAML, compiles regex, corpus SHA-256 hash
│   └── scorer.py            # Scorer: max(individual, weighted_average) → final score
├── output_guard/            # L6: Output validation
│   └── __init__.py          # OutputGuard: schema check → rule match → PII redaction → feedback loop
├── telemetry/               # L7: Observability
│   ├── __init__.py          # Public exports
│   ├── metrics.py           # PrometheusMetrics: zero-dep text-format renderer
│   ├── otel.py              # OpenTelemetry tracing (optional, pip install picowatch[otel])
│   └── sink.py              # TelemetrySink: JSON logging + SQLite WAL audit + HMAC checksums
└── rules/                   # Bundled YAML rule files
    ├── prompt_injection/     # 59 rules across 6 YAML files
    │   ├── instruction_override.yaml  (13 rules)
    │   ├── role_manipulation.yaml     (15 rules)
    │   ├── context_injection.yaml     (7 rules)
    │   ├── encoding_attack.yaml       (8 rules)
    │   ├── extraction_attempt.yaml     (8 rules)
    │   └── multi_turn_trap.yaml       (8 rules)
    └── output_policy/        # 32 rules across 4 YAML files
        ├── pii_leak.yaml              (10 rules)
        ├── harmful_content.yaml       (7 rules)
        ├── exfiltration.yaml          (8 rules)
        └── format_violation.yaml      (7 rules)
```

## Component Status

| Component | Status | Notes |
|-----------|--------|-------|
| L5 PromptGuard | Works | 59 regex rules, normalization pipeline, decode-then-rescan for base64/ROT13/URL-encoding |
| L6 OutputGuard | Works | 32 output policy rules, hardcoded PII redaction in Python (duplicates YAML patterns), basic schema validation |
| L7 TelemetrySink | Works | SQLite WAL audit, Prometheus text renderer, optional OTel spans |
| CLI | Works | scan-prompt, validate-output, serve, rules, health, --picoshogun-plugin |
| HTTP server (main) | Works | POST /v1/scan/prompt, POST /v1/scan/output, GET /v1/health, GET /metrics, GET /v1/rules, GET /v1/rules/:id |
| HTTP server (admin) | Works | Separate app on port 9091, GET health/metrics/rules only |
| API key auth | Works | X-API-Key or Bearer token on POST endpoints, constant-time compare |
| Rate limiting | Works | Per-IP sliding window, 429 + Retry-After header |
| Determinism | Verified | 10-run test suite, frozen dataclasses, sorted rule evaluation |
| PicoShogun plugin | Works | WatchGuard Protocol, on_event() dispatch, 17 tests |
| Audit HMAC | Works | HMAC-SHA256 checksums, verify_audit_integrity(), tamper detection |
| Docker | Scaffolded | Dockerfile + docker-compose exist; not tested in real K8s |
| Helm chart | Scaffolded | deploy/helm/ exists; Chart.yaml still says appVersion "0.7.0", not tested in real cluster |
| SBOM generation | Scripted | scripts/generate_sbom.py calls pip list — not integrated into CI release flow |
| PyPI publish | Workflow exists | .github/workflows/ has publish action; v1.0.1 tag exists but no evidence of actual PyPI upload |

## What Actually Works (with file references)

### PromptGuard (L5) — `src/picowatch/prompt_guard/__init__.py`
- `PromptGuard.check()` normalizes input, runs all 59 compiled regex rules, decodes base64/ROT13/URL-encoded payloads and re-scans, then scores
- Scoring: `max(max_individual_rule_weight, weighted_average_of_matches)` — `src/picowatch/prompt_guard/scorer.py`
- Normalizer handles: NFKC unicode, whitespace collapse, spaced-text collapse ("i g n o r e" → "ignore"), separator-punct collapse ("i.g.n.o.r.e" → "ignore"), HTML/C/line comment stripping, zero-width char removal — `src/picowatch/prompt_guard/normalize.py`
- Decode-then-rescan: base64 payloads decoded and re-scanned; ROT13 only decoded if ROT13-encoded injection keywords already detected in raw text; URL-encoded decoded if `%XX` sequences present — `src/picowatch/prompt_guard/normalize.py:decode_and_rescan()`

### OutputGuard (L6) — `src/picowatch/output_guard/__init__.py`
- `OutputGuard.validate()` runs: schema check → content policy rules → PII detection/redaction → feedback loop
- Schema validation is basic (type check + required fields only) — no full JSON Schema Draft 2020-12 without `jsonschema` dependency
- PII redaction is hardcoded in Python (`_detect_pii()` method) with 14 pattern categories — this **duplicates** the YAML rule patterns rather than using the rule engine output
- Feedback loop: if prompt_result.score >= 0.4, output violations are amplified by 1.3x multiplier

### Telemetry (L7) — `src/picowatch/telemetry/sink.py`
- SQLite WAL audit log with HMAC-SHA256 integrity checksums
- `verify_audit_integrity()` detects tampered rows
- `cleanup_audit()` prunes entries older than retention_days
- `render_prometheus()` generates text-format metrics from in-memory counters/histograms
- OTel tracing is optional and graceful-noop when deps missing — `src/picowatch/telemetry/otel.py`

### Server — `src/picowatch/server.py`
- `create_app()` returns FastAPI app with all endpoints
- `create_admin_app()` returns read-only admin FastAPI app (health/metrics/rules only)
- `run_server()` spawns admin app on a daemon thread, then runs main app via uvicorn
- Rate limiting middleware on POST endpoints
- Auth via `verify_api_key` dependency using `secrets.compare_digest`

### PicoShogun Plugin — `src/picowatch/picoshogun/__init__.py`
- `PicoWatchPlugin` implements `WatchGuard` Protocol
- `on_event()` dispatches: prompt_received → L5, output_generated → L6, health_check → status
- `metrics()` returns Prometheus text for PicoShogun's aggregator
- **Never tested against actual PicoShogun** — PicoShogun itself may not have a stable event bus yet

### Config — `src/picowatch/config.py`
- Priority: CLI > env vars > TOML file > defaults
- `assert_secure()` refuses to boot if API key < 32 chars; warns on 0.0.0.0 bind + API key; warns on missing API key
- `check_config_permissions()` warns on group/world-readable config files
- Config search: `./picowatch.toml`, `~/.config/picowatch/picowatch.toml`, `/etc/picowatch/picowatch.toml`

## What's Stubbed, Scaffolded, or Non-Functional

### Helm chart is stale — `deploy/helm/picowatch/Chart.yaml`
- `appVersion: "0.7.0"` and `version: 0.7.0` — not updated to 1.0.1
- `values.yaml` image tag defaults to `"0.7.0"`
- Never tested against a real Kubernetes cluster
- Liveness/readiness probes reference `port: admin` which is a named port in the deployment — this works but hasn't been validated E2E

### SBOM script — `scripts/generate_sbom.py`
- Calls `pip list --format=json` to enumerate installed packages
- Not integrated into CI release workflow
- Not a proper CycloneDX SBOM from build metadata — just a snapshot of whatever's installed at generation time
- SLSA provenance claims in docs are aspirational

### OTel service version hardcoded — `src/picowatch/telemetry/otel.py:41,60`
- `service.version` and tracer version both hardcoded to `"0.7.0"` instead of reading from `picowatch.__version__`
- This means OTel spans will report the wrong version (0.7.0) when the package is actually 1.0.1

### Schema validation is minimal — `src/picowatch/output_guard/__init__.py:_check_schema()`
- Only checks: top-level `type`, `required` fields
- Does NOT validate: properties, nested objects, enum, pattern, min/max, additionalProperties, anyOf/allOf/oneOf, $ref
- README implies JSON Schema validation but it's a stub without the `jsonschema` library
- `jsonschema` is a dev dependency only — not available at runtime unless explicitly installed

### PII redaction duplicates YAML rules — `src/picowatch/output_guard/__init__.py:_detect_pii()`
- The `_detect_pii()` method has 14 hardcoded regex patterns in Python that overlap with the YAML output_policy rules
- Both the YAML rule engine AND the hardcoded Python patterns run on every output
- The YAML rules flag violations and contribute to the score, but don't redact
- The hardcoded Python patterns both flag AND redact
- This means: some patterns (SSN, credit card, email, phone, API key, IP, passport, JWT, crypto wallet, AWS ARN, SSH key, DB URL, OAuth token, env vars, Docker/K8s secrets) have dual detection — once from YAML, once from Python
- Any new PII pattern added to YAML won't get redacted unless someone also adds it to the Python code
- The `out_pii_email` YAML pattern exists but `_detect_pii()` does NOT redact emails (no email regex in the Python method) — emails are flagged by YAML rules but not redacted in the output

### `schema_dir` config field is unused — `src/picowatch/config.py:50`
- `PicoWatchConfig.schema_dir` is declared as `Path | None = None`
- `from_env()` reads `PICOWATCH_SCHEMA_DIR` env var
- But `OutputGuard.__init__()` never uses `self._config.schema_dir` — it only uses `rules_dir / "output_policy"` for rules
- No code loads user-provided schemas from `schema_dir`
- The field is dead config

### CLI `serve` subcommand defaults to `0.0.0.0` — `src/picowatch/cli.py:114`
- `se.add_argument("--host", default="0.0.0.0")`
- This conflicts with `PicoWatchConfig.host` which defaults to `"127.0.0.1"`
- The CLI arg overrides the config default, so `picowatch serve` without `--host` binds to `0.0.0.0` — less secure than the config default
- `assert_secure()` warns about this but doesn't block it

### `detect_encodings()` is a no-op — `src/picowatch/prompt_guard/normalize.py`
- `Normalizer.detect_encodings()` just returns the input text unchanged
- Docstring says "Kept for backward compatibility" and "Detection adds markers so rules can match"
- But it doesn't actually add markers — it's a dead method
- Encoding detection is now handled by `decode_and_rescan()` instead

### Multi-turn trap rules are low-weight and noisy — `src/picowatch/rules/prompt_injection/multi_turn_trap.yaml`
- Rules like `inj_multiturn_game` (weight 0.6) match "let's play a game" — extremely common benign phrasing
- `inj_multiturn_bypass` (weight 0.55) matches "hypothetically, what" — common in research/academic contexts
- `inj_multiturn_emergency` (weight 0.6) matches "urgent" / "critical" — common in business contexts
- These will generate false positives in normal conversation; they're below the 0.7 block threshold alone but contribute to cumulative scoring

### `out_pii_passport` pattern is overly broad — `src/picowatch/rules/output_policy/pii_leak.yaml`
- Pattern `\b[A-Z]{1,2}\d{6,9}\b` matches any 1-2 uppercase letters followed by 6-9 digits
- This matches product codes, part numbers, flight numbers (AA1234567), room numbers, etc.
- Weight is 0.85 — high for such a broad pattern

### `out_pii_crypto_wallet` pattern is overly broad — `src/picowatch/rules/output_policy/pii_leak.yaml`
- Pattern `(?:0x)?[0-9a-fA-F]{40}` matches any 40+ hex character sequence
- Matches memory addresses, hash values, hex-encoded data, UUIDs without hyphens
- Weight is 0.80

### `out_harm_hacking` pattern is overly broad — `src/picowatch/rules/output_policy/harmful_content.yaml`
- Matches "how to hack into a system" but also "how to hack into a system" in cybersecurity educational content
- Weight 0.70 — below block threshold alone but contributes to cumulative scoring

## Known Bugs and Logic Issues

1. **OTel version mismatch** — `src/picowatch/telemetry/otel.py:41,60` hardcodes `"0.7.0"` instead of reading `__version__`. Spans report wrong version.

2. **CLI serve defaults to 0.0.0.0** — `src/picowatch/cli.py:114` overrides the config default of `127.0.0.1`. Running `picowatch serve` without `--host` exposes the server on all interfaces, contradicting the "default bind 127.0.0.1" claim in README.

3. **Email detection gap** — `out_pii_email` YAML rule detects emails, but `_detect_pii()` in `src/picowatch/output_guard/__init__.py` does NOT redact emails. Emails are flagged as violations but passed through unredacted.

4. **Phone detection gap** — `out_pii_phone` YAML rule detects phone numbers, but `_detect_pii()` does NOT have a phone number regex. Phone numbers are flagged but not redacted.

5. **`schema_dir` dead config** — `PicoWatchConfig.schema_dir` is settable but never read by OutputGuard. Setting `PICOWATCH_SCHEMA_DIR` has no effect.

6. **Helm chart version stale** — `deploy/helm/picowatch/Chart.yaml` says `appVersion: "0.7.0"` and `version: 0.7.0`. Values.yaml image tag is `"0.7.0"`. Two major versions behind.

7. **Passport regex false positives** — `out_pii_passport` YAML pattern `\b[A-Z]{1,2}\d{6,9}\b` matches flight numbers, part numbers, room codes, etc. at weight 0.85.

8. **Crypto wallet regex false positives** — `out_pii_crypto_wallet` pattern matches any 40-char hex string at weight 0.80. SHA-256 hashes, memory addresses, etc. will trigger it.

9. **PII redaction in `_detect_pii()` runs after YAML rule engine** — the YAML rules add violations to the list, then `_detect_pii()` adds its own violations. If both detect the same pattern (e.g., SSN), the violation appears twice in the list: once from YAML (`out_pii_ssn`) and once from Python (`out_pii_ssn`). The `violations` list is deduplicated by `set()` in the YAML path but `_detect_pii()` appends directly — so some violations could appear duplicated.

10. **Admin app creates its own PromptGuard** — `create_admin_app()` in `server.py` instantiates a fresh `PromptGuard(config=config)`. This means rule loading and regex compilation happens twice (once for main app, once for admin app). Not a bug per se, but wasteful.

## Test Coverage

**258 tests across 14 test files** (per README badge; actual count at time of writing):

| Test File | Approx Count | What It Tests |
|-----------|-------------|---------------|
| test_prompt_guard.py | ~45 | Normalizer, RuleEngine, Scorer, PromptGuard integration |
| test_output_guard.py | ~29 | OutputGuard validation, PII detection/redaction, schema check |
| test_server.py | ~55 | All HTTP endpoints, auth, rate limiting |
| test_server_integration.py | ~29 | Full request flow, dual-port, auth enforcement |
| test_picoshogun.py | ~17 | Plugin init, WatchGuard protocol, event bus, determinism |
| test_otel.py | ~16 | OTel span creation, graceful degradation, attribute setting |
| test_config.py | ~8 | Defaults, env vars, TOML loading, file permissions |
| test_ratelimit.py | ~10 | Sliding window, IP isolation, reset, expiry |
| test_telemetry.py | ~8 | Audit log, Prometheus rendering, integrity checksums |
| test_rules_corpus.py | ~6 | YAML validity, unique IDs, required fields |
| test_determinism.py | ~3 | 10-run stability for prompt + output |
| test_types.py | ~10 | Dataclass construction, verdict derivation |
| test_cli.py | ~2 | Help output, health subcommand |

**Not tested:**
- Docker build or docker-compose deployment
- Helm chart rendering (helm template) or deployment
- Actual PicoShogun integration (only unit tests with mock events)
- OTel with real collector endpoint
- Rate limiter under concurrent load
- Audit DB under concurrent writes
- Schema validation with `jsonschema` library present (basic path only)
- PyPI package build and install from wheel

## Dependencies

**Runtime (hard):**
- `pyyaml>=6.0` — YAML rule loading
- `tomli>=2.0` — TOML config (Python < 3.11 only; 3.11+ uses stdlib `tomllib`)

**Runtime (optional):**
- `fastapi>=0.100` + `uvicorn>=0.23` — HTTP server (`pip install picowatch[server]`)
- `opentelemetry-api>=1.20`, `opentelemetry-sdk>=1.20`, `opentelemetry-exporter-otlp>=1.20` — OTel tracing (`pip install picowatch[otel]`)

**Dev:**
- `pytest>=7.0`, `pytest-asyncio>=0.21`, `pytest-cov>=4.0` — testing
- `ruff>=0.4` — linting
- `mypy>=1.8` — type checking
- `jsonschema>=4.0` — full schema validation (dev only, not runtime)
- `httpx>=0.24` — test client
- `fastapi>=0.100`, `uvicorn>=0.23` — server testing

## What's NOT Done That README or Docs Imply IS Done

1. **"Production/Stable" classifier in pyproject.toml** — `Development Status :: 5 - Production/Stable`. No production deployments exist. This is aspirational.

2. **README says "default bind 127.0.0.1"** — True for `PicoWatchConfig.host` default, but CLI `serve` subcommand defaults `--host` to `0.0.0.0` (`cli.py:114`), which overrides the config default.

3. **README implies full JSON Schema validation** — Only basic type + required fields checked without `jsonschema`. Full Draft 2020-12 validation requires the dev-only `jsonschema` package.

4. **Docker section in README** — Dockerfile and docker-compose exist but are untested in real deployments. No published container image.

5. **Helm chart** — Exists in `deploy/helm/` but version is stale (0.7.0) and never tested in a real cluster.

6. **SBOM / SLSA claims** — ADR-008 mentions SLSA compliance. The SBOM script exists but is not integrated into CI. No SLSA provenance is actually generated or verified.

7. **PicoShogun integration** — Plugin code works in isolation. PicoShogun's event bus API is not stable or documented. The integration is one-sided.

8. **README badge says "91 rules"** — Actual count is 59 prompt + 32 output = 91 total. This matches.

9. **README badge says "258 tests passing"** — Test count is approximately correct based on test file review.

10. **`--picoshogun-plugin` CLI flag** — Prints plugin status and exits. Doesn't actually connect to PicoShogun or run a daemon. The docstring says "In production, PicoShogun would call plugin.on_event() directly" — it's a print-and-exit stub for CLI use.