# Release Notes

## Upcoming

The next release expands `oss-repo-healthcheck` from a simple repository hygiene
checklist into a local maintainer dashboard.

Highlights:

- Stable check IDs and categories for easier automation.
- Configurable weights and disabled checks through JSON config files.
- Additional governance and collaboration checks for CODEOWNERS, issue
  templates, pull request templates, and dependency update automation.
- Markdown and JSON reports for CI, PR comments, and release preparation.
- Offline Git activity metrics, including commit charts, top authors, active
  days, commits per week, and locally detected merged pull requests.
- Maintainer workflow commands: `--list-checks`, `--init-config`, `--output`,
  `--metrics`, `--metrics-days`, and `--include-health`.

## 0.1.0

Initial public version with local repository hygiene checks, human-readable
output, JSON output, strict mode, score thresholds, and focused failure reports.
