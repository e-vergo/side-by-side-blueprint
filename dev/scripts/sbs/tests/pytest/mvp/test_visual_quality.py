"""
Visual Quality Tests (96-100)

Verifies visual quality indicators and design elements.
"""

from __future__ import annotations

import pytest

from .conftest import SiteArtifacts
from .helpers import parse_html


@pytest.mark.evergreen
class TestVisualQuality:
    """Tests for visual quality and design elements."""

    def test_theme_toggle_exists(self, sbstest_site: SiteArtifacts):
        """96. Theme toggle button exists."""
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        toggle = soup.select(".theme-toggle, [data-theme-toggle]")
        assert len(toggle) > 0, "Should have theme toggle"

    def test_theme_toggle_icons(self, sbstest_site: SiteArtifacts):
        """97. Theme toggle has sun/moon icons."""
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        # Check for sun and moon indicators
        toggle = soup.select_one(".theme-toggle")
        if toggle:
            has_sun = "sun" in str(toggle).lower() or "☀" in str(toggle)
            has_moon = "moon" in str(toggle).lower() or "☾" in str(toggle)
            assert has_sun and has_moon, "Theme toggle should have sun and moon"
        else:
            pytest.skip("No theme toggle found")

    def test_rainbow_bracket_css_defined(self, sbstest_site: SiteArtifacts):
        """98. Rainbow bracket CSS classes defined."""
        css = sbstest_site.css

        # Check for bracket color classes
        has_bracket_classes = ".lean-bracket" in css or "bracket" in css.lower()
        assert has_bracket_classes, "Should have bracket highlighting CSS"

    def test_code_font_specified(self, sbstest_site: SiteArtifacts):
        """99. Monospace font specified for code."""
        css = sbstest_site.css

        has_mono = "monospace" in css.lower() or "font-family" in css
        assert has_mono, "Should specify code font"

    def test_tippy_tooltips_loaded(self, sbstest_site: SiteArtifacts):
        """100. Tippy.js loaded for tooltips."""
        html = sbstest_site.get_page("dashboard")

        has_tippy = "tippy" in html.lower()
        assert has_tippy, "Should load Tippy.js for tooltips"
