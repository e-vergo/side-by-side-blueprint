"""
Theme and Dark Mode Tests

Verifies theme toggle presence, dark mode CSS coverage,
and design invariants (status colors constant across themes).
"""

from __future__ import annotations

import re

import pytest

from .conftest import SiteArtifacts
from .helpers import parse_html, require_bs4, extract_css_block_variables


def _get_dark_mode_vars(css: str) -> set[str]:
    """Extract variable names from the dark mode block in CSS.

    Uses a direct regex rather than extract_css_block_variables because
    the selector contains brackets and quotes that complicate re.escape.
    """
    pattern = r'html\[data-theme="dark"\]\s*\{([^}]+)\}'
    match = re.search(pattern, css, re.DOTALL)
    if not match:
        pattern = r"html\[data-theme=[\"']dark[\"']\]\s*\{([^}]+)\}"
        match = re.search(pattern, css, re.DOTALL)
    if not match:
        return set()
    block = match.group(1)
    return {m.group(1) for m in re.finditer(r"(--[\w-]+)\s*:", block)}


# Verso pages are not MVP -- they use different templates
VERSO_PAGES = {"paper_verso", "blueprint_verso"}


def _all_js_content(site: SiteArtifacts) -> str:
    """Concatenate all JS asset content."""
    return "\n".join(site.js_assets.values())


def _all_css_content(site: SiteArtifacts) -> str:
    """Concatenate all CSS asset content."""
    return "\n".join(site.all_css.values())


# ---------------------------------------------------------------------------
# Theme Toggle (5 tests)
# ---------------------------------------------------------------------------


@pytest.mark.evergreen
class TestThemeToggle:
    """Tests for theme toggle presence and behaviour."""

    def test_theme_toggle_on_all_pages(self, sbstest_site: SiteArtifacts):
        """Theme toggle button present on every runway HTML page."""
        require_bs4()
        pages = sbstest_site.list_pages()
        assert pages, "No HTML pages found in runway output"

        for page_name in pages:
            if page_name in VERSO_PAGES:
                continue
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            toggles = soup.select(".theme-toggle")
            assert toggles, f"Page '{page_name}' missing .theme-toggle element"

    def test_theme_toggle_js_sets_data_theme(self, sbstest_site: SiteArtifacts):
        """plastex.js contains the data-theme attribute setter."""
        js = _all_js_content(sbstest_site)
        assert js, "No JS assets found"
        assert "data-theme" in js, "JS assets should reference data-theme attribute"

    def test_theme_persists_to_localstorage(self, sbstest_site: SiteArtifacts):
        """Theme toggle persists choice via localStorage with sbs-theme key."""
        js = _all_js_content(sbstest_site)
        assert "localStorage" in js, "JS should use localStorage for theme persistence"
        assert "sbs-theme" in js, "JS should use 'sbs-theme' localStorage key"

    def test_no_system_preference_autodetect(self, sbstest_site: SiteArtifacts):
        """Theme must NOT auto-detect system preference — manual toggle only (#172)."""
        combined = _all_css_content(sbstest_site) + "\n" + _all_js_content(sbstest_site)
        assert "prefers-color-scheme" not in combined, (
            "Assets should not contain prefers-color-scheme; theme is manual-only"
        )

    def test_pages_no_hardcoded_theme(self, sbstest_site: SiteArtifacts):
        """No page HTML has a hardcoded data-theme attribute (set dynamically by JS)."""
        pages = sbstest_site.list_pages()
        assert pages, "No HTML pages found"

        for page_name in pages:
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            assert 'data-theme=' not in html, (
                f"Page '{page_name}' has hardcoded data-theme attribute; "
                "theme should be set dynamically by JS"
            )


# ---------------------------------------------------------------------------
# Dark Mode CSS Coverage (8 tests)
# ---------------------------------------------------------------------------


