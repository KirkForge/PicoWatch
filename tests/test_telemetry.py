"""PicoWatch Telemetry tests."""

from picowatch.telemetry import TelemetryConfig, TelemetrySink
from picowatch.telemetry.metrics import PrometheusMetrics
from picowatch.types import PromptScanResult, ValidationResult


class TestTelemetrySink:
    """Test L7 TelemetrySink."""

    def test_record_prompt_scan(self, tmp_path) -> None:
        """Prompt scan results are recorded to audit log."""
        db_path = tmp_path / "test_audit.db"
        config = TelemetryConfig(audit_db_path=db_path)
        sink = TelemetrySink(config=config)

        result = PromptScanResult(
            blocked=True,
            score=0.94,
            rules_matched=["inj_override_ignore"],
            corpus_hash="abc123",
            corpus_version="1.0",
            duration_ms=2.1,
        )
        sink.record_prompt_scan(result, request_id="req-001")

        # Verify audit log was written
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        rows = conn.execute("SELECT * FROM audit_log").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][2] == "prompt_scan"  # event_type

    def test_record_validation(self, tmp_path) -> None:
        """Validation results are recorded to audit log."""
        db_path = tmp_path / "test_audit.db"
        config = TelemetryConfig(audit_db_path=db_path)
        sink = TelemetrySink(config=config)

        result = ValidationResult(
            valid=False,
            score=0.95,
            violations=["out_pii_ssn"],
            corpus_hash="abc123",
            corpus_version="1.0",
            duration_ms=1.8,
        )
        sink.record_validation(result, request_id="req-002")

        import sqlite3

        conn = sqlite3.connect(str(db_path))
        rows = conn.execute("SELECT * FROM audit_log").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][2] == "output_validation"

    def test_prometheus_rendering(self, tmp_path) -> None:
        """Prometheus metrics render correctly."""
        db_path = tmp_path / "test_audit.db"
        config = TelemetryConfig(audit_db_path=db_path)
        sink = TelemetrySink(config=config)

        result = PromptScanResult(
            blocked=True,
            score=0.9,
            rules_matched=["inj_override_ignore"],
            corpus_hash="abc",
            corpus_version="1.0",
            duration_ms=3.0,
        )
        sink.record_prompt_scan(result)

        metrics = sink.render_prometheus()
        assert "picowatch_requests_total" in metrics
        assert "picowatch_prompt_blocked_total" in metrics

    def test_health_status(self, tmp_path) -> None:
        """Health check returns status."""
        db_path = tmp_path / "test_audit.db"
        config = TelemetryConfig(audit_db_path=db_path)
        sink = TelemetrySink(config=config)

        health = sink.health(rules_loaded=25, corpus_hash="abc123", corpus_version="1.0")
        assert health.healthy is True
        assert health.rules_loaded == 25
        assert health.corpus_hash == "abc123"


class TestPrometheusMetrics:
    """Test Prometheus metrics renderer."""

    def test_counter(self) -> None:
        """Counter increments work."""
        metrics = PrometheusMetrics()
        metrics.inc_counter("picowatch_requests_total", labels={"model": "gpt-4"})
        output = metrics.render()
        assert "picowatch_requests_total" in output

    def test_gauge(self) -> None:
        """Gauge set works."""
        metrics = PrometheusMetrics()
        metrics.set_gauge("picowatch_active_scans", 3.0, labels={"guard_type": "prompt"})
        output = metrics.render()
        assert "picowatch_active_scans" in output
