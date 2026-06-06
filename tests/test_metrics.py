from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from oss_repo_healthcheck.metrics import (
    CommitEntry,
    collect_commit_activity,
    render_markdown_metrics,
    render_text_metrics,
)


class MetricsTests(unittest.TestCase):
    def test_collect_commit_activity_summarizes_entries(self) -> None:
        entries = (
            CommitEntry(datetime(2026, 6, 1, tzinfo=timezone.utc), "Ada", "Add feature"),
            CommitEntry(datetime(2026, 6, 2, tzinfo=timezone.utc), "Ada", "Merge pull request #12 from branch"),
            CommitEntry(datetime(2026, 6, 3, tzinfo=timezone.utc), "Linus", "Fix bug PR #13"),
        )

        with patch("oss_repo_healthcheck.metrics._read_git_log", return_value=entries):
            activity = collect_commit_activity(Path("."), days=14)

        self.assertEqual(activity.total_commits, 3)
        self.assertEqual(activity.active_days, 3)
        self.assertEqual(activity.authors[0], ("Ada", 2))
        self.assertEqual(activity.merged_pull_requests, (12, 13))
        self.assertGreater(sum(count for _, count in activity.weekly_merged_pull_requests), 0)

    def test_text_metrics_render_ascii_graphs(self) -> None:
        entries = (
            CommitEntry(datetime(2026, 6, 1, tzinfo=timezone.utc), "Ada", "Add feature"),
            CommitEntry(datetime(2026, 6, 2, tzinfo=timezone.utc), "Ada", "Fix bug"),
        )

        with patch("oss_repo_healthcheck.metrics._read_git_log", return_value=entries):
            activity = collect_commit_activity(Path("."), days=14)

        report = render_text_metrics(activity)

        self.assertIn("Commits: 2", report)
        self.assertIn("Top authors:", report)
        self.assertIn("Merged PRs by week:", report)
        self.assertIn("Ada", report)
        self.assertIn("#", report)

    def test_markdown_metrics_render_tables(self) -> None:
        entries = (
            CommitEntry(datetime(2026, 6, 1, tzinfo=timezone.utc), "Ada | Team", "Merge pull request #9"),
        )

        with patch("oss_repo_healthcheck.metrics._read_git_log", return_value=entries):
            activity = collect_commit_activity(Path("."), days=14)

        report = render_markdown_metrics(activity)

        self.assertIn("| Week | Commits | Graph |", report)
        self.assertIn("### Merged PRs by week", report)
        self.assertIn("Ada \\| Team", report)
        self.assertIn("#9", report)

    def test_collect_commit_activity_rejects_invalid_window(self) -> None:
        with self.assertRaises(ValueError):
            collect_commit_activity(Path("."), days=0)


if __name__ == "__main__":
    unittest.main()
