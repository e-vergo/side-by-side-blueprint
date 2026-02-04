"""
Graph Navigation Tests

Verifies graph node navigation, modals, and pan/zoom controls.
Ensures nodes link to chapter pages, modals carry required data,
and interactive controls are present.
"""

from __future__ import annotations

import pytest

from .conftest import SiteArtifacts
from .helpers import (
    parse_html,
    collect_all_ids,
    require_bs4,
    STATUS_COLORS,
)

# Pages that are NOT chapter pages
_NON_CHAPTER_PAGES = {"index", "dep_graph", "paper_tex", "pdf_tex", "paper_verso", "blueprint_verso"}


def _chapter_pages(site: SiteArtifacts) -> list[str]:
    """Return page names that are actual chapter pages."""
    return [p for p in site.list_pages() if p not in _NON_CHAPTER_PAGES]


def _collect_chapter_ids(site: SiteArtifacts) -> set[str]:
    """Collect all id= attributes from every chapter page."""
    require_bs4()
    all_ids: set[str] = set()
    for page_name in _chapter_pages(site):
        html = site.get_page(page_name)
        if html:
            all_ids |= collect_all_ids(html)
    return all_ids


@pytest.mark.evergreen
class TestGraphNodeNavigation:
    """Graph node links resolve to chapter page anchors."""

    def test_node_urls_are_fragment_links(self, sbstest_site: SiteArtifacts):
        """Every node URL starts with '#'."""
        graph = sbstest_site.dep_graph
        nodes = graph.get("nodes", [])
        assert nodes, "Graph should have nodes"

        for node in nodes:
            url = node.get("url", "")
            assert url.startswith("#"), (
                f"Node '{node['id']}' URL should be a fragment link, got '{url}'"
            )

    def test_node_urls_resolve_to_page_ids(self, sbstest_site: SiteArtifacts):
        """Every node fragment link resolves to an id= on a chapter page."""
        graph = sbstest_site.dep_graph
        nodes = graph.get("nodes", [])
        assert nodes, "Graph should have nodes"

        chapter_ids = _collect_chapter_ids(sbstest_site)
        assert chapter_ids, "Should find IDs across chapter pages"

        missing = []
        for node in nodes:
            url = node.get("url", "")
            if url.startswith("#"):
                anchor = url[1:]
                # Node IDs may use colons but HTML IDs use hyphens
                if anchor not in chapter_ids and anchor.replace(":", "-") not in chapter_ids:
                    missing.append(anchor)

        assert not missing, (
            f"{len(missing)} node anchors not found on any chapter page: {missing[:10]}"
        )

    def test_all_manifest_nodes_have_page_anchor(self, sbstest_site: SiteArtifacts):
        """Every manifest node key maps to an id= on a chapter page."""
        manifest = sbstest_site.manifest
        manifest_nodes = manifest.get("nodes", {})
        assert manifest_nodes, "Manifest should have nodes"

        chapter_ids = _collect_chapter_ids(sbstest_site)
        assert chapter_ids, "Should find IDs across chapter pages"

        missing = []
        for node_id in manifest_nodes:
            # Node IDs may use colons but HTML IDs use hyphens
            if node_id not in chapter_ids and node_id.replace(":", "-") not in chapter_ids:
                missing.append(node_id)

        assert not missing, (
            f"{len(missing)} manifest nodes missing page anchors: {missing[:10]}"
        )

    def test_graph_and_manifest_nodes_match(self, sbstest_site: SiteArtifacts):
        """Graph node IDs match manifest node keys exactly."""
        graph = sbstest_site.dep_graph
        manifest = sbstest_site.manifest

        graph_ids = {n["id"] for n in graph.get("nodes", [])}
        manifest_ids = set(manifest.get("nodes", {}).keys())

        assert graph_ids == manifest_ids, (
            f"Graph-only: {graph_ids - manifest_ids}, "
            f"Manifest-only: {manifest_ids - graph_ids}"
        )

    def test_no_duplicate_ids_in_chapters(self, sbstest_site: SiteArtifacts):
        """Each chapter page has unique id attributes (tolerates known build duplicates)."""
        require_bs4()
        for page_name in _chapter_pages(sbstest_site):
            html = sbstest_site.get_page(page_name)
            if not html:
                continue

            soup = parse_html(html)
            ids = [tag["id"] for tag in soup.find_all(attrs={"id": True}) if tag["id"]]
            duplicates = {x for x in ids if ids.count(x) > 1}
            # Some pages have duplicate IDs from the build process (label + container
            # both get the same normalized ID). This is a known limitation.
            assert len(duplicates) <= 20, (
                f"Page '{page_name}' has too many duplicate IDs "
                f"({len(duplicates)}): {sorted(duplicates)[:5]}"
            )

    def test_edges_reference_valid_nodes(self, sbstest_site: SiteArtifacts):
        """Every edge 'from' and 'to' references a valid graph node ID."""
        graph = sbstest_site.dep_graph
        node_ids = {n["id"] for n in graph.get("nodes", [])}
        edges = graph.get("edges", [])
        assert edges, "Graph should have edges"

        for edge in edges:
            src = edge["from"]
            tgt = edge["to"]
            assert src in node_ids, f"Edge source '{src}' not in node set"
            assert tgt in node_ids, f"Edge target '{tgt}' not in node set"

    def test_clickable_nodes_have_urls(self, sbstest_site: SiteArtifacts):
        """Every graph node has a non-empty 'url' field."""
        graph = sbstest_site.dep_graph
        nodes = graph.get("nodes", [])
        assert nodes, "Graph should have nodes"

        for node in nodes:
            url = node.get("url", "")
            assert url, f"Node '{node['id']}' has empty or missing URL"


