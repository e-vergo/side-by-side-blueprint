"""
Visual Quality Tests (96-100) + Extended Visual Quality (126-145)

Verifies visual quality indicators, design elements, asset presence,
and cross-page coherence.
"""

from __future__ import annotations

import pytest

from .conftest import SiteArtifacts, MONOREPO_ROOT
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
            has_sun = "sun" in str(toggle).lower() or "\u2600" in str(toggle)
            has_moon = "moon" in str(toggle).lower() or "\u263e" in str(toggle)
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


# =========================================================================
# Extended: CSS Asset Coverage
# =========================================================================


@pytest.mark.evergreen
class TestCSSAssetCoverage:
    """Tests verifying all 4 CSS files are present and well-formed."""

    EXPECTED_CSS_FILES = ["common.css", "blueprint.css", "paper.css", "dep_graph.css"]

    def test_all_four_css_files_present(self, sbstest_site: SiteArtifacts):
        """126. All 4 CSS files exist in runway assets."""
        all_css = sbstest_site.all_css
        for filename in self.EXPECTED_CSS_FILES:
            assert filename in all_css, f"Missing CSS asset: {filename}"

    def test_common_css_has_root_variables(self, sbstest_site: SiteArtifacts):
        """127. common.css defines :root CSS custom properties."""
        css = sbstest_site.css
        assert ":root" in css, "common.css should define :root variables"
        assert "--" in css, "common.css should have CSS custom properties"

    def test_common_css_dark_mode_variables(self, sbstest_site: SiteArtifacts):
        """128. common.css defines dark mode overrides."""
        css = sbstest_site.css
        # Dark mode via data-theme or prefers-color-scheme
        has_dark = (
            '[data-theme="dark"]' in css
            or "prefers-color-scheme: dark" in css
            or ".dark" in css
        )
        assert has_dark, "common.css should have dark mode definitions"

    def test_blueprint_css_has_sidebar_styles(self, sbstest_site: SiteArtifacts):
        """129. blueprint.css defines sidebar styles."""
        all_css = sbstest_site.all_css
        blueprint = all_css.get("blueprint.css", "")
        if not blueprint:
            pytest.skip("blueprint.css not found")
        assert ".sidebar" in blueprint or ".toc" in blueprint, \
            "blueprint.css should have sidebar/toc styles"

    def test_blueprint_css_has_sbs_container(self, sbstest_site: SiteArtifacts):
        """130. blueprint.css defines side-by-side container styles."""
        all_css = sbstest_site.all_css
        blueprint = all_css.get("blueprint.css", "")
        if not blueprint:
            pytest.skip("blueprint.css not found")
        assert ".sbs-container" in blueprint or "side-by-side" in blueprint.lower(), \
            "blueprint.css should have SBS container styles"

    def test_paper_css_has_academic_styling(self, sbstest_site: SiteArtifacts):
        """131. paper.css defines academic paper styles."""
        all_css = sbstest_site.all_css
        paper = all_css.get("paper.css", "")
        if not paper:
            pytest.skip("paper.css not found")
        assert len(paper) > 100, "paper.css should have substantial content"

    def test_dep_graph_css_has_graph_styles(self, sbstest_site: SiteArtifacts):
        """132. dep_graph.css defines graph container styles."""
        all_css = sbstest_site.all_css
        dep_graph = all_css.get("dep_graph.css", "")
        if not dep_graph:
            pytest.skip("dep_graph.css not found")
        has_graph = ".graph-container" in dep_graph or "graph" in dep_graph.lower()
        assert has_graph, "dep_graph.css should have graph container styles"

    def test_css_files_non_trivial_size(self, sbstest_site: SiteArtifacts):
        """133. Each CSS file has meaningful content (not empty stubs)."""
        all_css = sbstest_site.all_css
        for filename in self.EXPECTED_CSS_FILES:
            content = all_css.get(filename, "")
            assert len(content) > 50, \
                f"{filename} should have non-trivial content (got {len(content)} chars)"


# =========================================================================
# Extended: JavaScript Asset Coverage
# =========================================================================


