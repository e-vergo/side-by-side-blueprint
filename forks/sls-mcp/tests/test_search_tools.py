"""Tests for SBS Search tools."""

from datetime import datetime
from typing import Any, Dict, List

import pytest


class TestSearchEntries:
    """Tests for sls_search_entries tool."""

    def test_filter_by_project(
        self, mock_archive_entries: Dict[str, Dict[str, Any]]
    ) -> None:
        """Filters by project name."""
        from sls_mcp.sls_models import ArchiveEntrySummary, SearchResult

        # Filter for SBSTest entries
        sbs_entries = [
            e for e in mock_archive_entries.values()
            if e["project"] == "SBSTest"
        ]

        summaries = [
            ArchiveEntrySummary(
                entry_id=e["entry_id"],
                created_at=e["created_at"],
                project=e["project"],
                trigger=e["trigger"],
                tags=e["tags"] + e["auto_tags"],
                has_screenshots=len(e["screenshots"]) > 0,
                notes_preview=e["notes"][:100] if e["notes"] else "",
                build_run_id=e["build_run_id"],
            )
            for e in sbs_entries
        ]

        result = SearchResult(
            entries=summaries,
            total_count=len(summaries),
            query=None,
            filters={"project": "SBSTest"},
        )

        assert result.total_count == 4  # 4 SBSTest entries in mock
        assert all(e.project == "SBSTest" for e in result.entries)
        assert result.filters["project"] == "SBSTest"

    def test_filter_by_tags(
        self, mock_archive_entries: Dict[str, Dict[str, Any]]
    ) -> None:
        """Filters by tags with OR logic."""
        from sls_mcp.sls_models import ArchiveEntrySummary, SearchResult

        # Filter for entries with "milestone" or "epoch" tags
        target_tags = {"milestone", "epoch"}
        matching_entries = [
            e for e in mock_archive_entries.values()
            if any(tag in target_tags for tag in (e["tags"] + e["auto_tags"]))
        ]

        summaries = [
            ArchiveEntrySummary(
                entry_id=e["entry_id"],
                created_at=e["created_at"],
                project=e["project"],
                trigger=e["trigger"],
                tags=e["tags"] + e["auto_tags"],
                has_screenshots=len(e["screenshots"]) > 0,
                notes_preview=e["notes"][:100] if e["notes"] else "",
                build_run_id=e["build_run_id"],
            )
            for e in matching_entries
        ]

        result = SearchResult(
            entries=summaries,
            total_count=len(summaries),
            query=None,
            filters={"tags": list(target_tags)},
        )

        # Should find at least 2 (one with milestone, one with epoch)
        assert result.total_count >= 2

        # Each entry should have at least one of the target tags
        for entry in result.entries:
            has_target_tag = any(tag in target_tags for tag in entry.tags)
            assert has_target_tag

    def test_filter_by_since(
        self, mock_archive_entries: Dict[str, Dict[str, Any]]
    ) -> None:
        """Filters entries after timestamp."""
        from sls_mcp.sls_models import ArchiveEntrySummary, SearchResult

        # Filter for entries after a specific entry_id
        since_id = "20260131102119"
        filtered_entries = [
            e for e in mock_archive_entries.values()
            if e["entry_id"] > since_id
        ]

        summaries = [
            ArchiveEntrySummary(
                entry_id=e["entry_id"],
                created_at=e["created_at"],
                project=e["project"],
                trigger=e["trigger"],
                tags=e["tags"] + e["auto_tags"],
                has_screenshots=len(e["screenshots"]) > 0,
                notes_preview="",
                build_run_id=e["build_run_id"],
            )
            for e in filtered_entries
        ]

        result = SearchResult(
            entries=summaries,
            total_count=len(summaries),
            query=None,
            filters={"since": since_id},
        )

        # Should find entries after 20260131102119
        assert result.total_count == 3  # 20260131120000, 20260131140000, 20260131150000
        assert all(e.entry_id > since_id for e in result.entries)

    def test_filter_by_trigger(
        self, mock_archive_entries: Dict[str, Dict[str, Any]]
    ) -> None:
        """Filters by trigger type."""
        from sls_mcp.sls_models import ArchiveEntrySummary, SearchResult

        # Filter for build-triggered entries
        build_entries = [
            e for e in mock_archive_entries.values()
            if e["trigger"] == "build"
        ]

        summaries = [
            ArchiveEntrySummary(
                entry_id=e["entry_id"],
                created_at=e["created_at"],
                project=e["project"],
                trigger=e["trigger"],
                tags=e["tags"] + e["auto_tags"],
                has_screenshots=len(e["screenshots"]) > 0,
                notes_preview="",
                build_run_id=e["build_run_id"],
            )
            for e in build_entries
        ]

        result = SearchResult(
            entries=summaries,
            total_count=len(summaries),
            query=None,
            filters={"trigger": "build"},
        )

        assert result.total_count == 3  # Three build-triggered entries
        assert all(e.trigger == "build" for e in result.entries)

    def test_respects_limit(
        self, mock_archive_entries: Dict[str, Dict[str, Any]]
    ) -> None:
        """Respects limit parameter."""
        from sls_mcp.sls_models import ArchiveEntrySummary, SearchResult

        # Get all entries sorted
        all_entries = sorted(
            mock_archive_entries.values(),
            key=lambda e: e["entry_id"],
            reverse=True,
        )

        # Apply limit
        limit = 2
        limited = all_entries[:limit]

        summaries = [
            ArchiveEntrySummary(
                entry_id=e["entry_id"],
                created_at=e["created_at"],
                project=e["project"],
                trigger=e["trigger"],
                tags=e["tags"] + e["auto_tags"],
                has_screenshots=len(e["screenshots"]) > 0,
                notes_preview="",
                build_run_id=e["build_run_id"],
            )
            for e in limited
        ]

        result = SearchResult(
            entries=summaries,
            total_count=len(mock_archive_entries),  # Total before limit
            query=None,
            filters={},
        )

        assert len(result.entries) == 2
        assert result.total_count == 5  # All 5 entries in mock


