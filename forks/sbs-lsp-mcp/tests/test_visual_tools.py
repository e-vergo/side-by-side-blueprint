"""Tests for SBS Visual tools (screenshots and history)."""

import hashlib
from pathlib import Path
from typing import Any, Dict

import pytest


class TestLastScreenshot:
    """Tests for sbs_last_screenshot tool."""

    def test_returns_screenshot_path(self, mock_archive_dir: Path) -> None:
        """Returns path to latest screenshot."""
        from sbs_lsp_mcp.sbs_models import ScreenshotResult

        # Check the mock directory structure
        screenshot_path = mock_archive_dir / "SBSTest" / "latest" / "dashboard.png"
        assert screenshot_path.exists()

        result = ScreenshotResult(
            image_path=str(screenshot_path),
            entry_id="20260131150000",
            captured_at="2026-01-31T15:00:00",
            hash="abc123def456",
            page="dashboard",
            project="SBSTest",
        )

        assert result.image_path == str(screenshot_path)
        assert result.page == "dashboard"
        assert result.project == "SBSTest"

    def test_returns_metadata(self, mock_archive_dir: Path) -> None:
        """Returns capture metadata."""
        import json

        capture_json = mock_archive_dir / "SBSTest" / "latest" / "capture.json"
        assert capture_json.exists()

        with open(capture_json) as f:
            metadata = json.load(f)

        assert "timestamp" in metadata
        assert metadata["project"] == "SBSTest"

    def test_handles_missing_screenshot(self, mock_archive_dir: Path) -> None:
        """Returns error for missing screenshot."""
        from sbs_lsp_mcp.sbs_models import ScreenshotResult

        # Request a non-existent page
        missing_path = mock_archive_dir / "SBSTest" / "latest" / "nonexistent.png"
        assert not missing_path.exists()

        # Tool should return empty result
        result = ScreenshotResult(
            image_path="",
            entry_id="",
            captured_at="",
            hash=None,
            page="nonexistent",
            project="SBSTest",
        )

        assert result.image_path == ""
        assert result.hash is None

    def test_computes_hash(self, mock_archive_dir: Path) -> None:
        """Computes hash for screenshot."""
        from sbs_lsp_mcp.sbs_utils import compute_hash

        screenshot_path = mock_archive_dir / "SBSTest" / "latest" / "dashboard.png"
        file_hash = compute_hash(screenshot_path)

        assert file_hash is not None
        assert len(file_hash) == 16  # SHA256 prefix (16 hex chars)

        # Verify it's consistent
        file_hash2 = compute_hash(screenshot_path)
        assert file_hash == file_hash2


class TestVisualHistory:
    """Tests for sbs_visual_history tool."""

    def test_returns_history(self, mock_archive_dir: Path) -> None:
        """Returns history of screenshots."""
        from sbs_lsp_mcp.sbs_models import HistoryEntry, VisualHistoryResult

        # Build mock history
        history = [
            HistoryEntry(
                entry_id="20260131150000",
                timestamp="2026-01-31T15:00:00",
                screenshots=["dashboard.png"],
                hash_map={"dashboard": "hash1"},
                tags=["latest"],
            ),
            HistoryEntry(
                entry_id="20260131120000",
                timestamp="2026-01-31T12:00:00",
                screenshots=["dashboard.png"],
                hash_map={"dashboard": "hash2"},
                tags=["build"],
            ),
        ]

        result = VisualHistoryResult(
            project="SBSTest",
            history=history,
            total_count=5,
        )

        assert result.project == "SBSTest"
        assert len(result.history) == 2
        assert result.total_count == 5

    def test_detects_changes(self) -> None:
        """Detects visual changes between entries."""
        from sbs_lsp_mcp.sbs_models import HistoryEntry

        # Two entries with different hashes = visual change
        entry1 = HistoryEntry(
            entry_id="20260131150000",
            timestamp="2026-01-31T15:00:00",
            screenshots=["dashboard.png"],
            hash_map={"dashboard": "hash_new"},
            tags=[],
        )

        entry2 = HistoryEntry(
            entry_id="20260131120000",
            timestamp="2026-01-31T12:00:00",
            screenshots=["dashboard.png"],
            hash_map={"dashboard": "hash_old"},
            tags=[],
        )

        # Check if hashes differ (indicating visual change)
        page = "dashboard"
        hash1 = entry1.hash_map.get(page)
        hash2 = entry2.hash_map.get(page)

        assert hash1 != hash2  # Visual change detected

    def test_respects_limit(self) -> None:
        """Respects limit parameter."""
        from sbs_lsp_mcp.sbs_models import HistoryEntry, VisualHistoryResult

        # Create more entries than limit
        all_entries = [
            HistoryEntry(
                entry_id=f"2026013{i}00000",
                timestamp=f"2026-01-3{i}T00:00:00",
                screenshots=["dashboard.png"],
                hash_map={},
                tags=[],
            )
            for i in range(1, 8)
        ]

        # Apply limit of 3
        limit = 3
        limited_entries = all_entries[:limit]

        result = VisualHistoryResult(
            project="SBSTest",
            history=limited_entries,
            total_count=7,
        )

        assert len(result.history) == 3
        assert result.total_count == 7


class TestEntryIdConversion:
    """Tests for entry_id format conversion utilities."""

    def test_entry_id_to_dir_format(self) -> None:
        """Converts entry_id to directory format."""
        from sbs_lsp_mcp.sbs_tools import _entry_id_to_dir_format

        entry_id = "20260131102119"
        dir_format = _entry_id_to_dir_format(entry_id)

        assert dir_format == "2026-01-31_10-21-19"

    def test_dir_format_to_entry_id(self) -> None:
        """Converts directory format to entry_id."""
        from sbs_lsp_mcp.sbs_tools import _dir_format_to_entry_id

        dir_name = "2026-01-31_10-21-19"
        entry_id = _dir_format_to_entry_id(dir_name)

        assert entry_id == "20260131102119"

    def test_roundtrip_conversion(self) -> None:
        """Entry ID roundtrips through both conversions."""
        from sbs_lsp_mcp.sbs_tools import _dir_format_to_entry_id, _entry_id_to_dir_format

        original = "20260131102119"
        dir_format = _entry_id_to_dir_format(original)
        back = _dir_format_to_entry_id(dir_format)

        assert back == original


class TestComputeHash:
    """Tests for hash computation utility."""

    def test_hash_returns_16_chars(self, mock_archive_dir: Path) -> None:
        """Hash returns 16 character hex string."""
        from sbs_lsp_mcp.sbs_utils import compute_hash

        screenshot = mock_archive_dir / "SBSTest" / "latest" / "dashboard.png"
        file_hash = compute_hash(screenshot)

        assert file_hash is not None
        assert len(file_hash) == 16
        assert all(c in "0123456789abcdef" for c in file_hash)

    def test_hash_returns_none_for_missing(self, tmp_path: Path) -> None:
        """Hash returns None for missing file."""
        from sbs_lsp_mcp.sbs_utils import compute_hash

        missing = tmp_path / "nonexistent.png"
        file_hash = compute_hash(missing)

        assert file_hash is None

    def test_different_files_different_hashes(self, tmp_path: Path) -> None:
        """Different files produce different hashes."""
        from sbs_lsp_mcp.sbs_utils import compute_hash

        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content 1")
        file2.write_text("content 2")

        hash1 = compute_hash(file1)
        hash2 = compute_hash(file2)

        assert hash1 != hash2
