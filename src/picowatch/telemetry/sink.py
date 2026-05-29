"""L7 Telemetry Sink — OpenTelemetry traces, Prometheus metrics, audit logging.

Core uses structured JSON logging + SQLite audit (zero external deps).
OpenTelemetry is optional (pip install picowatch[otel]).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from picowatch import __version__
from picowatch.types import HealthStatus, PromptScanResult, ValidationResult

logger = logging.getLogger("picowatch")


@dataclass
class TelemetryConfig:
    """Telemetry configuration."""

    audit_db_path: Path = field(default_factory=lambda: Path("picowatch_audit.db"))
    audit_retention_days: int = 30
    otel_endpoint: str | None = None
    admin_port: int = 9091
    enable_otel: bool = False


class TelemetrySink:
    """L7 Telemetry: structured logging + SQLite audit + optional OTel.

    Usage:
        sink = TelemetrySink()
        sink.record_prompt_scan(result)
        sink.record_validation(validation_result)
    """

    def __init__(self, config: TelemetryConfig | None = None) -> None:
        self._config = config or TelemetryConfig()
        self._start_time = time.monotonic()
        self._metrics: dict[str, int | float] = {
            "picowatch_requests_total": 0,
            "picowatch_prompt_blocked_total": 0,
            "picowatch_prompt_score_sum": 0.0,
            "picowatch_output_violations_total": 0,
            "picowatch_scan_duration_ms_sum": 0.0,
        }
        self._init_audit_db()

    def _init_audit_db(self) -> None:
        """Initialize SQLite audit database in WAL mode."""
        conn = sqlite3.connect(str(self._config.audit_db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                request_id TEXT,
                score REAL,
                verdict TEXT,
                rules TEXT,
                details TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)
        """)
        conn.commit()
        conn.close()

    def record_prompt_scan(self, result: PromptScanResult, request_id: str | None = None) -> None:
        """Record a prompt scan result."""
        self._metrics["picowatch_requests_total"] += 1
        self._metrics["picowatch_prompt_score_sum"] = float(self._metrics["picowatch_prompt_score_sum"]) + result.score
        self._metrics["picowatch_scan_duration_ms_sum"] = (
            float(self._metrics["picowatch_scan_duration_ms_sum"]) + result.duration_ms
        )

        if result.blocked:
            self._metrics["picowatch_prompt_blocked_total"] = int(self._metrics["picowatch_prompt_blocked_total"]) + 1

        # Structured JSON log
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "warn" if result.blocked else "info",
            "event": "prompt.blocked" if result.blocked else "prompt.scanned",
            "request_id": request_id,
            "score": result.score,
            "verdict": result.verdict.value,
            "rules": result.rules_matched,
            "corpus_hash": result.corpus_hash,
            "latency_ms": result.duration_ms,
        }
        logger.info(json.dumps(log_entry))

        # SQLite audit
        self._audit_write(
            event_type="prompt_scan",
            request_id=request_id,
            score=result.score,
            verdict=result.verdict.value,
            rules=json.dumps(result.rules_matched),
            details=json.dumps(result.details) if result.details else None,
        )

    def record_validation(self, result: ValidationResult, request_id: str | None = None) -> None:
        """Record an output validation result."""
        if result.violations:
            self._metrics["picowatch_output_violations_total"] = (
                int(self._metrics["picowatch_output_violations_total"]) + 1
            )
        self._metrics["picowatch_scan_duration_ms_sum"] = (
            float(self._metrics["picowatch_scan_duration_ms_sum"]) + result.duration_ms
        )

        # Structured JSON log
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "warn" if not result.valid else "info",
            "event": "output.violated" if result.violations else "output.validated",
            "request_id": request_id,
            "score": result.score,
            "verdict": result.verdict.value,
            "violations": result.violations,
            "corpus_hash": result.corpus_hash,
            "latency_ms": result.duration_ms,
        }
        logger.info(json.dumps(log_entry))

        # SQLite audit
        self._audit_write(
            event_type="output_validation",
            request_id=request_id,
            score=result.score,
            verdict=result.verdict.value,
            rules=json.dumps(result.violations),
            details=json.dumps(result.details) if result.details else None,
        )

    def _audit_write(
        self,
        event_type: str,
        request_id: str | None,
        score: float,
        verdict: str,
        rules: str,
        details: str | None,
    ) -> None:
        """Write to SQLite audit log."""
        try:
            conn = sqlite3.connect(str(self._config.audit_db_path))
            conn.execute(
                """
                INSERT INTO audit_log
                    (timestamp, event_type, request_id, score, verdict, rules, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    event_type,
                    request_id,
                    score,
                    verdict,
                    rules,
                    details,
                ),
            )
            conn.commit()
            conn.close()
        except sqlite3.Error:
            # Audit write failure should not break scanning
            logger.warning("Failed to write audit log entry")

    def render_prometheus(self) -> str:
        """Render Prometheus metrics in text format (zero-dep)."""
        lines: list[str] = []

        # Counters
        lines.append("# HELP picowatch_requests_total Total requests processed")
        lines.append("# TYPE picowatch_requests_total counter")
        lines.append(f"picowatch_requests_total {self._metrics['picowatch_requests_total']}")

        lines.append("# HELP picowatch_prompt_blocked_total Total prompts blocked")
        lines.append("# TYPE picowatch_prompt_blocked_total counter")
        lines.append(f"picowatch_prompt_blocked_total {self._metrics['picowatch_prompt_blocked_total']}")

        lines.append("# HELP picowatch_prompt_score_sum Cumulative prompt scores")
        lines.append("# TYPE picowatch_prompt_score_sum counter")
        lines.append(f"picowatch_prompt_score_sum {self._metrics['picowatch_prompt_score_sum']}")

        lines.append("# HELP picowatch_output_violations_total Total output violations")
        lines.append("# TYPE picowatch_output_violations_total counter")
        lines.append(f"picowatch_output_violations_total {self._metrics['picowatch_output_violations_total']}")

        lines.append("# HELP picowatch_scan_duration_ms_sum Cumulative scan duration in ms")
        lines.append("# TYPE picowatch_scan_duration_ms_sum counter")
        lines.append(f"picowatch_scan_duration_ms_sum {self._metrics['picowatch_scan_duration_ms_sum']}")

        return "\n".join(lines) + "\n"

    def health(self, rules_loaded: int, corpus_hash: str, corpus_version: str) -> HealthStatus:
        """Return health status."""
        return HealthStatus(
            healthy=True,
            version=__version__,
            rules_loaded=rules_loaded,
            corpus_hash=corpus_hash,
            corpus_version=corpus_version,
            uptime_seconds=round(time.monotonic() - self._start_time, 2),
        )

    def cleanup_audit(self) -> int:
        """Remove audit entries older than retention period. Returns count deleted."""
        if self._config.audit_retention_days <= 0:
            return 0

        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=self._config.audit_retention_days)
        try:
            conn = sqlite3.connect(str(self._config.audit_db_path))
            cursor = conn.execute("DELETE FROM audit_log WHERE timestamp < ?", (cutoff.isoformat(),))
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted
        except sqlite3.Error:
            return 0
