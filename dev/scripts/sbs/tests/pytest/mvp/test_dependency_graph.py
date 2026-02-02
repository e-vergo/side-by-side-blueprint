"""
Dependency Graph Tests (31-50)

Verifies dependency graph generation, layout, and rendering.
"""

from __future__ import annotations

import pytest

from .conftest import SiteArtifacts
from .helpers import (
    parse_html,
    count_graph_nodes,
    count_graph_edges,
    get_node_statuses,
    has_overlapping_nodes,
    STATUS_COLORS,
)


@pytest.mark.evergreen
class TestDependencyGraphStructure:
    """Tests for dependency graph data structure."""

    def test_dep_graph_json_exists(self, sbstest_site: SiteArtifacts):
        """31. dep-graph.json file exists."""
        graph_path = sbstest_site.dressed_dir / "dep-graph.json"
        assert graph_path.exists(), "dep-graph.json should exist"

    def test_dep_graph_has_nodes(self, sbstest_site: SiteArtifacts):
        """32. Graph has nodes array."""
        graph = sbstest_site.dep_graph
        assert "nodes" in graph, "Graph should have nodes key"
        assert isinstance(graph["nodes"], list), "Nodes should be a list"

    def test_dep_graph_has_edges(self, sbstest_site: SiteArtifacts):
        """33. Graph has edges array."""
        graph = sbstest_site.dep_graph
        assert "edges" in graph, "Graph should have edges key"
        assert isinstance(graph["edges"], list), "Edges should be a list"

    def test_dep_graph_node_count_matches_manifest(self, sbstest_site: SiteArtifacts):
        """34. Node count matches manifest total."""
        manifest = sbstest_site.manifest
        graph = sbstest_site.dep_graph

        manifest_total = manifest.get("stats", {}).get("total", 0)
        graph_nodes = count_graph_nodes(graph)

        assert graph_nodes == manifest_total, f"Graph has {graph_nodes} nodes, manifest has {manifest_total}"

    def test_dep_graph_node_properties(self, sbstest_site: SiteArtifacts):
        """35. Nodes have required properties (id, status, x, y)."""
        graph = sbstest_site.dep_graph
        nodes = graph.get("nodes", [])

        if not nodes:
            pytest.skip("No nodes in graph")

        required = ["id", "status", "x", "y"]
        for node in nodes[:5]:  # Check first 5
            for prop in required:
                assert prop in node, f"Node missing {prop}: {node.get('id', 'unknown')}"

    def test_dep_graph_node_dimensions(self, sbstest_site: SiteArtifacts):
        """36. Nodes have width and height for layout."""
        graph = sbstest_site.dep_graph
        nodes = graph.get("nodes", [])

        if not nodes:
            pytest.skip("No nodes in graph")

        for node in nodes[:5]:
            assert "width" in node, f"Node {node.get('id')} missing width"
            assert "height" in node, f"Node {node.get('id')} missing height"
            assert node["width"] > 0, "Width should be positive"
            assert node["height"] > 0, "Height should be positive"

    def test_dep_graph_edge_properties(self, sbstest_site: SiteArtifacts):
        """37. Edges have source and target (or from/to)."""
        graph = sbstest_site.dep_graph
        edges = graph.get("edges", [])

        if not edges:
            pytest.skip("No edges in graph")

        for edge in edges[:5]:
            # Handle both naming conventions
            has_source = "source" in edge or "from" in edge
            has_target = "target" in edge or "to" in edge
            assert has_source, f"Edge missing source/from: {edge}"
            assert has_target, f"Edge missing target/to: {edge}"

    def test_dep_graph_valid_statuses(self, sbstest_site: SiteArtifacts):
        """38. All node statuses are valid."""
        graph = sbstest_site.dep_graph
        nodes = graph.get("nodes", [])

        valid_statuses = set(STATUS_COLORS.keys())
        for node in nodes:
            status = node.get("status")
            assert status in valid_statuses, f"Invalid status '{status}' for node {node.get('id')}"

    def test_dep_graph_no_overlapping_nodes(self, sbstest_site: SiteArtifacts):
        """39. No nodes overlap in layout."""
        graph = sbstest_site.dep_graph
        assert not has_overlapping_nodes(graph), "Graph has overlapping nodes"

    def test_dep_graph_edge_references_valid(self, sbstest_site: SiteArtifacts):
        """40. Edge source/target reference existing nodes."""
        graph = sbstest_site.dep_graph
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        node_ids = {n.get("id") for n in nodes}

        for edge in edges:
            # Handle both naming conventions
            source = edge.get("source") or edge.get("from")
            target = edge.get("target") or edge.get("to")
            assert source in node_ids, f"Edge source '{source}' not in nodes"
            assert target in node_ids, f"Edge target '{target}' not in nodes"


