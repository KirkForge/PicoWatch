# AGENTS.md — PicoWatch

## What PicoWatch IS

- A **deterministic pre-filter** for LLM prompt injection and output validation
- A **telemetry layer** (OTel, Prometheus, audit logging) for LLM interactions
- A standalone tool that also integrates with PicoShogun as a plugin
- Part of the **Pico Security Series** (PicoSentry → PicoDome → PicoWatch → PicoShogun)

## What PicoWatch is NOT

- A complete LLM security solution (it's a fast pre-filter, not an adaptive classifier)
- "Enterprise-grade" until proven in real deployments
- A replacement for human review of flagged content

## Mandatory Rules

- **Never commit**: `node_modules/`, `.venv/`, `venv/`, `__pycache__/`, `*.pyc`, `dist/`, `build/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `coverage/`, `*.log`, `.env`, `*.pem`, `*.key`
- **Always pull before work, push after work**
- **Git identity**: `Henrik Kirk <285947470+KirkForge@users.noreply.github.com>`
- **Commit format**: `type(scope): message` — feat, fix, docs, refactor, test, chore, wip
- **Pre-push CI**: `ci-cleandev` hooks block pushes on failure. Fix, don't bypass.

## Python Project Rules

- Use `python3 -m pytest` not bare `pytest`
- Use `ruff check .` for linting
- Use `mypy src` for type checking
- Never create venv in project root — use `.venv/`
- Never `pip install` without venv active

## Before Editing

1. `git pull`
2. Check `.gitignore` — don't stage ignored files
3. Check this file for project-specific rules

## Before Committing

1. `git status --short` — review staged files
2. No secrets, no generated files, no cache directories
3. `git diff --cached` — verify actual content
4. Let pre-push CI pass before pushing

## Anti-Slop Rules

- **No inflated claims** — if PicoWatch hasn't been deployed in production, don't call it "production-ready" or "enterprise-grade"
- **No AI co-authors** — commit author is Henrik Kirk, not any AI model
- **Honest status** — use ✅ /🔶 /❌ in STATE.md, not "98/100 readiness scores"
- **Correct naming** — PicoSentry, PicoDome, PicoWatch, PicoShogun (not IronDome, Shogun, 55NDeep)
- **No dead code** that implies capabilities the product doesn't have

## Secure-Defaults Checklist (Definition of Done)

> The secure state is the DEFAULT. Opening it up is an EXPLICIT, LOGGED, opt-in — never the fallback.

### Network binding
- [ ] Servers bind `127.0.0.1` by default. Non-loopback requires explicit flag/env AND auth enabled.
- [ ] Non-loopback bind logs a startup WARNING naming the exposure.
- [ ] CORS / allowed-hosts default to an explicit allowlist, never `["*"]`.

### Secrets
- [ ] No secret has a usable default value. Missing secret in production → refuse to boot (`exit 1`).
- [ ] Empty-string / placeholder secrets are never a valid signing key, even in dev.
- [ ] No secret value is written into generated artifacts.
- [ ] Secrets come from env or a secret manager — never a committed file.

### Comparisons (constant-time)
- [ ] Every secret / token / signature / hash comparison uses constant-time compare (`hmac.compare_digest`), never `==` / `!==`.
- [ ] `grep -rEn '(sig|hmac|token|secret|hash|key)\b.*(==|!=|!==)' src/` returns nothing that compares a secret.

### Allowlists / deny-by-default
- [ ] An empty allowlist means DENY, never ALLOW-ALL.
- [ ] Filesystem paths from tool/API input are confined to a configured root by default.
- [ ] Command execution uses argv arrays, never `shell=True` / string interpolation.

### Multi-tenant isolation
- [ ] Every shared store (sessions, cache, files, memory, routing) is keyed by `tenant_id`, not a global namespace.
- [ ] List/enumerate endpoints scope results to the calling tenant.
- [ ] Identity (owner/role/tenant) is derived from the authenticated session/token, never from the request body.
- [ ] At least one test asserts tenant A cannot read/modify tenant B's data.

### Authorization (not just authentication)
- [ ] Every protected endpoint calls BOTH authn (who are you) AND authz (are you allowed).
- [ ] New endpoints are deny-by-default — added to the authz table, not left to fall through.

### Sandbox / untrusted execution
- [ ] Child processes get an explicit env allowlist, not `{...process.env}` inheritance.
- [ ] For untrusted/model-generated code, real isolation (container/microVM/namespaces + rlimits + no-new-privs) is the DEFAULT path.
- [ ] Isolation claims in README match what the code enforces.

### Claims vs reality
- [ ] README maturity label matches code reality.
- [ ] Threat model is documented for anything that takes untrusted input.
- [ ] No dead code that implies a capability the product doesn't have.
