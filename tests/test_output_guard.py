"""PicoWatch OutputGuard tests."""

from pathlib import Path

from picowatch.config import PicoWatchConfig
from picowatch.output_guard import OutputGuard

RULES_DIR = Path(__file__).parent.parent / "rules"
OUTPUT_RULES_DIR = RULES_DIR / "output_policy"


class TestOutputGuard:
    """Test L6 OutputGuard."""

    def test_clean_output_passes(self) -> None:
        """Clean output with no violations passes."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        result = guard.validate("The weather is sunny today.")
        assert result.valid is True
        assert result.score < 0.4

    def test_pii_ssn_detected(self) -> None:
        """SSN in output is detected and redacted."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        result = guard.validate("Your SSN is 123-45-6789")
        assert "out_pii_ssn" in result.violations
        assert result.redacted is not None
        assert "[SSN-REDACTED]" in result.redacted

    def test_pii_email_detected(self) -> None:
        """Email in output is detected and redacted."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        result = guard.validate("Contact admin@example.com for help")
        assert "out_pii_email" in result.violations
        assert "[EMAIL-REDACTED]" in (result.redacted or "")

    def test_api_key_detected(self) -> None:
        """AWS API key pattern is detected."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        result = guard.validate("The key is AKIAIOSFODNN7EXAMPLE")
        assert "out_pii_api_key" in result.violations

    def test_schema_validation_type_mismatch(self) -> None:
        """Schema type mismatch is detected."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        result = guard.validate('"hello"', schema={"type": "object"})
        assert "out_fmt_type_mismatch" in result.violations

    def test_schema_validation_missing_required(self) -> None:
        """Missing required fields are detected."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        result = guard.validate('{"name": "test"}', schema={"type": "object", "required": ["name", "email"]})
        assert "out_fmt_missing_required_email" in result.violations

    def test_internal_url_detected(self) -> None:
        """Internal/private URLs are detected."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        result = guard.validate("The server is at 192.168.1.100")
        assert "out_exfil_internal_url" in result.violations

    def test_deterministic(self) -> None:
        """Same input + same rules = same result."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        text = "Your SSN is 123-45-6789"
        result1 = guard.validate(text)
        result2 = guard.validate(text)
        assert result1.score == result2.score
        assert result1.violations == result2.violations
