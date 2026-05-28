# feat(cli): implement CLI commands and HTTP daemon

**Labels:** enhancement

ADR-007 implementation.

## Scope

- `picowatch scan-prompt --text/--file` → PromptScanResult JSON
- `picowatch validate-output --schema --output` → ValidationResult JSON
- `picowatch serve --host --port` → FastAPI HTTP daemon
- `picowatch --verify-determinism` → run twice, compare results
- `picowatch rules` → list active rules
- `picowatch health` → health status
- Config from `PICOWATCH_*` env vars, `picowatch.toml`, CLI flags

### HTTP API

- `POST /v1/scan/prompt`
- `POST /v1/scan/output`
- `GET /v1/health`
- `GET /metrics` (Prometheus)
- `GET /v1/rules`

## Acceptance Criteria

- [ ] All CLI subcommands functional
- [ ] HTTP daemon starts and responds
- [ ] Config priority: CLI > env > file > defaults
- [ ] API key auth on write endpoints

**Depends on:** L5, L6, L7
