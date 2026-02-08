"""Tests for the DuckDB query layer.

Tests schema creation, core access methods, analytics, oracle queries,
and lifecycle (invalidation, staleness).
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import pytest

from sls_mcp.duckdb_layer import DuckDBLayer


# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def mock_archive_entries() -> Dict[str, Dict[str, Any]]:
    """Rich mock archive entries covering various features."""
    now = datetime.now()
    return {
        "20260130100000": {
            "entry_id": "20260130100000",
            "created_at": (now - timedelta(days=1)).isoformat(),
            "project": "SBSTest",
            "build_run_id": None,
            "notes": "End of previous epoch",
            "tags": ["epoch"],
            "screenshots": ["dashboard.png"],
            "repo_commits": {},
            "synced_to_icloud": False,
            "auto_tags": ["epoch-close"],
            "trigger": "skill",
            "quality_scores": {"overall": 75.0, "scores": {}},
            "quality_delta": None,
            "global_state": {"skill": "self-improve", "substate": "archive"},
            "state_transition": "phase_end",
            "epoch_summary": {"entries": 5, "builds": 3},
            "gate_validation": None,
            "issue_refs": [],
            "pr_refs": [],
            "added_at": None,
        },
        "20260131102119": {
            "entry_id": "20260131102119",
            "created_at": (now - timedelta(hours=2)).isoformat(),
            "project": "SBSTest",
            "build_run_id": "build-001",
            "notes": "Initial build with dashboard fixes",
            "tags": ["milestone", "release"],
            "screenshots": ["dashboard.png", "dep_graph.png"],
            "repo_commits": {"SBS-Test": "abc123"},
            "synced_to_icloud": False,
            "auto_tags": ["build", "visual-change"],
            "trigger": "build",
            "quality_scores": {"overall": 85.0, "scores": {"T5": {"value": 100.0, "passed": True, "stale": False}}},
            "quality_delta": None,
            "global_state": None,
            "state_transition": None,
            "epoch_summary": None,
            "gate_validation": None,
            "issue_refs": [],
            "pr_refs": [],
            "added_at": None,
        },
        "20260131120000": {
            "entry_id": "20260131120000",
            "created_at": (now - timedelta(hours=1)).isoformat(),
            "project": "SBSTest",
            "build_run_id": "build-002",
            "notes": "CSS refinements",
            "tags": ["styling"],
            "screenshots": ["dashboard.png"],
            "repo_commits": {"SBS-Test": "def456"},
            "synced_to_icloud": False,
            "auto_tags": ["build"],
            "trigger": "build",
            "quality_scores": None,
            "quality_delta": None,
            "global_state": None,
            "state_transition": None,
            "epoch_summary": None,
            "gate_validation": None,
            "issue_refs": [],
            "pr_refs": [],
            "added_at": None,
        },
        "20260131140000": {
            "entry_id": "20260131140000",
            "created_at": (now - timedelta(minutes=30)).isoformat(),
            "project": "GCR",
            "build_run_id": "build-003",
            "notes": "",
            "tags": [],
            "screenshots": ["paper_tex.png", "pdf_tex.png"],
            "repo_commits": {"GCR": "ghi789"},
            "synced_to_icloud": False,
            "auto_tags": ["build"],
            "trigger": "build",
            "quality_scores": None,
            "quality_delta": None,
            "global_state": None,
            "state_transition": None,
            "epoch_summary": None,
            "gate_validation": None,
            "issue_refs": [],
            "pr_refs": [],
            "added_at": None,
        },
        "20260131150000": {
            "entry_id": "20260131150000",
            "created_at": now.isoformat(),
            "project": "SBSTest",
            "build_run_id": None,
            "notes": "Manual checkpoint before refactor",
            "tags": ["checkpoint"],
            "screenshots": [],
            "repo_commits": {},
            "synced_to_icloud": False,
            "auto_tags": [],
            "trigger": "skill",
            "quality_scores": None,
            "quality_delta": None,
            "global_state": {"skill": "task", "substate": "execution"},
            "state_transition": "phase_start",
            "epoch_summary": None,
            "gate_validation": None,
            "issue_refs": ["42"],
            "pr_refs": [10],
            "added_at": None,
        },
    }


@pytest.fixture
def mock_archive_index(mock_archive_entries) -> Dict[str, Any]:
    """Create a full archive index dict."""
    by_tag: Dict[str, list] = {}
    by_project: Dict[str, list] = {}
    latest_by_project: Dict[str, str] = {}

    for eid, entry in mock_archive_entries.items():
        project = entry["project"]
        all_tags = entry["tags"] + entry["auto_tags"]

        by_project.setdefault(project, []).append(eid)
        for tag in all_tags:
            by_tag.setdefault(tag, []).append(eid)
        if project not in latest_by_project or eid > latest_by_project[project]:
            latest_by_project[project] = eid

    return {
        "version": "1.1",
        "entries": mock_archive_entries,
        "by_tag": by_tag,
        "by_project": by_project,
        "latest_by_project": latest_by_project,
        "global_state": {"skill": "task", "substate": "execution"},
        "last_epoch_entry": "20260130100000",
    }


@pytest.fixture
def mock_oracle_content() -> str:
    return '''# SBS Oracle

## File Map

| Concept | Primary Location | Notes |
|---------|------------------|-------|
| Graph layout | `Dress/Graph/Layout.lean` | Sugiyama algorithm |
| Status colors | `Dress/Graph/Svg.lean` | Canonical hex values |
| CLI entry | `dev/scripts/sbs/cli.py` | Main CLI dispatcher |

## Concepts

| Concept | Location | Notes |
|---------|----------|-------|
| Sugiyama layout | `Dress/Graph/Layout.lean` | ~1500 lines, layer assignment |
| 6-status model | `Dress/Graph/Svg.lean` | notReady, ready, sorry, proven, fullyProven, mathlibReady |
| Epoch | Archive system | Period between skill-triggered entries |

## Architecture

The SBS toolchain consists of several repos:
- SubVerso: Syntax highlighting (fork with O(1) indexed lookups)
- Dress: Artifact generation + graph layout + validation
'''


@pytest.fixture
def db_layer(tmp_path, mock_archive_index, mock_oracle_content) -> DuckDBLayer:
    """Create a DuckDBLayer with test data."""
    archive_dir = tmp_path / "storage"
    archive_dir.mkdir()

    # Write archive index
    index_path = archive_dir / "archive_index.json"
    with open(index_path, "w") as f:
        json.dump(mock_archive_index, f)

    # Write oracle
    oracle_path = tmp_path / "sbs-oracle.md"
    oracle_path.write_text(mock_oracle_content)

    layer = DuckDBLayer(
        archive_dir=archive_dir,
        session_dir=tmp_path / "sessions",  # empty, no session files
        oracle_path=oracle_path,
    )
    return layer


# ======================================================================
# Schema creation & loading
# ======================================================================


class TestSchemaCreation:
    """Test that schema is created and data loads correctly."""

    def test_ensure_loaded_creates_tables(self, db_layer: DuckDBLayer):
        db_layer.ensure_loaded()
        assert db_layer._conn is not None
        # Verify tables exist by querying them
        tables = db_layer._conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        table_names = {t[0] for t in tables}
        assert "entries" in table_names
        assert "index_metadata" in table_names
        assert "questions" in table_names
        assert "oracle_concepts" in table_names
        assert "oracle_files" in table_names

    def test_entries_loaded(self, db_layer: DuckDBLayer):
        db_layer.ensure_loaded()
        count = db_layer._conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        assert count == 5

    def test_metadata_loaded(self, db_layer: DuckDBLayer):
        db_layer.ensure_loaded()
        row = db_layer._conn.execute(
            "SELECT global_state_skill, global_state_substate, last_epoch_entry FROM index_metadata"
        ).fetchone()
        assert row[0] == "task"
        assert row[1] == "execution"
        assert row[2] == "20260130100000"

    def test_oracle_concepts_loaded(self, db_layer: DuckDBLayer):
        db_layer.ensure_loaded()
        count = db_layer._conn.execute("SELECT COUNT(*) FROM oracle_concepts").fetchone()[0]
        # 3 from File Map + 3 from Concepts = 6
        assert count >= 6

    def test_oracle_files_loaded(self, db_layer: DuckDBLayer):
        db_layer.ensure_loaded()
        count = db_layer._conn.execute("SELECT COUNT(*) FROM oracle_files").fetchone()[0]
        # 3 from File Map + 2 from Concepts (with file paths)
        assert count >= 3


# ======================================================================
# Core access methods
# ======================================================================


class TestCoreAccess:
    """Test core data access methods."""

    def test_get_global_state(self, db_layer: DuckDBLayer):
        skill, substate = db_layer.get_global_state()
        assert skill == "task"
        assert substate == "execution"

    def test_get_metadata(self, db_layer: DuckDBLayer):
        meta = db_layer.get_metadata()
        assert meta["global_state"] == {"skill": "task", "substate": "execution"}
        assert meta["last_epoch_entry"] == "20260130100000"
        assert "SBSTest" in meta["projects"]
        assert "GCR" in meta["projects"]
        assert meta["total_entries"] == 5

    def test_get_entry_existing(self, db_layer: DuckDBLayer):
        entry = db_layer.get_entry("20260131102119")
        assert entry is not None
        assert entry["entry_id"] == "20260131102119"
        assert entry["project"] == "SBSTest"
        assert entry["build_run_id"] == "build-001"

    def test_get_entry_missing(self, db_layer: DuckDBLayer):
        entry = db_layer.get_entry("nonexistent")
        assert entry is None

    def test_get_entries_no_filter(self, db_layer: DuckDBLayer):
        entries = db_layer.get_entries(limit=100)
        assert len(entries) == 5
        # Should be DESC order by created_at (most recent first)
        for i in range(len(entries) - 1):
            ca_cur = entries[i].get("created_at", "")
            ca_next = entries[i + 1].get("created_at", "")
            if ca_cur and ca_next:
                assert ca_cur >= ca_next

    def test_get_entries_filter_project(self, db_layer: DuckDBLayer):
        entries = db_layer.get_entries(project="SBSTest")
        assert all(e["project"] == "SBSTest" for e in entries)
        assert len(entries) == 4  # 4 SBSTest entries

    def test_get_entries_filter_trigger(self, db_layer: DuckDBLayer):
        entries = db_layer.get_entries(trigger="build")
        assert all(e["trigger"] == "build" for e in entries)
        assert len(entries) == 3

    def test_get_entries_filter_tags(self, db_layer: DuckDBLayer):
        entries = db_layer.get_entries(tags=["milestone"])
        assert len(entries) == 1
        assert entries[0]["entry_id"] == "20260131102119"

    def test_get_entries_filter_since(self, db_layer: DuckDBLayer):
        # Use ISO timestamp relative to fixture data:
        # entry 20260131120000 has created_at = now - 1hr
        # We want entries AFTER that point, so use (now - 1hr) as since
        since_ts = (datetime.now() - timedelta(hours=1)).isoformat()
        entries = db_layer.get_entries(since=since_ts)
        # Should get entries with created_at > (now-1hr): 140000 (now-30min) and 150000 (now)
        assert len(entries) == 2
        ids = {e["entry_id"] for e in entries}
        assert "20260131140000" in ids
        assert "20260131150000" in ids

    def test_get_entries_filter_since_old_entry_id_format(self, db_layer: DuckDBLayer):
        # Verify old YYYYMMDDHHMMSS format still works (parsed to datetime)
        entries = db_layer.get_entries(since="20260131120000")
        # 20260131120000 = 2026-01-31T12:00:00 UTC -- all fixture entries have
        # created_at relative to now(), so all should be after that fixed date
        assert len(entries) >= 2

    def test_get_entries_limit(self, db_layer: DuckDBLayer):
        entries = db_layer.get_entries(limit=2)
        assert len(entries) == 2

    def test_get_epoch_entries_current(self, db_layer: DuckDBLayer):
        # Current epoch: entries after last_epoch_entry "20260130100000"
        entries = db_layer.get_epoch_entries()
        assert len(entries) == 4  # All entries after epoch close
        # Verify none of the returned entries is the epoch boundary itself
        assert all(e["entry_id"] != "20260130100000" for e in entries)

    def test_get_epoch_entries_by_id(self, db_layer: DuckDBLayer):
        # The epoch that 20260131120000 closes: entries between previous skill trigger and this ID
        entries = db_layer.get_epoch_entries("20260131120000")
        # Should include entries after last skill-triggered entry before 20260131120000
        assert len(entries) >= 1

    def test_get_entries_by_project(self, db_layer: DuckDBLayer):
        entries = db_layer.get_entries_by_project("GCR")
        assert len(entries) == 1
        assert entries[0]["project"] == "GCR"

    def test_list_projects(self, db_layer: DuckDBLayer):
        projects = db_layer.list_projects()
        assert "SBSTest" in projects
        assert "GCR" in projects
        assert len(projects) == 2


# ======================================================================
# Analytics methods
# ======================================================================


class TestAnalytics:
    """Test analytics methods match original behavior."""

    def test_analysis_summary_basic(self, db_layer: DuckDBLayer):
        result = db_layer.analysis_summary()
        assert result.total_entries == 5
        assert "build" in result.entries_by_trigger
        assert result.entries_by_trigger["build"] == 3
        assert "SBSTest" in result.projects_summary
        assert result.projects_summary["SBSTest"] == 4
        assert result.quality_metrics is not None
        assert result.quality_metrics["count"] >= 1

    def test_analysis_summary_tags(self, db_layer: DuckDBLayer):
        result = db_layer.analysis_summary()
        assert len(result.most_common_tags) > 0
        # "build" should be common (appears 3 times as auto_tag)
        assert "build" in result.most_common_tags

    def test_entries_since_self_improve(self, db_layer: DuckDBLayer):
        result = db_layer.entries_since_self_improve()
        # The self-improve session ended at 20260130100000 (phase_end)
        assert result.last_self_improve_entry == "20260130100000"
        # Entries since: 4 entries after 20260130100000
        assert result.count == 4
        assert len(result.entries_since) == 4

    def test_successful_sessions(self, db_layer: DuckDBLayer):
        result = db_layer.successful_sessions()
        assert result.total_sessions_analyzed == 5
        # Should find clean_execution pattern (skill entries with <=3 auto_tags)
        pattern_types = [p.pattern_type for p in result.patterns]
        # The epoch-close entry has trigger=skill with 1 auto_tag -> clean
        assert "clean_execution" in pattern_types

    def test_comparative_analysis(self, db_layer: DuckDBLayer):
        result = db_layer.comparative_analysis()
        assert isinstance(result.approved_count, int)
        assert isinstance(result.rejected_count, int)

    def test_system_health(self, db_layer: DuckDBLayer):
        result = db_layer.system_health()
        assert result.overall_health in ("healthy", "warning", "degraded")
        # Should have build_metrics
        metric_names = [m.metric for m in result.build_metrics]
        assert "total_builds" in metric_names
        assert "quality_score_coverage" in metric_names

    def test_user_patterns(self, db_layer: DuckDBLayer):
        result = db_layer.user_patterns()
        assert result.total_sessions_analyzed == 5

    def test_skill_stats(self, db_layer: DuckDBLayer):
        result = db_layer.skill_stats()
        assert result.total_sessions >= 1
        # We have a task phase_start and a self-improve phase_end
        assert "task" in result.skills or "self-improve" in result.skills

    def test_skill_stats_with_findings(self, db_layer: DuckDBLayer):
        result = db_layer.skill_stats(as_findings=True)
        # May or may not have findings depending on completion rates
        assert isinstance(result.findings, list)

    def test_phase_transition_health(self, db_layer: DuckDBLayer):
        result = db_layer.phase_transition_health()
        assert len(result.reports) >= 1
        assert isinstance(result.summary, str)

    def test_interruption_analysis(self, db_layer: DuckDBLayer):
        result = db_layer.interruption_analysis()
        assert isinstance(result.events, list)
        assert result.total_sessions_analyzed >= 1

    def test_gate_failures_no_gates(self, db_layer: DuckDBLayer):
        result = db_layer.gate_failures()
        assert result.total_gate_checks == 0
        assert "No gate validation" in result.summary

    def test_tag_effectiveness(self, db_layer: DuckDBLayer):
        result = db_layer.tag_effectiveness()
        # We have auto_tags in entries
        assert len(result.tags) > 0
        # "build" appears multiple times
        build_tag = next((t for t in result.tags if t.tag == "build"), None)
        assert build_tag is not None
        assert build_tag.frequency >= 3


# ======================================================================
# Oracle query
# ======================================================================


class TestOracleQuery:
    """Test oracle search functionality."""

    def test_query_file_match(self, db_layer: DuckDBLayer):
        result = db_layer.oracle_query("Layout.lean")
        assert len(result.file_matches) >= 1
        paths = [m.file for m in result.file_matches]
        assert any("Layout.lean" in p for p in paths)

    def test_query_concept_match(self, db_layer: DuckDBLayer):
        result = db_layer.oracle_query("Sugiyama")
        # Should find the Sugiyama concept
        all_matches = result.file_matches + [
            OracleMatch(file="", lines=None, context=c.name, relevance=0.5)
            for c in result.concepts
        ]
        assert len(all_matches) >= 1

    def test_query_no_match(self, db_layer: DuckDBLayer):
        result = db_layer.oracle_query("xyznonexistent12345")
        assert len(result.file_matches) == 0
        assert len(result.concepts) == 0

    def test_query_with_scope(self, db_layer: DuckDBLayer):
        result = db_layer.oracle_query("layout", scope="Dress")
        # Should only return Dress-related results
        for m in result.file_matches:
            assert "Dress" in m.file or "Dress" in m.context

    def test_query_with_archive_context(self, db_layer: DuckDBLayer):
        result = db_layer.oracle_query("graph", include_archive=True)
        assert result.archive_context is not None
        assert "recent_entries" in result.archive_context

    def test_query_with_quality(self, db_layer: DuckDBLayer):
        result = db_layer.oracle_query("graph", include_quality=True)
        # We have at least one entry with quality_overall
        assert result.quality_snapshot is not None
        assert "overall" in result.quality_snapshot

    def test_query_result_type_files(self, db_layer: DuckDBLayer):
        result = db_layer.oracle_query("status", result_type="files")
        # Should only get file matches, no concepts
        assert len(result.concepts) == 0

    def test_query_min_relevance(self, db_layer: DuckDBLayer):
        result = db_layer.oracle_query("graph", min_relevance=0.8)
        for m in result.file_matches:
            assert m.relevance >= 0.8


# ======================================================================
# Lifecycle: invalidation, staleness, close
# ======================================================================


class TestLifecycle:
    """Test lifecycle methods."""

    def test_invalidate_forces_reload(self, db_layer: DuckDBLayer):
        db_layer.ensure_loaded()
        assert db_layer._loaded is True
        db_layer.invalidate()
        assert db_layer._invalidated is True
        # Next ensure_loaded should reload
        db_layer.ensure_loaded()
        assert db_layer._invalidated is False
        assert db_layer._loaded is True

    def test_close_cleans_up(self, db_layer: DuckDBLayer):
        db_layer.ensure_loaded()
        assert db_layer._conn is not None
        db_layer.close()
        assert db_layer._conn is None
        assert db_layer._loaded is False

    def test_ensure_loaded_idempotent(self, db_layer: DuckDBLayer):
        db_layer.ensure_loaded()
        conn1 = db_layer._conn
        # Second call should NOT recreate connection
        db_layer.ensure_loaded()
        conn2 = db_layer._conn
        assert conn1 is conn2

    def test_refresh_detects_stale(self, tmp_path, mock_archive_index, mock_oracle_content):
        archive_dir = tmp_path / "storage"
        archive_dir.mkdir()
        index_path = archive_dir / "archive_index.json"
        with open(index_path, "w") as f:
            json.dump(mock_archive_index, f)
        oracle_path = tmp_path / "sbs-oracle.md"
        oracle_path.write_text(mock_oracle_content)

        layer = DuckDBLayer(archive_dir=archive_dir, session_dir=tmp_path, oracle_path=oracle_path)
        layer.ensure_loaded()
        old_conn = layer._conn

        # Modify the file (touch it to change mtime)
        import time
        time.sleep(0.1)
        index_path.write_text(json.dumps(mock_archive_index))

        layer.refresh_if_stale()
        # Connection should be recreated
        assert layer._conn is not old_conn


# ======================================================================
# Edge cases
# ======================================================================


class TestEdgeCases:
    """Test edge cases and empty data."""

    def test_empty_archive(self, tmp_path):
        archive_dir = tmp_path / "storage"
        archive_dir.mkdir()
        oracle_path = tmp_path / "sbs-oracle.md"
        # No archive_index.json, no oracle file

        layer = DuckDBLayer(archive_dir=archive_dir, session_dir=tmp_path, oracle_path=oracle_path)
        layer.ensure_loaded()

        skill, substate = layer.get_global_state()
        assert skill is None
        assert substate is None

        meta = layer.get_metadata()
        assert meta["total_entries"] == 0
        assert meta["projects"] == []

        entries = layer.get_entries()
        assert entries == []

        projects = layer.list_projects()
        assert projects == []

    def test_empty_archive_analytics(self, tmp_path):
        archive_dir = tmp_path / "storage"
        archive_dir.mkdir()
        oracle_path = tmp_path / "sbs-oracle.md"

        layer = DuckDBLayer(archive_dir=archive_dir, session_dir=tmp_path, oracle_path=oracle_path)

        # All analytics should return empty results without errors
        result = layer.analysis_summary()
        assert result.total_entries == 0

        result2 = layer.entries_since_self_improve()
        assert result2.count == 0

        result3 = layer.successful_sessions()
        assert result3.total_sessions_analyzed == 0

        result4 = layer.system_health()
        assert result4.overall_health in ("healthy", "warning", "degraded", "unknown")

        result5 = layer.skill_stats()
        assert "No archive entries" in result5.summary

        result6 = layer.tag_effectiveness()
        assert "No archive entries" in result6.summary

    def test_entry_global_state_reconstruction(self, db_layer: DuckDBLayer):
        """Verify global_state dict is reconstructed from flattened gs_skill/gs_substate."""
        entry = db_layer.get_entry("20260131150000")
        assert entry is not None
        assert entry["global_state"] == {"skill": "task", "substate": "execution"}

    def test_entry_null_global_state(self, db_layer: DuckDBLayer):
        """Entries without global_state should have global_state=None."""
        entry = db_layer.get_entry("20260131102119")
        assert entry is not None
        assert entry["global_state"] is None

    def test_context_block_generation(self, db_layer: DuckDBLayer):
        """Test build_context_block generates valid markdown."""
        block = db_layer.build_context_block(include=["state", "recent"])
        assert "## Current State" in block
        assert "## Recent Archive Activity" in block
        assert "task" in block

    def test_context_block_all_sections(self, db_layer: DuckDBLayer):
        block = db_layer.build_context_block()
        assert "## Current State" in block
        assert "## Current Epoch" in block
        assert "## Recent Archive Activity" in block


# ======================================================================
# Gate failures with actual gate data
# ======================================================================


class TestGateFailuresWithData:
    """Test gate_failures with entries that have gate_validation."""

    def test_gate_failures_with_data(self, tmp_path, mock_oracle_content):
        """Create entries with gate_validation and verify analysis."""
        now = datetime.now()
        entries = {
            "20260131100000": {
                "entry_id": "20260131100000",
                "created_at": (now - timedelta(hours=2)).isoformat(),
                "project": "SBSTest",
                "build_run_id": None,
                "notes": "",
                "tags": [],
                "screenshots": [],
                "repo_commits": {},
                "synced_to_icloud": False,
                "auto_tags": [],
                "trigger": "skill",
                "quality_scores": None,
                "quality_delta": None,
                "global_state": {"skill": "task", "substate": "execution"},
                "state_transition": "phase_start",
                "epoch_summary": None,
                "gate_validation": {"passed": False, "findings": ["tests_failed", "lint_error"]},
                "issue_refs": [],
                "pr_refs": [],
                "added_at": None,
            },
            "20260131110000": {
                "entry_id": "20260131110000",
                "created_at": (now - timedelta(hours=1)).isoformat(),
                "project": "SBSTest",
                "build_run_id": None,
                "notes": "",
                "tags": [],
                "screenshots": [],
                "repo_commits": {},
                "synced_to_icloud": False,
                "auto_tags": [],
                "trigger": "skill",
                "quality_scores": None,
                "quality_delta": None,
                "global_state": {"skill": "task", "substate": "finalization"},
                "state_transition": "phase_start",
                "epoch_summary": None,
                "gate_validation": {"passed": True},
                "issue_refs": [],
                "pr_refs": [],
                "added_at": None,
            },
        }

        archive_dir = tmp_path / "storage"
        archive_dir.mkdir()
        index = {
            "version": "1.1",
            "entries": entries,
            "by_tag": {},
            "by_project": {"SBSTest": list(entries.keys())},
            "latest_by_project": {"SBSTest": "20260131110000"},
            "global_state": {"skill": "task", "substate": "finalization"},
            "last_epoch_entry": None,
        }
        with open(archive_dir / "archive_index.json", "w") as f:
            json.dump(index, f)

        oracle_path = tmp_path / "sbs-oracle.md"
        oracle_path.write_text(mock_oracle_content)

        layer = DuckDBLayer(archive_dir=archive_dir, session_dir=tmp_path, oracle_path=oracle_path)
        result = layer.gate_failures()

        assert result.total_gate_checks == 2
        assert result.total_failures == 1
        assert result.failures[0].entry_id == "20260131100000"
        assert "tests_failed" in result.failures[0].gate_findings
