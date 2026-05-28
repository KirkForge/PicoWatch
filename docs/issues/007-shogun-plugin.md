# feat(shogun-plugin): Shogun Iron Dome firewall integration adapter

**Labels:** enhancement

ADR-005 Shogun integration.

## Scope

- WatchGuard protocol class that Shogun loads as a plugin
- Adapter that receives Shogun event bus events, passes through PromptGuard/OutputGuard
- Emits L7 telemetry back to Shogun metrics pipeline
- Plugin config in Shogun's YAML
- Firewall pipeline order: L1 (rate limit) → L2 (PicoSentry) → L3 (sandbox) → L4 (behavioral) → L5 (PicoWatch prompt) → L6 (PicoWatch output)

## Acceptance Criteria

- [ ] WatchGuard protocol implements scan_prompt(), validate_output(), health()
- [ ] Plugin loads in Shogun via config
- [ ] Events flow through all 6 layers
- [ ] Telemetry emitted to Shogun metrics

**Depends on:** L5, L6, L7, Shogun repo
