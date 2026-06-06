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
    weight: int = 10

    @property
    def passed(self) -> bool:
        return self.status == "pass"


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

    checks: tuple[Callable[[Path], CheckResult], ...] = (
        _check_readme,
        _check_license,
        _check_contributing,
        _check_security_policy,
        _check_changelog,
        _check_ci,
        _check_tests,
        _check_package_metadata,
        _check_release_notes,
    )
    config = load_config(repo_path, config_path=config_path)
    results = []
    for check in checks:
        result = check(repo_path)
        if result.id in config.disabled_checks:
            continue
        results.append(
            CheckResult(
                result.id,
                result.name,
                result.status,
                result.detail,
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

    return AuditConfig(
        disabled_checks=frozenset(disabled_checks),
        weights=weights,
        path=candidate,
    )


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
