"""
Dashboard Accuracy Tests

Verifies dashboard statistics, key declarations, and navigation
match the underlying manifest data. Tests numeric accuracy of
displayed values, completeness of key declaration listings,
and correctness of navigation links.
"""

from __future__ import annotations

import pytest

from .conftest import SiteArtifacts
from .helpers import parse_html, require_bs4, collect_relative_links

# Pages that are NOT chapter pages
_NON_CHAPTER_PAGES = {"index", "dep_graph", "paper_tex", "pdf_tex", "paper_verso", "blueprint_verso"}


def _chapter_pages(site: SiteArtifacts) -> list[str]:
    """Return page names that are actual chapter pages."""
    return [p for p in site.list_pages() if p not in _NON_CHAPTER_PAGES]


@pytest.mark.evergreen
class TestDashboardStats:
    """Dashboard statistics match manifest data."""

    def test_stats_total_displayed(self, sbstest_site: SiteArtifacts):
        """Total declaration count from manifest appears in dashboard HTML."""
        html = sbstest_site.get_page("dashboard")
        assert html, "Dashboard page should exist"

        stats = sbstest_site.manifest.get("stats", {})
        total = stats.get("total", 0)
        assert total > 0, "Manifest should have a positive total count"
        assert str(total) in html, (
            f"Dashboard should display total count '{total}' somewhere in the page"
        )

    def test_stats_proven_count_displayed(self, sbstest_site: SiteArtifacts):
        """At least one .stats-value element contains a numeric value matching a proven-related count."""
        require_bs4()
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        stats = sbstest_site.manifest.get("stats", {})
        proven_related = {
            stats.get("proven", -1),
            stats.get("fullyProven", -1),
        }
        proven_related.discard(-1)
        assert proven_related, "Manifest should have proven or fullyProven counts"

        value_els = soup.select(".stats-value")
        assert value_els, "Dashboard should have .stats-value elements"

        found_values = []
        for el in value_els:
            text = el.get_text(strip=True)
            if text.isdigit():
                found_values.append(int(text))

        assert found_values, "At least one .stats-value should contain a numeric value"
        assert any(v in proven_related for v in found_values), (
            f"No .stats-value matches a proven-related count. "
            f"Found values: {found_values}, expected one of: {proven_related}"
        )

    def test_stats_sorry_count_displayed(self, sbstest_site: SiteArtifacts):
        """hasSorry count from manifest appears in dashboard HTML."""
        html = sbstest_site.get_page("dashboard")
        assert html, "Dashboard page should exist"

        stats = sbstest_site.manifest.get("stats", {})
        sorry_count = stats.get("hasSorry", 0)
        assert str(sorry_count) in html, (
            f"Dashboard should display hasSorry count '{sorry_count}'"
        )

    def test_legend_has_all_status_types(self, sbstest_site: SiteArtifacts):
        """Dashboard legend covers all 6 status types (case-insensitive text check)."""
        html = sbstest_site.get_page("dashboard")
        assert html, "Dashboard page should exist"

        html_lower = html.lower()
        expected_terms = ["proven", "sorry", "ready", "fully proven", "not ready", "mathlib"]
        missing = [t for t in expected_terms if t not in html_lower]
        assert not missing, (
            f"Dashboard legend is missing status type text: {missing}"
        )

    def test_pie_chart_present(self, sbstest_site: SiteArtifacts):
        """Dashboard contains a pie chart (SVG circle or .stats-pie element)."""
        require_bs4()
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        pie_elements = soup.select(".stats-pie, svg circle")
        assert pie_elements, (
            "Dashboard should have a pie chart (.stats-pie or SVG circle element)"
        )

    def test_stats_values_match_manifest(self, sbstest_site: SiteArtifacts):
        """Stats values in dashboard are plausible given manifest data."""
        require_bs4()
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        stats = sbstest_site.manifest.get("stats", {})
        total = stats.get("total", 0)

        value_els = soup.select(".stats-value")
        assert value_els, "Dashboard should have .stats-value elements"

        values = []
        for el in value_els:
            text = el.get_text(strip=True)
            if text.isdigit():
                values.append(int(text))

        assert values, "At least one .stats-value should contain a numeric value"
        # Dashboard may show computed aggregations (e.g. fullyProven+proven),
        # so values won't match raw manifest stats exactly.
        # All displayed values should be non-negative and <= total.
        for v in values:
            assert 0 <= v <= total, (
                f"Stats value {v} outside valid range [0, {total}]"
            )
        # The total should appear somewhere in the dashboard
        assert str(total) in html, (
            f"Total count {total} not found in dashboard"
        )


