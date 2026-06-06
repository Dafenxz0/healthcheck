import json
import tempfile
import unittest
from pathlib import Path

from oss_repo_healthcheck import audit_repository


class AuditRepositoryTests(unittest.TestCase):
    def test_audit_scores_complete_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_path = Path(directory)
            (repo_path / "README.md").write_text("# Project\n", encoding="utf-8")
            (repo_path / "LICENSE").write_text("MIT\n", encoding="utf-8")
            (repo_path / "CONTRIBUTING.md").write_text("Contribute\n", encoding="utf-8")
            (repo_path / "SECURITY.md").write_text("Security\n", encoding="utf-8")
            (repo_path / "CHANGELOG.md").write_text("Changes\n", encoding="utf-8")
            (repo_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
            (repo_path / "RELEASES.md").write_text("Releases\n", encoding="utf-8")
            (repo_path / "tests").mkdir()
            workflow_dir = repo_path / ".github" / "workflows"
            workflow_dir.mkdir(parents=True)
            (workflow_dir / "test.yml").write_text("name: test\n", encoding="utf-8")

            result = audit_repository(repo_path)

            self.assertEqual(result.score, 100)
            self.assertFalse(result.has_failures)

    def test_audit_reports_missing_required_signals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = audit_repository(directory)
            statuses = {check.name: check.status for check in result.checks}

            self.assertEqual(statuses["README documentation"], "fail")
            self.assertEqual(statuses["License"], "fail")
            self.assertTrue(result.has_failures)
            self.assertEqual(result.score, 0)

    def test_audit_accepts_github_yaml_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_path = Path(directory)
            workflow_dir = repo_path / ".github" / "workflows"
            workflow_dir.mkdir(parents=True)
            (workflow_dir / "ci.yaml").write_text("name: ci\n", encoding="utf-8")

            result = audit_repository(repo_path)
            statuses = {check.name: check.status for check in result.checks}

            self.assertEqual(statuses["Continuous integration"], "pass")

    def test_audit_exposes_stable_check_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = audit_repository(directory)
            ids = {check.id for check in result.checks}

            self.assertIn("readme", ids)
            self.assertIn("license", ids)
            self.assertIn("ci", ids)

    def test_audit_can_disable_checks_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_path = Path(directory)
            (repo_path / ".oss-repo-healthcheck.json").write_text(
                json.dumps({"disabled_checks": ["release-notes", "security"]}),
                encoding="utf-8",
            )

            result = audit_repository(repo_path)
            ids = {check.id for check in result.checks}

            self.assertNotIn("release-notes", ids)
            self.assertNotIn("security", ids)
            self.assertEqual(result.config_path, repo_path / ".oss-repo-healthcheck.json")

    def test_audit_can_override_weights_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_path = Path(directory)
            (repo_path / "README.md").write_text("# Project\n", encoding="utf-8")
            config_path = repo_path / "healthcheck.json"
            config_path.write_text(
                json.dumps({"weights": {"readme": 100, "license": 0}}),
                encoding="utf-8",
            )

            result = audit_repository(repo_path, config_path=config_path)
            weights = {check.id: check.weight for check in result.checks}

            self.assertEqual(weights["readme"], 100)
            self.assertEqual(weights["license"], 0)
            self.assertGreater(result.score, 50)


if __name__ == "__main__":
    unittest.main()
