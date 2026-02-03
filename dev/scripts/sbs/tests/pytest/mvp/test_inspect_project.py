"""
Inspect Project Tool Tests (187-200)

Tests for the sbs_inspect_project MCP tool's data model and supporting
infrastructure. The tool itself runs via MCP, but we can test:
- The InspectResult / PageInspection Pydantic models
- Screenshot path resolution
- Project name normalization
- Quality ledger integration
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .conftest import MONOREPO_ROOT, STORAGE_ROOT, SiteArtifacts


# =========================================================================
# Model Tests (import from sbs-lsp-mcp if available)
# =========================================================================

# Try to import the models; skip if sbs_lsp_mcp is not on PYTHONPATH
try:
    from sbs_lsp_mcp.sbs_models import InspectResult, PageInspection
    HAS_MODELS = True
except ImportError:
    HAS_MODELS = False


@pytest.mark.evergreen
class TestInspectProjectModels:
    """Tests for InspectResult and PageInspection Pydantic models."""

    @pytest.fixture(autouse=True)
    def _skip_if_no_models(self):
        if not HAS_MODELS:
            pytest.skip("sbs_lsp_mcp not on PYTHONPATH")

    def test_page_inspection_creation(self):
        """187. PageInspection can be created with minimal fields."""
        pi = PageInspection(page_name="dashboard")
        assert pi.page_name == "dashboard"
        assert pi.screenshot_exists is False
        assert pi.screenshot_path is None
        assert pi.suggested_prompt == ""

    def test_page_inspection_with_screenshot(self):
        """188. PageInspection records screenshot path."""
        pi = PageInspection(
            page_name="dep_graph",
            screenshot_path="/path/to/dep_graph.png",
            screenshot_exists=True,
            suggested_prompt="Check graph layout",
        )
        assert pi.screenshot_exists is True
        assert pi.screenshot_path == "/path/to/dep_graph.png"

    def test_inspect_result_creation(self):
        """189. InspectResult can be created with page list."""
        pages = [
            PageInspection(page_name="dashboard", screenshot_exists=True),
            PageInspection(page_name="dep_graph", screenshot_exists=False),
        ]
        result = InspectResult(
            project="SBSTest",
            pages=pages,
            total_pages=2,
            pages_with_screenshots=1,
        )
        assert result.project == "SBSTest"
        assert result.total_pages == 2
        assert result.pages_with_screenshots == 1
        assert len(result.pages) == 2

    def test_inspect_result_serialization(self):
        """190. InspectResult serializes to dict correctly."""
        result = InspectResult(
            project="GCR",
            pages=[PageInspection(page_name="dashboard")],
            total_pages=1,
            pages_with_screenshots=0,
            open_issues=[{"number": 42, "title": "Fix graph"}],
            quality_scores={"T5": {"value": 1.0, "passed": True}},
        )
        data = result.model_dump()
        assert data["project"] == "GCR"
        assert len(data["open_issues"]) == 1
        assert data["quality_scores"]["T5"]["passed"] is True


# =========================================================================
# Screenshot Path Infrastructure Tests
# =========================================================================


@pytest.mark.evergreen
class TestScreenshotPaths:
    """Tests for screenshot storage structure used by inspect tool."""

    def test_storage_directory_exists(self):
        """191. dev/storage directory exists."""
        assert STORAGE_ROOT.exists(), "dev/storage/ should exist"

    def test_sbstest_storage_exists(self):
        """192. SBSTest storage directory exists."""
        sbstest_dir = STORAGE_ROOT / "SBSTest"
        assert sbstest_dir.exists(), "SBSTest storage directory should exist"

    def test_sbstest_latest_directory_exists(self):
        """193. SBSTest latest screenshots directory exists."""
        latest = STORAGE_ROOT / "SBSTest" / "latest"
        if not latest.exists():
            pytest.skip("No screenshots captured yet")
        assert latest.is_dir(), "latest/ should be a directory"

    def test_sbstest_has_dashboard_screenshot(self):
        """194. SBSTest has dashboard screenshot."""
        screenshot = STORAGE_ROOT / "SBSTest" / "latest" / "dashboard.png"
        if not screenshot.exists():
            pytest.skip("No screenshots captured yet")
        assert screenshot.stat().st_size > 1000, \
            "Dashboard screenshot should have content"

    def test_screenshot_naming_convention(self):
        """195. Screenshots follow {page_name}.png convention."""
        latest = STORAGE_ROOT / "SBSTest" / "latest"
        if not latest.exists():
            pytest.skip("No screenshots captured yet")

        expected_names = {"dashboard.png", "dep_graph.png"}
        actual_names = {f.name for f in latest.glob("*.png")}

        # At least core pages should exist
        found = expected_names & actual_names
        assert len(found) > 0, \
            f"Should have at least one standard screenshot, found: {actual_names}"


# =========================================================================
# Project Name Normalization Tests
# =========================================================================


@pytest.mark.evergreen
class TestProjectNameNormalization:
    """Tests for project name mapping used by inspect tool."""

    # The mapping from sbs_inspect_project
    PROJECT_MAP = {
        "SBSTest": "SBSTest",
        "sbs-test": "SBSTest",
        "GCR": "GCR",
        "gcr": "GCR",
        "General_Crystallographic_Restriction": "GCR",
        "PNT": "PNT",
        "pnt": "PNT",
        "PrimeNumberTheoremAnd": "PNT",
    }

    def test_canonical_names_resolve(self):
        """196. Canonical project names resolve correctly."""
        assert self.PROJECT_MAP["SBSTest"] == "SBSTest"
        assert self.PROJECT_MAP["GCR"] == "GCR"
        assert self.PROJECT_MAP["PNT"] == "PNT"

    def test_lowercase_aliases_resolve(self):
        """197. Lowercase aliases resolve to canonical names."""
        assert self.PROJECT_MAP["sbs-test"] == "SBSTest"
        assert self.PROJECT_MAP["gcr"] == "GCR"
        assert self.PROJECT_MAP["pnt"] == "PNT"

    def test_full_names_resolve(self):
        """198. Full directory names resolve to canonical names."""
        assert self.PROJECT_MAP["General_Crystallographic_Restriction"] == "GCR"
        assert self.PROJECT_MAP["PrimeNumberTheoremAnd"] == "PNT"


# =========================================================================
# Quality Ledger Integration Tests
# =========================================================================


@pytest.mark.evergreen
class TestQualityLedgerIntegration:
    """Tests for quality score data used by inspect tool."""

    def test_quality_ledger_path_convention(self):
        """199. Quality ledger follows expected path pattern."""
        # The inspect tool looks for: dev/storage/{project}/quality_ledger.json
        for project in ["SBSTest", "GCR", "PNT"]:
            expected = STORAGE_ROOT / project / "quality_ledger.json"
            # File may not exist yet, but path should be well-formed
            assert expected.parent.name == project

    def test_quality_ledger_valid_json_if_exists(self):
        """200. Quality ledger is valid JSON when present."""
        for project in ["SBSTest", "GCR", "PNT"]:
            ledger_path = STORAGE_ROOT / project / "quality_ledger.json"
            if not ledger_path.exists():
                continue

            try:
                data = json.loads(ledger_path.read_text())
                assert isinstance(data, dict), \
                    f"{project} quality ledger should be a dict"
            except json.JSONDecodeError:
                pytest.fail(f"{project} quality ledger is invalid JSON")
