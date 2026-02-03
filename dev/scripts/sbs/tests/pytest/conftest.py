"""
Shared pytest fixtures for sbs CLI tests.

Provides fixtures for creating isolated test environments that don't
pollute the real archive data.

Test Tier Markers:
  @pytest.mark.evergreen - Tests that always run, never skip (production tests)
  @pytest.mark.dev       - Development/WIP tests, toggle-able
  @pytest.mark.temporary - Tests with explicit discard flag
"""

from __future__ import annotations

import io
import sys
import tempfile
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pytest

from sbs.archive.entry import ArchiveEntry, ArchiveIndex


# =============================================================================
# Test Data Constants
# =============================================================================

# Shared test data for fixtures creating multiple entries
# Format: (entry_id, project, tags, notes)
MULTI_ENTRY_TEST_DATA: list[tuple[str, str, list[str], str]] = [
    ("1700000001", "ProjectA", ["release"], "First entry"),
    ("1700000002", "ProjectB", ["beta", "test"], "Second entry"),
    ("1700000003", "ProjectA", ["dev"], "Third entry"),
    ("1700000004", "ProjectC", [], "Fourth entry"),
]


# =============================================================================
# Test Entry Factory
# =============================================================================


def _create_test_entry(
    entry_id: str,
    project: str = "TestProject",
    tags: list[str] | None = None,
    notes: str = "",
    trigger: str = "manual",
    screenshots: list[str] | None = None,
    build_run_id: str | None = None,
    repo_commits: dict[str, str] | None = None,
) -> ArchiveEntry:
    """Create a test archive entry with sensible defaults.

    Args:
        entry_id: Unique entry ID (timestamp format)
        project: Project name
        tags: Optional list of tags (defaults to empty list)
        notes: Optional notes string
        trigger: Trigger type (manual, build, skill)
        screenshots: Optional list of screenshot filenames
        build_run_id: Optional build run identifier
        repo_commits: Optional dict of repo -> commit hash

    Returns:
        Configured ArchiveEntry instance
    """
    return ArchiveEntry(
        entry_id=entry_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        project=project,
        tags=tags or [],
        notes=notes,
        trigger=trigger,
        screenshots=screenshots or [],
        build_run_id=build_run_id,
        repo_commits=repo_commits,
    )


def _create_test_archive(
    archive_dir: Path,
    entries: list[ArchiveEntry],
) -> tuple[Path, ArchiveIndex]:
    """Create an archive index with the given entries.

    Args:
        archive_dir: Directory to save the index
        entries: List of entries to add

    Returns:
        Tuple of (index_path, index)
    """
    index = ArchiveIndex()
    for entry in entries:
        index.add_entry(entry)

    index_path = archive_dir / "archive_index.json"
    index.save(index_path)
    return index_path, index


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for test tiers."""
    config.addinivalue_line(
        "markers",
        "evergreen: tests that always run, never skip (production tests)"
    )
    config.addinivalue_line(
        "markers",
        "dev: development/WIP tests, toggle-able for active development"
    )
    config.addinivalue_line(
        "markers",
        "temporary: tests with explicit discard flag"
    )
    config.addinivalue_line(
        "markers",
        "interactive: tests requiring browser automation (Playwright)"
    )


@pytest.fixture
def temp_archive_dir() -> Generator[Path, None, None]:
    """Create a temporary archive directory for testing.

    Yields the path to the temp directory, then cleans up after the test.
    """
    with tempfile.TemporaryDirectory(prefix="sbs_test_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_archive_index(temp_archive_dir: Path) -> tuple[Path, ArchiveIndex]:
    """Create a temporary archive_index.json with an empty index.

    Returns (index_path, index) tuple.
    """
    index = ArchiveIndex()
    index_path = temp_archive_dir / "archive_index.json"
    index.save(index_path)
    return index_path, index


@pytest.fixture
def temp_archive_entry(temp_archive_dir: Path) -> tuple[Path, ArchiveEntry, ArchiveIndex]:
    """Create a temporary archive with a single entry.

    Returns (index_path, entry, index) tuple.
    """
    entry = _create_test_entry(
        entry_id="1700000000",
        project="TestProject",
        build_run_id="build_123",
        screenshots=["dashboard.png", "dep_graph.png"],
        repo_commits={"SBS-Test": "abc123def"},
    )
    index_path, index = _create_test_archive(temp_archive_dir, [entry])
    return index_path, entry, index


@pytest.fixture
def archive_with_multiple_entries(temp_archive_dir: Path) -> tuple[Path, list[ArchiveEntry], ArchiveIndex]:
    """Create a temporary archive with multiple entries for list testing.

    Returns (index_path, entries, index) tuple.
    """
    entries = [
        _create_test_entry(entry_id, project, tags, notes)
        for entry_id, project, tags, notes in MULTI_ENTRY_TEST_DATA
    ]
    index_path, index = _create_test_archive(temp_archive_dir, entries)
    return index_path, entries, index


@pytest.fixture
def mock_archive_dir(temp_archive_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Monkeypatch ARCHIVE_DIR to point to temp directory.

    This allows CLI commands to use the temp directory instead of the real archive.
    Returns the temp directory path.
    """
    from sbs.core import utils
    monkeypatch.setattr(utils, "ARCHIVE_DIR", temp_archive_dir)
    return temp_archive_dir


