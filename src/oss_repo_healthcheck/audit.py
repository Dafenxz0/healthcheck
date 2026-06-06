from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Mapping


@dataclass(frozen=True)
class CheckResult:
    id: str
    name: str
    status: str
    detail: str
    category: str = "general"
    weight: int = 10

    @property
    def passed(self) -> bool:
        return self.status == "pass"


@dataclass(frozen=True)
class CheckDefinition:
    id: str
    name: str
    category: str
    default_weight: int
    runner: Callable[[Path], CheckResult]


@dataclass(frozen=True)
class AuditResult:
    path: Path
    checks: tuple[CheckResult, ...]
    config_path: Path | None = None

    @property
    def score(self) -> int:
        total = sum(check.weight for check in self.checks)
        if total == 0:
            return 0
        earned = sum(check.weight for check in self.checks if check.passed)
        return round((earned / total) * 100)

    @property
    def has_failures(self) -> bool:
        return any(check.status == "fail" for check in self.checks)

    @property
    def passed_count(self) -> int:
        return sum(1 for check in self.checks if check.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for check in self.checks if not check.passed)

    @property
    def categories(self) -> dict[str, dict[str, int]]:
        summary: dict[str, dict[str, int]] = {}
        for check in self.checks:
            category = summary.setdefault(check.category, {"passed": 0, "failed": 0, "total": 0})
            category["total"] += 1
            if check.passed:
                category["passed"] += 1
            else:
                category["failed"] += 1
        return summary

    def to_dict(self, *, only_failures: bool = False) -> dict[str, object]:
        checks = self.checks
        if only_failures:
            checks = tuple(check for check in checks if not check.passed)
        return {
            "path": str(self.path),
            "config_path": str(self.config_path) if self.config_path else None,
            "score": self.score,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "categories": self.categories,
            "checks": [asdict(check) for check in checks],
        }


@dataclass(frozen=True)
class AuditConfig:
    disabled_checks: frozenset[str] = frozenset()
    weights: Mapping[str, int] | None = None
    path: Path | None = None

    def weight_for(self, check: CheckResult) -> int:
        weights = self.weights or {}
        return weights.get(check.id, check.weight)


def audit_repository(path: str | Path, *, config_path: str | Path | None = None) -> AuditResult:
    repo_path = Path(path).resolve()
    if not repo_path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
    if not repo_path.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {repo_path}")

    config = load_config(repo_path, config_path=config_path)
    results = []
    for definition in CHECK_DEFINITIONS:
        result = definition.runner(repo_path)
        if result.id in config.disabled_checks:
            continue
        results.append(
            CheckResult(
                result.id,
                result.name,
                result.status,
                result.detail,
                category=definition.category,
                weight=config.weight_for(result),
            )
        )

    return AuditResult(
        path=repo_path,
        checks=tuple(results),
        config_path=config.path,
    )


def load_config(repo_path: Path, *, config_path: str | Path | None = None) -> AuditConfig:
    candidate = Path(config_path).resolve() if config_path else repo_path / ".oss-repo-healthcheck.json"
    if not candidate.exists():
        return AuditConfig()
    with candidate.open(encoding="utf-8") as config_file:
        data = json.load(config_file)
    if not isinstance(data, dict):
        raise ValueError("Healthcheck config must be a JSON object.")

    disabled_checks = data.get("disabled_checks", [])
    if not isinstance(disabled_checks, list) or not all(isinstance(item, str) for item in disabled_checks):
        raise ValueError("disabled_checks must be a list of check IDs.")

    weights = data.get("weights", {})
    if not isinstance(weights, dict) or not all(isinstance(key, str) and isinstance(value, int) for key, value in weights.items()):
        raise ValueError("weights must be an object mapping check IDs to integer weights.")
    if any(value < 0 for value in weights.values()):
        raise ValueError("weights must be zero or greater.")

    known_ids = {definition.id for definition in CHECK_DEFINITIONS}
    unknown_ids = (set(disabled_checks) | set(weights)) - known_ids
    if unknown_ids:
        unknown = ", ".join(sorted(unknown_ids))
        raise ValueError(f"Unknown check ID in config: {unknown}")

    return AuditConfig(
        disabled_checks=frozenset(disabled_checks),
        weights=weights,
        path=candidate,
    )


def list_checks() -> tuple[CheckDefinition, ...]:
    return CHECK_DEFINITIONS


def _check_readme(path: Path) -> CheckResult:
    return _exists(
        path,
        ("README", "README.md", "README.rst", "README.txt"),
        "readme",
        "README documentation",
        "Add a README that explains purpose, install steps, and usage.",
        weight=15,
    )


def _check_license(path: Path) -> CheckResult:
    return _exists(
        path,
        ("LICENSE", "LICENSE.md", "COPYING", "COPYING.md"),
        "license",
        "License",
        "Add a clear open-source license.",
        weight=15,
    )


def _check_contributing(path: Path) -> CheckResult:
    return _exists(
        path,
        ("CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md"),
        "contributing",
        "Contribution guide",
        "Add contribution instructions for issues, pull requests, and local setup.",
    )


def _check_security_policy(path: Path) -> CheckResult:
    return _exists(
        path,
        ("SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md"),
        "security",
        "Security policy",
        "Add a security policy that explains responsible disclosure.",
    )


def _check_changelog(path: Path) -> CheckResult:
    return _exists(
        path,
        ("CHANGELOG.md", "HISTORY.md", "NEWS.md"),
        "changelog",
        "Changelog",
        "Add a changelog so users can track releases.",
    )


