import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oss_repo_healthcheck.__main__ import _format_report, main
from oss_repo_healthcheck import audit_repository


class CliTests(unittest.TestCase):
    def test_fail_under_passes_when_score_meets_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_path = _complete_repo(Path(directory))

            with patch("builtins.print"):
                exit_code = main([str(repo_path), "--fail-under", "90"])

            self.assertEqual(exit_code, 0)

    def test_fail_under_fails_when_score_is_below_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_path = Path(directory)
            (repo_path / "README.md").write_text("# Project\n", encoding="utf-8")

            with patch("builtins.print"):
                exit_code = main([str(repo_path), "--fail-under", "80"])

            self.assertEqual(exit_code, 1)

    def test_fail_under_rejects_out_of_range_threshold(self) -> None:
        with self.assertRaises(SystemExit):
            main(["--fail-under", "101"])

    def test_only_failures_filters_human_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_path = Path(directory)
            (repo_path / "README.md").write_text("# Project\n", encoding="utf-8")

            report = _format_report(audit_repository(repo_path), only_failures=True)

            self.assertIn("License", report)
            self.assertNotIn("PASS  README documentation", report)

    def test_only_failures_filters_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_path = Path(directory)
            (repo_path / "README.md").write_text("# Project\n", encoding="utf-8")

            result = audit_repository(repo_path).to_dict(only_failures=True)
            names = {check["name"] for check in result["checks"]}

            self.assertIn("License", names)
            self.assertNotIn("README documentation", names)


def _complete_repo(repo_path: Path) -> Path:
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
    return repo_path


if __name__ == "__main__":
    unittest.main()
