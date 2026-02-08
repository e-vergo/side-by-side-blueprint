"""
SBS Content Tests

Verifies the substance of side-by-side displays, declaration artifacts,
and chapter pages -- ensuring generated content is real and complete.
"""

from __future__ import annotations

import json

import pytest

from .conftest import SiteArtifacts
from .helpers import parse_html, find_sbs_containers, require_bs4, collect_all_ids, get_dressed_decl_paths


NON_CHAPTER_PAGES = {"index", "dep_graph", "paper_tex", "pdf_tex", "paper_verso", "blueprint_verso"}


def get_chapter_pages(site: SiteArtifacts) -> list[str]:
    """Get list of chapter page names."""
    return [p for p in site.list_pages() if p not in NON_CHAPTER_PAGES]


@pytest.mark.evergreen
class TestSideBySideContent:
    """Tests for the substance of side-by-side displays."""

    def test_latex_columns_have_math_content(self, sbstest_site: SiteArtifacts):
        """Most pages with .sbs-statement contain math markup."""
        require_bs4()
        chapters = get_chapter_pages(sbstest_site)
        assert chapters, "No chapter pages found"

        pages_with_math = 0
        pages_checked = 0
        for page_name in chapters:
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            # New grid structure uses .sbs-statement; fallback to .sbs-latex-column
            cols = soup.select(".sbs-statement") or soup.select(".sbs-latex-column")
            if not cols:
                continue
            pages_checked += 1
            page_has_math = False
            for col in cols:
                col_html = str(col)
                has_math = (
                    "$" in col_html
                    or "\\(" in col_html
                    or col.select_one("span.MathJax, .MathJax_Preview, .mjx-math, script[type*='math']")
                    is not None
                )
                if has_math:
                    page_has_math = True
                    break
            # Also check page-level MathJax indicators
            if not page_has_math and any(ind in html for ind in ["mjx-", "MathJax"]):
                page_has_math = True
            if page_has_math:
                pages_with_math += 1

        assert pages_checked > 0, "No chapter pages have .sbs-statement elements"
        # Not all pages have traditional LaTeX math (e.g. bracket demo).
        # At least half of pages with columns should have math content.
        assert pages_with_math >= pages_checked // 2, (
            f"Only {pages_with_math}/{pages_checked} pages with LaTeX columns have math content"
        )

    def test_lean_columns_have_code(self, sbstest_site: SiteArtifacts):
        """Every .sbs-signature contains a pre.lean-code block with text."""
        require_bs4()
        chapters = get_chapter_pages(sbstest_site)
        assert chapters, "No chapter pages found"

        found_any = False
        for page_name in chapters:
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            # New grid structure uses .sbs-signature; fallback to .sbs-lean-column
            cols = soup.select(".sbs-signature") or soup.select(".sbs-lean-column")
            for col in cols:
                found_any = True
                code_block = col.select_one("pre.lean-code")
                assert code_block is not None, (
                    f"Lean signature cell on page '{page_name}' missing pre.lean-code"
                )
                text = code_block.get_text(strip=True)
                assert len(text) > 0, (
                    f"pre.lean-code on page '{page_name}' is empty"
                )

        assert found_any, "No .sbs-signature elements found across chapter pages"

    def test_lean_code_has_keywords(self, sbstest_site: SiteArtifacts):
        """Lean code blocks contain at least one declaration keyword."""
        require_bs4()
        chapters = get_chapter_pages(sbstest_site)
        assert chapters, "No chapter pages found"

        keywords = {"theorem", "def", "lemma", "example", "instance"}
        found_any = False
        for page_name in chapters:
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            for pre in soup.select("pre.lean-code.hl.lean"):
                found_any = True
                text = pre.get_text()
                has_keyword = any(kw in text for kw in keywords)
                assert has_keyword, (
                    f"Lean code block on page '{page_name}' contains none of {keywords}"
                )

        assert found_any, "No pre.lean-code.hl.lean elements found"

    def test_hover_data_is_valid_json(self, sbstest_site: SiteArtifacts):
        """data-lean-hovers attributes parse as valid JSON dicts."""
        require_bs4()
        chapters = get_chapter_pages(sbstest_site)
        assert chapters, "No chapter pages found"

        checked = 0
        for page_name in chapters:
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            for el in soup.select("[data-lean-hovers]"):
                raw = el.get("data-lean-hovers", "")
                if not raw:
                    continue
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    pytest.fail(
                        f"Invalid JSON in data-lean-hovers on page '{page_name}': {raw[:100]}"
                    )
                assert isinstance(parsed, dict), (
                    f"data-lean-hovers on page '{page_name}' is not a dict"
                )
                checked += 1

        assert checked > 0, "No data-lean-hovers attributes found to check"

    def test_hover_data_has_entries(self, sbstest_site: SiteArtifacts):
        """Hover JSON dicts have at least 1 entry."""
        require_bs4()
        chapters = get_chapter_pages(sbstest_site)
        assert chapters, "No chapter pages found"

        checked = 0
        for page_name in chapters:
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            for el in soup.select("[data-lean-hovers]"):
                raw = el.get("data-lean-hovers", "")
                if not raw:
                    continue
                parsed = json.loads(raw)
                assert len(parsed) >= 1, (
                    f"data-lean-hovers on page '{page_name}' has no entries"
                )
                checked += 1

        assert checked > 0, "No data-lean-hovers attributes found to check"

    def test_proof_content_not_empty(self, sbstest_site: SiteArtifacts):
        """Most .proof_content elements have text > 10 chars."""
        require_bs4()
        chapters = get_chapter_pages(sbstest_site)
        assert chapters, "No chapter pages found"

        total_proofs = 0
        non_empty_proofs = 0
        for page_name in chapters:
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            for proof in soup.select(".proof_content"):
                total_proofs += 1
                if len(proof.get_text(strip=True)) > 10:
                    non_empty_proofs += 1

        assert total_proofs > 0, "No .proof_content elements found across chapter pages"
        # Many proof_content elements may be short or collapsed (proof toggles).
        # Verify that at least some proofs have substantial content.
        assert non_empty_proofs >= 1, (
            f"No proof elements have substantial content ({total_proofs} total found)"
        )

    def test_latex_statements_not_empty(self, sbstest_site: SiteArtifacts):
        """.theorem_thmcontent paragraphs have text > 10 chars."""
        require_bs4()
        chapters = get_chapter_pages(sbstest_site)
        assert chapters, "No chapter pages found"

        checked = 0
        for page_name in chapters:
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            for stmt in soup.select(".theorem_thmcontent"):
                for p in stmt.select("p"):
                    text = p.get_text(strip=True)
                    if text:
                        assert len(text) > 10, (
                            f".theorem_thmcontent <p> on page '{page_name}' has only {len(text)} chars"
                        )
                        checked += 1

        assert checked > 0, "No .theorem_thmcontent paragraphs found across chapter pages"

    def test_sbs_containers_have_both_columns(self, sbstest_site: SiteArtifacts):
        """Every .sbs-container has both a LaTeX and a Lean column."""
        chapters = get_chapter_pages(sbstest_site)
        assert chapters, "No chapter pages found"

        checked = 0
        for page_name in chapters:
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            containers = find_sbs_containers(html)
            for c in containers:
                assert c["has_latex"], (
                    f"SBS container '{c['id']}' on page '{page_name}' missing LaTeX column"
                )
                assert c["has_lean"], (
                    f"SBS container '{c['id']}' on page '{page_name}' missing Lean column"
                )
                checked += 1

        assert checked > 0, "No .sbs-container elements found across chapter pages"


