"""
Paper Quality Tests

Verifies paper content richness, PDF structural validity,
and verification badge integration.
"""

from __future__ import annotations

import pytest

from .conftest import SiteArtifacts
from .helpers import parse_html, require_bs4, extract_css_variables


@pytest.mark.evergreen
class TestPaperContent:
    """Tests for paper page content quality."""

    def test_paper_has_math_content(self, sbstest_site: SiteArtifacts):
        """Paper page contains math indicators."""
        paper = sbstest_site.get_page("paper_tex")
        if not paper or len(paper) < 100:
            pytest.skip("Paper not generated")

        math_indicators = ["$", "\\(", "\\(", "MathJax", "math", "mjx-"]
        has_math = any(indicator in paper for indicator in math_indicators)
        assert has_math, (
            "Paper should contain math content (expected one of: "
            "$, \\(, MathJax, math, mjx-)"
        )

    def test_paper_has_multiple_sections(self, sbstest_site: SiteArtifacts):
        """Paper has more than one heading element."""
        paper = sbstest_site.get_page("paper_tex")
        if not paper or len(paper) < 100:
            pytest.skip("Paper not generated")

        require_bs4()
        soup = parse_html(paper)
        headings = soup.find_all(["h2", "h3", "h4"])
        assert len(headings) > 1, (
            f"Paper should have multiple sections, found {len(headings)} headings"
        )

    def test_paper_has_substantial_text(self, sbstest_site: SiteArtifacts):
        """Paper page visible text exceeds 2000 characters."""
        paper = sbstest_site.get_page("paper_tex")
        if not paper or len(paper) < 100:
            pytest.skip("Paper not generated")

        require_bs4()
        soup = parse_html(paper)
        text = soup.get_text()
        assert len(text) > 2000, (
            f"Paper should have substantial text content, got {len(text)} chars"
        )

    def test_paper_mathjax_loads(self, sbstest_site: SiteArtifacts):
        """MathJax script tag present in paper page."""
        paper = sbstest_site.get_page("paper_tex")
        if not paper or len(paper) < 100:
            pytest.skip("Paper not generated")

        require_bs4()
        soup = parse_html(paper)
        scripts = soup.find_all("script")
        mathjax_scripts = [
            s for s in scripts
            if s.get("src") and "mathjax" in s["src"].lower()
            or (s.string and "MathJax" in (s.string or ""))
        ]
        # Also check raw HTML as fallback
        has_mathjax = len(mathjax_scripts) > 0 or "MathJax" in paper
        assert has_mathjax, "Paper page should include MathJax script"

    def test_paper_title_present(self, sbstest_site: SiteArtifacts):
        """Paper has a title in h1 or .paper-title element."""
        paper = sbstest_site.get_page("paper_tex")
        if not paper or len(paper) < 100:
            pytest.skip("Paper not generated")

        require_bs4()
        soup = parse_html(paper)
        title_el = soup.select_one("h1, .paper-title")
        assert title_el is not None, "Paper should have an h1 or .paper-title element"
        title_text = title_el.get_text(strip=True)
        assert len(title_text) > 0, "Paper title element should contain text"

    def test_paper_has_theorem_environments(self, sbstest_site: SiteArtifacts):
        """Paper has elements with theorem/lemma/proposition classes."""
        paper = sbstest_site.get_page("paper_tex")
        if not paper or len(paper) < 100:
            pytest.skip("Paper not generated")

        require_bs4()
        soup = parse_html(paper)

        # Find elements whose class contains theorem, lemma, or proposition
        env_elements = []
        for tag in soup.find_all(attrs={"class": True}):
            classes = " ".join(tag.get("class", []))
            if any(kw in classes.lower() for kw in ("theorem", "lemma", "proposition")):
                env_elements.append(tag)

        assert len(env_elements) > 0, (
            "Paper should have theorem/lemma/proposition environments"
        )


