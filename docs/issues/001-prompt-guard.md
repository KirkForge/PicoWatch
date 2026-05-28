# feat(prompt-guard): implement L5 PromptGuard rule engine

**Labels:** enhancement

ADR-003 implementation.

## Scope

- Rule engine with YAML rule loading from configurable directory
- Normalization pipeline: NFKC unicode, whitespace, encoding detection (base64/hex/URL/ROT13), comment stripping, markdown deobfuscation
- Rule categories: `inj_override_`, `inj_role_`, `inj_context_`, `inj_encode_`, `inj_extract_`, `inj_multiturn_`
- Weighted scoring: per-rule weights (0.0–1.0), final score = max(individual, weighted average)
- Configurable thresholds: block (0.7), warn (0.4), pass (<0.4)
- Determinism guarantee: sorted rule evaluation, rounded scores, no randomness
- Corpus versioning (SHA-256 hash of all rule files)

## Acceptance Criteria

- [ ] `PromptGuard` class with `check() → PromptScanResult`
- [ ] 20+ default rules across all 6 categories
- [ ] Normalization pipeline unit tests
- [ ] Determinism verification (`--verify-determinism` passes)
- [ ] YAML rule loading with custom rules dir
- [ ] Corpus hash in every `PromptScanResult`

**Depends on:** `types.py` data structures from scaffold