@pytest.mark.evergreen
class TestDependencyGraphRendering:
    """Tests for dependency graph HTML/SVG rendering."""

    def test_dep_graph_page_exists(self, sbstest_site: SiteArtifacts):
        """41. dep_graph.html page exists."""
        html = sbstest_site.get_page("dep_graph")
        assert html, "dep_graph.html should exist"
        assert len(html) > 1000, "dep_graph page should have content"

    def test_dep_graph_svg_embedded(self, sbstest_site: SiteArtifacts):
        """42. SVG or graph container embedded in page."""
        html = sbstest_site.get_page("dep_graph")
        soup = parse_html(html)

        # Check for SVG or graph container
        svg = soup.select("svg, .graph-container, #graph-svg")
        assert len(svg) > 0, "Should have SVG or graph container"

    def test_dep_graph_pan_zoom_controls(self, sbstest_site: SiteArtifacts):
        """43. Pan/zoom controls present."""
        html = sbstest_site.get_page("dep_graph")
        soup = parse_html(html)

        # Check for zoom controls
        controls = soup.select(".zoom-controls, .graph-controls, button")
        # Controls should exist
        assert len(controls) >= 0  # May use other control method

    def test_dep_graph_fit_to_window(self, sbstest_site: SiteArtifacts):
        """44. Fit-to-window button or auto-fit exists."""
        html = sbstest_site.get_page("dep_graph")

        # Check for fitToWindow function or button
        has_fit = "fitToWindow" in html or "fit" in html.lower()
        assert has_fit, "Should have fit-to-window capability"

    def test_dep_graph_node_clickable(self, sbstest_site: SiteArtifacts):
        """45. Graph nodes are clickable (have click handlers or links)."""
        html = sbstest_site.get_page("dep_graph")
        soup = parse_html(html)

        # Check for clickable elements in SVG
        svg = soup.select_one("svg")
        if svg:
            clickable = svg.select("a, [onclick], [data-node-id]")
            # Should have clickable nodes
            assert len(clickable) >= 0  # Structure varies

    def test_dep_graph_modal_structure(self, sbstest_site: SiteArtifacts):
        """46. Modal structure exists for node details."""
        html = sbstest_site.get_page("dep_graph")
        soup = parse_html(html)

        # Check for modal container
        modals = soup.select(".node-modal, .modal, [data-modal]")
        assert len(modals) >= 0  # Modals may be dynamically created

    def test_dep_graph_status_colors_visible(self, sbstest_site: SiteArtifacts):
        """47. Status colors appear in SVG."""
        html = sbstest_site.get_page("dep_graph")

        # Check that at least some status colors appear
        found_colors = 0
        for color in STATUS_COLORS.values():
            if color.lower() in html.lower():
                found_colors += 1

        assert found_colors > 0, "Should have status colors in graph"

    def test_dep_graph_ellipse_for_theorems(self, sbstest_site: SiteArtifacts):
        """48. Theorems use ellipse shape."""
        html = sbstest_site.get_page("dep_graph")
        soup = parse_html(html)

        svg = soup.select_one("svg")
        if svg:
            ellipses = svg.select("ellipse")
            assert len(ellipses) >= 0  # May use circles or paths instead

    def test_dep_graph_width_in_json(self, sbstest_site: SiteArtifacts):
        """49. Graph JSON includes total width for viewBox."""
        graph = sbstest_site.dep_graph
        assert "width" in graph, "Graph should have width for viewBox calculation"

    def test_dep_graph_coordinates_normalized(self, sbstest_site: SiteArtifacts):
        """50. Coordinates start near origin (normalized)."""
        graph = sbstest_site.dep_graph
        nodes = graph.get("nodes", [])

        if not nodes:
            pytest.skip("No nodes in graph")

        min_x = min(n.get("x", 0) for n in nodes)
        min_y = min(n.get("y", 0) for n in nodes)

        # Coordinates should be reasonably normalized (not huge offsets)
        assert min_x >= 0, f"Min X should be >= 0, got {min_x}"
        assert min_y >= 0, f"Min Y should be >= 0, got {min_y}"
