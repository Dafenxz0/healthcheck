# oss-repo-healthcheck

A small command-line audit tool for maintainers who want a quick, local read on
open-source repository hygiene.

`oss-repo-healthcheck` scans a repository and reports whether common maintainer
signals are present: README, license, security policy, contribution docs, CI,
tests, changelog, package metadata, release notes, ownership, collaboration
templates, and dependency update automation. It is intentionally dependency-free
and works offline.

## Why this exists

Maintainers often inherit small gaps that make projects harder to review,
contribute to, or keep healthy over time. This tool gives a fast checklist-style
summary that can be run before a release, during onboarding, or as part of a
maintenance sweep.

## Install

```bash
pip install oss-repo-healthcheck
```

For local development:

```bash
python -m pip install -e .
```

## Usage

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
