# ADR-008: Security & Supply-Chain Hardening

**Status:** Accepted

**Context:**

PicoWatch is itself a security tool. It must be trustworthy — a compromised or tampered PicoWatch undermines the entire defense stack. Supply-chain attacks on security tools are a known attack vector (e.g., XZ Utils, ua-parser-js).

The Pico Security Series already includes PicoSentry for static scanning and PicoDome for runtime sandboxing. PicoWatch should follow the same hardening model.

**Decision:**

### Supply-Chain Protection

1. **Minimal dependencies**: Core functionality uses only Python stdlib. `opentelemetry-*` and `fastapi`/`uvicorn` are optional extras. The `pip install picowatch` base has zero third-party dependencies.
2. **Pinned dependencies**: All optional dependencies pinned to exact versions in `pyproject.toml`.
3. **Self-scan**: PicoWatch's CI runs PicoSentry against its own dependencies before merge.
4. **Self-sandbox**: CI runs PicoDome sandbox on any post-install hooks.

### Runtime Security

1. **No eval, no exec**: PicoWatch never calls `eval()`, `exec()`, or `subprocess` during rule evaluation.
2. **No network during evaluation**: Scoring and rule matching are offline. Network is only for telemetry export (optional).
3. **Rule sandboxing**: Custom user rules are loaded from YAML only. No Python code execution from rule files.
4. **Input size limits**: Default max prompt size 1MB. Configurable. Rejects oversized inputs immediately.
5. **Rate limiting**: Built-in per-IP rate limiting on HTTP daemon (same model as PicoShogun).

### Secrets & Configuration

1. **No secrets in code**: API keys, tokens, and OTLP endpoints are environment variables only.
2. **Config file permissions**: `picowatch.toml` is checked for overly-permissive modes on startup. Warns if group/world-readable.
3. **Audit log integrity**: SQLite audit log uses WAL mode with checksums (same model as PicoPicoShogun's WORM audit).

### Build & Release

1. **Reproducible builds**: `pip install picowatch==X.Y.Z` produces the same wheel hash across environments.
2. **SLSA Level 3**: Build provenance attestation on every release, matching PicoSentry/PicoDome.
3. **SBOM**: CycloneDX SBOM generated on every release.
4. **Signed releases**: GPG-signed tags for every version.

### CI Pipeline

```bash
# ci-cleandev v3 pipeline
1. ruff check .         # lint
2. mypy src             # type check
3. python -m pytest     # tests
4. picosentry scan .    # self-scan dependencies
5. build wheel + hash   # reproducibility check
```

**Consequences:**

✅ Positive: Zero mandatory dependencies means minimal attack surface.
✅ Positive: Self-scan and self-sandbox provide defense-in-depth.
✅ Positive: SLSA L3 + SBOM matches PicoSentry PicoSentry/PicoDome hardening PicoDome hardening.
⚠️ Negative: Zero-dependency core limits what normalization can do without optional deps (e.g., `regex` package for advanced Unicode).
⚠️ Negative: Reproducible builds require careful Python version pinning.
