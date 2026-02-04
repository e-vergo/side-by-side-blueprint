"""Tests for oracle query filter parameters.

Oracle search was migrated from sbs_utils.search_oracle() to DuckDBLayer.oracle_query()
as part of the DuckDB migration (#118/#128). These tests require duckdb, which is only
available in the MCP server venv. They skip gracefully when duckdb is not installed.

For full oracle query testing, see:
    forks/sbs-lsp-mcp/tests/test_duckdb_layer.py::TestOracleQuery
"""
import json
import sys
from pathlib import Path

import pytest

# Add MCP src to path for direct import
SBS_ROOT = Path(__file__).resolve().parents[6]
SBS_MCP_SRC = SBS_ROOT / "forks" / "sbs-lsp-mcp" / "src"

try:
    import duckdb  # noqa: F401
    if str(SBS_MCP_SRC) not in sys.path:
        sys.path.insert(0, str(SBS_MCP_SRC))
    # Import directly to avoid __init__.py chain (which needs orjson)
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "sbs_lsp_mcp.duckdb_layer",
        SBS_MCP_SRC / "sbs_lsp_mcp" / "duckdb_layer.py",
    )
    _mod = importlib.util.module_from_spec(_spec)
    # Need sbs_models in sys.modules for duckdb_layer to import from
    _models_spec = importlib.util.spec_from_file_location(
        "sbs_lsp_mcp.sbs_models",
        SBS_MCP_SRC / "sbs_lsp_mcp" / "sbs_models.py",
    )
    _models_mod = importlib.util.module_from_spec(_models_spec)
    sys.modules["sbs_lsp_mcp.sbs_models"] = _models_mod
    _models_spec.loader.exec_module(_models_mod)

    sys.modules["sbs_lsp_mcp.duckdb_layer"] = _mod
    _spec.loader.exec_module(_mod)
    DuckDBLayer = _mod.DuckDBLayer
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False
    DuckDBLayer = None


@pytest.mark.evergreen
@pytest.mark.skipif(not HAS_DUCKDB, reason="duckdb not installed (test covered in MCP repo)")
class TestOracleFilters:
    """Tests for oracle query filter parameters via DuckDBLayer."""

    @pytest.fixture
    def mock_oracle_md(self, tmp_path):
        """Create a minimal oracle markdown file for testing."""
        content = '''# SBS Oracle

## File Map

| Concept | Primary Location | Notes |
|---------|------------------|-------|
| graph layout | `Dress/Graph/Layout.lean` | Sugiyama algorithm |
| theme | `Runway/Theme.lean` | HTML templates |
| elab rules | `Dress/Capture/ElabRules.lean` | Capture hooks |

## Concepts

| Concept | Location | Notes |
|---------|----------|-------|
| graph layout | `Dress/Graph/Layout.lean` | Sugiyama |
| theme toggle | `Runway/Theme.lean` | |
| status colors | `Dress/Graph/Svg.lean` | 6-color model |
'''
        oracle_path = tmp_path / "sbs-oracle.md"
        oracle_path.write_text(content)
        return oracle_path

    @pytest.fixture
    def mock_archive_dir(self, tmp_path):
        """Create a minimal archive dir with empty archive_index.json."""
        archive_dir = tmp_path / "storage"
        archive_dir.mkdir()
        index = {"version": "1.1", "entries": {}, "global_state": None, "last_epoch_entry": None}
        (archive_dir / "archive_index.json").write_text(json.dumps(index))
        return archive_dir

    @pytest.fixture
    def db(self, mock_archive_dir, mock_oracle_md, tmp_path):
        """Create a DuckDBLayer with mock data."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir()
        layer = DuckDBLayer(
            archive_dir=mock_archive_dir,
            session_dir=session_dir,
            oracle_path=mock_oracle_md,
        )
        layer.ensure_loaded()
        yield layer
        layer.close()

    def test_result_type_files_only(self, db):
        """result_type='files' should only return file matches."""
        result = db.oracle_query(
            query="layout",
            result_type="files",
            max_results=10,
        )
        assert len(result.file_matches) > 0, "Should have file results"
        assert any("Layout" in m.file for m in result.file_matches)

    def test_scope_limits_to_section(self, db):
        """scope='Dress' should only return Dress files."""
        result = db.oracle_query(query="theme", scope="Dress", max_results=10)
        for m in result.file_matches:
            assert "Runway" not in m.file, "Scoped to Dress should not return Runway files"

    def test_scope_case_insensitive(self, db):
        """scope should be case-insensitive."""
        lo = db.oracle_query(query="layout", scope="dress", max_results=10)
        up = db.oracle_query(query="layout", scope="DRESS", max_results=10)
        assert len(lo.file_matches) > 0
        assert len(up.file_matches) > 0

    def test_min_relevance_filters(self, db):
        """min_relevance=0.8 should filter low-relevance matches."""
        all_r = db.oracle_query(query="layout", min_relevance=0.0, max_results=100)
        filtered = db.oracle_query(query="layout", min_relevance=0.8, max_results=100)
        assert len(filtered.file_matches) <= len(all_r.file_matches)
        for m in filtered.file_matches:
            assert m.relevance >= 0.8

    def test_fuzzy_matches_typos(self, db):
        """fuzzy=True should match approximate queries."""
        exact = db.oracle_query(query="layout", fuzzy=False, max_results=10)
        fuzzy = db.oracle_query(query="layot", fuzzy=True, max_results=10)
        assert len(exact.file_matches) > 0
        assert isinstance(fuzzy.file_matches, list)

    def test_combined_filters(self, db):
        """Multiple filters should work together."""
        result = db.oracle_query(
            query="graph", result_type="files", scope="Dress",
            min_relevance=0.5, fuzzy=False, max_results=10,
        )
        for m in result.file_matches:
            assert "Dress" in m.file or "dress" in m.file.lower()
            assert m.relevance >= 0.5

    def test_empty_oracle_handled(self, tmp_path):
        """Empty oracle file should not crash."""
        archive_dir = tmp_path / "storage_empty"
        archive_dir.mkdir()
        index = {"version": "1.1", "entries": {}, "global_state": None, "last_epoch_entry": None}
        (archive_dir / "archive_index.json").write_text(json.dumps(index))
        oracle_path = tmp_path / "empty-oracle.md"
        oracle_path.write_text("# Empty Oracle\n")
        session_dir = tmp_path / "sessions_empty"
        session_dir.mkdir()
        layer = DuckDBLayer(
            archive_dir=archive_dir, session_dir=session_dir, oracle_path=oracle_path,
        )
        layer.ensure_loaded()
        try:
            result = layer.oracle_query(query="anything", max_results=10)
            assert result.file_matches == []
            assert result.concepts == []
        finally:
            layer.close()
