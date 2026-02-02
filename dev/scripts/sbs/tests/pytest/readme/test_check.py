"""
Tests for sbs.readme.check module.

Tests the git-based README staleness detector that checks for uncommitted
or unpushed changes across repositories.
"""

from __future__ import annotations

import json

import pytest

from sbs.readme.check import (
    RepoStatus,
    format_report,
    format_json,
)


@pytest.mark.evergreen
class TestRepoStatus:
    """Tests for RepoStatus dataclass."""

    def test_has_changes_true_when_uncommitted(self) -> None:
        """has_changes is True when has_uncommitted is True."""
        status = RepoStatus(
            name="Test",
            path="test",
            readme_path="test/README.md",
            has_uncommitted=True,
            has_unpushed=False,
        )
        assert status.has_changes is True

    def test_has_changes_true_when_unpushed(self) -> None:
        """has_changes is True when has_unpushed is True."""
        status = RepoStatus(
            name="Test",
            path="test",
            readme_path="test/README.md",
            has_uncommitted=False,
            has_unpushed=True,
        )
        assert status.has_changes is True

    def test_has_changes_true_when_both(self) -> None:
        """has_changes is True when both uncommitted and unpushed."""
        status = RepoStatus(
            name="Test",
            path="test",
            readme_path="test/README.md",
            has_uncommitted=True,
            has_unpushed=True,
        )
        assert status.has_changes is True

    def test_has_changes_false_when_clean(self) -> None:
        """has_changes is False when no uncommitted or unpushed changes."""
        status = RepoStatus(
            name="Test",
            path="test",
            readme_path="test/README.md",
            has_uncommitted=False,
            has_unpushed=False,
        )
        assert status.has_changes is False

    def test_changed_files_default_empty(self) -> None:
        """changed_files defaults to empty list."""
        status = RepoStatus(
            name="Test",
            path="test",
            readme_path="test/README.md",
        )
        assert status.changed_files == []

    def test_changed_files_populated(self) -> None:
        """changed_files can be populated."""
        status = RepoStatus(
            name="Test",
            path="test",
            readme_path="test/README.md",
            has_uncommitted=True,
            changed_files=["file1.py", "file2.py"],
        )
        assert status.changed_files == ["file1.py", "file2.py"]


@pytest.mark.evergreen
class TestFormatReport:
    """Tests for format_report function."""

    def test_report_shows_changed_repos(self) -> None:
        """Report lists repos with changes."""
        statuses = [
            RepoStatus("Dirty", "dirty", "dirty/README.md", True, False, ["file.py"]),
            RepoStatus("Clean", "clean", "clean/README.md", False, False, []),
        ]
        report = format_report(statuses)

        assert "Dirty" in report
        assert "uncommitted changes" in report
        assert "Clean" in report
        assert "1 repos need README review" in report

    def test_report_handles_all_clean(self) -> None:
        """Report indicates when no changes found."""
        statuses = [
            RepoStatus("Clean1", "c1", "c1/README.md", False, False, []),
            RepoStatus("Clean2", "c2", "c2/README.md", False, False, []),
        ]
        report = format_report(statuses)

        assert "No repos have changes" in report

    def test_report_shows_unpushed_commits(self) -> None:
        """Report mentions unpushed commits."""
        statuses = [
            RepoStatus("Unpushed", "unpushed", "unpushed/README.md", False, True, []),
        ]
        report = format_report(statuses)

        assert "unpushed commits" in report

    def test_report_shows_changed_files(self) -> None:
        """Report lists changed files."""
        statuses = [
            RepoStatus("Test", "test", "test/README.md", True, False, ["a.py", "b.py"]),
        ]
        report = format_report(statuses)

        assert "Changed files" in report
        assert "a.py" in report
        assert "b.py" in report

    def test_report_limits_file_list(self) -> None:
        """Report truncates long file lists."""
        many_files = [f"file{i}.py" for i in range(20)]
        statuses = [
            RepoStatus("Test", "test", "test/README.md", True, False, many_files),
        ]
        report = format_report(statuses)

        # Should show first 10 and indicate more
        assert "file0.py" in report
        assert "file9.py" in report
        assert "and 10 more" in report

    def test_report_includes_readme_path(self) -> None:
        """Report shows README path for each changed repo."""
        statuses = [
            RepoStatus("Test", "test", "test/README.md", True, False, []),
        ]
        report = format_report(statuses)

        assert "README: test/README.md" in report

    def test_report_summary_counts(self) -> None:
        """Report shows correct summary counts."""
        statuses = [
            RepoStatus("Dirty1", "d1", "d1/README.md", True, False, []),
            RepoStatus("Dirty2", "d2", "d2/README.md", False, True, []),
            RepoStatus("Clean1", "c1", "c1/README.md", False, False, []),
        ]
        report = format_report(statuses)

        assert "2 repos need README review" in report
        assert "1 repos clean" in report


@pytest.mark.evergreen
class TestFormatJson:
    """Tests for format_json function."""

    def test_json_is_valid(self) -> None:
        """Output is valid JSON."""
        statuses = [
            RepoStatus("Test", "test", "test/README.md", True, False, ["a.py"]),
        ]
        result = format_json(statuses)

        data = json.loads(result)
        assert "repos_with_changes" in data
        assert "clean_repos" in data
        assert "summary" in data

    def test_json_includes_changed_files(self) -> None:
        """JSON includes changed_files array."""
        statuses = [
            RepoStatus("Test", "test", "test/README.md", True, False, ["a.py", "b.py"]),
        ]
        result = format_json(statuses)

        data = json.loads(result)
        assert data["repos_with_changes"][0]["changed_files"] == ["a.py", "b.py"]

    def test_json_separates_changed_and_clean(self) -> None:
        """JSON correctly separates changed and clean repos."""
        statuses = [
            RepoStatus("Dirty", "dirty", "dirty/README.md", True, False, []),
            RepoStatus("Clean", "clean", "clean/README.md", False, False, []),
        ]
        result = format_json(statuses)

        data = json.loads(result)
        assert len(data["repos_with_changes"]) == 1
        assert data["repos_with_changes"][0]["name"] == "Dirty"
        assert "Clean" in data["clean_repos"]

    def test_json_includes_all_status_fields(self) -> None:
        """JSON includes all RepoStatus fields for changed repos."""
        statuses = [
            RepoStatus("Test", "test/path", "test/path/README.md", True, True, ["x.py"]),
        ]
        result = format_json(statuses)

        data = json.loads(result)
        repo = data["repos_with_changes"][0]
        assert repo["name"] == "Test"
        assert repo["path"] == "test/path"
        assert repo["readme_path"] == "test/path/README.md"
        assert repo["has_uncommitted"] is True
        assert repo["has_unpushed"] is True
        assert repo["changed_files"] == ["x.py"]

    def test_json_summary_counts(self) -> None:
        """JSON summary has correct counts."""
        statuses = [
            RepoStatus("D1", "d1", "d1/README.md", True, False, []),
            RepoStatus("D2", "d2", "d2/README.md", False, True, []),
            RepoStatus("C1", "c1", "c1/README.md", False, False, []),
        ]
        result = format_json(statuses)

        data = json.loads(result)
        assert data["summary"]["needs_review"] == 2
        assert data["summary"]["clean"] == 1

    def test_json_empty_statuses(self) -> None:
        """JSON handles empty status list."""
        statuses: list[RepoStatus] = []
        result = format_json(statuses)

        data = json.loads(result)
        assert data["repos_with_changes"] == []
        assert data["clean_repos"] == []
        assert data["summary"]["needs_review"] == 0
        assert data["summary"]["clean"] == 0
