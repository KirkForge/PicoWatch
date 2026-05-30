# feat(shogun-plugin): PicoShogun firewall integration adapter

**Labels:** enhancement

ADR-005 PicoShogun integration.

## Scope

- WatchGuard protocol class that PicoShogun loads as a plugin
- Adapter that receives PicoShogun event bus events, passes through PromptGuard/OutputGuard
- Emits L7 telemetry back to PicoShogun metrics pipeline
- Plugin config in PicoShogun's YAML
- Firewall pipeline order: L1 (rate limit) → L2 (PicoSentry) → L3 (PicoDome sandbox) → L4 (PicoDome behavioral) → L5 (PicoWatch prompt) → L6 (PicoWatch output)

## Acceptance Criteria

- [ ] WatchGuard protocol implements scan_prompt(), validate_output(), health()
- [ ] Plugin loads in PicoShogun via config
- [ ] Events flow through all 6 layers
- [ ] Telemetry emitted to PicoShogun metrics

**Depends on: L5, L6, L7, PicoShogun repo
