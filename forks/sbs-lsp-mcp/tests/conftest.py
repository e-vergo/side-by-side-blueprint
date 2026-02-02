"""Shared test fixtures for SBS tools testing."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest


# =============================================================================
# Mock Archive Data
# =============================================================================


@pytest.fixture
def mock_archive_entries() -> Dict[str, Dict[str, Any]]:
    """Create mock archive entries for testing."""
    now = datetime.now()

    # Entry timestamps (entry_id is Unix timestamp format: YYYYMMDDHHmmss)
    entries = {
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
            "sync_timestamp": None,
            "sync_error": None,
            "rubric_id": None,
            "rubric_evaluation": None,
            "claude_data": None,
            "auto_tags": ["build", "visual-change"],
            "trigger": "build",
            "quality_scores": {"overall": 85.0, "scores": {"T5": {"value": 100.0, "passed": True, "stale": False}}},
            "quality_delta": None,
            "global_state": None,
            "state_transition": None,
            "epoch_summary": None,
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
            "sync_timestamp": None,
            "sync_error": None,
            "rubric_id": None,
            "rubric_evaluation": None,
            "claude_data": None,
            "auto_tags": ["build"],
            "trigger": "build",
            "quality_scores": None,
            "quality_delta": None,
            "global_state": None,
            "state_transition": None,
            "epoch_summary": None,
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
            "sync_timestamp": None,
            "sync_error": None,
            "rubric_id": None,
            "rubric_evaluation": None,
            "claude_data": None,
            "auto_tags": ["build"],
            "trigger": "build",
            "quality_scores": None,
            "quality_delta": None,
            "global_state": None,
            "state_transition": None,
            "epoch_summary": None,
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
            "sync_timestamp": None,
            "sync_error": None,
            "rubric_id": None,
            "rubric_evaluation": None,
            "claude_data": None,
            "auto_tags": [],
            "trigger": "manual",
            "quality_scores": None,
            "quality_delta": None,
            "global_state": {"skill": "task", "substate": "execution"},
            "state_transition": "phase_start",
            "epoch_summary": None,
        },
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
            "sync_timestamp": None,
            "sync_error": None,
            "rubric_id": None,
            "rubric_evaluation": None,
            "claude_data": None,
            "auto_tags": ["epoch-close"],
            "trigger": "skill",
            "quality_scores": {"overall": 75.0, "scores": {}},
            "quality_delta": None,
            "global_state": None,
            "state_transition": "phase_end",
            "epoch_summary": {"entries": 5, "builds": 3},
        },
    }
    return entries


@pytest.fixture
def mock_archive_index(mock_archive_entries: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Create a mock archive index."""
    # Build indices
    by_tag: Dict[str, list] = {}
    by_project: Dict[str, list] = {}
    latest_by_project: Dict[str, str] = {}

    for entry_id, entry in mock_archive_entries.items():
        project = entry["project"]
        all_tags = entry["tags"] + entry["auto_tags"]

        # Update by_project
        if project not in by_project:
            by_project[project] = []
        by_project[project].append(entry_id)

        # Update by_tag
        for tag in all_tags:
            if tag not in by_tag:
                by_tag[tag] = []
            by_tag[tag].append(entry_id)

        # Update latest_by_project
        if project not in latest_by_project or entry_id > latest_by_project[project]:
            latest_by_project[project] = entry_id

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
def mock_archive_dir(tmp_path: Path, mock_archive_index: Dict[str, Any]) -> Path:
    """Create a mock archive directory with test data."""
    archive_dir = tmp_path / "storage"
    archive_dir.mkdir()

    # Write archive index
    index_path = archive_dir / "archive_index.json"
    with open(index_path, "w") as f:
        json.dump(mock_archive_index, f)

    # Create project directories with screenshots
    for project in ["SBSTest", "GCR"]:
        project_dir = archive_dir / project
        project_dir.mkdir()

        # Create latest directory
        latest_dir = project_dir / "latest"
        latest_dir.mkdir()

        # Create a capture.json
        capture_data = {
            "timestamp": datetime.now().isoformat(),
            "project": project,
            "pages": ["dashboard", "dep_graph"],
        }
        with open(latest_dir / "capture.json", "w") as f:
            json.dump(capture_data, f)

        # Create mock screenshots (minimal valid PNG header)
        png_header = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D,  # IHDR length
            0x49, 0x48, 0x44, 0x52,  # IHDR
            0x00, 0x00, 0x00, 0x01,  # width: 1
            0x00, 0x00, 0x00, 0x01,  # height: 1
            0x08, 0x02,  # bit depth, color type
            0x00, 0x00, 0x00,  # compression, filter, interlace
            0x90, 0x77, 0x53, 0xDE,  # CRC
            0x00, 0x00, 0x00, 0x0C,  # IDAT length
            0x49, 0x44, 0x41, 0x54,  # IDAT
            0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0xFF, 0x00,  # compressed data
            0x05, 0xFE, 0x02, 0xFE,  # CRC
            0x00, 0x00, 0x00, 0x00,  # IEND length
            0x49, 0x45, 0x4E, 0x44,  # IEND
            0xAE, 0x42, 0x60, 0x82,  # CRC
        ])
        for page in ["dashboard", "dep_graph", "paper_tex", "pdf_tex"]:
            (latest_dir / f"{page}.png").write_bytes(png_header)

        # Create archive directory with timestamped snapshots
        archive_subdir = project_dir / "archive"
        archive_subdir.mkdir()

        # Create a timestamped archive
        ts_dir = archive_subdir / "2026-01-31_10-21-19"
        ts_dir.mkdir()
        (ts_dir / "dashboard.png").write_bytes(png_header)
        (ts_dir / "dep_graph.png").write_bytes(png_header)

    return archive_dir