@pytest.mark.evergreen
class TestDarkModeCSSCoverage:
    """Tests that dark mode overrides the required CSS variable categories."""

    def test_dark_mode_block_exists(self, sbstest_site: SiteArtifacts):
        """common.css contains the html[data-theme="dark"] selector block."""
        css = sbstest_site.css
        assert 'html[data-theme="dark"]' in css, (
            'common.css must contain html[data-theme="dark"] block'
        )

    def test_dark_overrides_backgrounds(self, sbstest_site: SiteArtifacts):
        """Dark block overrides page and surface background variables."""
        dark_vars = _get_dark_mode_vars(sbstest_site.css)
        assert dark_vars, "Could not parse dark mode block"
        assert "--sbs-bg-page" in dark_vars, "Dark mode must override --sbs-bg-page"
        assert "--sbs-bg-surface" in dark_vars, "Dark mode must override --sbs-bg-surface"

    def test_dark_overrides_text(self, sbstest_site: SiteArtifacts):
        """Dark block overrides text color variables."""
        dark_vars = _get_dark_mode_vars(sbstest_site.css)
        assert "--sbs-text" in dark_vars, "Dark mode must override --sbs-text"
        assert "--sbs-text-muted" in dark_vars, "Dark mode must override --sbs-text-muted"

    def test_dark_overrides_borders(self, sbstest_site: SiteArtifacts):
        """Dark block overrides border variable."""
        dark_vars = _get_dark_mode_vars(sbstest_site.css)
        assert "--sbs-border" in dark_vars, "Dark mode must override --sbs-border"

    def test_dark_overrides_links(self, sbstest_site: SiteArtifacts):
        """Dark block overrides link color variables."""
        dark_vars = _get_dark_mode_vars(sbstest_site.css)
        assert "--sbs-link" in dark_vars, "Dark mode must override --sbs-link"
        assert "--sbs-link-hover" in dark_vars, "Dark mode must override --sbs-link-hover"

    def test_dark_overrides_heading(self, sbstest_site: SiteArtifacts):
        """Dark block overrides heading color variable."""
        dark_vars = _get_dark_mode_vars(sbstest_site.css)
        assert "--sbs-heading" in dark_vars, "Dark mode must override --sbs-heading"

    def test_dark_overrides_accent(self, sbstest_site: SiteArtifacts):
        """Dark block overrides accent color variable."""
        dark_vars = _get_dark_mode_vars(sbstest_site.css)
        assert "--sbs-accent" in dark_vars, "Dark mode must override --sbs-accent"

    def test_dark_overrides_graph_vars(self, sbstest_site: SiteArtifacts):
        """Dark block overrides graph-related variables."""
        dark_vars = _get_dark_mode_vars(sbstest_site.css)
        for var in ("--sbs-graph-bg", "--sbs-graph-edge", "--sbs-graph-edge-hover"):
            assert var in dark_vars, f"Dark mode must override {var}"


# ---------------------------------------------------------------------------
# Dark Mode Design Invariants (3 tests)
# ---------------------------------------------------------------------------


@pytest.mark.evergreen
class TestDarkModeDesign:
    """Tests for dark mode design decisions and invariants."""

    def test_status_colors_constant_across_themes(self, sbstest_site: SiteArtifacts):
        """Status colors are NOT overridden in dark mode (intentionally constant)."""
        dark_vars = _get_dark_mode_vars(sbstest_site.css)
        status_vars = {
            "--sbs-status-not-ready",
            "--sbs-status-ready",
            "--sbs-status-sorry",
            "--sbs-status-proven",
            "--sbs-status-fully-proven",
            "--sbs-status-mathlib-ready",
        }
        overridden = status_vars & dark_vars
        assert not overridden, (
            f"Status colors should be constant across themes but found "
            f"dark overrides for: {overridden}"
        )

    def test_no_prefers_color_scheme_media_query(self, sbstest_site: SiteArtifacts):
        """common.css must NOT have @media (prefers-color-scheme: dark) — removed per #172."""
        css = sbstest_site.css
        assert "@media (prefers-color-scheme: dark)" not in css, (
            "common.css must not include @media (prefers-color-scheme: dark); "
            "auto-detect was removed per #172"
        )

    def test_dark_mode_badge_vars_overridden(self, sbstest_site: SiteArtifacts):
        """Dark block overrides badge variables for verified and progress."""
        dark_vars = _get_dark_mode_vars(sbstest_site.css)
        assert "--sbs-badge-verified-bg" in dark_vars, (
            "Dark mode must override --sbs-badge-verified-bg"
        )
        assert "--sbs-badge-progress-bg" in dark_vars, (
            "Dark mode must override --sbs-badge-progress-bg"
        )
