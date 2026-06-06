# Changelog

## Unreleased

- Added stable check IDs to make JSON output and configuration easier to consume.
- Added `.oss-repo-healthcheck.json` support for disabling checks and overriding weights.
- Added `--config` for using an explicit configuration file.
- Added `--format markdown` for pull request and issue comments.
- Added check pass/fail counts to text and JSON reports.
- Added check categories and category summaries in JSON output.
- Added checks for CODEOWNERS, issue templates, pull request templates, and dependency update automation.
- Added `--list-checks`, `--init-config`, and `--output` for maintainer workflows.
- Added GitHub collaboration templates and Dependabot configuration to this repository.

## 0.1.0

- Initial release with local repository hygiene checks.
- Added human-readable and JSON output.
- Added strict mode for CI usage.
- Added score threshold support with `--fail-under`.
- Added `--only-failures` for focused CI and maintainer reports.
