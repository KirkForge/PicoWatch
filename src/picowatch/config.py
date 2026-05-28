"""PicoWatch configuration.

Reads from: CLI flags > environment variables > config file > defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_RULES_DIR = Path(__file__).parent.parent.parent / "rules"
DEFAULT_THRESHOLD_BLOCK = 0.7
DEFAULT_THRESHOLD_WARN = 0.4
DEFAULT_MAX_PROMPT_SIZE = 1_000_000  # 1MB
DEFAULT_AUDIT_RETENTION_DAYS = 30
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8766
DEFAULT_ADMIN_PORT = 9091
DEFAULT_CORPUS_VERSION = "2026.05.1"


@dataclass
class PicoWatchConfig:
    """PicoWatch configuration.

    Priority: CLI > env > file > defaults.
    """

    # L5 Prompt Guard
    rules_dir: Path = field(default_factory=lambda: DEFAULT_RULES_DIR)
    threshold_block: float = DEFAULT_THRESHOLD_BLOCK
    threshold_warn: float = DEFAULT_THRESHOLD_WARN
    max_prompt_size: int = DEFAULT_MAX_PROMPT_SIZE

    # L6 Output Guard
    schema_dir: Path | None = None

    # L7 Telemetry
    otel_endpoint: str | None = None
    audit_retention_days: int = DEFAULT_AUDIT_RETENTION_DAYS

    # Server
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    admin_port: int = DEFAULT_ADMIN_PORT
    api_key: str | None = None  # If set, POST endpoints require this key

    # Corpus
    corpus_version: str = DEFAULT_CORPUS_VERSION

    # Misc
    verify_determinism: bool = False
    verbose: bool = False

    @classmethod
    def from_env(cls) -> PicoWatchConfig:
        """Load configuration from environment variables."""
        return cls(
            rules_dir=Path(os.environ.get("PICOWATCH_RULES_DIR", str(DEFAULT_RULES_DIR))),
            threshold_block=float(os.environ.get("PICOWATCH_THRESHOLD_BLOCK", str(DEFAULT_THRESHOLD_BLOCK))),
            threshold_warn=float(os.environ.get("PICOWATCH_THRESHOLD_WARN", str(DEFAULT_THRESHOLD_WARN))),
            max_prompt_size=int(os.environ.get("PICOWATCH_MAX_PROMPT_SIZE", str(DEFAULT_MAX_PROMPT_SIZE))),
            schema_dir=Path(p) if (p := os.environ.get("PICOWATCH_SCHEMA_DIR")) else None,
            otel_endpoint=os.environ.get("PICOWATCH_OTEL_ENDPOINT"),
            audit_retention_days=int(
                os.environ.get(
                    "PICOWATCH_AUDIT_RETENTION_DAYS",
                    str(DEFAULT_AUDIT_RETENTION_DAYS),
                )
            ),
            host=os.environ.get("PICOWATCH_HOST", DEFAULT_HOST),
            port=int(os.environ.get("PICOWATCH_PORT", str(DEFAULT_PORT))),
            admin_port=int(os.environ.get("PICOWATCH_ADMIN_PORT", str(DEFAULT_ADMIN_PORT))),
            api_key=os.environ.get("PICOWATCH_API_KEY"),
            corpus_version=os.environ.get("PICOWATCH_CORPUS_VERSION", DEFAULT_CORPUS_VERSION),
        )
