"""PicoWatch — LLM defender with telemetry."""

__version__ = "0.1.0"

from picowatch.config import PicoWatchConfig
from picowatch.health import health_check
from picowatch.output_guard import OutputGuard
from picowatch.prompt_guard import PromptGuard
from picowatch.telemetry import TelemetrySink
from picowatch.types import (
    HealthStatus,
    PromptScanResult,
    Rule,
    ValidationResult,
    Verdict,
)

__all__ = [
    "PicoWatchConfig",
    "PromptGuard",
    "OutputGuard",
    "TelemetrySink",
    "PromptScanResult",
    "ValidationResult",
    "Rule",
    "Verdict",
    "HealthStatus",
    "health_check",
]