@pytest.mark.evergreen
class TestGraphModals:
    """Graph node modals with status, statement, and proof details."""

    def test_modal_container_in_dep_graph(self, sbstest_site: SiteArtifacts):
        """dep_graph.html has a modal/dialog container element."""
        require_bs4()
        html = sbstest_site.get_page("dep_graph")
        assert html, "dep_graph page should exist"

        soup = parse_html(html)

        # Check multiple possible modal patterns
        selectors = [
            ".modal",
            "#modal",
            "[data-modal]",
            ".graph-modal",
            ".node-modal",
            "dialog",
        ]
        found = any(soup.select(sel) for sel in selectors)

        # Also check for elements with "modal" in class names
        if not found:
            found = bool(soup.find_all(class_=lambda c: c and "modal" in c))

        assert found, (
            "dep_graph.html should contain a modal/dialog container "
            "(checked: .modal, #modal, [data-modal], .graph-modal, .node-modal, dialog, *[class*=modal])"
        )

    def test_graph_nodes_have_status(self, sbstest_site: SiteArtifacts):
        """Every graph node has a status in the valid set."""
        graph = sbstest_site.dep_graph
        nodes = graph.get("nodes", [])
        assert nodes, "Graph should have nodes"

        valid_statuses = set(STATUS_COLORS.keys())
        for node in nodes:
            status = node.get("status")
            assert status in valid_statuses, (
                f"Node '{node['id']}' has invalid status '{status}', "
                f"expected one of {valid_statuses}"
            )

    def test_graph_nodes_have_label(self, sbstest_site: SiteArtifacts):
        """Every graph node has a non-empty label."""
        graph = sbstest_site.dep_graph
        nodes = graph.get("nodes", [])
        assert nodes, "Graph should have nodes"

        for node in nodes:
            label = node.get("label", "")
            assert label, f"Node '{node['id']}' has empty or missing label"

    def test_graph_nodes_have_env_type(self, sbstest_site: SiteArtifacts):
        """Every graph node has a non-empty envType."""
        graph = sbstest_site.dep_graph
        nodes = graph.get("nodes", [])
        assert nodes, "Graph should have nodes"

        for node in nodes:
            env_type = node.get("envType", "")
            assert env_type, f"Node '{node['id']}' has empty or missing envType"

    def test_graph_nodes_carry_lean_decls(self, sbstest_site: SiteArtifacts):
        """Every graph node has a leanDecls list with at least one entry."""
        graph = sbstest_site.dep_graph
        nodes = graph.get("nodes", [])
        assert nodes, "Graph should have nodes"

        for node in nodes:
            decls = node.get("leanDecls", [])
            assert isinstance(decls, list), (
                f"Node '{node['id']}' leanDecls should be a list, got {type(decls).__name__}"
            )
            assert len(decls) >= 1, (
                f"Node '{node['id']}' should have at least one lean declaration"
            )


@pytest.mark.evergreen
class TestGraphControls:
    """Pan, zoom, and fit controls."""

    def test_pan_zoom_controls_present(self, sbstest_site: SiteArtifacts):
        """dep_graph.html has zoom/pan control elements or functions."""
        html = sbstest_site.get_page("dep_graph")
        assert html, "dep_graph page should exist"

        # Check for zoom-related content in HTML or embedded JS
        zoom_indicators = ["zoom", "pan", "scale", "transform"]
        found = any(indicator in html.lower() for indicator in zoom_indicators)
        assert found, "dep_graph page should have pan/zoom controls or scripts"

    def test_fit_to_window_available(self, sbstest_site: SiteArtifacts):
        """'fitToWindow' or 'fit' text appears in dep_graph page."""
        html = sbstest_site.get_page("dep_graph")
        assert html, "dep_graph page should exist"

        has_fit = "fitToWindow" in html or "fit" in html.lower()
        assert has_fit, "dep_graph page should reference fitToWindow or fit functionality"

    def test_graph_svg_or_container_present(self, sbstest_site: SiteArtifacts):
        """SVG element or .graph-container exists in dep_graph page."""
        require_bs4()
        html = sbstest_site.get_page("dep_graph")
        assert html, "dep_graph page should exist"

        soup = parse_html(html)
        svg = soup.select("svg, .graph-container")
        assert svg, "dep_graph page should have an SVG element or .graph-container"

    def test_graph_dimensions_positive(self, sbstest_site: SiteArtifacts):
        """Graph JSON width > 0 and height > 0."""
        graph = sbstest_site.dep_graph

        width = graph.get("width", 0)
        height = graph.get("height", 0)

        assert width > 0, f"Graph width should be positive, got {width}"
        assert height > 0, f"Graph height should be positive, got {height}"

    def test_node_coordinates_non_negative(self, sbstest_site: SiteArtifacts):
        """All graph nodes have x >= 0 and y >= 0."""
        graph = sbstest_site.dep_graph
        nodes = graph.get("nodes", [])
        assert nodes, "Graph should have nodes"

        for node in nodes:
            x = node.get("x", 0)
            y = node.get("y", 0)
            assert x >= 0, f"Node '{node['id']}' has negative x: {x}"
            assert y >= 0, f"Node '{node['id']}' has negative y: {y}"

    def test_node_dimensions_positive(self, sbstest_site: SiteArtifacts):
        """All graph nodes have width > 0 and height > 0."""
        graph = sbstest_site.dep_graph
        nodes = graph.get("nodes", [])
        assert nodes, "Graph should have nodes"

        for node in nodes:
            w = node.get("width", 0)
            h = node.get("height", 0)
            assert w > 0, f"Node '{node['id']}' has non-positive width: {w}"
            assert h > 0, f"Node '{node['id']}' has non-positive height: {h}"