@pytest.mark.evergreen
class TestJSAssetCoverage:
    """Tests verifying JS assets are present and functional."""

    EXPECTED_JS_FILES = ["plastex.js", "verso-code.js"]

    def test_all_js_files_present(self, sbstest_site: SiteArtifacts):
        """134. Both JS files exist in runway assets."""
        js_assets = sbstest_site.js_assets
        for filename in self.EXPECTED_JS_FILES:
            assert filename in js_assets, f"Missing JS asset: {filename}"

    def test_plastex_js_has_proof_toggle(self, sbstest_site: SiteArtifacts):
        """135. plastex.js implements proof toggle."""
        js_assets = sbstest_site.js_assets
        plastex = js_assets.get("plastex.js", "")
        if not plastex:
            pytest.skip("plastex.js not found")
        has_toggle = "proof" in plastex.lower() or "toggle" in plastex.lower()
        assert has_toggle, "plastex.js should handle proof toggle"

    def test_plastex_js_has_theme_toggle(self, sbstest_site: SiteArtifacts):
        """136. plastex.js implements theme toggle."""
        js_assets = sbstest_site.js_assets
        plastex = js_assets.get("plastex.js", "")
        if not plastex:
            pytest.skip("plastex.js not found")
        has_theme = "theme" in plastex.lower()
        assert has_theme, "plastex.js should handle theme switching"

    def test_verso_code_js_has_hover_handling(self, sbstest_site: SiteArtifacts):
        """137. verso-code.js implements hover handling."""
        js_assets = sbstest_site.js_assets
        verso = js_assets.get("verso-code.js", "")
        if not verso:
            pytest.skip("verso-code.js not found")
        has_hover = "hover" in verso.lower() or "tippy" in verso.lower()
        assert has_hover, "verso-code.js should handle hovers"

    def test_verso_code_js_has_pan_zoom(self, sbstest_site: SiteArtifacts):
        """138. verso-code.js implements pan/zoom for graph."""
        js_assets = sbstest_site.js_assets
        verso = js_assets.get("verso-code.js", "")
        if not verso:
            pytest.skip("verso-code.js not found")
        has_zoom = "zoom" in verso.lower() or "scale" in verso.lower()
        assert has_zoom, "verso-code.js should handle pan/zoom"

    def test_verso_code_js_has_modal_handling(self, sbstest_site: SiteArtifacts):
        """139. verso-code.js implements modal handling."""
        js_assets = sbstest_site.js_assets
        verso = js_assets.get("verso-code.js", "")
        if not verso:
            pytest.skip("verso-code.js not found")
        has_modal = "modal" in verso.lower()
        assert has_modal, "verso-code.js should handle modals"

    def test_dashboard_loads_both_js_files(self, sbstest_site: SiteArtifacts):
        """140. Dashboard HTML references both JS assets."""
        html = sbstest_site.get_page("dashboard")
        assert "plastex.js" in html, "Dashboard should load plastex.js"
        assert "verso-code.js" in html, "Dashboard should load verso-code.js"


# =========================================================================
# Extended: Cross-Page Design Coherence
# =========================================================================


