"""
Cross-Page Consistency Tests

Verifies no horizontal scrollbars, cross-page uniformity, design language
consistency, and build output completeness across all generated pages.
"""

from __future__ import annotations

import re

import pytest

from .conftest import SiteArtifacts
from .helpers import parse_html, require_bs4


# Non-chapter pages that have distinct layouts
NON_CHAPTER_PAGES = {"index", "dep_graph", "paper_tex", "pdf_tex", "paper_verso", "blueprint_verso"}

# Verso pages are not MVP -- they use different templates and lack standard elements
VERSO_PAGES = {"paper_verso", "blueprint_verso"}


# =========================================================================
# No Horizontal Scrollbars
# =========================================================================


@pytest.mark.evergreen
class TestNoHorizontalScrollbars:
    """Tests that CSS prevents horizontal overflow on all pages."""

    def test_css_overflow_handling(self, sbstest_site: SiteArtifacts):
        """Combined CSS contains overflow-x, overflow-wrap, or word-break rules."""
        combined = "\n".join(sbstest_site.all_css.values())
        has_overflow = (
            "overflow-x" in combined
            or "overflow-wrap" in combined
            or "word-break" in combined
        )
        assert has_overflow, (
            "CSS should contain at least one of: overflow-x, overflow-wrap, word-break"
        )

    def test_sbs_container_bounded_width(self, sbstest_site: SiteArtifacts):
        """blueprint.css constrains .sbs-container width."""
        blueprint = sbstest_site.all_css.get("blueprint.css", "")
        assert blueprint, "blueprint.css should exist"

        # Find .sbs-container rules and check for width constraints
        has_sbs = ".sbs-container" in blueprint
        assert has_sbs, "blueprint.css should define .sbs-container"

        has_width_constraint = "max-width" in blueprint or "width" in blueprint
        assert has_width_constraint, (
            "blueprint.css should contain max-width or width rules for layout control"
        )

    def test_code_blocks_overflow_wrap(self, sbstest_site: SiteArtifacts):
        """CSS has overflow handling near pre or code elements."""
        combined = "\n".join(sbstest_site.all_css.values())

        # Look for overflow-related rules near pre/code selectors
        has_pre_overflow = bool(re.search(r'pre[^}]*overflow', combined, re.DOTALL))
        has_code_overflow = bool(re.search(r'code[^}]*overflow', combined, re.DOTALL))
        has_overflow_near_code = bool(
            re.search(r'overflow[^}]*(?:pre|code)', combined, re.DOTALL)
        )

        assert has_pre_overflow or has_code_overflow or has_overflow_near_code, (
            "CSS should have overflow handling for pre or code elements"
        )

    def test_no_fixed_width_exceeding_viewport(self, sbstest_site: SiteArtifacts):
        """No CSS pixel width exceeds 1920px."""
        combined = "\n".join(sbstest_site.all_css.values())

        oversized = []
        for match in re.finditer(r'width:\s*(\d+)px', combined):
            px = int(match.group(1))
            if px > 1920:
                oversized.append(f"{px}px at position {match.start()}")

        assert not oversized, (
            f"Found pixel widths exceeding 1920px: {', '.join(oversized)}"
        )


# =========================================================================
# Cross-Page Uniformity
# =========================================================================


