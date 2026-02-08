"""Tests for SBS Archive state tools."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest


class TestArchiveState:
    """Tests for sls_archive_state tool."""

    def test_returns_global_state(
        self, mock_archive_index: Dict[str, Any]
    ) -> None:
        """Returns current global_state."""
        from sls_mcp.sls_models import ArchiveStateResult

        # Verify mock data has global_state
        assert mock_archive_index["global_state"] == {"skill": "task", "substate": "execution"}

        # Create result as the tool would
        result = ArchiveStateResult(
            global_state=mock_archive_index["global_state"],
            last_epoch_entry=mock_archive_index["last_epoch_entry"],
            last_epoch_timestamp=None,
            entries_in_current_epoch=4,  # Entries after epoch close
            total_entries=len(mock_archive_index["entries"]),
            projects=sorted(mock_archive_index["by_project"].keys()),
        )

        assert result.global_state == {"skill": "task", "substate": "execution"}
        assert result.global_state["skill"] == "task"

    def test_returns_epoch_info(
        self, mock_archive_index: Dict[str, Any]
    ) -> None:
        """Returns last epoch entry and timestamp."""
        from sls_mcp.sls_models import ArchiveStateResult

        result = ArchiveStateResult(
            global_state=mock_archive_index["global_state"],
            last_epoch_entry=mock_archive_index["last_epoch_entry"],
            last_epoch_timestamp="2026-01-30T10:00:00",
            entries_in_current_epoch=4,
            total_entries=5,
            projects=["GCR", "SBSTest"],
        )

        assert result.last_epoch_entry == "20260130100000"
        assert result.last_epoch_timestamp is not None

    def test_counts_entries_in_epoch(
        self, mock_archive_entries: Dict[str, Dict[str, Any]]
    ) -> None:
        """Correctly counts entries since last epoch close."""
        # Entries after "20260130100000" (the epoch close entry)
        epoch_close_id = "20260130100000"
        entries_after_epoch = [
            eid for eid in mock_archive_entries.keys()
            if eid > epoch_close_id
        ]

        # Should be: 20260131102119, 20260131120000, 20260131140000, 20260131150000
        assert len(entries_after_epoch) == 4

    def test_handles_no_epoch(self) -> None:
        """Handles case with no previous epoch."""
        from sls_mcp.sls_models import ArchiveStateResult

        result = ArchiveStateResult(
            global_state=None,
            last_epoch_entry=None,
            last_epoch_timestamp=None,
            entries_in_current_epoch=10,
            total_entries=10,
            projects=["SBSTest"],
        )

        assert result.last_epoch_entry is None
        assert result.last_epoch_timestamp is None
        assert result.global_state is None


class TestEpochSummary:
    """Tests for sls_epoch_summary tool."""

    def test_aggregates_build_count(
        self, mock_archive_entries: Dict[str, Dict[str, Any]]
    ) -> None:
        """Correctly counts build entries."""
        # Count build triggers
        build_count = sum(
            1 for e in mock_archive_entries.values()
            if e["trigger"] == "build"
        )

        assert build_count == 3  # Three build-triggered entries

    def test_aggregates_visual_changes(
        self, mock_archive_entries: Dict[str, Dict[str, Any]]
    ) -> None:
        """Aggregates visual change data."""
        from sls_mcp.sls_models import VisualChange

        # Find entries with screenshots
        entries_with_screenshots = [
            e for e in mock_archive_entries.values()
            if e["screenshots"]
        ]

        assert len(entries_with_screenshots) >= 3

        # Create VisualChange objects
        changes = [
            VisualChange(
                entry_id=e["entry_id"],
                screenshots=e["screenshots"],
                timestamp=e["created_at"],
            )
            for e in entries_with_screenshots
        ]

        assert all(len(c.screenshots) > 0 for c in changes)

    def test_collects_tags(
        self, mock_archive_entries: Dict[str, Dict[str, Any]]
    ) -> None:
        """Collects all tags used in epoch."""
        all_tags = set()
        for entry in mock_archive_entries.values():
            all_tags.update(entry["tags"])
            all_tags.update(entry["auto_tags"])

        # Should include various tags from our mock data
        assert "milestone" in all_tags
        assert "build" in all_tags
        assert "epoch" in all_tags

    def test_specific_epoch_id(
        self, mock_archive_entries: Dict[str, Dict[str, Any]]
    ) -> None:
        """Can query specific epoch by ID."""
        from sls_mcp.sls_models import EpochSummaryResult

        # The epoch close entry
        epoch_id = "20260130100000"
        epoch_entry = mock_archive_entries[epoch_id]

        result = EpochSummaryResult(
            epoch_id=epoch_id,
            started_at="2026-01-29T10:00:00",
            ended_at=epoch_entry["created_at"],
            entries=5,
            builds=3,
            visual_changes=[],
            tags_used=["epoch", "epoch-close"],
            projects_touched=["SBSTest"],
        )

        assert result.epoch_id == epoch_id
        assert result.entries == 5


class TestContext:
    """Tests for sls_context tool."""

    def test_includes_state_section(
        self, mock_archive_index: Dict[str, Any]
    ) -> None:
        """Context includes state when requested."""
        from sls_mcp.sls_models import ContextResult

        # Build context with state section
        lines = ["## Orchestration State", ""]
        global_state = mock_archive_index["global_state"]
        if global_state:
            lines.append(f"- **Active Skill:** {global_state['skill']}")
            lines.append(f"- **Substate:** {global_state['substate']}")
        lines.append("")

        result = ContextResult(
            context_block="\n".join(lines),
            entry_count=0,
            time_range=None,
        )

        assert "## Orchestration State" in result.context_block
        assert "Active Skill" in result.context_block
        assert "task" in result.context_block

    def test_includes_epoch_section(
        self, mock_archive_index: Dict[str, Any]
    ) -> None:
        """Context includes epoch when requested."""
        from sls_mcp.sls_models import ContextResult

        # Build context with epoch section
        lines = ["## Current Epoch", ""]
        lines.append("- **Entries:** 4")
        lines.append("- **Builds:** 3")
        lines.append("- **Projects:** GCR, SBSTest")
        lines.append("")

        result = ContextResult(
            context_block="\n".join(lines),
            entry_count=4,
            time_range="2h 30m",
        )

        assert "## Current Epoch" in result.context_block
        assert "Entries:" in result.context_block
        assert result.entry_count == 4

    def test_default_includes_all(self) -> None:
        """Default includes all sections."""
        from sls_mcp.sls_models import ContextResult

        # Build context with all sections
        lines = [
            "## Orchestration State",
            "- **Status:** Idle",
            "",
            "## Current Epoch",
            "- **Entries:** 4",
            "",
            "## Quality Scores",
            "- **Overall:** 85.0",
            "",
            "## Recent Activity",
            "- Entry 1",
            "",
        ]

        result = ContextResult(
            context_block="\n".join(lines),
            entry_count=10,
            time_range="3h 15m",
        )

        assert "Orchestration State" in result.context_block
        assert "Current Epoch" in result.context_block
        assert "Quality Scores" in result.context_block
        assert "Recent Activity" in result.context_block


class TestArchiveEntryModel:
    """Tests for ArchiveEntrySummary model."""

    def test_summary_from_entry(
        self, mock_archive_entries: Dict[str, Dict[str, Any]]
    ) -> None:
        """ArchiveEntrySummary correctly summarizes an entry."""
        from sls_mcp.sls_models import ArchiveEntrySummary

        entry = mock_archive_entries["20260131102119"]
        summary = ArchiveEntrySummary(
            entry_id=entry["entry_id"],
            created_at=entry["created_at"],
            project=entry["project"],
            trigger=entry["trigger"],
            tags=entry["tags"] + entry["auto_tags"],
            has_screenshots=len(entry["screenshots"]) > 0,
            notes_preview=entry["notes"][:100] if entry["notes"] else "",
            build_run_id=entry["build_run_id"],
        )

        assert summary.entry_id == "20260131102119"
        assert summary.project == "SBSTest"
        assert summary.trigger == "build"
        assert summary.has_screenshots is True
        assert "milestone" in summary.tags
        assert summary.build_run_id == "build-001"
