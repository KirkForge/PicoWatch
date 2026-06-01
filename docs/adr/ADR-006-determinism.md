# ADR-006: Determinism & Reproducibility

**Status:** Accepted

**Context:**

PicoWatch inherits the PicoShogun platform's determinism requirement. PicoSentry guarantees same input + same corpus = same output. PicoDome guarantees same command + same policy = same verdict. PicoWatch must make the same guarantee for prompt/output defense.

The challenge: scoring thresholds, rule ordering, and normalization could introduce nondeterminism if not carefully controlled.

**Decision:**

### Determinism Contract

**Same input + same rule set + same config = same score, same verdict, same rule list. Always.**

This is PicoWatch's core promise, matching PicoSentry's SCAAT.md guarantee.

### Sources of Nondeterminism (Eliminated)

| Source | Risk | Mitigation |
|--------|------|------------|
| Rule ordering | Different match order → different score | Rules sorted by ID before evaluation |
| Float precision | Score rounding → different threshold result | Use `round(score, 6)` everywhere |
| Unicode normalization | Different NFC/NFKC results | Always NFKC, checked at import time |
| Regex engine | Different backtracking across Python versions | Use `re` stdlib only, no `regex` package |
| Timestamp in output | Time varies across runs | Timestamps in results, not in scoring logic |
| Random state | None expected, but guarded | `random.seed(0)` if any randomness is introduced |

### Corpus Versioning

Rule sets are versioned with a corpus hash (SHA-256 of all rule files concatenated). This is included in every `PromptScanResult` and `ValidationResult`:

```python
@dataclass(frozen=True)
class PromptScanResult:
    blocked: bool
    score: float
    rules_matched: list[str]
    corpus_hash: str      # SHA-256 of rule files
    corpus_version: str   # e.g. "2026.05.1"
    duration_ms: float
```

### Verification Mode

Like PicoSentry and PicoDome, PicoWatch supports `--verify-determinism`:

```bash
picowatch scan-prompt --text "test input" --verify-determinism
# Runs twice, compares results. Exits 0 if identical, 1 if different.
```

### SCAAT Compliance

PicoWatch follows the same SCAAT (Supply Chain Artifact Attestation) model as PicoSentry:
- Corpus hash in every output
- Build reproducibility (same source = same wheel hash)
- No network calls during evaluation
- No environment-dependent behavior

**Consequences:**

✅ Positive: Audit-friendly — every result is verifiable and reproducible.
✅ Positive: Test-friendly — deterministic means stable test suites.
✅ Positive: SCAAT compliance enables supply-chain attestation.
⚠️ Negative: No ML-based scoring (nondeterministic by nature). Future ML layer must be optional and non-blocking.
