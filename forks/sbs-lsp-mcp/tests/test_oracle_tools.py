"""Tests for SBS Oracle tools (ask_oracle via DuckDB)."""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from sbs_lsp_mcp.sbs_models import AskOracleResult, OracleConcept, OracleMatch


class TestAskOracleResult:
    """Tests for AskOracleResult model."""

    def test_empty_result_structure(self) -> None:
        """Empty result should have correct structure."""
        result = AskOracleResult(
            file_matches=[], concepts=[], raw_section=None
        )

        assert result.file_matches == []
        assert result.concepts == []
        assert result.raw_section is None
        assert result.archive_context is None
        assert result.quality_snapshot is None
        assert result.related_issues is None

    def test_result_with_file_matches(self) -> None:
        """Result with file matches serializes correctly."""
        result = AskOracleResult(
            file_matches=[
                OracleMatch(
                    file="Dress/Graph/Layout.lean",
                    lines="10-50",
                    context="Sugiyama layout algorithm",
                    relevance=0.9,
                )
            ],
            concepts=[OracleConcept(name="Sugiyama", section="Concepts")],
            raw_section="## Concepts\nSugiyama layout...",
        )

        assert len(result.file_matches) == 1
        assert result.file_matches[0].file == "Dress/Graph/Layout.lean"
        assert result.file_matches[0].relevance == 0.9
        assert len(result.concepts) == 1
        assert result.concepts[0].name == "Sugiyama"

    def test_result_with_archive_context(self) -> None:
        """Result with archive context includes project activity."""
        result = AskOracleResult(
            file_matches=[],
            concepts=[],
            archive_context={
                "recent_entries": 5,
                "projects_touched": ["SBSTest", "GCR"],
            },
        )

        assert result.archive_context is not None
        assert result.archive_context["recent_entries"] == 5

    def test_result_with_quality_snapshot(self) -> None:
        """Result with quality snapshot includes scores."""
        result = AskOracleResult(
            file_matches=[],
            concepts=[],
            quality_snapshot={
                "overall": 85.0,
                "T5": {"value": 100.0, "passed": True},
            },
        )

        assert result.quality_snapshot is not None
        assert result.quality_snapshot["overall"] == 85.0

    def test_result_with_related_issues(self) -> None:
        """Result with related issues includes issue data."""
        result = AskOracleResult(
            file_matches=[],
            concepts=[],
            related_issues=[
                {"number": 42, "title": "Fix graph layout", "state": "open"},
                {"number": 43, "title": "Status color mismatch", "state": "closed"},
            ],
        )

        assert result.related_issues is not None
        assert len(result.related_issues) == 2
        assert result.related_issues[0]["number"] == 42

    def test_full_result(self) -> None:
        """Full result with all fields populated."""
        result = AskOracleResult(
            file_matches=[
                OracleMatch(
                    file="Dress/Graph/Layout.lean",
                    context="Graph layout algorithm",
                    relevance=0.95,
                )
            ],
            concepts=[
                OracleConcept(name="Sugiyama layout", section="Concepts"),
            ],
            archive_context={"recent_entries": 3},
            quality_snapshot={"overall": 90.0},
            related_issues=[{"number": 10, "title": "Test", "state": "open"}],
            raw_section="## Architecture\n...",
        )

        assert len(result.file_matches) == 1
        assert len(result.concepts) == 1
        assert result.archive_context is not None
        assert result.quality_snapshot is not None
        assert result.related_issues is not None
        assert result.raw_section is not None


class TestOracleMatchModel:
    """Tests for OracleMatch model validation."""

    def test_match_without_lines(self) -> None:
        """Match without line range is valid."""
        match = OracleMatch(
            file="some/file.lean",
            context="Description",
            relevance=0.5,
        )
        assert match.lines is None

    def test_match_with_lines(self) -> None:
        """Match with line range stores correctly."""
        match = OracleMatch(
            file="some/file.lean",
            lines="10-50",
            context="Description",
            relevance=0.8,
        )
        assert match.lines == "10-50"


class TestOracleConceptModel:
    """Tests for OracleConcept model."""

    def test_concept_creation(self) -> None:
        """Concept creates with required fields."""
        concept = OracleConcept(name="Sugiyama", section="Concepts")
        assert concept.name == "Sugiyama"
        assert concept.section == "Concepts"


class TestLegacyOracleQueryResult:
    """Tests for the legacy OracleQueryResult model (still in sbs_models)."""

    def test_legacy_model_exists(self) -> None:
        """OracleQueryResult still exists for backward compatibility."""
        from sbs_lsp_mcp.sbs_models import OracleQueryResult

        result = OracleQueryResult(matches=[], concepts=[], raw_section=None)
        assert result.matches == []
        assert result.concepts == []
        assert result.raw_section is None