@pytest.mark.evergreen
class TestPdfValidity:
    """Tests for PDF structural validity."""

    def test_pdf_has_valid_header(self, sbstest_site: SiteArtifacts):
        """paper.pdf starts with %PDF- magic bytes."""
        pdf_path = sbstest_site.runway_dir / "paper.pdf"
        if not pdf_path.exists():
            pytest.skip("paper.pdf not generated")

        header = pdf_path.read_bytes()[:8]
        assert header.startswith(b"%PDF-"), (
            f"PDF should start with %PDF- header, got {header!r}"
        )

    def test_pdf_has_eof_marker(self, sbstest_site: SiteArtifacts):
        """paper.pdf contains %%EOF marker."""
        pdf_path = sbstest_site.runway_dir / "paper.pdf"
        if not pdf_path.exists():
            pytest.skip("paper.pdf not generated")

        content = pdf_path.read_bytes()
        assert b"%%EOF" in content, "PDF should contain %%EOF marker"

    def test_pdf_minimum_size(self, sbstest_site: SiteArtifacts):
        """paper.pdf exceeds 10KB minimum size."""
        pdf_path = sbstest_site.runway_dir / "paper.pdf"
        if not pdf_path.exists():
            pytest.skip("paper.pdf not generated")

        size = pdf_path.stat().st_size
        assert size > 10240, (
            f"PDF should be larger than 10KB, got {size} bytes"
        )

    def test_pdf_embed_page_references_file(self, sbstest_site: SiteArtifacts):
        """pdf_tex.html references paper.pdf."""
        html = sbstest_site.get_page("pdf_tex")
        if not html or len(html) < 100:
            pytest.skip("pdf_tex.html not generated")

        assert "paper.pdf" in html, (
            "PDF embed page should reference paper.pdf"
        )


@pytest.mark.evergreen
class TestVerificationBadges:
    """Tests for verification badge integration in paper."""

    def test_paper_has_verification_indicators(self, sbstest_site: SiteArtifacts):
        """Paper page contains verification-related elements or text."""
        paper = sbstest_site.get_page("paper_tex")
        if not paper or len(paper) < 100:
            pytest.skip("Paper not generated")

        require_bs4()
        soup = parse_html(paper)
        paper_lower = paper.lower()

        # Check for verification keywords in text
        keyword_match = any(
            kw in paper_lower
            for kw in ("verified", "progress", "badge", "status-badge")
        )

        # Check for elements with badge-related classes
        badge_elements = []
        for tag in soup.find_all(attrs={"class": True}):
            classes = " ".join(tag.get("class", []))
            if any(kw in classes.lower() for kw in ("badge", "verified", "status")):
                badge_elements.append(tag)

        assert keyword_match or len(badge_elements) > 0, (
            "Paper should contain verification indicators "
            "(keywords or badge-related elements)"
        )

    def test_badge_css_variables_defined(self, sbstest_site: SiteArtifacts):
        """CSS contains badge-related variable definitions."""
        css = sbstest_site.css
        assert css, "common.css should exist and have content"

        variables = extract_css_variables(css)
        assert "--sbs-badge-verified-bg" in variables, (
            "CSS should define --sbs-badge-verified-bg variable"
        )
        assert "--sbs-badge-progress-bg" in variables, (
            "CSS should define --sbs-badge-progress-bg variable"
        )

    def test_badge_verified_and_progress_variants(self, sbstest_site: SiteArtifacts):
        """CSS has both badge-verified and badge-progress variable families."""
        css = sbstest_site.css
        assert css, "common.css should exist and have content"

        variables = extract_css_variables(css)

        # Check verified family
        verified_vars = [v for v in variables if "badge-verified" in v]
        assert len(verified_vars) >= 2, (
            f"CSS should define multiple --sbs-badge-verified-* variables, "
            f"found: {verified_vars}"
        )

        # Check progress family
        progress_vars = [v for v in variables if "badge-progress" in v]
        assert len(progress_vars) >= 2, (
            f"CSS should define multiple --sbs-badge-progress-* variables, "
            f"found: {progress_vars}"
        )

    def test_badges_link_to_blueprint(self, sbstest_site: SiteArtifacts):
        """Paper page references blueprint sections."""
        paper = sbstest_site.get_page("paper_tex")
        if not paper or len(paper) < 100:
            pytest.skip("Paper not generated")

        require_bs4()
        soup = parse_html(paper)

        # Paper should reference blueprint chapter pages via links
        links = soup.find_all("a", href=True)
        blueprint_links = [a for a in links if "#" in a["href"] or ".html" in a["href"]]

        # Badges may be decorative CSS elements without explicit <a> wrapping.
        # Accept either internal links OR badge/verified indicators in the page.
        assert len(blueprint_links) > 0 or "badge" in paper.lower() or "verified" in paper.lower(), (
            "Paper should reference blueprint sections or display verification badges"
        )
