# feat(output-guard): implement L6 OutputGuard validation pipeline

**Labels:** enhancement

ADR-004 implementation.

## Scope

- Output validation pipeline: Schema Check → Content Policy → PII Scan → Format Guard → Verdict
- JSON Schema validation (Draft 2020-12) for structured outputs
- Content policy rules (same YAML format as L5): `out_pii_`, `out_harm_`, `out_halluc_`, `out_fmt_`, `out_exfil_`
- PII detection: regex patterns for SSN, credit card, phone, email, API keys
- PII redaction in `ValidationResult`
- Feedback loop: flagged prompts get stricter output validation (lower threshold)

## Acceptance Criteria

- [ ] `OutputGuard` class with `validate() → ValidationResult`
- [ ] Schema validation against JSON Schema
- [ ] Content policy rule engine (reuse L5 patterns)
- [ ] PII detection + redaction with configurable patterns
- [ ] Feedback integration with PromptGuard results
- [ ] Deterministic: same output + same rules = same verdict

**Depends on:** L5 PromptGuard (shared rule engine infrastructure)
