# ADR-005: Integration Interface — Standalone-First with Shogun Binding

**Status:** Accepted

**Context:**

PicoWatch must work standalone (like IronDome and PicoSentry) while also integrating into Shogun's Iron Dome firewall when available. The integration must be loose — PicoWatch should not import Shogun code or require Shogun to run.

Options considered:
- **Tight coupling** — import Shogun modules directly
- **HTTP API only** — communicate via REST/WebSocket
- **Python library + optional adapter** — import as library, with a Shogun adapter that hooks into the event bus

**Decision:**

**Python library first, with an optional Shogun adapter.**

### Standalone Mode

```python
from picowatch import PromptGuard, OutputGuard, TelemetrySink

guard = PromptGuard(rules_dir="/etc/picowatch/rules")
result = guard.check("user input here")

sink = TelemetrySink()
sink.record_prompt_scan(result)
```

### Shogun Integration Mode

When Shogun is present, PicoWatch loads as a plugin:

```yaml
# In Shogun's config
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

Shogun calls PicoWatch's defense functions through a thin adapter that:
1. Receives events from Shogun's event bus
2. Passes prompts through L5 PromptGuard
3. Passes responses through L6 OutputGuard
4. Emits L7 telemetry back to Shogun's metrics pipeline

### Interface Contract

```python
class WatchGuard(Protocol):
    """Protocol that both standalone and Shogun modes implement."""
    def scan_prompt(self, text: str, context: dict | None = None) -> PromptScanResult: ...
    def validate_output(self, output: str, schema: dict | None = None) -> ValidationResult: ...
    def health(self) -> HealthStatus: ...
```

### Firewall Binding

In Shogun, PicoWatch's PromptGuard and OutputGuard are wired into the Iron Dome firewall pipeline as L5/L6 filters. The firewall runs: L1 (rate limit) → L2 (PicoSentry static scan) → L3 (sandbox) → L4 (behavioral) → L5 (PicoWatch prompt guard) → L6 (PicoWatch output guard).

### CLI

The `picowatch` CLI works in all modes:

```bash
# Standalone scan
picowatch scan-prompt --text "hello"

# Daemon mode (Shogun calls via HTTP)
picowatch serve --port 8766

# Shogun plugin mode (loaded by Shogun process)
picowatch --shogun-plugin
```

**Consequences:**

✅ Positive: PicoWatch works without Shogun — no coupling.
✅ Positive: Shogun integration is a thin adapter, not a rewrite.
✅ Positive: Protocol-based interface allows mocking in tests.
⚠️ Negative: Maintaining two modes (standalone + plugin) adds test surface.
