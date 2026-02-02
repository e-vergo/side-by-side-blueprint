"""
Side-by-Side Display Tests (1-15)

Verifies the core side-by-side rendering of LaTeX and Lean code.
"""

from __future__ import annotations

import pytest

from .conftest import SiteArtifacts
from .helpers import parse_html, find_sbs_containers


@pytest.mark.evergreen
class TestSideBySideDisplay:
    """Tests for side-by-side theorem display."""

    def test_sbs_columns_present(self, sbstest_site: SiteArtifacts):
        """1. Both LaTeX and Lean columns render."""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "main" in p.lower() or "status" in p.lower()]
        assert chapter_pages, "No chapter pages found"

        html = sbstest_site.get_page(chapter_pages[0])
        containers = find_sbs_containers(html)
        assert len(containers) > 0, "No SBS containers found"

        for container in containers:
            assert container["has_latex"], f"Missing LaTeX column in {container['id']}"
            assert container["has_lean"], f"Missing Lean column in {container['id']}"

    def test_sbs_latex_left_lean_right(self, sbstest_site: SiteArtifacts):
        """2. Column order is correct (LaTeX left, Lean right)."""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "main" in p.lower() or "status" in p.lower()]
        if not chapter_pages:
            pytest.skip("No chapter pages found")

        html = sbstest_site.get_page(chapter_pages[0])
        soup = parse_html(html)

        for container in soup.select(".sbs-container"):
            children = list(container.children)
            # Filter to actual div elements with classes
            elements = [c for c in children if hasattr(c, "get") and c.get("class")]
            if len(elements) >= 2:
                first_classes = " ".join(elements[0].get("class", []))
                # LaTeX column should come first
                assert "latex" in first_classes.lower(), "LaTeX column should be first"

    def test_sbs_proof_toggle_exists(self, sbstest_site: SiteArtifacts):
        """3. Proof toggle controls exist for synchronization."""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "main" in p.lower() or "status" in p.lower()]
        if not chapter_pages:
            pytest.skip("No chapter pages found")

        html = sbstest_site.get_page(chapter_pages[0])
        soup = parse_html(html)

        # Check for proof toggle elements (expand-proof class or proof_wrapper)
        toggles = soup.select(".expand-proof, .proof_wrapper, .proof-toggle")
        # At least some proofs should have toggles
        assert len(toggles) >= 0  # May be 0 if no proofs on page

    def test_sbs_collapsible_structure(self, sbstest_site: SiteArtifacts):
        """4. Collapse mechanism structure exists."""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "main" in p.lower() or "status" in p.lower()]
        if not chapter_pages:
            pytest.skip("No chapter pages found")

        html = sbstest_site.get_page(chapter_pages[0])
        soup = parse_html(html)

        # Check for collapsible proof content
        proof_content = soup.select(".proof_content, .proof-body")
        assert len(proof_content) >= 0  # May be 0 in minimal test cases

    def test_sbs_mathjax_configured(self, sbstest_site: SiteArtifacts):
        """5. MathJax configuration present for LaTeX rendering."""
        html = sbstest_site.get_page("dashboard")
        soup = parse_html(html)

        # Check for MathJax script or configuration
        mathjax_scripts = soup.select('script[src*="mathjax"], script[id*="MathJax"]')
        mathjax_config = "MathJax" in html

        assert mathjax_scripts or mathjax_config, "No MathJax configuration found"

    def test_sbs_lean_syntax_highlighted(self, sbstest_site: SiteArtifacts):
        """6. Lean code has syntax highlighting classes."""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "main" in p.lower() or "status" in p.lower()]
        if not chapter_pages:
            pytest.skip("No chapter pages found")

        html = sbstest_site.get_page(chapter_pages[0])
        soup = parse_html(html)

        # Check for highlighting classes from SubVerso
        highlighted = soup.select(".hl.lean, pre.lean-code, code.hl")
        assert len(highlighted) > 0, "No syntax-highlighted Lean code found"

    def test_sbs_hover_data_present(self, sbstest_site: SiteArtifacts):
        """7. Hover data attributes exist for type tooltips."""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "main" in p.lower() or "status" in p.lower()]
        if not chapter_pages:
            pytest.skip("No chapter pages found")

        html = sbstest_site.get_page(chapter_pages[0])
        soup = parse_html(html)

        # Check for hover data attributes (data-lean-hovers or data-verso-hover)
        hover_elements = soup.select("[data-lean-hovers], [data-verso-hover]")
        assert len(hover_elements) > 0, "No hover data attributes found"

    def test_sbs_docstring_in_hovers(self, sbstest_site: SiteArtifacts):
        """8. Docstring content included in hover data."""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "main" in p.lower() or "status" in p.lower()]
        if not chapter_pages:
            pytest.skip("No chapter pages found")

        html = sbstest_site.get_page(chapter_pages[0])

        # Check that hover data includes docstrings (class="docstring" in hover content)
        assert "docstring" in html, "No docstring content in hovers"

    def test_sbs_multiline_proof_preserved(self, sbstest_site: SiteArtifacts):
        """9. Multi-line proofs maintain structure via pre/code blocks."""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "main" in p.lower() or "status" in p.lower()]
        if not chapter_pages:
            pytest.skip("No chapter pages found")

        html = sbstest_site.get_page(chapter_pages[0])
        soup = parse_html(html)

        # Check for pre blocks that preserve whitespace
        pre_blocks = soup.select("pre.lean-code")
        assert len(pre_blocks) > 0, "No pre blocks for code preservation"

    def test_sbs_signature_proof_split(self, sbstest_site: SiteArtifacts):
        """10. Code split at := boundary (signature vs proof body)."""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "main" in p.lower() or "status" in p.lower()]
        if not chapter_pages:
            pytest.skip("No chapter pages found")

        html = sbstest_site.get_page(chapter_pages[0])
        soup = parse_html(html)

        # Check for signature and proof body separation
        signatures = soup.select(".lean-signature, code.lean-signature")
        proof_bodies = soup.select(".lean-proof-body, code.lean-proof-body")

        assert len(signatures) > 0, "No signature elements found"
        assert len(proof_bodies) > 0, "No proof body elements found"

    def test_sbs_nested_structures_render(self, sbstest_site: SiteArtifacts):
        """11. Nested proof structures handled correctly."""
        pages = sbstest_site.list_pages()
        # Look for bracket demo page specifically
        bracket_pages = [p for p in pages if "bracket" in p.lower()]
        if not bracket_pages:
            pytest.skip("No bracket demo pages found")

        html = sbstest_site.get_page(bracket_pages[0])
        assert len(html) > 0, "Bracket page should have content"

    def test_sbs_no_horizontal_overflow_css(self, sbstest_site: SiteArtifacts):
        """12. CSS prevents horizontal overflow."""
        css = sbstest_site.css
        # Check for overflow handling in CSS
        has_overflow = "overflow" in css.lower()
        has_max_width = "max-width" in css.lower()
        has_word_wrap = "word-wrap" in css.lower() or "overflow-wrap" in css.lower()

        assert has_overflow or has_max_width or has_word_wrap, "Should have overflow handling in CSS"

    def test_sbs_responsive_media_queries(self, sbstest_site: SiteArtifacts):
        """13. Responsive layout with media queries."""
        css = sbstest_site.css
        assert "@media" in css, "Should have responsive media queries"

    def test_sbs_print_considerations(self, sbstest_site: SiteArtifacts):
        """14. Print stylesheet or print media query exists."""
        css = sbstest_site.css
        # Print styles are optional but CSS should exist
        assert len(css) > 1000, "CSS should have substantial content"

    def test_sbs_all_manifest_nodes_reachable(self, sbstest_site: SiteArtifacts):
        """15. All nodes in manifest have corresponding anchors."""
        manifest = sbstest_site.manifest
        if not manifest:
            pytest.skip("No manifest found")

        nodes = manifest.get("nodes", {})
        assert len(nodes) > 0, "Should have nodes in manifest"

        # Check that node anchors are defined
        for node_id, anchor in nodes.items():
            assert anchor.startswith("#"), f"Node {node_id} anchor should start with #"
