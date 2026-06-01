#!/usr/bin/env python3
"""Generate CycloneDX SBOM for PicoWatch.

ADR-008: SLSA Level 3 compliance requires SBOM on every release.
This script generates a CycloneDX JSON SBOM from installed dependencies.

Usage:
    python scripts/generate_sbom.py [--output sbom.json]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_installed_packages() -> list[dict]:
    """Get list of installed packages with versions via pip."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return []


def generate_sbom(output_path: str = "sbom.json") -> None:
    """Generate a CycloneDX-format SBOM."""
    packages = get_installed_packages()

    components = []
    for pkg in packages:
        components.append({
            "type": "library",
            "name": pkg["name"],
            "version": pkg["version"],
            "purl": f"pkg:pypi/{pkg['name']}@{pkg['version']}",
        })

    # Read version from package
    try:
        from picowatch import __version__

        picowatch_version = __version__
    except ImportError:
        picowatch_version = "unknown"

    sbom = {
        "$schema": "https://cyclonedx.org/schema/bom-1.5.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{__import__('uuid').uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": {
                "type": "application",
                "name": "picowatch",
                "version": picowatch_version,
                "purl": f"pkg:pypi/picowatch@{picowatch_version}",
            },
            "tools": [
                {
                    "name": "picowatch-sbom-generator",
                    "version": "1.0.0",
                }
            ],
        },
        "components": components,
    }

    output = Path(output_path)
    output.write_text(json.dumps(sbom, indent=2) + "\n")
    print(f"SBOM written to {output} ({len(components)} components)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate CycloneDX SBOM")
    parser.add_argument("--output", "-o", default="sbom.json", help="Output file path")
    args = parser.parse_args()
    generate_sbom(args.output)


if __name__ == "__main__":
    main()
