"""
Dashboard Tests (63-75)

Verifies dashboard page structure and content.
"""

from __future__ import annotations

import pytest

from .conftest import SiteArtifacts
from .helpers import parse_html


@pytest.mark.evergreen
class TestDashboardStructure:
    """Tests for dashboard page structure."""

    def test_dashboard_exists(self, sbstest_site: SiteArtifacts):
        """63. Dashboard page (index.html) exists."""
        html = sbstest_site.get_page("dashboard")
        assert html, "Dashboard should exist"
        assert len(html) > 1000, "Dashboard should have substantial content"

    def test_dashboard_title(self, sbstest_site: SiteArtifacts):
        """64. Dashboard has project title."""
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        title = soup.select_one("title, h1, .index-header")
        assert title, "Dashboard should have title"

    def test_dashboard_grid_layout(self, sbstest_site: SiteArtifacts):
        """65. Dashboard uses grid layout."""
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        grid = soup.select(".dashboard-grid, .dashboard-row, .dashboard-cell")
        assert len(grid) > 0, "Dashboard should have grid structure"

    def test_dashboard_stats_section(self, sbstest_site: SiteArtifacts):
        """66. Dashboard has stats/progress section."""
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        stats = soup.select(".stats-box, .progress-cell, .stats-pie")
        assert len(stats) > 0, "Dashboard should have stats section"

    def test_dashboard_pie_chart(self, sbstest_site: SiteArtifacts):
        """67. Dashboard has pie chart visualization."""
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        pie = soup.select(".stats-pie, svg circle")
        assert len(pie) > 0, "Dashboard should have pie chart"

    def test_dashboard_legend(self, sbstest_site: SiteArtifacts):
        """68. Dashboard has status legend."""
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        legend = soup.select(".stats-legend, .legend-item")
        assert len(legend) > 0, "Dashboard should have legend"

    def test_dashboard_completion_column(self, sbstest_site: SiteArtifacts):
        """69. Dashboard has completion statistics column."""
        html = sbstest_site.get_page("dashboard")

        # Check for completion-related content
        has_completion = "proven" in html.lower() and "sorry" in html.lower()
        assert has_completion, "Dashboard should show completion stats"

    def test_dashboard_attention_column(self, sbstest_site: SiteArtifacts):
        """70. Dashboard has attention statistics column."""
        html = sbstest_site.get_page("dashboard")

        # Check for attention-related content
        has_attention = "blocked" in html.lower() or "issues" in html.lower()
        assert has_attention, "Dashboard should show attention stats"


@pytest.mark.evergreen
class TestDashboardContent:
    """Tests for dashboard content sections."""

    def test_dashboard_key_declarations(self, sbstest_site: SiteArtifacts):
        """71. Dashboard has key declarations section."""
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        key_decls = soup.select(".key-declarations, .key-declarations-cell")
        assert len(key_decls) > 0, "Dashboard should have key declarations"

    def test_dashboard_checks_section(self, sbstest_site: SiteArtifacts):
        """72. Dashboard has checks/validation section."""
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        checks = soup.select(".checks-tile, .checks-list, .check-item")
        assert len(checks) > 0, "Dashboard should have checks section"

    def test_dashboard_navigation_links(self, sbstest_site: SiteArtifacts):
        """73. Dashboard has navigation sidebar."""
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        nav = soup.select("nav.toc, .sidebar-item")
        assert len(nav) > 0, "Dashboard should have navigation"

    def test_dashboard_dep_graph_link(self, sbstest_site: SiteArtifacts):
        """74. Dashboard links to dependency graph."""
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        dep_link = soup.select('a[href*="dep_graph"]')
        assert len(dep_link) > 0, "Dashboard should link to dep graph"

    def test_dashboard_total_count(self, sbstest_site: SiteArtifacts):
        """75. Dashboard shows total declaration count."""
        html = sbstest_site.get_page("dashboard")
        manifest = sbstest_site.manifest

        total = manifest.get("stats", {}).get("total", 0)
        assert str(total) in html, f"Dashboard should show total count {total}"
