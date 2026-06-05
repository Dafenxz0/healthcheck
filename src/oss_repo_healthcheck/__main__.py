from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit import audit_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oss-repo-healthcheck",
        description="Audit a repository for common open-source maintainer hygiene signals.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repository path to audit. Defaults to the current directory.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON instead of a human-readable report.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 when any check fails.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = audit_repository(Path(args.path))

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(_format_report(result))

    return 1 if args.strict and result.has_failures else 0


def _format_report(result) -> str:
    lines = [f"oss-repo-healthcheck: {result.path}", ""]
    for check in result.checks:
        label = check.status.upper()
        lines.append(f"{label:<5} {check.name}")
        lines.append(f"      {check.detail}")
    lines.append("")
    lines.append(f"Score: {result.score}/100")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
