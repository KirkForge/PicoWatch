"""PicoWatch CLI — prompt guard, output validation, and telemetry daemon."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="picowatch",
        description="PicoWatch — LLM defender with telemetry",
    )
    sub = parser.add_subparsers(dest="command")

    # scan-prompt
    sp = sub.add_parser("scan-prompt", help="Scan a prompt for injection patterns")
    sp.add_argument("--text", "-t", help="Prompt text to scan")
    sp.add_argument("--file", "-f", help="File containing prompt text")

    # validate-output
    vo = sub.add_parser("validate-output", help="Validate LLM output against a schema")
    vo.add_argument("--schema", "-s", required=True, help="JSON schema file")
    vo.add_argument("--output", "-o", required=True, help="LLM output file")

    # serve
    se = sub.add_parser("serve", help="Start telemetry daemon")
    se.add_argument("--host", default="0.0.0.0", help="Bind host")
    se.add_argument("--port", "-p", type=int, default=8766, help="Bind port")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # TODO: implement command dispatch


if __name__ == "__main__":
    main()
