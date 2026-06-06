import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oss_repo_healthcheck.__main__ import _format_markdown_report, _format_report, main
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

    def test_report_includes_check_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_path = _complete_repo(Path(directory))

            report = _format_report(audit_repository(repo_path))
            result = audit_repository(repo_path).to_dict()

            self.assertIn("Checks: 13 passed, 0 failed", report)
            self.assertEqual(result["passed"], 13)
            self.assertEqual(result["failed"], 0)

    def test_config_flag_is_used_by_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_path = Path(directory)
            config_path = repo_path / "healthcheck.json"
            config_path.write_text(
                json.dumps({"disabled_checks": ["license"]}),
                encoding="utf-8",
            )

            with patch("builtins.print") as mocked_print:
                exit_code = main([str(repo_path), "--config", str(config_path)])

            self.assertEqual(exit_code, 0)
            report = mocked_print.call_args.args[0]
            self.assertIn(f"Config: {config_path}", report)
            self.assertNotIn("License", report)

    def test_markdown_report_renders_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_path = Path(directory)
            (repo_path / "README.md").write_text("# Project\n", encoding="utf-8")

            report = _format_markdown_report(audit_repository(repo_path), only_failures=True)

            self.assertIn("## oss-repo-healthcheck:", report)
            self.assertIn("| Status | Check | Detail |", report)
            self.assertIn("| FAIL | License | Add a clear open-source license. |", report)
            self.assertNotIn("README documentation", report)

    def test_markdown_format_is_available_from_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_path = Path(directory)

            with patch("builtins.print") as mocked_print:
                exit_code = main([str(repo_path), "--format", "markdown"])

            self.assertEqual(exit_code, 0)
            self.assertIn("| Status | Check | Detail |", mocked_print.call_args.args[0])


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
    (repo_path / ".github" / "CODEOWNERS").write_text("* @maintainer\n", encoding="utf-8")
    issue_template_dir = repo_path / ".github" / "ISSUE_TEMPLATE"
    issue_template_dir.mkdir()
    (issue_template_dir / "bug.md").write_text("# Bug\n", encoding="utf-8")
    (repo_path / ".github" / "PULL_REQUEST_TEMPLATE.md").write_text("## Tests\n", encoding="utf-8")
    (repo_path / ".github" / "dependabot.yml").write_text("version: 2\n", encoding="utf-8")
    return repo_path


if __name__ == "__main__":
    unittest.main()
