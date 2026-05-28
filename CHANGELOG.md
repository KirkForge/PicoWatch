# Changelog

All notable changes to PicoWatch will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

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
