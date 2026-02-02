"""
Paper Generation Tests (76-87)

Verifies paper and PDF generation from LaTeX sources.
"""

from __future__ import annotations

import pytest

from .conftest import SiteArtifacts, GCR_ROOT
from .helpers import parse_html


@pytest.mark.evergreen
class TestPaperGeneration:
    """Tests for paper HTML generation."""

    def test_paper_tex_source_exists(self, sbstest_site: SiteArtifacts):
        """76. paper.tex source file exists."""
        paper_tex = sbstest_site.project_root / "blueprint" / "src" / "paper.tex"
        # Paper is optional
        if not paper_tex.exists():
            pytest.skip("paper.tex not present (optional)")
        assert paper_tex.exists()

    def test_paper_tex_html_generated(self, sbstest_site: SiteArtifacts):
        """77. paper_tex.html page generated."""
        html = sbstest_site.get_page("paper_tex")
        if not html:
            pytest.skip("paper_tex.html not generated")
        assert len(html) > 100, "Paper page should have content"

    def test_paper_title_extracted(self, sbstest_site: SiteArtifacts):
        """78. Paper title extracted from LaTeX."""
        html = sbstest_site.get_page("paper_tex")
        if not html:
            pytest.skip("paper_tex.html not generated")

        soup = parse_html(html)
        # Look for title element or h1
        title = soup.select_one("h1, .paper-title, title")
        assert title, "Paper should have title"

    def test_paper_has_content(self, sbstest_site: SiteArtifacts):
        """79. Paper page has mathematical content."""
        html = sbstest_site.get_page("paper_tex")
        if not html:
            pytest.skip("paper_tex.html not generated")

        # Should have math content (MathJax delimiters or rendered content)
        has_math = "$" in html or "\\(" in html or "math" in html.lower()
        assert has_math, "Paper should have mathematical content"

    def test_paper_mathjax_loaded(self, sbstest_site: SiteArtifacts):
        """80. Paper page loads MathJax."""
        html = sbstest_site.get_page("paper_tex")
        if not html:
            pytest.skip("paper_tex.html not generated")

        assert "MathJax" in html, "Paper should load MathJax"


@pytest.mark.evergreen
class TestPdfGeneration:
    """Tests for PDF generation."""

    def test_pdf_page_exists(self, sbstest_site: SiteArtifacts):
        """81. pdf_tex.html page exists."""
        html = sbstest_site.get_page("pdf_tex")
        if not html:
            pytest.skip("pdf_tex.html not generated")
        assert len(html) > 100, "PDF page should have content"

    def test_pdf_file_generated(self, sbstest_site: SiteArtifacts):
        """82. PDF file generated in runway directory."""
        pdf_path = sbstest_site.runway_dir / "paper.pdf"
        if not pdf_path.exists():
            pytest.skip("paper.pdf not generated")
        assert pdf_path.stat().st_size > 1000, "PDF should have substantial content"

    def test_pdf_page_has_embed(self, sbstest_site: SiteArtifacts):
        """83. PDF page has embed or iframe."""
        html = sbstest_site.get_page("pdf_tex")
        if not html:
            pytest.skip("pdf_tex.html not generated")

        soup = parse_html(html)
        embed = soup.select("embed, iframe, object")
        assert len(embed) > 0, "PDF page should embed the PDF"

    def test_pdf_references_paper_pdf(self, sbstest_site: SiteArtifacts):
        """84. PDF page references paper.pdf file."""
        html = sbstest_site.get_page("pdf_tex")
        if not html:
            pytest.skip("pdf_tex.html not generated")

        assert "paper.pdf" in html, "PDF page should reference paper.pdf"


@pytest.mark.evergreen
class TestGcrPaper:
    """Tests for GCR paper generation (requires GCR build)."""

    def test_gcr_paper_exists(self, gcr_site: SiteArtifacts):
        """85. GCR project has paper page."""
        html = gcr_site.get_page("paper_tex")
        if not html:
            pytest.skip("GCR paper not built")
        assert len(html) > 100, "GCR paper should have content"

    def test_gcr_has_introduction(self, gcr_site: SiteArtifacts):
        """86. GCR paper has introduction or abstract."""
        html = gcr_site.get_page("paper_tex")
        if not html:
            pytest.skip("GCR paper not built")

        # Check for abstract or introduction section
        has_content = "abstract" in html.lower() or "introduction" in html.lower()
        assert has_content, "GCR paper should have abstract or introduction"

    def test_gcr_has_authors(self, gcr_site: SiteArtifacts):
        """87. GCR paper extracts authors."""
        html = gcr_site.get_page("paper_tex")
        if not html:
            pytest.skip("GCR paper not built")

        # Check for author section or content
        soup = parse_html(html)
        # Author info should be present somewhere
        has_author = "author" in html.lower() or soup.select(".author, .paper-author")
        assert has_author, "GCR paper should have author information"