@pytest.mark.evergreen
class TestCrossPageCoherence:
    """Tests that common elements appear consistently across Runway-generated pages.

    Verso-generated pages (paper_verso, blueprint_verso) use Verso's own
    template system and are excluded from these checks.
    """

    # Verso pages use their own template, not Runway's
    VERSO_PAGES = {"paper_verso", "blueprint_verso"}

    def _runway_pages(self, site: SiteArtifacts) -> list[str]:
        """Return pages generated by Runway (excludes Verso pages)."""
        return [p for p in site.list_pages() if p not in self.VERSO_PAGES]

    def test_runway_pages_have_theme_toggle(self, sbstest_site: SiteArtifacts):
        """141. Theme toggle appears on all Runway-generated pages."""
        for page_name in self._runway_pages(sbstest_site):
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            toggle = soup.select(".theme-toggle, [data-theme-toggle]")
            assert len(toggle) > 0, f"Page '{page_name}' missing theme toggle"

    def test_runway_pages_load_css(self, sbstest_site: SiteArtifacts):
        """142. All Runway-generated pages reference common.css."""
        for page_name in self._runway_pages(sbstest_site):
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            assert "common.css" in html, \
                f"Page '{page_name}' does not load common.css"

    def test_all_pages_have_title(self, sbstest_site: SiteArtifacts):
        """143. All pages have <title> element."""
        pages = sbstest_site.list_pages()
        for page_name in pages:
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            title = soup.select_one("title")
            assert title is not None, f"Page '{page_name}' missing <title>"
            assert title.get_text(strip=True), f"Page '{page_name}' has empty <title>"

    def test_chapter_pages_have_navigation(self, sbstest_site: SiteArtifacts):
        """144. Chapter pages include sidebar navigation."""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if p not in ["index", "dep_graph",
                         "paper_tex", "pdf_tex", "paper_verso", "blueprint_verso"]]
        if not chapter_pages:
            pytest.skip("No chapter pages found")

        for page_name in chapter_pages:
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            nav = soup.select("nav.toc, nav, .sidebar")
            assert len(nav) > 0, \
                f"Chapter page '{page_name}' missing sidebar navigation"

    def test_dep_graph_page_loads_dep_graph_css(self, sbstest_site: SiteArtifacts):
        """145. Dep graph page loads dep_graph.css."""
        html = sbstest_site.get_page("dep_graph")
        if not html:
            pytest.skip("dep_graph.html not generated")
        assert "dep_graph.css" in html, \
            "Dep graph page should load dep_graph.css"


# =========================================================================
# Extended: Responsive Layout
# =========================================================================


@pytest.mark.evergreen
class TestResponsiveLayout:
    """Tests for responsive CSS considerations."""

    def test_media_queries_in_blueprint_css(self, sbstest_site: SiteArtifacts):
        """146. blueprint.css has responsive breakpoints."""
        all_css = sbstest_site.all_css
        blueprint = all_css.get("blueprint.css", "")
        if not blueprint:
            pytest.skip("blueprint.css not found")
        assert "@media" in blueprint, "blueprint.css should have media queries"

    def test_rainbow_brackets_have_six_colors(self, sbstest_site: SiteArtifacts):
        """147. Rainbow bracket CSS defines 6 color levels."""
        css = sbstest_site.css
        bracket_count = 0
        for i in range(1, 7):
            if f".lean-bracket-{i}" in css:
                bracket_count += 1
        assert bracket_count == 6, \
            f"Should have 6 rainbow bracket levels, found {bracket_count}"

    def test_status_dot_sizes_defined(self, sbstest_site: SiteArtifacts):
        """148. Status dot size variants are defined in CSS."""
        css = sbstest_site.css
        # All 4 dot size classes
        assert ".status-dot" in css, "Should have base .status-dot"
        # At least one size variant
        variants_found = sum(1 for v in [
            ".header-status-dot",
            ".paper-status-dot",
            ".modal-status-dot",
        ] if v in css)
        assert variants_found > 0, "Should have at least one status dot size variant"


# =========================================================================
# Extended: Source Asset Integrity
# =========================================================================


@pytest.mark.evergreen
class TestSourceAssetIntegrity:
    """Tests that source assets exist in the dress-blueprint-action repo."""

    SOURCE_ASSETS_DIR = MONOREPO_ROOT / "toolchain" / "dress-blueprint-action" / "assets"

    def test_source_assets_dir_exists(self):
        """149. dress-blueprint-action/assets directory exists."""
        assert self.SOURCE_ASSETS_DIR.exists(), \
            "Source assets directory should exist"

    def test_source_css_files_exist(self):
        """150. All 4 CSS source files exist."""
        for name in ["common.css", "blueprint.css", "paper.css", "dep_graph.css"]:
            path = self.SOURCE_ASSETS_DIR / name
            assert path.exists(), f"Source CSS file missing: {name}"

    def test_source_js_files_exist(self):
        """151. Both JS source files exist."""
        for name in ["plastex.js", "verso-code.js"]:
            path = self.SOURCE_ASSETS_DIR / name
            assert path.exists(), f"Source JS file missing: {name}"
