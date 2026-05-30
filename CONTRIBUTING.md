# Contributing to PicoWatch

## Quick Start

```bash
make dev        # Install with all dependencies
make lint       # Run linting
make test       # Run test suite
make check      # Lint + test (CI equivalent)
```

## Development Setup

1. Clone the repo
2. Create a virtual environment: `python3 -m venv .venv && source .venv/bin/activate`
3. Install dev dependencies: `make dev`
4. Create a feature branch: `git checkout -b feat/my-feature`

## Commit Convention

We use conventional commits:

```
type(scope): description

feat(rules): add new injection pattern for base64 payloads
fix(server): fix rate limiter window calculation
docs(adr): add ADR-009 for caching strategy
test(determinism): add 100-run stability test
refactor(normalizer): extract encoding detection into separate method
chore(deps): pin pyyaml to 6.0.2
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `wip`

## Code Standards

- **Python 3.10+** — use union types (`X | Y`), match statements, etc.
- **Deterministic-first** — no randomness in scoring, no network calls during evaluation
- **Zero-dep core** — `picowatch` must work with only stdlib + PyYAML
- **Type hints everywhere** — `mypy --strict` must pass
- **Ruff** — linting and formatting
- **Tests** — every new rule, feature, or bug fix needs tests

## Architecture

PicoWatch has three independent subsystems (ADR-001):

| Layer | Module | Responsibility |
|-------|--------|---------------|
| L5 | `prompt_guard` | Injection detection |
| L6 | `output_guard` | Output validation + PII redaction |
| L7 | `telemetry` | Observability (OTel, Prometheus, audit) |

Each layer is independently testable. The PicoShogun plugin adapter (`shogun/`) composes them.

## Adding Rules

Rules are YAML files in `rules/`:

```yaml
- id: inj_override_custom
  category: instruction_override
  weight: 0.85
  pattern: "your\\\\s+custom\\\\s+regex"
  description: "Detect custom instruction override"
  normalization: [unicode, whitespace, comments]
```

Add corresponding tests in `tests/test_prompt_guard.py` or `tests/test_output_guard.py`.

## Pull Request Process

1. Ensure `make check` passes (lint + test)
2. Update `CHANGELOG.md` under `[Unreleased]`
3. Update `STATE.md` if architecture changes
4. Add ADR for significant design decisions
5. Keep PRs focused — one feature or fix per PR

## Determinism Contract

Same input + same rules + same config = same score, same verdict, same rule list. Always.

If your change affects scoring, run `make test-determinism` to verify.