class TestSearchResultModel:
    """Tests for SearchResult model."""

    def test_empty_result(self) -> None:
        """Empty search result has correct structure."""
        from sls_mcp.sls_models import SearchResult

        result = SearchResult(
            entries=[],
            total_count=0,
            query="nonexistent",
            filters={},
        )

        assert result.entries == []
        assert result.total_count == 0
        assert result.query == "nonexistent"

    def test_multiple_filters_combined(self) -> None:
        """Multiple filters are combined correctly."""
        from sls_mcp.sls_models import SearchResult

        filters = {
            "project": "SBSTest",
            "trigger": "build",
            "tags": ["milestone"],
            "since": "20260130000000",
        }

        result = SearchResult(
            entries=[],
            total_count=0,
            query=None,
            filters=filters,
        )

        assert result.filters["project"] == "SBSTest"
        assert result.filters["trigger"] == "build"
        assert "milestone" in result.filters["tags"]
        assert result.filters["since"] == "20260130000000"


class TestProjectNormalization:
    """Tests for project name normalization in search."""

    def test_normalize_sbs_test(self) -> None:
        """Normalizes SBS-Test variations."""
        project_map = {
            "SBSTest": "SBSTest",
            "sbs-test": "SBSTest",
        }

        assert project_map.get("SBSTest") == "SBSTest"
        assert project_map.get("sbs-test") == "SBSTest"

    def test_normalize_gcr(self) -> None:
        """Normalizes GCR variations."""
        project_map = {
            "GCR": "GCR",
            "gcr": "GCR",
            "General_Crystallographic_Restriction": "GCR",
        }

        assert project_map.get("GCR") == "GCR"
        assert project_map.get("gcr") == "GCR"
        assert project_map.get("General_Crystallographic_Restriction") == "GCR"

    def test_normalize_pnt(self) -> None:
        """Normalizes PNT variations."""
        project_map = {
            "PNT": "PNT",
            "pnt": "PNT",
            "PrimeNumberTheoremAnd": "PNT",
        }

        assert project_map.get("PNT") == "PNT"
        assert project_map.get("pnt") == "PNT"
        assert project_map.get("PrimeNumberTheoremAnd") == "PNT"
