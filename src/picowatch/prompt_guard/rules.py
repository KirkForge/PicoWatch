"""Rule engine: loads YAML rules, evaluates them against normalized input.

Rules are sorted by ID for deterministic evaluation order.
Corpus hash is SHA-256 of all rule files concatenated.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml

from picowatch.types import Rule


class RuleEngine:
    """Deterministic rule engine for prompt injection detection.

    Rules loaded from YAML files, sorted by ID, evaluated in order.
    Same rule set + same input = same matches. Always.
    """

    def __init__(self, rules_dir: Path | None = None) -> None:
        self._rules_dir = rules_dir
        self._rules: list[Rule] = []
        self._compiled: dict[str, re.Pattern[str]] = {}
        self._corpus_hash = ""
        if rules_dir and rules_dir.exists():
            self._load_rules(rules_dir)

    @property
    def rules(self) -> list[Rule]:
        """Loaded rules, sorted by ID for determinism."""
        return list(self._rules)

    @property
    def corpus_hash(self) -> str:
        """SHA-256 hash of all rule files concatenated."""
        return self._corpus_hash

    def _load_rules(self, rules_dir: Path) -> None:
        """Load all YAML rule files from directory."""
        yaml_files = sorted(rules_dir.rglob("*.yaml")) + sorted(rules_dir.rglob("*.yml"))
        raw_rules: list[Rule] = []
        hash_parts: list[bytes] = []

        for yaml_file in yaml_files:
            try:
                content = yaml_file.read_text(encoding="utf-8")
                hash_parts.append(content.encode("utf-8"))
                data = yaml.safe_load(content)
                if data is None:
                    continue
                # Support both single rule and list of rules per file
                rule_dicts = data if isinstance(data, list) else [data]
                for rd in rule_dicts:
                    if not isinstance(rd, dict):
                        continue
                    rule = Rule(
                        id=rd["id"],
                        category=rd["category"],
                        weight=float(rd.get("weight", 0.5)),
                        pattern=rd["pattern"],
                        description=rd.get("description", ""),
                        normalization=rd.get("normalization", ["unicode", "whitespace"]),
                    )
                    raw_rules.append(rule)
            except Exception:
                # Skip malformed files silently — they'll be caught by test suite
                continue

        # Sort by ID for deterministic evaluation
        raw_rules.sort(key=lambda r: r.id)
        self._rules = raw_rules

        # Compile regex patterns
        for rule in self._rules:
            try:
                self._compiled[rule.id] = re.compile(rule.pattern, re.IGNORECASE | re.DOTALL)
            except re.error:
                # Skip invalid regex — test suite will catch these
                continue

        # Compute corpus hash
        if hash_parts:
            hasher = hashlib.sha256()
            for part in hash_parts:
                hasher.update(part)
            self._corpus_hash = hasher.hexdigest()[:16]
        else:
            self._corpus_hash = "no-rules-loaded"

    def evaluate(self, text: str) -> list[tuple[Rule, re.Match[str]]]:
        """Evaluate all rules against normalized text.

        Returns list of (rule, match) tuples for all matching rules.
        """
        matches: list[tuple[Rule, re.Match[str]]] = []

        for rule in self._rules:
            compiled = self._compiled.get(rule.id)
            if compiled is None:
                continue
            match = compiled.search(text)
            if match:
                matches.append((rule, match))

        return matches
