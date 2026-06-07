# Changelog

## 0.2.0

- Added a Windows PowerShell installer that creates a local virtual environment, installs from the GitHub release archive, and creates an `oss-repo-healthcheck.cmd` launcher.
- Added stable check IDs to make JSON output and configuration easier to consume.
- Added `.oss-repo-healthcheck.json` support for disabling checks and overriding weights.
- Added `--config` for using an explicit configuration file.
- Added `--format markdown` for pull request and issue comments.
- Added check pass/fail counts to text and JSON reports.
- Added check categories and category summaries in JSON output.
- Added `--category` filters for focused category-specific reports.
- Added checks for CODEOWNERS, issue templates, pull request templates, and dependency update automation.
- Added `--list-checks`, `--init-config`, and `--output` for maintainer workflows.
- Added GitHub collaboration templates and Dependabot configuration to this repository.
- Added offline Git activity metrics with commit charts, author summaries, and detected merged PR charts.
- Added `--metrics`, `--metrics-days`, and `--include-health` for combined health and activity reports.
- Expanded README, package metadata, and release notes to describe the maintainer dashboard workflow.

## 0.1.0

- Initial release with local repository hygiene checks.
- Added human-readable and JSON output.
- Added strict mode for CI usage.
- Added score threshold support with `--fail-under`.
- Added `--only-failures` for focused CI and maintainer reports.
