# ADR-005: Integration Interface — Standalone-First with PicoShogun Binding

**Status:** Accepted

**Context:**

PicoWatch must work standalone (like PicoDome and PicoSentry) while also integrating into PicoShogun's firewall when available. The integration must be loose — PicoWatch should not import PicoShogun code or require PicoShogun to run.

Options considered:
- **Tight coupling** — import PicoShogun modules directly
- **HTTP API only** — communicate via REST/WebSocket
- **Python library + optional adapter** — import as library, with a PicoShogun adapter that hooks into the event bus

**Decision:**

**Python library first, with an optional PicoShogun adapter.**

### Standalone Mode

```python
from picowatch import PromptGuard, OutputGuard, TelemetrySink

guard = PromptGuard(rules_dir="/etc/picowatch/rules")
result = guard.check("user input here")

sink = TelemetrySink()
sink.record_prompt_scan(result)
```

### PicoShogun Integration Mode

When PicoShogun is present, PicoWatch loads as a plugin:

```yaml
# In PicoShogun's config
plugins:
  picowatch:
    enabled: true
    config:
      prompt_guard:
        threshold: 0.7
      output_guard:
        schema_dir: /etc/picowatch/schemas
      telemetry:
        otel_endpoint: localhost:4317
```

PicoShogun calls PicoWatch's defense functions through a thin adapter that:
1. Receives events from PicoShogun's event bus
2. Passes prompts through L5 PromptGuard
3. Passes responses through L6 OutputGuard
4. Emits L7 telemetry back to PicoShogun's metrics pipeline

### Interface Contract

```python
class WatchGuard(Protocol):
    """Protocol that both standalone and PicoShogun modes implement."""
    def scan_prompt(self, text: str, context: dict | None = None) -> PromptScanResult: ...
    def validate_output(self, output: str, schema: dict | None = None) -> ValidationResult: ...
    def health(self) -> HealthStatus: ...
```

### Firewall Binding

In PicoShogun, PicoWatch's PromptGuard and OutputGuard are wired into the PicoShogun firewall pipeline as L5/L6 filters. The firewall runs: L1 (rate limit) → L2 (PicoSentry static scan) → L3 (PicoDome sandbox) → L4 (PicoDome behavioral) → L5 (PicoWatch prompt guard) → L6 (PicoWatch output guard).

### CLI

The `picowatch` CLI works in all modes:

```bash
# Standalone scan
picowatch scan-prompt --text "hello"

# Daemon mode (PicoShogun calls via HTTP)
picowatch serve --port 8766

# PicoShogun plugin mode (loaded by PicoShogun process)
picowatch --picoshogun-plugin
```

**Consequences:**

✅ Positive: PicoWatch works without PicoShogun — no coupling.
✅ Positive: PicoShogun integration is a thin adapter, not a rewrite.
✅ Positive: Protocol-based interface allows mocking in tests.
⚠️ Negative: Maintaining two modes (standalone + plugin) adds test surface.