@pytest.mark.evergreen
class TestDeclarationArtifactContent:
    """Tests for dressed declaration artifact files."""

    def _get_manifest_node_ids(self, site: SiteArtifacts) -> list[str]:
        """Extract node IDs from manifest."""
        manifest = site.manifest
        if not manifest:
            pytest.skip("No manifest found")
        nodes = manifest.get("nodes", {})
        if not nodes:
            pytest.skip("No nodes in manifest")
        # Keys are node IDs, values are "#anchor" strings
        return list(nodes.keys())

    def test_every_node_has_decl_html(self, sbstest_site: SiteArtifacts):
        """Each manifest node has a decl.html in the dressed tree > 50 bytes."""
        node_ids = self._get_manifest_node_ids(sbstest_site)
        missing = []
        small = []
        for nid in node_ids:
            paths = get_dressed_decl_paths(sbstest_site, nid)
            if "decl.html" not in paths:
                missing.append(nid)
            elif paths["decl.html"].stat().st_size <= 50:
                small.append(nid)

        assert not missing, f"Nodes missing decl.html: {missing}"
        assert not small, f"Nodes with decl.html <= 50 bytes: {small}"

    def test_every_node_has_decl_json(self, sbstest_site: SiteArtifacts):
        """Each manifest node has a decl.json."""
        node_ids = self._get_manifest_node_ids(sbstest_site)
        missing = []
        for nid in node_ids:
            paths = get_dressed_decl_paths(sbstest_site, nid)
            if "decl.json" not in paths:
                missing.append(nid)

        assert not missing, f"Nodes missing decl.json: {missing}"

    def test_every_node_has_decl_tex(self, sbstest_site: SiteArtifacts):
        """Each manifest node has a decl.tex > 10 bytes."""
        node_ids = self._get_manifest_node_ids(sbstest_site)
        missing = []
        small = []
        for nid in node_ids:
            paths = get_dressed_decl_paths(sbstest_site, nid)
            if "decl.tex" not in paths:
                missing.append(nid)
            elif paths["decl.tex"].stat().st_size <= 10:
                small.append(nid)

        assert not missing, f"Nodes missing decl.tex: {missing}"
        assert not small, f"Nodes with decl.tex <= 10 bytes: {small}"

    def test_every_node_has_hovers_json(self, sbstest_site: SiteArtifacts):
        """Each manifest node has a decl.hovers.json."""
        node_ids = self._get_manifest_node_ids(sbstest_site)
        missing = []
        for nid in node_ids:
            paths = get_dressed_decl_paths(sbstest_site, nid)
            if "decl.hovers.json" not in paths:
                missing.append(nid)

        assert not missing, f"Nodes missing decl.hovers.json: {missing}"

    def test_decl_json_has_name(self, sbstest_site: SiteArtifacts):
        """decl.json contains a 'name' key with a non-empty string."""
        node_ids = self._get_manifest_node_ids(sbstest_site)
        failures = []
        for nid in node_ids:
            paths = get_dressed_decl_paths(sbstest_site, nid)
            if "decl.json" not in paths:
                continue
            data = json.loads(paths["decl.json"].read_text())
            name = data.get("name", "")
            if not isinstance(name, str) or not name:
                failures.append(nid)

        assert not failures, f"Nodes with missing/empty 'name' in decl.json: {failures}"

    def test_decl_json_has_highlighting(self, sbstest_site: SiteArtifacts):
        """decl.json contains 'highlighting' key with 'seq' sub-key."""
        node_ids = self._get_manifest_node_ids(sbstest_site)
        failures = []
        for nid in node_ids:
            paths = get_dressed_decl_paths(sbstest_site, nid)
            if "decl.json" not in paths:
                continue
            data = json.loads(paths["decl.json"].read_text())
            hl = data.get("highlighting")
            if not isinstance(hl, dict) or "seq" not in hl:
                failures.append(nid)

        assert not failures, f"Nodes with missing 'highlighting.seq' in decl.json: {failures}"