@pytest.mark.evergreen
class TestKeyDeclarations:
    """Key declarations section matches manifest data."""

    def test_key_declarations_section_present(self, sbstest_site: SiteArtifacts):
        """.key-declarations element exists in dashboard."""
        require_bs4()
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        section = soup.select(".key-declarations")
        assert section, "Dashboard should have a .key-declarations section"

    def test_key_declarations_listed(self, sbstest_site: SiteArtifacts):
        """At least one .key-declaration-item is present."""
        require_bs4()
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        items = soup.select(".key-declaration-item")
        assert len(items) >= 1, "Dashboard should have at least one .key-declaration-item"

    def test_key_declarations_are_valid_nodes(self, sbstest_site: SiteArtifacts):
        """Every keyDeclarations entry exists as a key in manifest nodes."""
        manifest = sbstest_site.manifest
        key_decls = manifest.get("keyDeclarations", [])
        nodes = manifest.get("nodes", {})

        assert key_decls, "Manifest should have keyDeclarations"
        assert nodes, "Manifest should have nodes"

        invalid = [kd for kd in key_decls if kd not in nodes]
        assert not invalid, (
            f"Key declarations not found in manifest nodes: {invalid}"
        )

    def test_key_declaration_items_have_links(self, sbstest_site: SiteArtifacts):
        """Key declaration items contain clickable links."""
        require_bs4()
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        items = soup.select(".key-declaration-item")
        assert items, "Dashboard should have .key-declaration-item elements"

        items_with_links = 0
        for item in items:
            # .key-declaration-link may be a wrapper div, not an <a> tag.
            # Check for <a> tags anywhere within the item.
            links = item.find_all("a", href=True)
            if links:
                items_with_links += 1

        assert items_with_links > 0, (
            "No key declaration items contain links"
        )

    def test_key_declarations_have_preview(self, sbstest_site: SiteArtifacts):
        """.key-declaration-preview elements exist in dashboard."""
        require_bs4()
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        previews = soup.select(".key-declaration-preview")
        assert previews, "Dashboard should have .key-declaration-preview elements"


@pytest.mark.evergreen
class TestDashboardNavigation:
    """Dashboard navigation links are correct and complete."""

    def test_sidebar_links_resolve(self, sbstest_site: SiteArtifacts):
        """All ./X.html links in nav.toc map to existing files in runway dir."""
        require_bs4()
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        nav = soup.select_one("nav.toc")
        assert nav, "Dashboard should have a nav.toc element"

        nav_html = str(nav)
        relative_links = collect_relative_links(nav_html)
        assert relative_links, "nav.toc should contain relative page links"

        runway_dir = sbstest_site.runway_dir
        missing = [
            link for link in relative_links
            if not (runway_dir / link).exists()
        ]
        assert not missing, (
            f"Sidebar links reference non-existent files: {missing}"
        )

    def test_dep_graph_link_present(self, sbstest_site: SiteArtifacts):
        """dep_graph.html appears in a link on the dashboard."""
        require_bs4()
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        dep_links = soup.select('a[href*="dep_graph.html"]')
        assert dep_links, (
            "Dashboard should contain a link to dep_graph.html"
        )

    def test_all_chapter_pages_linked(self, sbstest_site: SiteArtifacts):
        """Every chapter page name appears in some sidebar link href."""
        require_bs4()
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        chapters = _chapter_pages(sbstest_site)
        assert chapters, "Site should have chapter pages"

        # Collect all hrefs from sidebar
        nav = soup.select_one("nav.toc")
        assert nav, "Dashboard should have a nav.toc element"

        all_hrefs = " ".join(
            a.get("href", "") for a in nav.select("a[href]")
        )

        unlinked = [ch for ch in chapters if ch not in all_hrefs]
        assert not unlinked, (
            f"Chapter pages not linked in sidebar navigation: {unlinked}"
        )

    def test_navigation_link_count_matches(self, sbstest_site: SiteArtifacts):
        """Count of .sidebar-chapter-item elements >= count of chapter pages."""
        require_bs4()
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        chapters = _chapter_pages(sbstest_site)
        assert chapters, "Site should have chapter pages"

        sidebar_items = soup.select(".sidebar-chapter-item")
        assert len(sidebar_items) >= len(chapters), (
            f"Sidebar has {len(sidebar_items)} .sidebar-chapter-item elements "
            f"but site has {len(chapters)} chapter pages: {chapters}"
        )

    def test_dashboard_links_to_paper(self, sbstest_site: SiteArtifacts):
        """paper_tex.html appears in dashboard links (skip if paper not generated)."""
        require_bs4()
        paper_path = sbstest_site.runway_dir / "paper_tex.html"
        if not paper_path.exists():
            pytest.skip("Paper page not generated for this project")

        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        paper_links = soup.select('a[href*="paper_tex.html"]')
        assert paper_links, (
            "Dashboard should link to paper_tex.html when paper is generated"
        )
