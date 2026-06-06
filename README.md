# oss-repo-healthcheck

A small command-line audit tool for maintainers who want a quick, local read on
open-source repository hygiene.

`oss-repo-healthcheck` scans a repository and reports whether common maintainer
signals are present: README, license, security policy, contribution docs, CI,
tests, changelog, package metadata, and release notes. It is intentionally
dependency-free and works offline.

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

Checks are intentionally simple and transparent. The goal is a practical first
pass, not a replacement for human review.

## Example

```text
oss-repo-healthcheck: .

PASS  README documentation
PASS  License
WARN  Security policy
PASS  Continuous integration
PASS  Tests

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