@pytest.mark.evergreen
class TestCrossPageUniformity:
    """Tests that all pages share consistent structural elements."""

    def test_all_pages_load_common_css(self, sbstest_site: SiteArtifacts):
        """Every page HTML references common.css."""
        pages = sbstest_site.list_pages()
        assert pages, "Should have at least one page"

        # Verso pages use inline CSS, not external stylesheets
        verso_pages = {"paper_verso", "blueprint_verso"}

        for page_name in pages:
            if page_name in verso_pages:
                continue
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            assert "common.css" in html, (
                f"Page '{page_name}' does not reference common.css"
            )

    def test_all_pages_have_theme_toggle(self, sbstest_site: SiteArtifacts):
        """Every page has an element with class 'theme-toggle'."""
        require_bs4()
        pages = sbstest_site.list_pages()
        assert pages, "Should have at least one page"

        for page_name in pages:
            if page_name in VERSO_PAGES:
                continue
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            toggles = soup.select(".theme-toggle")
            assert len(toggles) > 0, (
                f"Page '{page_name}' missing .theme-toggle element"
            )

    def test_all_pages_have_sidebar_nav(self, sbstest_site: SiteArtifacts):
        """Every page has a nav with class 'toc' or sidebar-related class."""
        require_bs4()
        pages = sbstest_site.list_pages()
        assert pages, "Should have at least one page"

        for page_name in pages:
            if page_name in VERSO_PAGES:
                continue
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            nav = soup.select("nav.toc, .sidebar, nav.sidebar, [class*='sidebar']")
            assert len(nav) > 0, (
                f"Page '{page_name}' missing sidebar navigation (nav.toc or sidebar class)"
            )

    def test_all_pages_have_html_title(self, sbstest_site: SiteArtifacts):
        """Every page has a <title> element with non-empty text."""
        require_bs4()
        pages = sbstest_site.list_pages()
        assert pages, "Should have at least one page"

        for page_name in pages:
            if page_name in VERSO_PAGES:
                continue
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            title = soup.select_one("title")
            assert title is not None, f"Page '{page_name}' missing <title>"
            assert title.get_text(strip=True), f"Page '{page_name}' has empty <title>"

    def test_chapter_pages_share_layout_classes(self, sbstest_site: SiteArtifacts):
        """All chapter pages use the same set of top-level wrapper class patterns."""
        require_bs4()
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if p not in NON_CHAPTER_PAGES]

        if len(chapter_pages) < 2:
            pytest.skip("Need at least 2 chapter pages to compare layout classes")

        # Collect the set of body > div class names for each chapter page
        layout_signatures = {}
        for page_name in chapter_pages:
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            body = soup.select_one("body")
            if not body:
                continue
            # Get classes of direct children of body
            child_classes = set()
            for child in body.children:
                if hasattr(child, "get") and child.get("class"):
                    child_classes.update(child["class"])
            layout_signatures[page_name] = child_classes

        if len(layout_signatures) < 2:
            pytest.skip("Not enough chapter pages with body content")

        # All chapter pages should share the same wrapper classes
        signatures = list(layout_signatures.values())
        first = signatures[0]
        for page_name, sig in layout_signatures.items():
            assert sig == first, (
                f"Chapter page '{page_name}' has different layout classes: "
                f"{sig} vs {first}"
            )

    def test_all_pages_load_plastex_js(self, sbstest_site: SiteArtifacts):
        """Every page HTML references plastex.js."""
        pages = sbstest_site.list_pages()
        assert pages, "Should have at least one page"

        # Verso pages use inline JS, not external scripts
        verso_pages = {"paper_verso", "blueprint_verso"}

        for page_name in pages:
            if page_name in verso_pages:
                continue
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            assert "plastex.js" in html, (
                f"Page '{page_name}' does not reference plastex.js"
            )

    def test_all_pages_have_header(self, sbstest_site: SiteArtifacts):
        """Every page has a header element (nav.header, .nav-wrapper, or .header)."""
        require_bs4()
        pages = sbstest_site.list_pages()
        assert pages, "Should have at least one page"

        for page_name in pages:
            if page_name in VERSO_PAGES:
                continue
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            header = soup.select("nav.header, .nav-wrapper, .header, header")
            assert len(header) > 0, (
                f"Page '{page_name}' missing header (nav.header, .nav-wrapper, "
                f".header, or header)"
            )

    def test_consistent_page_structure(self, sbstest_site: SiteArtifacts):
        """Every page has <html>, <head>, and <body> tags."""
        require_bs4()
        pages = sbstest_site.list_pages()
        assert pages, "Should have at least one page"

        for page_name in pages:
            if page_name in VERSO_PAGES:
                continue
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            assert soup.select_one("html") is not None, (
                f"Page '{page_name}' missing <html> tag"
            )
            assert soup.select_one("head") is not None, (
                f"Page '{page_name}' missing <head> tag"
            )
            assert soup.select_one("body") is not None, (
                f"Page '{page_name}' missing <body> tag"
            )


# =========================================================================
# Design Language
# =========================================================================


