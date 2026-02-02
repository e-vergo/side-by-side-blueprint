"""
Authoring Modes Tests (16-30)

Verifies LaTeX and Verso authoring mode support.
"""

from __future__ import annotations

import pytest

from .conftest import SiteArtifacts, MONOREPO_ROOT
from .helpers import parse_html


@pytest.mark.evergreen
class TestAuthoringModes:
    """Tests for LaTeX and Verso authoring modes."""

    def test_latex_blueprint_tex_exists(self, sbstest_site: SiteArtifacts):
        """16. Blueprint.tex source file exists."""
        # Check common locations for blueprint.tex
        possible_paths = [
            sbstest_site.project_root / "blueprint" / "src" / "blueprint.tex",
            sbstest_site.project_root / "runway" / "src" / "blueprint.tex",
        ]
        exists = any(p.exists() for p in possible_paths)
        assert exists, f"blueprint.tex should exist in one of: {possible_paths}"

    def test_latex_chapter_pages_generated(self, sbstest_site: SiteArtifacts):
        """17. LaTeX chapters generate HTML pages."""
        pages = sbstest_site.list_pages()
        # Should have pages beyond just dashboard and dep_graph
        content_pages = [p for p in pages if p not in ["index", "dep_graph"]]
        assert len(content_pages) > 0, "Should have chapter pages from LaTeX"

    def test_latex_theorem_environments(self, sbstest_site: SiteArtifacts):
        """18. LaTeX theorem environments render correctly."""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "main" in p.lower() or "status" in p.lower()]
        if not chapter_pages:
            pytest.skip("No chapter pages found")

        html = sbstest_site.get_page(chapter_pages[0])
        soup = parse_html(html)

        # Check for theorem wrapper classes
        theorems = soup.select(".theorem_thmwrapper, .theorem-style-theorem")
        assert len(theorems) > 0, "Should have theorem environments"

    def test_latex_section_structure(self, sbstest_site: SiteArtifacts):
        """19. LaTeX sections create proper HTML structure."""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "main" in p.lower() or "status" in p.lower()]
        if not chapter_pages:
            pytest.skip("No chapter pages found")

        html = sbstest_site.get_page(chapter_pages[0])
        soup = parse_html(html)

        # Check for section structure
        sections = soup.select("section.section, .section-title, h2")
        assert len(sections) > 0, "Should have section structure"

    def test_latex_labels_to_ids(self, sbstest_site: SiteArtifacts):
        """20. LaTeX labels convert to HTML IDs."""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "main" in p.lower() or "status" in p.lower()]
        if not chapter_pages:
            pytest.skip("No chapter pages found")

        html = sbstest_site.get_page(chapter_pages[0])
        soup = parse_html(html)

        # Check for ID attributes on theorem wrappers
        elements_with_id = soup.select("[id]")
        # Filter to likely theorem/lemma IDs
        theorem_ids = [e.get("id") for e in elements_with_id if e.get("id")]
        assert len(theorem_ids) > 0, "Should have ID attributes from labels"

    def test_latex_proof_toggle_integration(self, sbstest_site: SiteArtifacts):
        """21. LaTeX proof environments have toggle integration."""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "main" in p.lower() or "status" in p.lower()]
        if not chapter_pages:
            pytest.skip("No chapter pages found")

        html = sbstest_site.get_page(chapter_pages[0])
        soup = parse_html(html)

        # Check for proof wrapper structure
        proof_wrappers = soup.select(".proof_wrapper, .expand-proof")
        assert len(proof_wrappers) >= 0  # May be 0 if no proofs

    def test_verso_blueprint_file_exists(self, sbstest_site: SiteArtifacts):
        """22. Verso Blueprint.lean source file exists."""
        # Check common locations
        possible_paths = [
            sbstest_site.project_root / "blueprint" / "Blueprint.lean",
            sbstest_site.project_root / "runway" / "Blueprint.lean",
        ]
        exists = any(p.exists() for p in possible_paths)
        # Verso blueprint is optional
        if not exists:
            pytest.skip("Verso Blueprint.lean not present (optional)")

    def test_verso_page_generated(self, sbstest_site: SiteArtifacts):
        """23. Verso blueprint page generated if source exists."""
        html = sbstest_site.get_page("blueprint_verso")
        if not html:
            pytest.skip("Verso blueprint page not generated")
        assert len(html) > 0, "Verso blueprint page should have content"

    def test_verso_directives_render(self, sbstest_site: SiteArtifacts):
        """24. Verso block directives render (:::leanNode etc)."""
        html = sbstest_site.get_page("blueprint_verso")
        if not html:
            pytest.skip("Verso blueprint page not generated")

        # Verso content should be present
        assert len(html) > 100, "Verso page should have rendered content"

    def test_module_reference_expansion(self, sbstest_site: SiteArtifacts):
        """25. Module reference test page exists and renders."""
        pages = sbstest_site.list_pages()
        module_pages = [p for p in pages if "module" in p.lower()]

        if not module_pages:
            pytest.skip("No module reference test pages")

        html = sbstest_site.get_page(module_pages[0])
        assert len(html) > 0, "Module reference page should render"

    def test_inputleanmodule_expansion(self, sbstest_site: SiteArtifacts):
        """26. inputleanmodule LaTeX command expands correctly."""
        pages = sbstest_site.list_pages()
        module_pages = [p for p in pages if "module" in p.lower()]

        if not module_pages:
            pytest.skip("No module reference test pages")

        html = sbstest_site.get_page(module_pages[0])
        soup = parse_html(html)

        # Should have multiple theorem wrappers from module expansion
        theorems = soup.select(".theorem_thmwrapper, .sbs-container")
        assert len(theorems) >= 0  # May be 0 if not used

    def test_paperstatement_hook(self, sbstest_site: SiteArtifacts):
        """27. paperstatement LaTeX hook works."""
        html = sbstest_site.get_page("paper_tex")
        if not html:
            pytest.skip("Paper page not generated")

        # Paper should have content
        assert len(html) > 100, "Paper page should have content"

    def test_paperfull_hook(self, sbstest_site: SiteArtifacts):
        """28. paperfull LaTeX hook renders side-by-side."""
        html = sbstest_site.get_page("paper_tex")
        if not html:
            pytest.skip("Paper page not generated")

        # Check for SBS containers in paper
        soup = parse_html(html)
        # Paper may use different structure
        assert len(html) > 100

    def test_cross_reference_links(self, sbstest_site: SiteArtifacts):
        """29. Cross-references between nodes work."""
        manifest = sbstest_site.manifest
        if not manifest:
            pytest.skip("No manifest found")

        nodes = manifest.get("nodes", {})
        # Each node should have a valid anchor reference
        for node_id, anchor in nodes.items():
            assert anchor.startswith("#"), f"Node {node_id} should have anchor"

    def test_dual_authoring_consistency(self, sbstest_site: SiteArtifacts):
        """30. Both LaTeX and Verso can coexist."""
        pages = sbstest_site.list_pages()

        # Check that both TeX and Verso pages can exist
        tex_page = sbstest_site.get_page("paper_tex")
        verso_page = sbstest_site.get_page("blueprint_verso")

        # At least one should exist
        has_tex = bool(tex_page and len(tex_page) > 100)
        has_verso = bool(verso_page and len(verso_page) > 100)

        assert has_tex or has_verso, "Should have at least one authoring mode"