class CLIRunner:
    """Helper class to run CLI commands in-process with captured output."""

    def __init__(self, archive_dir: Path, monkeypatch: pytest.MonkeyPatch):
        self.archive_dir = archive_dir
        self.monkeypatch = monkeypatch
        # Patch ARCHIVE_DIR in both utils AND archive.cmd (since it imports directly)
        from sbs.core import utils
        from sbs.archive import cmd as archive_cmd
        monkeypatch.setattr(utils, "ARCHIVE_DIR", archive_dir)
        monkeypatch.setattr(archive_cmd, "ARCHIVE_DIR", archive_dir)

    def run(self, args: list[str]) -> "CLIResult":
        """Run CLI with given args and return result.

        Args:
            args: Command line arguments (without 'sbs' prefix)

        Returns:
            CLIResult with return code and captured output
        """
        from sbs.cli import main

        stdout_capture = io.StringIO()

        with redirect_stdout(stdout_capture):
            try:
                returncode = main(args)
            except SystemExit as e:
                returncode = e.code if isinstance(e.code, int) else 1

        return CLIResult(
            returncode=returncode or 0,
            stdout=stdout_capture.getvalue(),
        )


class CLIResult:
    """Result of running a CLI command."""

    def __init__(self, returncode: int, stdout: str):
        self.returncode = returncode
        self.stdout = stdout

    def __repr__(self) -> str:
        return f"CLIResult(returncode={self.returncode}, stdout={self.stdout[:100]!r}...)"


@pytest.fixture
def cli_runner(temp_archive_dir: Path, monkeypatch: pytest.MonkeyPatch) -> CLIRunner:
    """Create a CLI runner with mocked archive directory.

    The runner patches ARCHIVE_DIR to use a temp directory, allowing
    isolated testing of archive commands.
    """
    return CLIRunner(temp_archive_dir, monkeypatch)


@pytest.fixture
def cli_with_entry(temp_archive_dir: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[CLIRunner, ArchiveEntry]:
    """Create a CLI runner with a pre-existing archive entry.

    Returns (runner, entry) tuple.
    """
    entry = _create_test_entry(
        entry_id="1700000000",
        project="TestProject",
        build_run_id="build_123",
        screenshots=["dashboard.png", "dep_graph.png"],
        repo_commits={"SBS-Test": "abc123def"},
    )
    _create_test_archive(temp_archive_dir, [entry])

    runner = CLIRunner(temp_archive_dir, monkeypatch)
    return runner, entry


@pytest.fixture
def cli_with_entries(temp_archive_dir: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[CLIRunner, list[ArchiveEntry]]:
    """Create a CLI runner with multiple pre-existing archive entries.

    Returns (runner, entries) tuple.
    """
    entries = [
        _create_test_entry(entry_id, project, tags, notes)
        for entry_id, project, tags, notes in MULTI_ENTRY_TEST_DATA
    ]
    _create_test_archive(temp_archive_dir, entries)

    runner = CLIRunner(temp_archive_dir, monkeypatch)
    return runner, entries