@pytest.mark.evergreen
class TestDesignLanguage:
    """Tests that the design system is consistently applied."""

    def test_rainbow_brackets_six_colors(self, sbstest_site: SiteArtifacts):
        """CSS defines .lean-bracket-1 through .lean-bracket-6."""
        combined = "\n".join(sbstest_site.all_css.values())

        missing = []
        for i in range(1, 7):
            cls = f".lean-bracket-{i}"
            if cls not in combined:
                missing.append(cls)

        assert not missing, (
            f"Missing rainbow bracket classes: {', '.join(missing)}"
        )

    def test_monospace_font_for_code(self, sbstest_site: SiteArtifacts):
        """CSS applies monospace font to code-related elements."""
        combined = "\n".join(sbstest_site.all_css.values())

        assert "monospace" in combined, (
            "CSS should specify monospace font for code elements"
        )

    def test_status_dot_is_circle(self, sbstest_site: SiteArtifacts):
        """CSS defines .status-dot with border-radius (making it circular)."""
        css = sbstest_site.css  # common.css
        assert ".status-dot" in css, "No .status-dot class in CSS"
        assert "border-radius" in css, "No border-radius in CSS"
        # Check that border-radius appears in the status-dot block
        idx = css.index(".status-dot")
        block_end = css.index("}", idx)
        block = css[idx:block_end]
        assert "border-radius" in block, (
            ".status-dot should have border-radius defined to create a circle"
        )

    def test_heading_hierarchy_defined(self, sbstest_site: SiteArtifacts):
        """CSS defines font-size for h1, h2, and h3."""
        combined = "\n".join(sbstest_site.all_css.values())

        for heading in ["h1", "h2", "h3"]:
            # Match heading selector followed by font-size within its rule block
            pattern = rf'{heading}[^{{]*\{{[^}}]*font-size'
            assert re.search(pattern, combined, re.DOTALL), (
                f"CSS should define font-size for {heading}"
            )


# =========================================================================
# Build Output Complete
# =========================================================================


@pytest.mark.evergreen
class TestBuildOutputComplete:
    """Tests that the build produces all expected output files."""

    def test_all_expected_html_pages_exist(self, sbstest_site: SiteArtifacts):
        """Runway dir contains expected HTML pages plus chapter pages."""
        runway = sbstest_site.runway_dir
        assert runway.exists(), "Runway output directory should exist"

        # Required non-chapter pages
        required = ["index.html", "dep_graph.html", "paper_tex.html", "pdf_tex.html"]
        for filename in required:
            path = runway / filename
            assert path.exists(), f"Missing required page: {filename}"

        # Should have at least 3 chapter pages
        all_html = list(runway.glob("*.html"))
        non_chapter_names = {"index.html", "dep_graph.html", "paper_tex.html",
                             "pdf_tex.html", "paper_verso.html", "blueprint_verso.html"}
        chapter_pages = [p for p in all_html if p.name not in non_chapter_names]
        assert len(chapter_pages) >= 3, (
            f"Expected at least 3 chapter pages, found {len(chapter_pages)}: "
            f"{[p.name for p in chapter_pages]}"
        )

    def test_all_css_assets_bundled(self, sbstest_site: SiteArtifacts):
        """Assets dir contains all 4 CSS files."""
        assets = sbstest_site.assets_dir
        assert assets.exists(), "Assets directory should exist"

        expected = ["common.css", "blueprint.css", "dep_graph.css", "paper.css"]
        for filename in expected:
            path = assets / filename
            assert path.exists(), f"Missing CSS asset: {filename}"

    def test_all_js_assets_bundled(self, sbstest_site: SiteArtifacts):
        """Assets dir contains both JS files."""
        assets = sbstest_site.assets_dir
        assert assets.exists(), "Assets directory should exist"

        expected = ["plastex.js", "verso-code.js"]
        for filename in expected:
            path = assets / filename
            assert path.exists(), f"Missing JS asset: {filename}"

    def test_no_zero_byte_output_files(self, sbstest_site: SiteArtifacts):
        """Every .html, .css, .js file in runway/ and assets/ is > 50 bytes."""
        runway = sbstest_site.runway_dir
        assets = sbstest_site.assets_dir

        tiny_files = []

        # Check HTML files in runway/
        for html_file in runway.glob("*.html"):
            size = html_file.stat().st_size
            if size <= 50:
                tiny_files.append(f"{html_file.name} ({size} bytes)")

        # Check CSS and JS files in assets/
        if assets.exists():
            for asset_file in list(assets.glob("*.css")) + list(assets.glob("*.js")):
                size = asset_file.stat().st_size
                if size <= 50:
                    tiny_files.append(f"assets/{asset_file.name} ({size} bytes)")

        assert not tiny_files, (
            f"Found files <= 50 bytes (likely empty/corrupt): {', '.join(tiny_files)}"
        )
