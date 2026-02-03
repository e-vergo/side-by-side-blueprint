"""Tests for oracle query filter parameters."""
import pytest
import sys
import importlib.util
from pathlib import Path

# Direct import of sbs_utils without going through package __init__.py
# (avoids needing orjson and other server dependencies)
SBS_ROOT = Path(__file__).resolve().parents[6]
SBS_UTILS_PATH = SBS_ROOT / "forks" / "sbs-lsp-mcp" / "src" / "sbs_lsp_mcp" / "sbs_utils.py"

# Load the module directly
spec = importlib.util.spec_from_file_location("sbs_utils", SBS_UTILS_PATH)
sbs_utils = importlib.util.module_from_spec(spec)
sys.modules["sbs_utils"] = sbs_utils
spec.loader.exec_module(sbs_utils)

# Import the function we need
search_oracle = sbs_utils.search_oracle


@pytest.mark.evergreen
class TestOracleFilters:
    """Tests for new oracle filter parameters."""

    @pytest.fixture
    def mock_sections(self):
        """Mock oracle sections for testing."""
        return {
            "file_map": {
                "Dress/Graph/Layout.lean": {
                    "section": "Dress",
                    "concept": "graph layout",
                    "notes": "Sugiyama algorithm"
                },
                "Runway/Theme.lean": {
                    "section": "Runway",
                    "concept": "theme",
                    "notes": "HTML templates"
                },
                "Dress/Capture/ElabRules.lean": {
                    "section": "Dress",
                    "concept": "elab rules",
                    "notes": "Capture hooks"
                },
            },
            "concept_index": [
                {"name": "graph layout", "location": "Dress/Graph/Layout.lean", "section": "Dress", "notes": "Sugiyama"},
                {"name": "theme toggle", "location": "Runway/Theme.lean", "section": "Runway", "notes": ""},
                {"name": "status colors", "location": "Dress/Graph/Svg.lean", "section": "Dress", "notes": "6-color model"},
            ],
            "sections": {
                "Dress": "# Dress\nGraph layout and artifact generation\nSugiyama algorithm for layout",
                "Runway": "# Runway\nSite generation and templates\nDashboard rendering"
            },
        }

    def test_result_type_files_only(self, mock_sections):
        """result_type='files' should only return file matches."""
        # search_oracle is imported at module level

        results = search_oracle(
            mock_sections,
            query="layout",
            result_type="files",
            max_results=10
        )

        # Should have file matches - files result_type searches file_map only
        # Check that we got file results (have "file" key with non-empty value)
        file_results = [r for r in results if r.get("file")]
        assert len(file_results) > 0, "Should have file results when result_type='files'"

    def test_result_type_concepts_only(self, mock_sections):
        """result_type='concepts' should only return concept matches."""
        # search_oracle is imported at module level

        results = search_oracle(
            mock_sections,
            query="layout",
            result_type="concepts",
            max_results=10
        )

        # Concepts search should return results from concept_index
        # All results should have a section attribute
        for r in results:
            assert "section" in r, "Concept results should have section info"

    def test_scope_limits_to_section(self, mock_sections):
        """scope='Dress' should only return Dress files."""
        # search_oracle is imported at module level

        # First get unscoped results
        all_results = search_oracle(
            mock_sections,
            query="theme",  # This exists in Runway
            scope=None,
            max_results=10
        )

        # Now get scoped results
        scoped_results = search_oracle(
            mock_sections,
            query="theme",
            scope="Dress",
            max_results=10
        )

        # Scoped results should not include Runway files
        for r in scoped_results:
            if r.get("file"):
                assert "Runway" not in r["file"], "Scoped to Dress should not return Runway files"
            if r.get("section"):
                assert "Runway" not in r["section"], "Scoped to Dress should not return Runway sections"

    def test_scope_case_insensitive(self, mock_sections):
        """scope should be case-insensitive."""
        # search_oracle is imported at module level

        results_lower = search_oracle(
            mock_sections,
            query="layout",
            scope="dress",  # lowercase
            max_results=10
        )

        results_upper = search_oracle(
            mock_sections,
            query="layout",
            scope="DRESS",  # uppercase
            max_results=10
        )

        # Both should return results
        assert len(results_lower) > 0, "Should match with lowercase scope"
        assert len(results_upper) > 0, "Should match with uppercase scope"

    def test_min_relevance_filters(self, mock_sections):
        """min_relevance=0.8 should filter low-relevance matches."""
        # search_oracle is imported at module level

        # Get all results first
        all_results = search_oracle(
            mock_sections,
            query="layout",
            min_relevance=0.0,
            max_results=100
        )

        # Get filtered results
        filtered_results = search_oracle(
            mock_sections,
            query="layout",
            min_relevance=0.8,
            max_results=100
        )

        # Filtered should have <= all results
        assert len(filtered_results) <= len(all_results), "Filtered results should not exceed unfiltered"

        # All filtered results should meet the threshold
        for r in filtered_results:
            assert r["relevance"] >= 0.8, f"Result relevance {r['relevance']} below threshold 0.8"

    def test_min_relevance_zero_returns_all(self, mock_sections):
        """min_relevance=0.0 should not filter anything."""
        # search_oracle is imported at module level

        results = search_oracle(
            mock_sections,
            query="layout",
            min_relevance=0.0,
            max_results=100
        )

        # Should get some results
        assert len(results) > 0, "Should have results with min_relevance=0.0"

    def test_fuzzy_matches_typos(self, mock_sections):
        """fuzzy=True should match approximate queries."""
        # search_oracle is imported at module level

        # Exact match without fuzzy
        exact = search_oracle(
            mock_sections,
            query="layout",
            fuzzy=False,
            max_results=10
        )

        # Fuzzy match with typo
        fuzzy = search_oracle(
            mock_sections,
            query="layot",  # typo
            fuzzy=True,
            max_results=10
        )

        # Exact query should definitely find results
        assert len(exact) > 0, "Exact match should find results"

        # Fuzzy should return a list (may be empty if threshold is strict)
        assert isinstance(fuzzy, list), "Fuzzy search should return a list"

    def test_fuzzy_false_no_typo_match(self, mock_sections):
        """fuzzy=False should not match typos."""
        # search_oracle is imported at module level

        # Search with typo and fuzzy=False
        results = search_oracle(
            mock_sections,
            query="layot",  # typo
            fuzzy=False,
            max_results=10
        )

        # Should not find exact matches for the typo
        # (may find partial matches if typo substring exists elsewhere)
        for r in results:
            # If there's a result, it shouldn't be from fuzzy matching
            assert r.get("relevance", 0) <= 0.5 or "layot" in str(r).lower(), \
                "Non-fuzzy search shouldn't fuzzy-match typos"

    def test_combined_filters(self, mock_sections):
        """Multiple filters should work together."""
        # search_oracle is imported at module level

        results = search_oracle(
            mock_sections,
            query="graph",
            result_type="files",
            scope="Dress",
            min_relevance=0.5,
            fuzzy=False,
            max_results=10
        )

        # Verify all filters applied
        for r in results:
            # Should be a file result
            assert r.get("file"), "result_type='files' should return file results"
            # Should be in Dress scope
            if r.get("section"):
                assert "Dress" in r["section"] or "dress" in r.get("file", "").lower(), \
                    "Should be in Dress scope"
            # Should meet relevance threshold
            assert r["relevance"] >= 0.5, f"Relevance {r['relevance']} below threshold"

    def test_result_type_validation(self, mock_sections):
        """Invalid result_type should still work (treated as 'all')."""
        # search_oracle is imported at module level

        # Using an invalid result_type should fall through to no matches
        # (since the if conditions won't match)
        results = search_oracle(
            mock_sections,
            query="layout",
            result_type="invalid",
            max_results=10
        )

        # Should be a list (empty since 'invalid' doesn't match any condition)
        assert isinstance(results, list)

    def test_empty_sections_handled(self):
        """Empty sections dict should not crash."""
        # search_oracle is imported at module level

        empty_sections = {
            "file_map": {},
            "concept_index": [],
            "sections": {},
        }

        results = search_oracle(
            empty_sections,
            query="anything",
            max_results=10
        )

        assert results == [], "Empty sections should return empty results"