def _check_ci(path: Path) -> CheckResult:
    workflow_dir = path / ".github" / "workflows"
    if workflow_dir.exists() and any(workflow_dir.glob("*.yml")):
        return CheckResult("ci", "Continuous integration", "pass", "Found GitHub Actions workflow.")
    if workflow_dir.exists() and any(workflow_dir.glob("*.yaml")):
        return CheckResult("ci", "Continuous integration", "pass", "Found GitHub Actions workflow.")
    return CheckResult("ci", "Continuous integration", "fail", "Add a CI workflow for tests and checks.", weight=15)


def _check_tests(path: Path) -> CheckResult:
    candidates = (path / "tests", path / "test")
    if any(candidate.exists() and candidate.is_dir() for candidate in candidates):
        return CheckResult("tests", "Tests", "pass", "Found a test directory.", weight=15)
    if any(path.glob("**/test_*.py")) or any(path.glob("**/*.test.*")):
        return CheckResult("tests", "Tests", "pass", "Found test files.", weight=15)
    return CheckResult("tests", "Tests", "fail", "Add tests for core behavior.", weight=15)


def _check_package_metadata(path: Path) -> CheckResult:
    metadata_files = (
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "Gemfile",
        "composer.json",
    )
    return _exists(
        path,
        metadata_files,
        "package-metadata",
        "Package metadata",
        "Add ecosystem metadata such as pyproject.toml, package.json, go.mod, or Cargo.toml.",
    )


def _check_release_notes(path: Path) -> CheckResult:
    if (path / ".github" / "workflows" / "release.yml").exists():
        return CheckResult("release-notes", "Release notes", "pass", "Found a release workflow.")
    return _exists(
        path,
        ("RELEASES.md", "docs/releases.md", "docs/RELEASES.md"),
        "release-notes",
        "Release notes",
        "Add release notes or a release workflow.",
    )


def _check_codeowners(path: Path) -> CheckResult:
    return _exists(
        path,
        ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"),
        "codeowners",
        "Code owners",
        "Add CODEOWNERS so review ownership is clear.",
    )


def _check_issue_templates(path: Path) -> CheckResult:
    issue_template_dir = path / ".github" / "ISSUE_TEMPLATE"
    if issue_template_dir.exists() and any(item.is_file() for item in issue_template_dir.iterdir()):
        return CheckResult("issue-templates", "Issue templates", "pass", "Found issue templates.")
    return _exists(
        path,
        ("ISSUE_TEMPLATE.md", ".github/ISSUE_TEMPLATE.md"),
        "issue-templates",
        "Issue templates",
        "Add issue templates to make incoming reports easier to triage.",
    )


def _check_pr_template(path: Path) -> CheckResult:
    pr_template_dir = path / ".github" / "PULL_REQUEST_TEMPLATE"
    if pr_template_dir.exists() and any(item.is_file() for item in pr_template_dir.iterdir()):
        return CheckResult("pull-request-template", "Pull request template", "pass", "Found pull request templates.")
    return _exists(
        path,
        ("PULL_REQUEST_TEMPLATE.md", ".github/PULL_REQUEST_TEMPLATE.md", "docs/PULL_REQUEST_TEMPLATE.md"),
        "pull-request-template",
        "Pull request template",
        "Add a pull request template with testing and review guidance.",
    )


def _check_dependency_updates(path: Path) -> CheckResult:
    return _exists(
        path,
        (
            ".github/dependabot.yml",
            ".github/dependabot.yaml",
            "renovate.json",
            ".renovaterc",
            ".renovaterc.json",
        ),
        "dependency-updates",
        "Dependency update automation",
        "Add Dependabot or Renovate configuration for dependency update visibility.",
    )


def _exists(
    path: Path,
    names: tuple[str, ...],
    check_id: str,
    check_name: str,
    missing_detail: str,
    weight: int = 10,
) -> CheckResult:
    for name in names:
        if (path / name).exists():
            return CheckResult(check_id, check_name, "pass", f"Found {name}.", weight=weight)
    return CheckResult(check_id, check_name, "fail", missing_detail, weight=weight)


CHECK_DEFINITIONS: tuple[CheckDefinition, ...] = (
    CheckDefinition("readme", "README documentation", "documentation", 15, _check_readme),
    CheckDefinition("license", "License", "governance", 15, _check_license),
    CheckDefinition("contributing", "Contribution guide", "collaboration", 10, _check_contributing),
    CheckDefinition("security", "Security policy", "governance", 10, _check_security_policy),
    CheckDefinition("changelog", "Changelog", "release", 10, _check_changelog),
    CheckDefinition("ci", "Continuous integration", "automation", 15, _check_ci),
    CheckDefinition("tests", "Tests", "quality", 15, _check_tests),
    CheckDefinition("package-metadata", "Package metadata", "packaging", 10, _check_package_metadata),
    CheckDefinition("release-notes", "Release notes", "release", 10, _check_release_notes),
    CheckDefinition("codeowners", "Code owners", "governance", 10, _check_codeowners),
    CheckDefinition("issue-templates", "Issue templates", "collaboration", 10, _check_issue_templates),
    CheckDefinition("pull-request-template", "Pull request template", "collaboration", 10, _check_pr_template),
    CheckDefinition("dependency-updates", "Dependency update automation", "automation", 10, _check_dependency_updates),
)
