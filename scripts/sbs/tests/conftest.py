"""
Shared pytest fixtures for sbs CLI tests.

Provides fixtures for creating isolated test environments that don't
pollute the real archive data.
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

from ..archive.entry import ArchiveEntry, ArchiveIndex


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
    # Create an entry with a known ID
    entry_id = "1700000000"
    entry = ArchiveEntry(
        entry_id=entry_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        project="TestProject",
        build_run_id="build_123",
        notes="",
        tags=[],
        screenshots=["dashboard.png", "dep_graph.png"],
        repo_commits={"SBS-Test": "abc123def"},
    )

    # Create index and add entry
    index = ArchiveIndex()
    index.add_entry(entry)

    # Save to temp directory
    index_path = temp_archive_dir / "archive_index.json"
    index.save(index_path)

    return index_path, entry, index


@pytest.fixture
def archive_with_multiple_entries(temp_archive_dir: Path) -> tuple[Path, list[ArchiveEntry], ArchiveIndex]:
    """Create a temporary archive with multiple entries for list testing.

    Returns (index_path, entries, index) tuple.
    """
    entries = []
    index = ArchiveIndex()

    # Create entries with different projects and tags
    test_data = [
        ("1700000001", "ProjectA", ["release"], "First entry"),
        ("1700000002", "ProjectB", ["beta", "test"], "Second entry"),
        ("1700000003", "ProjectA", ["dev"], "Third entry"),
        ("1700000004", "ProjectC", [], "Fourth entry"),
    ]

    for entry_id, project, tags, notes in test_data:
        entry = ArchiveEntry(
            entry_id=entry_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            project=project,
            tags=tags,
            notes=notes,
            screenshots=[],
        )
        entries.append(entry)
        index.add_entry(entry)

    index_path = temp_archive_dir / "archive_index.json"
    index.save(index_path)

    return index_path, entries, index


@pytest.fixture
def mock_archive_dir(temp_archive_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Monkeypatch ARCHIVE_DIR to point to temp directory.

    This allows CLI commands to use the temp directory instead of the real archive.
    Returns the temp directory path.
    """
    from .. import utils
    monkeypatch.setattr(utils, "ARCHIVE_DIR", temp_archive_dir)
    return temp_archive_dir


class CLIRunner:
    """Helper class to run CLI commands in-process with captured output."""

    def __init__(self, archive_dir: Path, monkeypatch: pytest.MonkeyPatch):
        self.archive_dir = archive_dir
        self.monkeypatch = monkeypatch
        # Patch ARCHIVE_DIR in both utils AND archive_cmd (since it imports directly)
        from .. import utils
        from .. import archive_cmd
        monkeypatch.setattr(utils, "ARCHIVE_DIR", archive_dir)
        monkeypatch.setattr(archive_cmd, "ARCHIVE_DIR", archive_dir)

    def run(self, args: list[str]) -> "CLIResult":
        """Run CLI with given args and return result.

        Args:
            args: Command line arguments (without 'sbs' prefix)

        Returns:
            CLIResult with return code and captured output
        """
        from ..cli import main

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
    # Create the entry first
    entry_id = "1700000000"
    entry = ArchiveEntry(
        entry_id=entry_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        project="TestProject",
        build_run_id="build_123",
        notes="",
        tags=[],
        screenshots=["dashboard.png", "dep_graph.png"],
        repo_commits={"SBS-Test": "abc123def"},
    )

    index = ArchiveIndex()
    index.add_entry(entry)
    index_path = temp_archive_dir / "archive_index.json"
    index.save(index_path)

    runner = CLIRunner(temp_archive_dir, monkeypatch)
    return runner, entry


@pytest.fixture
def cli_with_entries(temp_archive_dir: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[CLIRunner, list[ArchiveEntry]]:
    """Create a CLI runner with multiple pre-existing archive entries.

    Returns (runner, entries) tuple.
    """
    entries = []
    index = ArchiveIndex()

    test_data = [
        ("1700000001", "ProjectA", ["release"], "First entry"),
        ("1700000002", "ProjectB", ["beta", "test"], "Second entry"),
        ("1700000003", "ProjectA", ["dev"], "Third entry"),
        ("1700000004", "ProjectC", [], "Fourth entry"),
    ]

    for entry_id, project, tags, notes in test_data:
        entry = ArchiveEntry(
            entry_id=entry_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            project=project,
            tags=tags,
            notes=notes,
            screenshots=[],
        )
        entries.append(entry)
        index.add_entry(entry)

    index_path = temp_archive_dir / "archive_index.json"
    index.save(index_path)

    runner = CLIRunner(temp_archive_dir, monkeypatch)
    return runner, entries
