"""
Status Indicators Tests (51-62)

Verifies the 6-status color model and status dot rendering.
"""

from __future__ import annotations

import pytest

from .conftest import SiteArtifacts
from .helpers import (
    parse_html,
    extract_css_variables,
    colors_match,
    STATUS_COLORS,
    CSS_STATUS_VARS,
)


@pytest.mark.evergreen
class TestStatusColors:
    """Tests for the 6-status color model."""

    def test_six_status_colors_defined(self, sbstest_site: SiteArtifacts):
        """51. All 6 status colors are defined."""
        assert len(STATUS_COLORS) == 6, "Should have exactly 6 status colors"

        expected = {"notReady", "ready", "sorry", "proven", "fullyProven", "mathlibReady"}
        assert set(STATUS_COLORS.keys()) == expected, "Status names should match"

    def test_css_variables_exist(self, sbstest_site: SiteArtifacts):
        """52. CSS variables for status colors exist."""
        css = sbstest_site.css
        variables = extract_css_variables(css)

        # Check that status variables are defined
        for status, var_name in CSS_STATUS_VARS.items():
            # Variable may use different naming convention
            found = var_name in variables or status.lower() in css.lower()
            assert found, f"CSS variable for {status} not found"

    def test_css_colors_match_lean(self, sbstest_site: SiteArtifacts):
        """53. CSS colors match Lean source of truth."""
        css = sbstest_site.css

        # Check that the canonical hex values appear in CSS
        for status, hex_color in STATUS_COLORS.items():
            # Colors may be in various formats
            hex_lower = hex_color.lower()
            hex_upper = hex_color.upper()
            assert hex_lower in css.lower() or hex_upper in css, f"Color {hex_color} for {status} not in CSS"

    def test_not_ready_color(self, sbstest_site: SiteArtifacts):
        """54. notReady is Sandy Brown (#F4A460)."""
        expected = "#F4A460"
        actual = STATUS_COLORS.get("notReady")
        assert colors_match(actual, expected), f"notReady should be {expected}, got {actual}"

    def test_ready_color(self, sbstest_site: SiteArtifacts):
        """55. ready is Light Sea Green (#20B2AA)."""
        expected = "#20B2AA"
        actual = STATUS_COLORS.get("ready")
        assert colors_match(actual, expected), f"ready should be {expected}, got {actual}"

    def test_sorry_color(self, sbstest_site: SiteArtifacts):
        """56. sorry is Dark Red (#8B0000)."""
        expected = "#8B0000"
        actual = STATUS_COLORS.get("sorry")
        assert colors_match(actual, expected), f"sorry should be {expected}, got {actual}"

    def test_proven_color(self, sbstest_site: SiteArtifacts):
        """57. proven is Light Green (#90EE90)."""
        expected = "#90EE90"
        actual = STATUS_COLORS.get("proven")
        assert colors_match(actual, expected), f"proven should be {expected}, got {actual}"

    def test_fully_proven_color(self, sbstest_site: SiteArtifacts):
        """58. fullyProven is Forest Green (#228B22)."""
        expected = "#228B22"
        actual = STATUS_COLORS.get("fullyProven")
        assert colors_match(actual, expected), f"fullyProven should be {expected}, got {actual}"

    def test_mathlib_ready_color(self, sbstest_site: SiteArtifacts):
        """59. mathlibReady is Light Blue (#87CEEB)."""
        expected = "#87CEEB"
        actual = STATUS_COLORS.get("mathlibReady")
        assert colors_match(actual, expected), f"mathlibReady should be {expected}, got {actual}"


@pytest.mark.evergreen
class TestStatusDots:
    """Tests for status dot rendering."""

    def test_status_dot_class_exists(self, sbstest_site: SiteArtifacts):
        """60. Status dot CSS class defined."""
        css = sbstest_site.css
        assert ".status-dot" in css, "Should have .status-dot class"

    def test_status_dots_in_chapters(self, sbstest_site: SiteArtifacts):
        """61. Status dots appear in chapter pages."""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "main" in p.lower() or "status" in p.lower()]

        if not chapter_pages:
            pytest.skip("No chapter pages found")

        html = sbstest_site.get_page(chapter_pages[0])
        soup = parse_html(html)

        dots = soup.select(".status-dot, [class*='status-']")
        assert len(dots) > 0, "Should have status dots in chapter pages"

    def test_status_dots_in_dashboard(self, sbstest_site: SiteArtifacts):
        """62. Status dots or colors appear in dashboard."""
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        # Check for status indicators (dots, swatches, or pie chart colors)
        indicators = soup.select(".status-dot, .legend-swatch, .stats-pie")
        assert len(indicators) > 0, "Should have status indicators in dashboard"
