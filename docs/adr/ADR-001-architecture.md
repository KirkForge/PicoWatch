# ADR-001: Architecture — Defense Layer Model (L5/L6/L7)

**Status:** Accepted

**Context:**

The Pico Security Series defends across multiple layers. PicoSentry covers static scanning (L2), PicoDome covers runtime sandboxing and behavioral analysis (L3/L4). No product addresses the emerging threat surface of LLM interactions: prompt injection, output manipulation, and lack of observability.

PicoWatch must fill this gap as a standalone tool that also integrates into PicoShogun's firewall when available.

The question: how should PicoWatch model its defense responsibilities?

**Decision:**

PicoWatch owns three defense layers:

| Layer | Name | Responsibility |
|-------|------|----------------|
| **L5** | Prompt Guard | Detect jailbreaks, indirect injections, role manipulation, instruction overrides, and encoding attacks in prompts before they reach the LLM |
| **L6** | Output Guard | Validate LLM outputs against schemas, content policies, PII/exfiltration rules, and format constraints |
| **L7** | Telemetry | OpenTelemetry traces, Prometheus metrics, structured audit logging — full observability for every LLM request/response cycle |

Architecture principles:

1. **Deterministic-first**: L5/L6 rules are pattern-matching and structural checks. No LLM-in-the-loop for defense decisions. This mirrors PicoSentry's deterministic guarantee — same input, same output, every time.
2. **Pipe-through, not proxy**: PicoWatch inspects and annotates requests; it doesn't become a network proxy between the LLM caller and the API. This keeps it composable and avoids latency injection.
3. **Three independent subsystems**: PromptGuard, OutputGuard, and TelemetrySink are separate modules that can be used independently. PicoShogun integration composes them into the firewall pipeline.
4. **Zero external dependencies at runtime**: Core defense rules work with only stdlib. OpenTelemetry is an optional dependency (`[otel]`).

**Consequences:**

✅ Positive: Clear separation of concerns — each layer is testable in isolation.
✅ Positive: Deterministic rules mean reproducible test results, matching PicoSentry's guarantee.
✅ Positive: Standalone operation — no PicoShogun dependency required.
⚠️ Negative: L5 rules are pattern-based and won't catch novel injection techniques until rules are updated.
⚠️ Negative: L6 output validation requires schemas; consumers must provide them or accept default policies.
