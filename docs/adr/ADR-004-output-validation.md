# ADR-004: Output Validation & Content Policy

**Status:** Accepted

**Context:**

LLM outputs can contain harmful content, PII leaks, hallucinated facts, schema violations, and format exploits. PicoWatch's L6 Output Guard must validate outputs against known constraints without introducing new attack surfaces.

Options considered:
- **Schema-only validation** — structural but misses semantic issues
- **Content policy engine** — semantic but needs rule definitions
- **Combined schema + policy** — comprehensive but more complex

**Decision:**

Use a **combined schema + policy engine** with deterministic evaluation.

### Output Validation Pipeline

```
LLM Output → Schema Check → Content Policy → PII Scan → Format Guard → Verdict
```

### Schema Validation

JSON Schema validation for structured outputs. Supports:
- Draft 2020-12 JSON Schema (stdlib `json` + optional `jsonschema`)
- Type checking: required fields, enum constraints, pattern matching
- Size limits: max string length, max array items, max nesting depth

### Content Policy Rules

Same YAML rule format as L5 prompt rules, but for outputs:

| Category | ID Prefix | Example |
|----------|-----------|---------|
| **PII leak** | `out_pii_` | SSN, email, phone, API keys in output |
| **Harmful content** | `out_harm_` | violence, CSAM, self-harm instructions |
| **Hallucination marker** | `out_halluc_` | unverifiable claims presented as fact |
| **Format violation** | `out_fmt_` | markdown in JSON-only mode, code injection |
| **Exfiltration** | `out_exfil_` | file contents, env vars, internal URLs |

### PII Detection

Deterministic regex patterns for common PII (SSN, credit card, phone, email). No ML models. Users can add custom PII patterns via YAML config.

### Verdict

Each validation step returns a `ValidationResult`:

```python
@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    score: float           # 0.0–1.0
    violations: list[str] # rule IDs
    redacted: str | None   # PII-redacted version of output
    duration_ms: float
```

Overall verdict: `pass` (all checks), `warn` (issues but below threshold), `fail` (above threshold or hard violation).

### Integration with L5

Output Guard can reference Prompt Guard results. If a prompt was flagged but not blocked, the output is scrutinized more aggressively (lower threshold). This creates a feedback loop: suspicious prompts get stricter output validation.

**Consequences:**

✅ Positive: Comprehensive — structural + semantic + privacy in one pipeline.
✅ Positive: Deterministic — same output + same rules = same verdict.
✅ Positive: PII redaction produces safe output immediately.
⚠️ Negative: Schema validation requires consumers to provide schemas.
⚠️ Negative: PII regex patterns have false positives (mitigated by configurable threshold).
