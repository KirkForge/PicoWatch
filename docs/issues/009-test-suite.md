# feat(tests): comprehensive test suite (target 90%+ coverage)

**Labels:** testing

## Scope

- test_prompt_guard.py: rule engine, normalization, scoring, determinism verification
- test_output_guard.py: schema validation, PII detection, content policy, redaction
- test_telemetry.py: metrics format, audit log writes, OTel spans
- test_cli.py: all CLI subcommands
- test_determinism.py: verify same input + same rules = same score across 10 runs
- test_rules_corpus.py: validate all default rules load and have valid regex

## Acceptance Criteria

- [ ] 90%+ line coverage
- [ ] All tests pass with ruff + mypy clean
- [ ] Determinism test: 10 identical runs produce identical results
- [ ] No network calls in test suite
