"""L6 Output Guard — deterministic output validation.

Schema check → Content policy → PII scan → Format guard → Verdict.
Same output + same rules + same config = same verdict. Always.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from picowatch.config import PicoWatchConfig
from picowatch.prompt_guard.normalize import Normalizer
from picowatch.prompt_guard.rules import RuleEngine
from picowatch.types import PromptScanResult, Rule, ValidationResult


class OutputGuard:
    """L6 Output Guard: deterministic output validation.

    Usage:
        guard = OutputGuard()
        result = guard.validate('{"name": "John"}', schema=my_schema)
        print(result.valid, result.score, result.violations)
    """

    def __init__(
        self,
        rules_dir: Path | None = None,
        config: PicoWatchConfig | None = None,
    ) -> None:
        self._config = config or PicoWatchConfig()
        self._rules_dir = rules_dir or self._config.rules_dir / "output_policy"
        self._normalizer = Normalizer()
        self._engine = RuleEngine(rules_dir=self._rules_dir)

    @property
    def rules(self) -> list[Rule]:
        """Loaded output policy rules, sorted by ID."""
        return self._engine.rules

    @property
    def corpus_hash(self) -> str:
        """SHA-256 hash of all rule files."""
        return self._engine.corpus_hash

    def validate(
        self,
        output: str,
        schema: dict | None = None,
        prompt_result: PromptScanResult | None = None,
    ) -> ValidationResult:
        """Validate an LLM output.

        Args:
            output: The LLM output text to validate.
            schema: Optional JSON Schema for structural validation.
            prompt_result: Optional L5 scan result — flagged prompts
                get stricter validation.

        Returns:
            ValidationResult with valid, score, violations, redacted, etc.
        """
        start = time.perf_counter()
        violations: list[str] = []
        total_score = 0.0
        redacted = output

        # Step 1: Schema validation (if schema provided)
        if schema is not None:
            schema_violations = self._check_schema(output, schema)
            violations.extend(schema_violations)

        # Step 2: Content policy (output rules)
        normalized = self._normalizer.normalize(output)
        matches = self._engine.evaluate(normalized)
        if matches:
            for rule, _match in matches:
                violations.append(rule.id)
                total_score = max(total_score, rule.weight)

        # Step 3: PII detection and redaction
        redacted, pii_violations = self._detect_pii(output)
        violations.extend(pii_violations)

        # Step 4: Feedback loop — if prompt was flagged, lower the threshold
        if prompt_result and prompt_result.score >= 0.4:
            # Flagged prompt: any output violation is more serious
            total_score = min(1.0, total_score * 1.3)

        # Final score
        score = round(total_score, 6)
        valid = score < self._config.threshold_block and len(violations) == 0

        duration_ms = round((time.perf_counter() - start) * 1000, 3)

        return ValidationResult(
            valid=valid,
            score=score,
            violations=violations,
            corpus_hash=self.corpus_hash,
            corpus_version=self._config.corpus_version,
            duration_ms=duration_ms,
            redacted=redacted if redacted != output else None,
        )

    def _check_schema(self, output: str, schema: dict) -> list[str]:
        """Basic schema validation without jsonschema dependency.

        For full Draft 2020-12 validation, install jsonschema.
        """
        violations: list[str] = []

        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            violations.append("out_fmt_invalid_json")
            return violations

        # Basic type checking from schema
        schema_type = schema.get("type")
        if schema_type and (
            (schema_type == "object" and not isinstance(data, dict))
            or (schema_type == "array" and not isinstance(data, list))
            or (schema_type == "string" and not isinstance(data, str))
        ):
            violations.append("out_fmt_type_mismatch")

        # Required fields
        required = schema.get("required", [])
        if isinstance(data, dict) and required:
            for field in required:
                if field not in data:
                    violations.append(f"out_fmt_missing_required_{field}")

        return violations

    def _detect_pii(self, text: str) -> tuple[str, list[str]]:
        """Detect and redact PII in text. Returns (redacted_text, violation_ids)."""
        violations: list[str] = []
        redacted = text

        # SSN pattern
        ssn_pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
        if ssn_pattern.search(redacted):
            violations.append("out_pii_ssn")
            redacted = ssn_pattern.sub("[SSN-REDACTED]", redacted)

        # Email pattern
        email_pattern = re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        )
        if email_pattern.search(redacted):
            violations.append("out_pii_email")
            redacted = email_pattern.sub("[EMAIL-REDACTED]", redacted)

        # Phone pattern (US)
        phone_pattern = re.compile(
            r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        )
        if phone_pattern.search(redacted):
            violations.append("out_pii_phone")
            redacted = phone_pattern.sub("[PHONE-REDACTED]", redacted)

        # API key patterns
        api_key_pattern = re.compile(
            r"(?:AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[0-9A-Z]{16}"
            r"|(?:sk|pk|rk)_[a-zA-Z0-9]{20,}"
            r"|AIza[0-9A-Za-z_-]{35}"
            r"|ghp_[a-zA-Z0-9]{36}"
        )
        if api_key_pattern.search(redacted):
            violations.append("out_pii_api_key")
            redacted = api_key_pattern.sub("[API-KEY-REDACTED]", redacted)

        return redacted, violations
