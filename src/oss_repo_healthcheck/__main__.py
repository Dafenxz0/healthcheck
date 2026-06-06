from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit import audit_repository, list_checks
from .metrics import collect_commit_activity, render_markdown_metrics, render_text_metrics


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
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
        help="Output format. Defaults to text.",
    )
    parser.add_argument(
        "--only-failures",
        action="store_true",
        help="Show only failing checks while keeping the overall score.",
    )
    parser.add_argument(
        "--list-checks",
        action="store_true",
        help="List available check IDs, categories, and default weights, then exit.",
    )
    parser.add_argument(
        "--init-config",
        nargs="?",
        const=".oss-repo-healthcheck.json",
        metavar="PATH",
        help="Write a starter JSON config file, then exit. Defaults to .oss-repo-healthcheck.json.",
    )
    parser.add_argument(
        "--config",
        help="Path to a JSON config file. Defaults to .oss-repo-healthcheck.json when present.",
    )
    parser.add_argument(
        "--output",
        help="Write the rendered report to a file instead of printing it.",
    )
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Show Git commit activity metrics instead of the standard health report.",
    )
    parser.add_argument(
        "--metrics-days",
        type=int,
        default=90,
        metavar="DAYS",
        help="Number of days to include in Git activity metrics. Defaults to 90.",
    )
    parser.add_argument(
        "--include-health",
        action="store_true",
        help="When using --metrics, include the standard health report before the activity metrics.",
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

    output_format = "json" if args.json else args.format

    if args.list_checks:
        print(_format_check_catalog(output_format))
        return 0

    if args.init_config:
        config_path = Path(args.init_config)
        if config_path.exists():
            raise SystemExit(f"Config file already exists: {config_path}")
        config_path.write_text(_format_starter_config(), encoding="utf-8")
        print(f"Wrote starter config to {config_path}")
        return 0

    if args.metrics:
        rendered = _render_metrics_report(
            Path(args.path),
            output_format=output_format,
            days=args.metrics_days,
            include_health=args.include_health,
            config_path=args.config,
            only_failures=args.only_failures,
        )
        result = audit_repository(Path(args.path), config_path=args.config) if args.include_health else None
    else:
        result = audit_repository(Path(args.path), config_path=args.config)
        rendered = _render_result(result, output_format=output_format, only_failures=args.only_failures)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote report to {output_path}")
    else:
        print(rendered)

    if result is not None and args.strict and result.has_failures:
        return 1
    if result is not None and args.fail_under is not None and result.score < args.fail_under:
        return 1
    return 0


def _render_result(result, *, output_format: str, only_failures: bool = False) -> str:
    if output_format == "json":
        return json.dumps(result.to_dict(only_failures=only_failures), indent=2)
    if output_format == "markdown":
        return _format_markdown_report(result, only_failures=only_failures)
    return _format_report(result, only_failures=only_failures)


def _render_metrics_report(
    path: Path,
    *,
    output_format: str,
    days: int,
    include_health: bool = False,
    config_path: str | None = None,
    only_failures: bool = False,
) -> str:
    activity = collect_commit_activity(path, days=days)
    if output_format == "json":
        payload: dict[str, object] = {"activity": activity.to_dict()}
        if include_health:
            payload["health"] = audit_repository(path, config_path=config_path).to_dict(only_failures=only_failures)
        return json.dumps(payload, indent=2)

    metrics = render_markdown_metrics(activity) if output_format == "markdown" else render_text_metrics(activity)
    if not include_health:
        return metrics

    health = audit_repository(path, config_path=config_path)
    health_report = _render_result(health, output_format=output_format, only_failures=only_failures)
    separator = "\n\n---\n\n" if output_format == "markdown" else "\n\n" + "=" * 72 + "\n\n"
    return health_report + separator + metrics


def _format_report(result, *, only_failures: bool = False) -> str:
    lines = [f"oss-repo-healthcheck: {result.path}", ""]
    checks = result.checks
    if only_failures:
        checks = tuple(check for check in checks if not check.passed)
    if not checks:
        lines.append("No failing checks.")
    for check in checks:
        label = check.status.upper()
        lines.append(f"{label:<5} [{check.category}] {check.name}")
        lines.append(f"      {check.detail}")
    lines.append("")
    if result.config_path:
        lines.append(f"Config: {result.config_path}")
    lines.append(f"Checks: {result.passed_count} passed, {result.failed_count} failed")
    lines.append(f"Score: {result.score}/100")
    return "\n".join(lines)


def _format_markdown_report(result, *, only_failures: bool = False) -> str:
    checks = result.checks
    if only_failures:
        checks = tuple(check for check in checks if not check.passed)

    lines = [
        f"## oss-repo-healthcheck: `{result.path}`",
        "",
        f"**Score:** {result.score}/100",
        f"**Checks:** {result.passed_count} passed, {result.failed_count} failed",
    ]
    if result.config_path:
        lines.append(f"**Config:** `{result.config_path}`")
    lines.extend(
        [
            "",
            "| Status | Category | Check | Detail |",
            "| --- | --- | --- | --- |",
        ]
    )
    if not checks:
        lines.append("| PASS | all | No failing checks | All enabled checks passed. |")
    for check in checks:
        lines.append(
            f"| {check.status.upper()} | {_markdown_cell(check.category)} | "
            f"{_markdown_cell(check.name)} | {_markdown_cell(check.detail)} |"
        )
    return "\n".join(lines)


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|")


def _format_check_catalog(output_format: str) -> str:
    checks = list_checks()
    if output_format == "json":
        return json.dumps(
            [
                {
                    "id": check.id,
                    "name": check.name,
                    "category": check.category,
                    "default_weight": check.default_weight,
                }
                for check in checks
            ],
            indent=2,
        )
    if output_format == "markdown":
        lines = [
            "| ID | Category | Weight | Name |",
            "| --- | --- | --- | --- |",
        ]
        for check in checks:
            lines.append(f"| `{check.id}` | {check.category} | {check.default_weight} | {check.name} |")
        return "\n".join(lines)

    lines = ["Available checks:"]
    for check in checks:
        lines.append(f"- {check.id:<22} {check.category:<14} weight={check.default_weight:<2} {check.name}")
    return "\n".join(lines)


def _format_starter_config() -> str:
    config = {
        "disabled_checks": [],
        "weights": {check.id: check.default_weight for check in list_checks()},
    }
    return json.dumps(config, indent=2) + "\n"


if __name__ == "__main__":
    sys.exit(main())
