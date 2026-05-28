# ADR-003: Prompt Injection Defense Strategy

**Status:** Accepted

**Context:**

Prompt injection is the #1 LLM security threat. Attacks range from obvious ("ignore previous instructions") to subtle (indirect injections in retrieved context, base64-encoded payloads, Unicode homoglyphs). PicoWatch's L5 Prompt Guard must detect these without using an LLM — the guard itself must be deterministic and fast.

Options considered:
- **LLM-as-judge** — powerful but slow, expensive, nondeterministic, and itself injectable
- **Regex-only** — fast but brittle, easy to evade
- **Structured rule engine with normalization** — balanced: fast, deterministic, extensible

**Decision:**

Use a **structured rule engine with input normalization**. Every prompt passes through a pipeline:

```
Raw Input → Normalize → Encode Detection → Rule Matching → Score → Verdict
```

### Normalization Pipeline (runs before all rules)

1. **Unicode normalization** (NFKC) — collapses homoglyphs, ligatures, and compatibility characters
2. **Whitespace normalization** — collapse runs, normalize line endings
3. **Encoding detection** — flag base64, hex, URL-encoded, and ROT13 payloads
4. **Comment stripping** — remove HTML comments `<!-- -->`, `/* */`, `//` line comments
5. **Markdown deobfuscation** — flatten zero-width characters, invisible Unicode

### Rule Categories

| Category | ID Prefix | Example |
|----------|-----------|---------|
| **Instruction override** | `inj_override_` | "ignore all previous instructions" |
| **Role manipulation** | `inj_role_` | "you are now DAN", "act as if you are..." |
| **Context injection** | `inj_context_` | hidden instructions in retrieved documents |
| **Encoding attack** | `inj_encode_` | base64/ROT13 payloads, Unicode tricks |
| **Extraction attempt** | `inj_extract_` | "repeat your system prompt", "what were you told?" |
| **Multi-turn trap** | `inj_multiturn_` | "let's play a game", "for research purposes" |

### Scoring

Each rule has a weight (0.0–1.0). Final score = max(individual rule score, weighted average). Threshold is configurable (default: 0.7 = block, 0.4 = warn, below = pass).

### Determinism Guarantee

Same input + same rule set + same corpus version = same score. Always. No randomness, no model calls, no network requests during evaluation.

### Extensibility

Rules are loaded from YAML files in a configurable directory. Users can add custom rules without modifying PicoWatch source. The rule format:

```yaml
id: inj_override_ignore
category: instruction_override
weight: 0.9
pattern: "ignore\\s+(?:all\\s+)?(?:previous|prior|above|earlier)\\s+(?:instructions?|rules?|prompts?)"
description: "Direct instruction override attempt"
normalization: [unicode, whitespace, comments]
```

**Consequences:**

✅ Positive: Deterministic — same input always produces the same score and verdict.
✅ Positive: Fast — regex + normalization is O(n) on input length.
✅ Positive: Extensible — custom rules via YAML without code changes.
✅ Positive: No LLM dependency — can't be attacked through the defense mechanism itself.
⚠️ Negative: Pattern-based rules require updates for novel attack vectors.
⚠️ Negative: Sophisticated obfuscation may evade individual rules (mitigated by normalization pipeline).