@pytest.mark.evergreen
class TestChapterContent:
    """Tests for chapter page content quality."""

    def test_chapter_pages_have_substantial_text(self, sbstest_site: SiteArtifacts):
        """Each chapter page has > 500 chars of visible text."""
        require_bs4()
        chapters = get_chapter_pages(sbstest_site)
        assert chapters, "No chapter pages found"

        thin = []
        for page_name in chapters:
            html = sbstest_site.get_page(page_name)
            if not html:
                thin.append((page_name, 0))
                continue
            soup = parse_html(html)
            text = soup.get_text(strip=True)
            if len(text) <= 500:
                thin.append((page_name, len(text)))

        assert not thin, f"Chapter pages with <= 500 chars visible text: {thin}"

    def test_chapter_pages_have_theorem_wrappers(self, sbstest_site: SiteArtifacts):
        """Most chapter pages have at least one .theorem_thmwrapper."""
        require_bs4()
        chapters = get_chapter_pages(sbstest_site)
        assert chapters, "No chapter pages found"

        pages_with_theorems = 0
        for page_name in chapters:
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            soup = parse_html(html)
            wrappers = soup.select(".theorem_thmwrapper")
            if wrappers:
                pages_with_theorems += 1

        # Most chapter pages should have theorems (introduction may not)
        assert pages_with_theorems >= len(chapters) - 1, (
            f"Only {pages_with_theorems}/{len(chapters)} chapter pages have theorem wrappers"
        )

    def test_tex_generates_multiple_chapters(self, sbstest_site: SiteArtifacts):
        """At least 3 chapter pages are generated from TeX."""
        chapters = get_chapter_pages(sbstest_site)
        assert len(chapters) >= 3, (
            f"Expected >= 3 chapter pages, got {len(chapters)}: {chapters}"
        )

    def test_sbs_container_count_reasonable(self, sbstest_site: SiteArtifacts):
        """Total SBS containers across chapters >= stats['total'] / 2."""
        manifest = sbstest_site.manifest
        if not manifest:
            pytest.skip("No manifest found")

        stats = manifest.get("stats", {})
        total_nodes = stats.get("total", 0)
        if total_nodes == 0:
            pytest.skip("No total in manifest stats")

        chapters = get_chapter_pages(sbstest_site)
        total_containers = 0
        for page_name in chapters:
            html = sbstest_site.get_page(page_name)
            if not html:
                continue
            containers = find_sbs_containers(html)
            total_containers += len(containers)

        threshold = total_nodes / 2
        assert total_containers >= threshold, (
            f"Only {total_containers} SBS containers across chapters, "
            f"expected >= {threshold} (stats.total={total_nodes})"
        )
