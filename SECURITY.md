# Security Policy

## Reporting a Vulnerability

PicoWatch is a security tool. If you discover a vulnerability, please report it responsibly.

**Contact:** security@kirkforge.dev

**Do not** file public issues for security vulnerabilities.

## Response Timeline

| Stage | Target |
|-------|--------|
| Acknowledgment | 24 hours |
| Initial assessment | 72 hours |
| Fix or mitigation | 7 days (critical), 14 days (high), 30 days (medium/low) |
| Disclosure | After fix is released |

## Supply-Chain Security

Per ADR-008, PicoWatch follows the Shogun platform hardening model:

- **Zero mandatory dependencies** for core functionality
- **Pinned dependencies** for all optional extras
- **Self-scan**: CI runs PicoSentry against our own dependencies before merge
- **Self-sandbox**: CI runs IronDome on any post-install hooks
- **SLSA Level 3**: Build provenance attestation on every release
- **SBOM**: CycloneDX SBOM generated on every release
- **Signed releases**: GPG-signed tags for every version

## Runtime Security

- No `eval()`, `exec()`, or `subprocess` during rule evaluation
- No network calls during scoring (offline by design)
- Rule sandboxing: custom rules are YAML-only, no Python code execution
- Input size limits: default 1MB max prompt size
- Per-IP rate limiting on HTTP daemon (configurable)
- API key authentication on write endpoints (configurable)
- Audit log integrity: SQLite WAL with checksums

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.5.x | Active development |
| < 0.5 | Not supported |

## Scope

This policy covers:
- The PicoWatch core library and CLI
- The FastAPI HTTP server
- The Shogun plugin adapter
- Rule definitions and normalization pipeline

Out of scope:
- Third-party dependencies (report to upstream)
- User-defined custom rules
- Infrastructure misconfiguration