# =============================================================================
# Mock Oracle Data
# =============================================================================


@pytest.fixture
def mock_oracle_content() -> str:
    """Return mock oracle markdown content."""
    return '''# SBS Oracle

## File Map

| Concept | Primary Location | Notes |
|---------|------------------|-------|
| Graph layout | `Dress/Graph/Layout.lean` | Sugiyama algorithm |
| Status colors | `Dress/Graph/Svg.lean` | Canonical hex values |
| CLI entry | `dev/scripts/sbs/cli.py` | Main CLI dispatcher |
| Archive entry | `dev/scripts/sbs/archive/entry.py` | Entry dataclass |
| Build pipeline | `dev/scripts/build.py` | One-click build script |

## Concepts

| Concept | Location | Notes |
|---------|----------|-------|
| Sugiyama layout | `Dress/Graph/Layout.lean` | ~1500 lines, layer assignment |
| 6-status model | `Dress/Graph/Svg.lean` | notReady, ready, sorry, proven, fullyProven, mathlibReady |
| Epoch | Archive system | Period between skill-triggered entries |
| Build facet | Lake build | dressed, blueprint, depGraph |
| Rainbow brackets | `Verso/Code/Highlighted.lean` | toHtmlRainbow function |

## Architecture

The SBS toolchain consists of several repos:
- SubVerso: Syntax highlighting (fork with O(1) indexed lookups)
- Verso: Document framework (fork with SBSBlueprint/VersoPaper genres)
- LeanArchitect: @[blueprint] attribute with 8 metadata + 3 status options
- Dress: Artifact generation + graph layout + validation
- Runway: Site generator + dashboard + paper/PDF

## Known Issues

- Verso LaTeX export not implemented
- Dashboard does NOT show chapter sidebar (intentional)
- SubVerso highlighting is 93-99% of build time
'''


