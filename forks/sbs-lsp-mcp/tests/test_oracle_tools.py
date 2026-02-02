"""Tests for SBS Oracle tools."""

from typing import Any, Dict
from unittest.mock import patch

import pytest


class TestOracleQuery:
    """Tests for sbs_oracle_query tool."""

    def test_query_returns_file_matches(
        self, mock_oracle_content: str, mock_parsed_oracle: Dict[str, Any]
    ) -> None:
        """Query should return file matches for path-like queries."""
        # Import here to avoid import errors if SBS modules not available
        from sbs_lsp_mcp.sbs_utils import parse_oracle_sections, search_oracle

        sections = parse_oracle_sections(mock_oracle_content)
        results = search_oracle(sections, "Layout.lean", max_results=5)

        # Should find Dress/Graph/Layout.lean
        file_results = [r for r in results if r["file"]]
        assert len(file_results) >= 1
        assert any("Layout.lean" in r["file"] for r in file_results)

    def test_query_returns_concept_matches(
        self, mock_oracle_content: str
    ) -> None:
        """Query should return concept matches for concept names."""
        from sbs_lsp_mcp.sbs_utils import parse_oracle_sections, search_oracle

        sections = parse_oracle_sections(mock_oracle_content)
        results = search_oracle(sections, "Sugiyama", max_results=5)

        # Should find Sugiyama layout concept
        assert len(results) >= 1
        # Either as a file match or concept match (case insensitive check)
        found_sugiyama = any(
            "sugiyama" in (r.get("context", "") or r.get("file", "")).lower()
            for r in results
        )
        assert found_sugiyama, f"Should find Sugiyama in results: {results}"

    def test_query_empty_returns_empty(self) -> None:
        """Empty query returns empty results."""
        from sbs_lsp_mcp.sbs_utils import search_oracle

        sections = {"file_map": {}, "concept_index": [], "sections": {}}
        results = search_oracle(sections, "", max_results=5)

        assert results == []

    def test_query_fuzzy_matching(
        self, mock_oracle_content: str
    ) -> None:
        """Fuzzy matching works for partial terms."""
        from sbs_lsp_mcp.sbs_utils import parse_oracle_sections, search_oracle

        sections = parse_oracle_sections(mock_oracle_content)
        # Query with partial word
        results = search_oracle(sections, "graph", max_results=10)

        # Should find graph-related items
        assert len(results) >= 1
        found_graph = any(
            "graph" in (r.get("context", "").lower() or r.get("file", "").lower())
            for r in results
        )
        assert found_graph, f"Should find graph in results: {results}"

    def test_query_case_insensitive(
        self, mock_oracle_content: str
    ) -> None:
        """Query is case insensitive."""
        from sbs_lsp_mcp.sbs_utils import parse_oracle_sections, search_oracle

        sections = parse_oracle_sections(mock_oracle_content)

        # Query with different cases
        results_lower = search_oracle(sections, "layout", max_results=5)
        results_upper = search_oracle(sections, "LAYOUT", max_results=5)
        results_mixed = search_oracle(sections, "Layout", max_results=5)

        # All should return similar results
        assert len(results_lower) == len(results_upper)
        assert len(results_lower) == len(results_mixed)


class TestOracleQueryResult:
    """Tests for OracleQueryResult model."""

    def test_empty_result_structure(self) -> None:
        """Empty result should have correct structure."""
        from sbs_lsp_mcp.sbs_models import OracleQueryResult

        result = OracleQueryResult(matches=[], concepts=[], raw_section=None)

        assert result.matches == []
        assert result.concepts == []
        assert result.raw_section is None

    def test_result_with_matches(self) -> None:
        """Result with matches should serialize correctly."""
        from sbs_lsp_mcp.sbs_models import OracleConcept, OracleMatch, OracleQueryResult

        result = OracleQueryResult(
            matches=[
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

        assert len(result.matches) == 1
        assert result.matches[0].file == "Dress/Graph/Layout.lean"
        assert result.matches[0].relevance == 0.9
        assert len(result.concepts) == 1
        assert result.concepts[0].name == "Sugiyama"
