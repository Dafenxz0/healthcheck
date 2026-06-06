from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str
    weight: int = 10

    @property
    def passed(self) -> bool:
        return self.status == "pass"


@dataclass(frozen=True)
class AuditResult:
    path: Path
    checks: tuple[CheckResult, ...]

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

    def to_dict(self, *, only_failures: bool = False) -> dict[str, object]:
        checks = self.checks
        if only_failures:
            checks = tuple(check for check in checks if not check.passed)
        return {
            "path": str(self.path),
            "score": self.score,
            "checks": [asdict(check) for check in checks],
        }


def audit_repository(path: str | Path) -> AuditResult:
    repo_path = Path(path).resolve()
    if not repo_path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
    if not repo_path.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {repo_path}")

    checks: tuple[tuple[str, Callable[[Path], CheckResult]], ...] = (
        ("README documentation", _check_readme),
        ("License", _check_license),
        ("Contribution guide", _check_contributing),
        ("Security policy", _check_security_policy),
        ("Changelog", _check_changelog),
        ("Continuous integration", _check_ci),
        ("Tests", _check_tests),
        ("Package metadata", _check_package_metadata),
        ("Release notes", _check_release_notes),
    )

    return AuditResult(
        path=repo_path,
        checks=tuple(check(repo_path) for _, check in checks),
    )


def _check_readme(path: Path) -> CheckResult:
    return _exists(
        path,
        ("README", "README.md", "README.rst", "README.txt"),
        "README documentation",
        "Add a README that explains purpose, install steps, and usage.",
        weight=15,
    )


def _check_license(path: Path) -> CheckResult:
    return _exists(
        path,
        ("LICENSE", "LICENSE.md", "COPYING", "COPYING.md"),
        "License",
        "Add a clear open-source license.",
        weight=15,
    )


def _check_contributing(path: Path) -> CheckResult:
    return _exists(
        path,
        ("CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md"),
        "Contribution guide",
        "Add contribution instructions for issues, pull requests, and local setup.",
    )


def _check_security_policy(path: Path) -> CheckResult:
    return _exists(
        path,
        ("SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md"),
        "Security policy",
        "Add a security policy that explains responsible disclosure.",
    )


def _check_changelog(path: Path) -> CheckResult:
    return _exists(
        path,
        ("CHANGELOG.md", "HISTORY.md", "NEWS.md"),
        "Changelog",
        "Add a changelog so users can track releases.",
    )


def _check_ci(path: Path) -> CheckResult:
    workflow_dir = path / ".github" / "workflows"
    if workflow_dir.exists() and any(workflow_dir.glob("*.yml")):
        return CheckResult("Continuous integration", "pass", "Found GitHub Actions workflow.")
    if workflow_dir.exists() and any(workflow_dir.glob("*.yaml")):
        return CheckResult("Continuous integration", "pass", "Found GitHub Actions workflow.")
    return CheckResult("Continuous integration", "fail", "Add a CI workflow for tests and checks.", weight=15)


def _check_tests(path: Path) -> CheckResult:
    candidates = (path / "tests", path / "test")
    if any(candidate.exists() and candidate.is_dir() for candidate in candidates):
        return CheckResult("Tests", "pass", "Found a test directory.", weight=15)
    if any(path.glob("**/test_*.py")) or any(path.glob("**/*.test.*")):
        return CheckResult("Tests", "pass", "Found test files.", weight=15)
    return CheckResult("Tests", "fail", "Add tests for core behavior.", weight=15)


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
        "Package metadata",
        "Add ecosystem metadata such as pyproject.toml, package.json, go.mod, or Cargo.toml.",
    )


def _check_release_notes(path: Path) -> CheckResult:
    if (path / ".github" / "workflows" / "release.yml").exists():
        return CheckResult("Release notes", "pass", "Found a release workflow.")
    return _exists(
        path,
        ("RELEASES.md", "docs/releases.md", "docs/RELEASES.md"),
        "Release notes",
        "Add release notes or a release workflow.",
    )


def _exists(
    path: Path,
    names: tuple[str, ...],
    check_name: str,
    missing_detail: str,
    weight: int = 10,
) -> CheckResult:
    for name in names:
        if (path / name).exists():
            return CheckResult(check_name, "pass", f"Found {name}.", weight=weight)
    return CheckResult(check_name, "fail", missing_detail, weight=weight)
