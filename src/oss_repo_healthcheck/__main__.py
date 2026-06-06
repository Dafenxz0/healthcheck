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
        "--only-failures",
        action="store_true",
        help="Show only failing checks while keeping the overall score.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 when any check fails.",
    )
    parser.add_argument(
        "--fail-under",
        type=int,
        metavar="SCORE",
        help="Exit with status 1 when the repository score is below SCORE.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.fail_under is not None and not 0 <= args.fail_under <= 100:
        raise SystemExit("--fail-under must be between 0 and 100")

    result = audit_repository(Path(args.path))

    if args.json:
        print(json.dumps(result.to_dict(only_failures=args.only_failures), indent=2))
    else:
        print(_format_report(result, only_failures=args.only_failures))

    if args.strict and result.has_failures:
        return 1
    if args.fail_under is not None and result.score < args.fail_under:
        return 1
    return 0


def _format_report(result, *, only_failures: bool = False) -> str:
    lines = [f"oss-repo-healthcheck: {result.path}", ""]
    checks = result.checks
    if only_failures:
        checks = tuple(check for check in checks if not check.passed)
    if not checks:
        lines.append("No failing checks.")
    for check in checks:
        label = check.status.upper()
        lines.append(f"{label:<5} {check.name}")
        lines.append(f"      {check.detail}")
    lines.append("")
    lines.append(f"Checks: {result.passed_count} passed, {result.failed_count} failed")
    lines.append(f"Score: {result.score}/100")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
