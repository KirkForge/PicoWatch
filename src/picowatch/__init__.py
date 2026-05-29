"""PicoWatch — LLM defender with telemetry."""

__version__ = "0.5.0"

from picowatch.config import PicoWatchConfig
from picowatch.health import health_check
from picowatch.output_guard import OutputGuard
from picowatch.prompt_guard import PromptGuard
from picowatch.shogun import PicoWatchPlugin, WatchGuard
from picowatch.telemetry import TelemetrySink
from picowatch.types import (
    HealthStatus,
    PromptScanResult,
    Rule,
    ValidationResult,
    Verdict,
)

__all__ = [
    "HealthStatus",
    "OutputGuard",
    "PicoWatchConfig",
    "PicoWatchPlugin",
    "PromptGuard",
    "PromptScanResult",
    "Rule",
    "TelemetrySink",
    "ValidationResult",
    "Verdict",
    "WatchGuard",
    "health_check",
]
