"""PicoWatch configuration.

Reads from: CLI flags > environment variables > config file > defaults.
Config file search order: ./picowatch.toml, ~/.config/picowatch/picowatch.toml, /etc/picowatch/picowatch.toml
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_RULES_DIR = Path(__file__).parent.parent.parent / "rules"
DEFAULT_THRESHOLD_BLOCK = 0.7
DEFAULT_THRESHOLD_WARN = 0.4
DEFAULT_MAX_PROMPT_SIZE = 1_000_000  # 1MB
DEFAULT_AUDIT_RETENTION_DAYS = 30
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8766
DEFAULT_ADMIN_PORT = 9091
DEFAULT_CORPUS_VERSION = "2026.05.1"
DEFAULT_RATE_LIMIT = 100  # requests per minute per IP
DEFAULT_RATE_LIMIT_WINDOW = 60  # seconds

CONFIG_SEARCH_PATHS = [
    Path("picowatch.toml"),
    Path.home() / ".config" / "picowatch" / "picowatch.toml",
    Path("/etc/picowatch/picowatch.toml"),
]


def _find_config_file() -> Path | None:
    """Find the first existing config file in the search path."""
    for path in CONFIG_SEARCH_PATHS:
        if path.exists():
            return path
    return None


def _load_toml_config(path: Path) -> dict[str, Any]:
    """Load configuration from a TOML file.

    Uses tomllib (Python 3.11+) with a fallback to tomli.
    """
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return {}

    try:
        with open(path, "rb") as f:
            data: dict[str, Any] = tomllib.load(f)
            return data
    except Exception:
        return {}


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
    rate_limit: int = DEFAULT_RATE_LIMIT
    rate_limit_window: int = DEFAULT_RATE_LIMIT_WINDOW

    # Corpus
    corpus_version: str = DEFAULT_CORPUS_VERSION

    # Misc
    verify_determinism: bool = False
    verbose: bool = False

    @classmethod
    def from_env(cls, config_path: Path | None = None) -> PicoWatchConfig:
        """Load configuration from config file, then environment overrides.

        Args:
            config_path: Explicit config file path. If None, auto-discovers.
        """
        # Layer 1: Config file
        file_config: dict[str, object] = {}
        config_file_path = config_path
        if config_path and config_path.exists():
            file_config = _load_toml_config(config_path)
        else:
            discovered = _find_config_file()
            if discovered:
                file_config = _load_toml_config(discovered)
                config_file_path = discovered

        # Check config file permissions (ADR-008)
        if config_file_path:
            check_config_permissions()

        # Extract the [picowatch] section if present, else use root
        picowatch_conf: dict[str, Any] = file_config.get("picowatch", file_config)  # type: ignore[assignment]

        # Helper: env > file > default
        def _env_or_file(key: str, env_var: str, default: Any, cast: type = str) -> Any:
            val = os.environ.get(env_var)
            if val is not None:
                return cast(val)
            file_val = picowatch_conf.get(key)
            if file_val is not None:
                return cast(file_val) if not isinstance(file_val, cast) else file_val
            return default

        # Layer 2: Environment variables override file values
        rules_dir_str = os.environ.get("PICOWATCH_RULES_DIR") or picowatch_conf.get("rules_dir")
        schema_dir_str = os.environ.get("PICOWATCH_SCHEMA_DIR") or picowatch_conf.get("schema_dir")

        return cls(
            rules_dir=Path(rules_dir_str) if rules_dir_str else DEFAULT_RULES_DIR,
            threshold_block=_env_or_file(
                "threshold_block",
                "PICOWATCH_THRESHOLD_BLOCK",
                DEFAULT_THRESHOLD_BLOCK,
                float,
            ),
            threshold_warn=_env_or_file("threshold_warn", "PICOWATCH_THRESHOLD_WARN", DEFAULT_THRESHOLD_WARN, float),
            max_prompt_size=_env_or_file("max_prompt_size", "PICOWATCH_MAX_PROMPT_SIZE", DEFAULT_MAX_PROMPT_SIZE, int),
            schema_dir=Path(schema_dir_str) if schema_dir_str else None,
            otel_endpoint=os.environ.get("PICOWATCH_OTEL_ENDPOINT") or picowatch_conf.get("otel_endpoint"),
            audit_retention_days=_env_or_file(
                "audit_retention_days",
                "PICOWATCH_AUDIT_RETENTION_DAYS",
                DEFAULT_AUDIT_RETENTION_DAYS,
                int,
            ),
            host=os.environ.get("PICOWATCH_HOST") or picowatch_conf.get("host", DEFAULT_HOST),
            port=_env_or_file("port", "PICOWATCH_PORT", DEFAULT_PORT, int),
            admin_port=_env_or_file("admin_port", "PICOWATCH_ADMIN_PORT", DEFAULT_ADMIN_PORT, int),
            api_key=os.environ.get("PICOWATCH_API_KEY") or picowatch_conf.get("api_key"),
            rate_limit=_env_or_file("rate_limit", "PICOWATCH_RATE_LIMIT", DEFAULT_RATE_LIMIT, int),
            rate_limit_window=_env_or_file(
                "rate_limit_window",
                "PICOWATCH_RATE_LIMIT_WINDOW",
                DEFAULT_RATE_LIMIT_WINDOW,
                int,
            ),
            corpus_version=os.environ.get("PICOWATCH_CORPUS_VERSION")
            or picowatch_conf.get("corpus_version", DEFAULT_CORPUS_VERSION),
        )


def check_config_permissions() -> list[str]:
    """Check config file permissions and warn about insecure settings (ADR-008).

    Returns a list of warning messages for overly-permissive config files.
    """
    import logging
    import stat

    logger = logging.getLogger("picowatch.config")
    warnings: list[str] = []

    for path in CONFIG_SEARCH_PATHS:
        if path.exists():
            mode = path.stat().st_mode
            if mode & stat.S_IRGRP:
                msg = (
                    f"Config file {path} is group-readable (mode {oct(stat.S_IMODE(mode))}). Consider: chmod 640 {path}"
                )
                warnings.append(msg)
                logger.warning(msg)
            if mode & stat.S_IROTH:
                msg = (
                    f"Config file {path} is world-readable (mode {oct(stat.S_IMODE(mode))}). Consider: chmod 600 {path}"
                )
                warnings.append(msg)
                logger.warning(msg)
            # Check if api_key is in a world-readable file
            try:
                content = path.read_text(encoding="utf-8")
                if "api_key" in content.lower() and (mode & stat.S_IROTH):
                    msg = f"SECURITY: api_key found in world-readable config {path}. Consider: chmod 600 {path}"
                    warnings.append(msg)
                    logger.error(msg)
            except Exception:
                pass

    return warnings
