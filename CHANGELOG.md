# Changelog

All notable changes to PicoWatch will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-05-29

### Added
- Shogun Iron Dome plugin adapter (`picowatch.shogun.PicoWatchPlugin`)
- WatchGuard protocol interface for Shogun firewall pipeline
- Event bus integration (`on_event`) for prompt_received, output_generated, health_check events
- Plugin health endpoint with uptime, rules_loaded, corpus_hash
- Prometheus metrics passthrough for Shogun aggregator
- 17 new tests for Shogun plugin (init, scan_prompt, validate_output, event bus, determinism, metrics)

### Changed
- Bumped version to 0.2.0
- Exported `PicoWatchPlugin` and `WatchGuard` from top-level package

## [0.1.0] - 2026-05-29

### Added
- Initial project scaffold (ADR 001–008)
- L5 Prompt Guard architecture (deterministic rule engine)
- L6 Output Guard architecture (schema + policy validation)
- L7 Telemetry architecture (OTel traces, Prometheus metrics, audit log)
- CLI skeleton (`scan-prompt`, `validate-output`, `serve`)
- Determinism contract and SCAAT compliance model
- Standalone-first integration design with Shogun binding
- Supply-chain hardening (zero-dep core, self-scan, self-sandbox)
