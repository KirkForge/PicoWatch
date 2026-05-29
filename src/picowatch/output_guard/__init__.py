"""L6 Output Guard — deterministic output validation.

Schema check → Content policy → PII scan → Format guard → Verdict.
Same output + same rules + same config = same verdict. Always.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

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
        schema: dict[str, Any] | None = None,
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

    def _check_schema(self, output: str, schema: dict[str, Any]) -> list[str]:
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
        """Detect and redact PII and exfiltration patterns in text.

        Covers all YAML rule patterns that require redaction:
        - PII: SSN, credit card, email, phone, API key, IP, passport, JWT, crypto wallet, AWS ARN
        - Exfiltration: env vars, internal URLs, DB URLs, SSH keys, OAuth tokens, Docker/K8s secrets

        Returns (redacted_text, violation_ids).
        """
        violations: list[str] = []
        redacted = text

        # Order matters: more specific patterns first to avoid partial matches

        # SSH/private key (highest severity exfiltration)
        ssh_key_pattern = re.compile(
            r"-----BEGIN\s+(?:RSA\s+)?(?:PRIVATE\s+)?KEY-----"
            r"[\s\S]*?"
            r"-----END\s+(?:RSA\s+)?(?:PRIVATE\s+)?KEY-----"
        )
        if ssh_key_pattern.search(redacted):
            violations.append("out_exfil_ssh_key")
            redacted = ssh_key_pattern.sub("[PRIVATE-KEY-REDACTED]", redacted)

        # JWT token
        jwt_pattern = re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
        if jwt_pattern.search(redacted):
            violations.append("out_pii_jwt")
            redacted = jwt_pattern.sub("[JWT-REDACTED]", redacted)

        # Database connection string
        db_url_pattern = re.compile(r"(?:postgres|mysql|mongodb|redis|mssql)://[^\s]+")
        if db_url_pattern.search(redacted):
            violations.append("out_exfil_database_url")
            redacted = db_url_pattern.sub("[DB-URL-REDACTED]", redacted)

        # OAuth/access tokens (Google, GitHub, GitLab, Slack)
        oauth_pattern = re.compile(
            r"(?:ya29[.\-_]|ghp_|gho_|github_pat_|glpat-|gitlab-[a-z]+-token|xox[bpas]-)[A-Za-z0-9_.\-]{20,}"
        )
        if oauth_pattern.search(redacted):
            violations.append("out_exfil_oauth_token")
            redacted = oauth_pattern.sub("[OAUTH-TOKEN-REDACTED]", redacted)

        # AWS ARN
        arn_pattern = re.compile(r"arn:aws[a-z-]*:[a-z0-9-]+:[a-z0-9-]*:\d*:[^\s]+")
        if arn_pattern.search(redacted):
            violations.append("out_pii_aws_arn")
            redacted = arn_pattern.sub("[AWS-ARN-REDACTED]", redacted)

        # API key patterns (AWS, OpenAI, GCP, GitHub)
        api_key_pattern = re.compile(
            r"(?:AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[0-9A-Z]{16}"
            r"|(?:sk|pk|rk)_[a-zA-Z0-9]{20,}"
            r"|AIza[0-9A-Za-z_-]{35}"
            r"|ghp_[a-zA-Z0-9]{36}"
        )
        if api_key_pattern.search(redacted):
            violations.append("out_pii_api_key")
            redacted = api_key_pattern.sub("[API-KEY-REDACTED]", redacted)

        # Credit card number
        cc_pattern = re.compile(r"\b(?:\d{4}[\s-]?){3}\d{4}\b")
        if cc_pattern.search(redacted):
            violations.append("out_pii_credit_card")
            redacted = cc_pattern.sub("[CC-REDACTED]", redacted)

        # SSN pattern
        ssn_pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
        if ssn_pattern.search(redacted):
            violations.append("out_pii_ssn")
            redacted = ssn_pattern.sub("[SSN-REDACTED]", redacted)

        # Passport/national ID
        passport_pattern = re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")
        if passport_pattern.search(redacted):
            violations.append("out_pii_passport")
            redacted = passport_pattern.sub("[PASSPORT-REDACTED]", redacted)

        # Cryptocurrency wallet address (ETH/BTC)
        crypto_pattern = re.compile(r"(?:0x)?[0-9a-fA-F]{40}|[13][0-9a-zA-Z]{25,34}|bc1[qQ][0-9a-zA-Z]{39,59}")
        if crypto_pattern.search(redacted):
            violations.append("out_pii_crypto_wallet")
            redacted = crypto_pattern.sub("[CRYPTO-WALLET-REDACTED]", redacted)

        # Internal/private URL (must check before generic IP)
        internal_url_pattern = re.compile(
            r"(?:https?://)?(?:10\.\d{1,3}|172\.(?:1[6-9]|2[0-9]|3[01])|192\.168)\.\d{1,3}\.\d{1,3}"
            r"|localhost|127\.0\.0\.1|0\.0\.0\.0"
        )
        if internal_url_pattern.search(redacted):
            violations.append("out_exfil_internal_url")
            redacted = internal_url_pattern.sub("[INTERNAL-URL-REDACTED]", redacted)

        # IP address (public or private — after internal URL check)
        ip_pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
        if ip_pattern.search(redacted):
            violations.append("out_pii_ip_address")
            redacted = ip_pattern.sub("[IP-REDACTED]", redacted)

        # Docker/Kubernetes secret exfiltration (more specific — before env var)
        docker_secret_pattern = re.compile(r"(?:DOCKER_|KUBERNETES_|K8S_)[A-Z_]+\s*=\s*[^\s]+")
        if docker_secret_pattern.search(redacted):
            violations.append("out_exfil_docker_secret")
            redacted = docker_secret_pattern.sub("[K8S-SECRET-REDACTED]", redacted)

        # Environment variable exfiltration
        env_var_pattern = re.compile(
            r"(?:AWS_|GCP_|AZURE_|DATABASE_|SECRET_|API_|TOKEN_|PASSWORD_|PRIVATE_)[A-Z_]*\s*=\s*[^\s]+"
        )
        if env_var_pattern.search(redacted):
            violations.append("out_exfil_env_var")
            redacted = env_var_pattern.sub("[ENV-VAR-REDACTED]", redacted)

        # Email pattern
        email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
        if email_pattern.search(redacted):
            violations.append("out_pii_email")
            redacted = email_pattern.sub("[EMAIL-REDACTED]", redacted)

        # Phone pattern (US)
        phone_pattern = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
        if phone_pattern.search(redacted):
            violations.append("out_pii_phone")
            redacted = phone_pattern.sub("[PHONE-REDACTED]", redacted)

        return redacted, violations
