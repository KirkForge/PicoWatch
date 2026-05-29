"""Health check endpoint."""

from __future__ import annotations

from picowatch import __version__
from picowatch.types import HealthStatus


def health_check(
    rules_loaded: int,
    corpus_hash: str,
    corpus_version: str,
    uptime_seconds: float = 0.0,
) -> HealthStatus:
    """Return health status for PicoWatch.

    Args:
        rules_loaded: Number of defense rules loaded.
        corpus_hash: SHA-256 hash of rule corpus.
        corpus_version: Version string of rule corpus.
        uptime_seconds: Process uptime in seconds.

    Returns:
        HealthStatus with healthy=True if rules are loaded.
    """
    return HealthStatus(
        healthy=rules_loaded > 0,
        version=__version__,
        rules_loaded=rules_loaded,
        corpus_hash=corpus_hash,
        corpus_version=corpus_version,
        uptime_seconds=uptime_seconds,
    )
