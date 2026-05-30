# feat(ci): full CI pipeline with self-scan and self-sandbox

**Labels:** enhancement

ADR-008 supply-chain hardening.

## Scope

- ci-cleandev v3 pipeline: ruff → mypy → pytest → build → hash check
- PicoSentry self-scan of dependencies in CI
- PicoDome self-sandbox of post-install hooks in CI
- Reproducible build verification (same source = same wheel hash)
- SLSA L3 build provenance
- CycloneDX SBOM on release

## Acceptance Criteria

- [ ] ci-cleandev runs clean (ruff, mypy, pytest all pass)
- [ ] PicoSentry scans picowatch dependencies in CI
- [ ] Build produces reproducible wheel hash
- [ ] SBOM generated on release
