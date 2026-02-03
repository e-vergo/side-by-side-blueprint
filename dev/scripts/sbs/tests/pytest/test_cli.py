"""
T1: CLI Archive Commands Execute Without Error

Category: (Functional, Deterministic, Binary)

Tests that CLI archive commands execute without error and produce expected
side effects. This is a functional test verifying the CLI interface works
correctly.

Pass condition: All commands return exit code 0 and produce expected modifications.
"""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from sbs.archive.entry import ArchiveEntry, ArchiveIndex
from .conftest import CLIRunner


# ---------------------------------------------------------------------------
# CLI Assertion Helpers
# ---------------------------------------------------------------------------


def assert_cli_success(result: CompletedProcess[str], msg: str = "") -> None:
    """Assert CLI command succeeded (returncode 0).

    Args:
        result: CompletedProcess from subprocess.run
        msg: Optional context for failure message
    """
    assert result.returncode == 0, (
        f"{msg + ': ' if msg else ''}Command failed with returncode {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def assert_cli_failure(result: CompletedProcess[str], msg: str = "") -> None:
    """Assert CLI command failed (returncode != 0).

    Args:
        result: CompletedProcess from subprocess.run
        msg: Optional context for failure message
    """
    assert result.returncode != 0, (
        f"{msg + ': ' if msg else ''}Command should have failed but returned 0\n"
        f"stdout: {result.stdout}"
    )


def assert_cli_contains(result: CompletedProcess[str], text: str, msg: str = "") -> None:
    """Assert CLI output contains expected text.

    Args:
        result: CompletedProcess from subprocess.run
        text: Text to find in stdout
        msg: Optional context for failure message
    """
    assert text in result.stdout, (
        f"{msg + ': ' if msg else ''}Expected '{text}' in output\n"
        f"stdout: {result.stdout}"
    )


def assert_cli_not_contains(result: CompletedProcess[str], text: str, msg: str = "") -> None:
    """Assert CLI output does not contain text.

    Args:
        result: CompletedProcess from subprocess.run
        text: Text that should not appear in stdout
        msg: Optional context for failure message
    """
    assert text not in result.stdout, (
        f"{msg + ': ' if msg else ''}Unexpected '{text}' in output\n"
        f"stdout: {result.stdout}"
    )


# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------


@pytest.mark.evergreen
class TestArchiveCLI:
    """Test suite for archive CLI commands."""

    def test_archive_tag_adds_tag(
        self,
        cli_with_entry: tuple[CLIRunner, ArchiveEntry],
    ) -> None:
        """Run 'sbs archive tag <id> test-tag' and verify tag appears.

        Verifies:
        - Command exits with code 0
        - Tag is added to entry in archive_index.json
        - Tag appears in by_tag index
        """
        runner, entry = cli_with_entry
        entry_id = entry.entry_id

        # Run CLI command
        result = runner.run(["archive", "tag", entry_id, "test-tag", "another-tag"])

        # Assert command succeeded
        assert_cli_success(result, "archive tag command")

        # Reload index and verify tags were added
        index_path = runner.archive_dir / "archive_index.json"
        updated_index = ArchiveIndex.load(index_path)
        updated_entry = updated_index.entries.get(entry_id)

        assert updated_entry is not None, f"Entry {entry_id} not found after tag command"
        assert "test-tag" in updated_entry.tags, "test-tag not found in entry tags"
        assert "another-tag" in updated_entry.tags, "another-tag not found in entry tags"

        # Verify by_tag index was updated
        assert "test-tag" in updated_index.by_tag, "test-tag not in by_tag index"
        assert entry_id in updated_index.by_tag["test-tag"], "entry_id not in by_tag[test-tag]"

    def test_archive_tag_duplicate_tag_is_idempotent(
        self,
        cli_with_entry: tuple[CLIRunner, ArchiveEntry],
    ) -> None:
        """Running tag command twice with same tag should be idempotent.

        Verifies:
        - Command exits with code 0 both times
        - Tag only appears once in entry
        """
        runner, entry = cli_with_entry
        entry_id = entry.entry_id

        # Run tag command twice
        for _ in range(2):
            result = runner.run(["archive", "tag", entry_id, "duplicate-tag"])
            assert_cli_success(result)

        # Verify tag only appears once
        index_path = runner.archive_dir / "archive_index.json"
        updated_index = ArchiveIndex.load(index_path)
        updated_entry = updated_index.entries.get(entry_id)
        assert updated_entry is not None
        assert updated_entry.tags.count("duplicate-tag") == 1

    def test_archive_tag_nonexistent_entry_fails(
        self,
        cli_with_entry: tuple[CLIRunner, ArchiveEntry],
    ) -> None:
        """Running tag command on nonexistent entry should fail.

        Verifies:
        - Command exits with non-zero code
        - Error message mentions entry not found
        """
        runner, _ = cli_with_entry

        result = runner.run(["archive", "tag", "9999999999", "some-tag"])

        assert_cli_failure(result, "tagging nonexistent entry")
        assert "not found" in result.stdout.lower()

    def test_archive_note_adds_note(
        self,
        cli_with_entry: tuple[CLIRunner, ArchiveEntry],
    ) -> None:
        """Run 'sbs archive note <id> "test note"' and verify note appears.

        Verifies:
        - Command exits with code 0
        - Note is set on entry in archive_index.json
        """
        runner, entry = cli_with_entry
        entry_id = entry.entry_id

        result = runner.run(["archive", "note", entry_id, "This is a test note"])

        assert_cli_success(result, "archive note command")

        # Reload index and verify note was added
        index_path = runner.archive_dir / "archive_index.json"
        updated_index = ArchiveIndex.load(index_path)
        updated_entry = updated_index.entries.get(entry_id)

        assert updated_entry is not None
        assert updated_entry.notes == "This is a test note"

    def test_archive_note_overwrites_existing_note(
        self,
        cli_with_entry: tuple[CLIRunner, ArchiveEntry],
    ) -> None:
        """Running note command should overwrite existing note.

        Verifies:
        - New note replaces old note
        - Only one note exists (not appended)
        """
        runner, entry = cli_with_entry
        entry_id = entry.entry_id

        # Set initial note
        result1 = runner.run(["archive", "note", entry_id, "First note"])
        assert_cli_success(result1, "first note")

        # Overwrite with second note
        result2 = runner.run(["archive", "note", entry_id, "Second note"])
        assert_cli_success(result2, "second note")

        index_path = runner.archive_dir / "archive_index.json"
        updated_index = ArchiveIndex.load(index_path)
        updated_entry = updated_index.entries.get(entry_id)
        assert updated_entry is not None
        assert updated_entry.notes == "Second note"
        assert "First note" not in updated_entry.notes

    def test_archive_note_nonexistent_entry_fails(
        self,
        cli_with_entry: tuple[CLIRunner, ArchiveEntry],
    ) -> None:
        """Running note command on nonexistent entry should fail."""
        runner, _ = cli_with_entry

        result = runner.run(["archive", "note", "9999999999", "some note"])

        assert_cli_failure(result, "noting nonexistent entry")

    def test_archive_list_returns_entries(
        self,
        cli_with_entries: tuple[CLIRunner, list[ArchiveEntry]],
    ) -> None:
        """Run 'sbs archive list' and verify output contains entries.

        Verifies:
        - Command exits with code 0
        - Output contains entry IDs
        - Output contains project names
        """
        runner, entries = cli_with_entries

        result = runner.run(["archive", "list"])

        assert_cli_success(result, "archive list command")

        # Verify all entries appear in output
        for entry in entries:
            assert_cli_contains(result, entry.entry_id, f"entry {entry.entry_id}")
            assert_cli_contains(result, entry.project, f"project {entry.project}")

    def test_archive_list_filter_by_project(
        self,
        cli_with_entries: tuple[CLIRunner, list[ArchiveEntry]],
    ) -> None:
        """Run 'sbs archive list --project ProjectA' and verify filtering.

        Verifies:
        - Only ProjectA entries appear
        - ProjectB and ProjectC entries do not appear
        """
        runner, _ = cli_with_entries

        result = runner.run(["archive", "list", "--project", "ProjectA"])

        assert_cli_success(result)

        # ProjectA entries should appear
        assert_cli_contains(result, "1700000001", "ProjectA entry 1")
        assert_cli_contains(result, "1700000003", "ProjectA entry 2")

        # Other project entries should not appear
        assert_cli_not_contains(result, "1700000002", "ProjectB filtered out")
        assert_cli_not_contains(result, "1700000004", "ProjectC filtered out")

    def test_archive_list_filter_by_tag(
        self,
        cli_with_entries: tuple[CLIRunner, list[ArchiveEntry]],
    ) -> None:
        """Run 'sbs archive list --tag release' and verify filtering.

        Verifies:
        - Only entries with 'release' tag appear
        """
        runner, _ = cli_with_entries

        result = runner.run(["archive", "list", "--tag", "release"])

        assert_cli_success(result)

        # Only the entry with 'release' tag should appear
        assert_cli_contains(result, "1700000001", "release-tagged entry")

        # Entries without 'release' tag should not appear
        assert_cli_not_contains(result, "1700000002", "non-release entry")
        assert_cli_not_contains(result, "1700000003", "non-release entry")
        assert_cli_not_contains(result, "1700000004", "non-release entry")

    def test_archive_list_empty_archive(
        self,
        cli_runner: CLIRunner,
    ) -> None:
        """Run 'sbs archive list' with empty archive.

        Verifies:
        - Command exits with code 0 (not an error)
        - Output indicates no entries
        """
        # Create an empty archive_index.json
        index = ArchiveIndex()
        index_path = cli_runner.archive_dir / "archive_index.json"
        index.save(index_path)

        result = cli_runner.run(["archive", "list"])

        assert_cli_success(result)
        # Should indicate no entries found (case insensitive check)
        assert "no entries" in result.stdout.lower()

    def test_archive_show_displays_entry(
        self,
        cli_with_entry: tuple[CLIRunner, ArchiveEntry],
    ) -> None:
        """Run 'sbs archive show <id>' and verify output contains entry data.

        Verifies:
        - Command exits with code 0
        - Output contains entry ID
        - Output contains project name
        - Output contains screenshots count
        """
        runner, entry = cli_with_entry
        entry_id = entry.entry_id

        result = runner.run(["archive", "show", entry_id])

        assert_cli_success(result, "archive show command")

        # Verify key fields appear in output
        assert_cli_contains(result, entry_id, "entry ID")
        assert_cli_contains(result, "TestProject", "project name")
        assert_cli_contains(result, "Screenshots", "screenshots label")
        assert_cli_contains(result, "2", "screenshot count")

    def test_archive_show_with_tags_and_notes(
        self,
        cli_with_entry: tuple[CLIRunner, ArchiveEntry],
    ) -> None:
        """Show command should display tags and notes if present."""
        runner, entry = cli_with_entry
        entry_id = entry.entry_id

        # Add tag and note first
        result1 = runner.run(["archive", "tag", entry_id, "show-test-tag"])
        assert_cli_success(result1, "adding tag")

        result2 = runner.run(["archive", "note", entry_id, "Show test note"])
        assert_cli_success(result2, "adding note")

        # Now show the entry
        result = runner.run(["archive", "show", entry_id])

        assert_cli_success(result)
        assert_cli_contains(result, "show-test-tag", "tag in show output")
        assert_cli_contains(result, "Show test note", "note in show output")

    def test_archive_show_nonexistent_entry_fails(
        self,
        cli_with_entry: tuple[CLIRunner, ArchiveEntry],
    ) -> None:
        """Running show command on nonexistent entry should fail."""
        runner, _ = cli_with_entry

        result = runner.run(["archive", "show", "9999999999"])

        assert_cli_failure(result, "showing nonexistent entry")

    def test_archive_no_subcommand_shows_error(
        self,
        cli_runner: CLIRunner,
    ) -> None:
        """Running 'sbs archive' without subcommand should show error.

        Verifies:
        - Command exits with non-zero code
        - Output mentions subcommand
        """
        result = cli_runner.run(["archive"])

        assert_cli_failure(result, "missing subcommand")
        # Should mention missing subcommand
        assert "subcommand" in result.stdout.lower()
