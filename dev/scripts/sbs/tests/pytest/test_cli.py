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

import pytest

from sbs.archive.entry import ArchiveEntry, ArchiveIndex
from .conftest import CLIRunner


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
        assert result.returncode == 0, f"Command failed with output: {result.stdout}"

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
            assert result.returncode == 0

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

        assert result.returncode != 0, "Command should fail for nonexistent entry"
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

        assert result.returncode == 0, f"Command failed with output: {result.stdout}"

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
        assert result1.returncode == 0

        # Overwrite with second note
        result2 = runner.run(["archive", "note", entry_id, "Second note"])
        assert result2.returncode == 0

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

        assert result.returncode != 0

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

        assert result.returncode == 0, f"Command failed with output: {result.stdout}"

        # Verify all entries appear in output
        for entry in entries:
            assert entry.entry_id in result.stdout, f"Entry {entry.entry_id} not in list output"
            assert entry.project in result.stdout, f"Project {entry.project} not in list output"

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

        assert result.returncode == 0

        # ProjectA entries should appear
        assert "1700000001" in result.stdout
        assert "1700000003" in result.stdout

        # Other project entries should not appear
        assert "1700000002" not in result.stdout  # ProjectB
        assert "1700000004" not in result.stdout  # ProjectC

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

        assert result.returncode == 0

        # Only the entry with 'release' tag should appear
        assert "1700000001" in result.stdout

        # Entries without 'release' tag should not appear
        assert "1700000002" not in result.stdout
        assert "1700000003" not in result.stdout
        assert "1700000004" not in result.stdout

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

        assert result.returncode == 0
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

        assert result.returncode == 0, f"Command failed with output: {result.stdout}"

        # Verify key fields appear in output
        assert entry_id in result.stdout
        assert "TestProject" in result.stdout
        assert "Screenshots" in result.stdout
        assert "2" in result.stdout  # Number of screenshots

    def test_archive_show_with_tags_and_notes(
        self,
        cli_with_entry: tuple[CLIRunner, ArchiveEntry],
    ) -> None:
        """Show command should display tags and notes if present."""
        runner, entry = cli_with_entry
        entry_id = entry.entry_id

        # Add tag and note first
        result1 = runner.run(["archive", "tag", entry_id, "show-test-tag"])
        assert result1.returncode == 0

        result2 = runner.run(["archive", "note", entry_id, "Show test note"])
        assert result2.returncode == 0

        # Now show the entry
        result = runner.run(["archive", "show", entry_id])

        assert result.returncode == 0
        assert "show-test-tag" in result.stdout
        assert "Show test note" in result.stdout

    def test_archive_show_nonexistent_entry_fails(
        self,
        cli_with_entry: tuple[CLIRunner, ArchiveEntry],
    ) -> None:
        """Running show command on nonexistent entry should fail."""
        runner, _ = cli_with_entry

        result = runner.run(["archive", "show", "9999999999"])

        assert result.returncode != 0

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

        assert result.returncode != 0
        # Should mention missing subcommand
        assert "subcommand" in result.stdout.lower()
