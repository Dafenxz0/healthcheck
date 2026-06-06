from __future__ import annotations

import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class CommitActivity:
    path: Path
    days: int
    total_commits: int
    active_days: int
    authors: tuple[tuple[str, int], ...]
    weekly_commits: tuple[tuple[str, int], ...]
    weekly_merged_pull_requests: tuple[tuple[str, int], ...]
    merged_pull_requests: tuple[int, ...]

    @property
    def commits_per_week(self) -> float:
        if self.days <= 0:
            return 0.0
        return round(self.total_commits / (self.days / 7), 2)

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "days": self.days,
            "total_commits": self.total_commits,
            "active_days": self.active_days,
            "commits_per_week": self.commits_per_week,
            "authors": [{"name": name, "commits": commits} for name, commits in self.authors],
            "weekly_commits": [{"week": week, "commits": commits} for week, commits in self.weekly_commits],
            "weekly_merged_pull_requests": [
                {"week": week, "pull_requests": pull_requests}
                for week, pull_requests in self.weekly_merged_pull_requests
            ],
            "merged_pull_requests": list(self.merged_pull_requests),
        }


@dataclass(frozen=True)
class CommitEntry:
    authored_at: datetime
    author: str
    subject: str


def collect_commit_activity(path: str | Path, *, days: int = 90) -> CommitActivity:
    repo_path = Path(path).resolve()
    if days <= 0:
        raise ValueError("days must be greater than zero")
    entries = _read_git_log(repo_path, days=days)
    author_counts = Counter(entry.author for entry in entries)
    day_counts = Counter(entry.authored_at.date() for entry in entries)
    week_counts = _count_weeks(entries, days=days)
    pr_week_counts = _count_pr_weeks(entries, days=days)
    merged_prs = sorted({number for entry in entries for number in _extract_pr_numbers(entry.subject)})

    return CommitActivity(
        path=repo_path,
        days=days,
        total_commits=len(entries),
        active_days=len(day_counts),
        authors=tuple(author_counts.most_common()),
        weekly_commits=tuple(week_counts.items()),
        weekly_merged_pull_requests=tuple(pr_week_counts.items()),
        merged_pull_requests=tuple(merged_prs),
    )


def render_text_metrics(activity: CommitActivity) -> str:
    lines = [
        f"oss-repo-healthcheck activity: {activity.path}",
        "",
        f"Window: last {activity.days} days",
        f"Commits: {activity.total_commits}",
        f"Active days: {activity.active_days}",
        f"Commits/week: {activity.commits_per_week}",
        f"Merged PRs detected: {len(activity.merged_pull_requests)}",
        "",
        "Commits by week:",
    ]
    lines.extend(_render_bar_chart(activity.weekly_commits))
    lines.extend(["", "Top authors:"])
    if activity.authors:
        lines.extend(_render_bar_chart(activity.authors[:5]))
    else:
        lines.append("  none")
    lines.extend(["", "Merged PRs by week:"])
    lines.extend(_render_bar_chart(activity.weekly_merged_pull_requests))
    if activity.merged_pull_requests:
        prs = ", ".join(f"#{number}" for number in activity.merged_pull_requests[:10])
        lines.extend(["", f"Recent merged PRs: {prs}"])
    return "\n".join(lines)


def render_markdown_metrics(activity: CommitActivity) -> str:
    lines = [
        f"## Repository activity: `{activity.path}`",
        "",
        f"- **Window:** last {activity.days} days",
        f"- **Commits:** {activity.total_commits}",
        f"- **Active days:** {activity.active_days}",
        f"- **Commits/week:** {activity.commits_per_week}",
        f"- **Merged PRs detected:** {len(activity.merged_pull_requests)}",
        "",
        "### Commits by week",
        "",
        "| Week | Commits | Graph |",
        "| --- | ---: | --- |",
    ]
    for week, count in activity.weekly_commits:
        lines.append(f"| {week} | {count} | `{_bar(count, _max_count(activity.weekly_commits))}` |")
    lines.extend(["", "### Merged PRs by week", "", "| Week | PRs | Graph |", "| --- | ---: | --- |"])
    for week, count in activity.weekly_merged_pull_requests:
        lines.append(f"| {week} | {count} | `{_bar(count, _max_count(activity.weekly_merged_pull_requests))}` |")
    lines.extend(["", "### Top authors", "", "| Author | Commits |", "| --- | ---: |"])
    if activity.authors:
        for author, count in activity.authors[:5]:
            lines.append(f"| {_markdown_cell(author)} | {count} |")
    else:
        lines.append("| none | 0 |")
    if activity.merged_pull_requests:
        prs = ", ".join(f"#{number}" for number in activity.merged_pull_requests[:10])
        lines.extend(["", f"### Recent merged PRs", "", prs])
    return "\n".join(lines)


def _read_git_log(path: Path, *, days: int) -> tuple[CommitEntry, ...]:
    if not (path / ".git").exists():
        return ()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    command = [
        "git",
        "-C",
        str(path),
        "log",
        f"--since={since}",
        "--date=iso-strict",
        "--pretty=format:%aI%x1f%an%x1f%s",
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    entries = []
    for line in completed.stdout.splitlines():
        parts = line.split("\x1f")
        if len(parts) != 3:
            continue
        authored_at, author, subject = parts
        entries.append(
            CommitEntry(
                authored_at=datetime.fromisoformat(authored_at),
                author=author,
                subject=subject,
            )
        )
    return tuple(entries)


def _count_weeks(entries: tuple[CommitEntry, ...], *, days: int) -> dict[str, int]:
    counts = _empty_week_counts(days=days)
    for entry in entries:
        week = entry.authored_at.date() - timedelta(days=entry.authored_at.date().weekday())
        key = week.isoformat()
        if key in counts:
            counts[key] += 1
    return counts


def _count_pr_weeks(entries: tuple[CommitEntry, ...], *, days: int) -> dict[str, int]:
    counts = _empty_week_counts(days=days)
    for entry in entries:
        if not _extract_pr_numbers(entry.subject):
            continue
        week = entry.authored_at.date() - timedelta(days=entry.authored_at.date().weekday())
        key = week.isoformat()
        if key in counts:
            counts[key] += 1
    return counts


def _empty_week_counts(*, days: int) -> dict[str, int]:
    today = date.today()
    start = today - timedelta(days=days - 1)
    week_starts = []
    cursor = start - timedelta(days=start.weekday())
    while cursor <= today:
        week_starts.append(cursor)
        cursor += timedelta(days=7)
    return {week.isoformat(): 0 for week in week_starts}


def _extract_pr_numbers(subject: str) -> tuple[int, ...]:
    return tuple(int(match) for match in re.findall(r"(?:pull request|PR)\s+#(\d+)", subject, flags=re.IGNORECASE))


def _render_bar_chart(rows: tuple[tuple[str, int], ...]) -> list[str]:
    if not rows:
        return ["  none"]
    maximum = _max_count(rows)
    return [f"  {label:<20} {count:>4} {_bar(count, maximum)}" for label, count in rows]


def _bar(count: int, maximum: int) -> str:
    if maximum <= 0 or count <= 0:
        return ""
    width = max(1, round((count / maximum) * 24))
    return "#" * width


def _max_count(rows: tuple[tuple[str, int], ...]) -> int:
    return max((count for _, count in rows), default=0)


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|")