@pytest.fixture
def mock_parsed_oracle(mock_oracle_content: str) -> Dict[str, Any]:
    """Return pre-parsed oracle sections."""
    return {
        "file_map": {
            "Dress/Graph/Layout.lean": {"section": "File Map", "concept": "Graph layout", "notes": "Sugiyama algorithm"},
            "Dress/Graph/Svg.lean": {"section": "File Map", "concept": "Status colors", "notes": "Canonical hex values"},
            "dev/scripts/sbs/cli.py": {"section": "File Map", "concept": "CLI entry", "notes": "Main CLI dispatcher"},
            "dev/scripts/sbs/archive/entry.py": {"section": "File Map", "concept": "Archive entry", "notes": "Entry dataclass"},
            "dev/scripts/build.py": {"section": "File Map", "concept": "Build pipeline", "notes": "One-click build script"},
        },
        "concept_index": [
            {"name": "Graph layout", "location": "Dress/Graph/Layout.lean", "notes": "Sugiyama algorithm", "section": "File Map"},
            {"name": "Status colors", "location": "Dress/Graph/Svg.lean", "notes": "Canonical hex values", "section": "File Map"},
            {"name": "Sugiyama layout", "location": "Dress/Graph/Layout.lean", "notes": "~1500 lines, layer assignment", "section": "Concepts"},
            {"name": "6-status model", "location": "Dress/Graph/Svg.lean", "notes": "notReady, ready, sorry, proven, fullyProven, mathlibReady", "section": "Concepts"},
            {"name": "Epoch", "location": "Archive system", "notes": "Period between skill-triggered entries", "section": "Concepts"},
        ],
        "sections": {
            "File Map": "| Concept | Primary Location | Notes |\n|---------|------------------|-------|\n...",
            "Concepts": "| Concept | Location | Notes |\n|---------|----------|-------|\n...",
            "Architecture": "The SBS toolchain consists of several repos:\n...",
            "Known Issues": "- Verso LaTeX export not implemented\n...",
        },
        "raw_content": "",  # Would be the full content
    }


# =============================================================================
# Mock Context
# =============================================================================


@pytest.fixture
def mock_mcp_context() -> MagicMock:
    """Create a mock MCP context for tool calls."""
    ctx = MagicMock()
    ctx.request_context = MagicMock()
    return ctx


# =============================================================================
# Test Runner Output Samples
# =============================================================================


@pytest.fixture
def sample_passing_output() -> str:
    """Sample pytest output with all tests passing."""
    return """============================= test session starts ==============================
platform darwin -- Python 3.14.0, pytest-8.0.0, pluggy-1.0.0
rootdir: /Users/eric/project
collected 10 items

tests/test_example.py ..........                                         [100%]

============================== 10 passed in 1.23s ==============================
"""


@pytest.fixture
def sample_failing_output() -> str:
    """Sample pytest output with failures."""
    return """============================= test session starts ==============================
platform darwin -- Python 3.14.0, pytest-8.0.0, pluggy-1.0.0
rootdir: /Users/eric/project
collected 10 items

tests/test_example.py ...F..F...                                         [100%]

=================================== FAILURES ===================================
FAILED tests/test_example.py::test_one - AssertionError: Expected 5 but got 3
FAILED tests/test_example.py::test_two - ValueError: Invalid input

============================== 2 failed, 8 passed in 2.45s =====================
"""


@pytest.fixture
def sample_mixed_output() -> str:
    """Sample pytest output with mixed results."""
    return """============================= test session starts ==============================
platform darwin -- Python 3.14.0, pytest-8.0.0, pluggy-1.0.0
collected 20 items

tests/test_suite.py ....sss..F.E....s...                                 [100%]

=================================== FAILURES ===================================
FAILED tests/test_suite.py::test_validation - AssertionError: Schema mismatch

=================================== ERRORS =====================================
ERROR tests/test_suite.py::test_network - ConnectionError: Timeout

============================= 1 failed, 1 error, 4 skipped, 14 passed in 5.67s =
"""


# =============================================================================
# Validation Output Samples
# =============================================================================


@pytest.fixture
def validation_passing_output() -> str:
    """Sample validation output with passing scores."""
    return """Running validation for SBSTest...
t5-color-match: 100.0 (PASS)
t6-css-variables: 95.5 (PASS)

Overall quality score: 97.75%
All validators passed!
"""


@pytest.fixture
def validation_failing_output() -> str:
    """Sample validation output with failures."""
    return """Running validation for SBSTest...
t5-color-match: 80.0 (FAIL)
t6-css-variables: 100.0 (PASS)

Overall quality score: 90.0%
compliance: needs attention - 1 validator(s) failed
"""
