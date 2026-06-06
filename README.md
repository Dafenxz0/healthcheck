# oss-repo-healthcheck

`oss-repo-healthcheck` is a dependency-free maintainer dashboard for open-source
repositories. It combines repository hygiene checks with lightweight Git
activity metrics, so maintainers can quickly answer two practical questions:

- Is this repository set up for contributors, releases, security, and CI?
- Is the project active, and what does recent commit/PR activity look like?

The CLI works offline against any local Git checkout. It can print human-readable
reports, JSON for automation, or Markdown tables that are ready to paste into
pull requests, release notes, onboarding docs, and maintainer reviews.

Current reports cover:

- Documentation, license, security, contribution, changelog, release, packaging,
  test, and CI readiness
- Governance and collaboration signals such as CODEOWNERS, issue templates, pull
  request templates, and Dependabot/Renovate configuration
- Configurable check weights and disabled checks for project-specific standards
- Commit activity windows, commits per week, active days, top authors, and
  locally detected merged pull requests
- Text, JSON, Markdown, and file output for CI or recurring reports

## Why this exists

Maintainers often inherit small gaps that make projects harder to review,
contribute to, or keep healthy over time. Teams also need a low-friction way to
summarize activity without opening dashboards or wiring up tokens.

This tool gives a fast local snapshot that can be run before a release, during
onboarding, as part of a maintenance sweep, or in CI as a lightweight quality
gate.

## Install

```bash
pip install oss-repo-healthcheck
```

For local development:

```bash
python -m pip install -e .
```

## Usage

Generate a full health report:

Audit the current repository:

```bash
oss-repo-healthcheck
```

Audit another path:

```bash
oss-repo-healthcheck /path/to/repo
```

Return a non-zero exit code when required checks fail:

```bash
oss-repo-healthcheck --strict
```

Fail CI when the score drops below a threshold:

```bash
oss-repo-healthcheck --fail-under 80
```

Show only failing checks:

```bash
oss-repo-healthcheck --only-failures
```

Print machine-readable JSON:

```bash
oss-repo-healthcheck --json
```

Render a Markdown table for pull request comments:

```bash
oss-repo-healthcheck --format markdown
```

Write a report to a file:

```bash
oss-repo-healthcheck --format markdown --output healthcheck.md
```

List available check IDs:

```bash
oss-repo-healthcheck --list-checks
```

Create a starter config:

```bash
oss-repo-healthcheck --init-config
```

Show commit activity charts:

```bash
oss-repo-healthcheck --metrics --metrics-days 30
```

Combine health checks and activity metrics in one Markdown report:

```bash
oss-repo-healthcheck --metrics --include-health --format markdown --output repo-report.md
```

Use a config file:

```bash
oss-repo-healthcheck --config healthcheck.json
```

## Checks

The current version looks for:

- README documentation
- License file
- Contribution guide
- Security policy
- Changelog
- CI workflow
- Test directory or test files
- Package metadata
- Release notes or GitHub release workflow
- CODEOWNERS
- Issue templates
- Pull request template
- Dependabot or Renovate configuration

Checks are intentionally simple and transparent. The goal is a practical first
pass, not a replacement for human review.

## Report outputs

`oss-repo-healthcheck` is designed to fit into different maintainer workflows:

- **Text:** quick terminal scans during local maintenance.
- **JSON:** CI gates, dashboards, and scripts that need structured data.
- **Markdown:** PR comments, issue updates, release preparation notes, and
  contributor-facing summaries.
- **Output files:** persistent reports such as `repo-report.md` or generated CI
  artifacts.

The combined report mode is useful when you want a single artifact with both
repository readiness and recent project activity:

```bash
oss-repo-healthcheck --metrics --include-health --format markdown --output repo-report.md
```

## Configuration

By default, the CLI will read `.oss-repo-healthcheck.json` from the repository
root when it exists. You can also pass a custom path with `--config`.

```json
{
  "disabled_checks": ["release-notes"],
  "weights": {
    "readme": 20,
    "tests": 20
  }
}
```

Use `disabled_checks` for checks that do not apply to a project, and `weights`
to make the score reflect what matters most in your ecosystem.

## Activity metrics

The `--metrics` mode reads local Git history and reports practical repository
activity signals:

- Total commits in the selected window
- Active commit days
- Commits per week
- ASCII or Markdown charts for commits by week
- Top commit authors
- Merged pull requests detected from merge commit messages
- Weekly chart for detected merged pull requests

Metrics are available in text, JSON, and Markdown formats. They work offline and
do not require a GitHub token.

## Example

```text
oss-repo-healthcheck: .

PASS  [documentation] README documentation
PASS  [governance] License
FAIL  [governance] Security policy
PASS  [automation] Continuous integration
PASS  [quality] Tests

Checks: 4 passed, 1 failed
Score: 76/100
```

## Contributing

Issues and pull requests are welcome. Good first improvements include support
for more ecosystems, better release workflow detection, and configurable check
weights.

## Continuous integration

The project is ready for a GitHub Actions test workflow, but the initial remote
publish may omit workflow files when the publishing token does not include the
`workflow` scope.

## License

MIT
