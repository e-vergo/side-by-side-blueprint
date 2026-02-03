"""
Tests for the label taxonomy system.

Validates that taxonomy.yaml loads correctly, labels are well-formed,
and the Python API works as expected.
"""

from __future__ import annotations

import re

import pytest

from sbs.labels import (
    get_all_labels,
    get_dimension_for_label,
    get_label_color,
    load_taxonomy,
    validate_labels,
)

# All tests in this module are evergreen (production tests, never skip)
pytestmark = pytest.mark.evergreen


# =============================================================================
# Loading
# =============================================================================


class TestTaxonomyLoading:
    """Tests that taxonomy.yaml loads and has expected structure."""

    def test_taxonomy_loads(self) -> None:
        """YAML loads without error and has required top-level keys."""
        taxonomy = load_taxonomy()
        assert "version" in taxonomy
        assert "dimensions" in taxonomy
        assert isinstance(taxonomy["dimensions"], dict)

    def test_taxonomy_has_dimensions(self) -> None:
        """Taxonomy defines the expected set of dimensions."""
        taxonomy = load_taxonomy()
        dimensions = taxonomy["dimensions"]
        expected = {
            "origin", "type", "area_sbs", "area_devtools", "area_lean",
            "loop", "impact", "scope", "pillar", "project", "friction",
        }
        assert set(dimensions.keys()) == expected

    def test_taxonomy_has_standalone(self) -> None:
        """Taxonomy defines standalone labels."""
        taxonomy = load_taxonomy()
        standalone = taxonomy.get("standalone", [])
        assert len(standalone) >= 1
        names = [l["name"] for l in standalone]
        assert "ai-authored" in names


# =============================================================================
# Label Uniqueness
# =============================================================================


class TestLabelUniqueness:
    """Tests that all label names are unique across dimensions."""

    def test_all_labels_unique(self) -> None:
        """No duplicate label names across all dimensions and standalone."""
        all_labels = get_all_labels()
        seen: set[str] = set()
        duplicates: list[str] = []
        for label in all_labels:
            if label in seen:
                duplicates.append(label)
            seen.add(label)
        assert duplicates == [], f"Duplicate labels found: {duplicates}"


# =============================================================================
# Naming Convention
# =============================================================================


class TestLabelNaming:
    """Tests that label names follow the colon-delimited convention."""

    # Labels that are intentionally single-segment (no colons)
    SINGLE_SEGMENT_EXCEPTIONS = {"behavior", "investigation", "ai-authored"}

    def test_label_names_colon_delimited(self) -> None:
        """All multi-segment labels use colons as delimiters."""
        all_labels = get_all_labels()
        violations: list[str] = []
        for label in all_labels:
            if label in self.SINGLE_SEGMENT_EXCEPTIONS:
                continue
            # Must contain at least one colon
            if ":" not in label:
                violations.append(label)
        assert violations == [], (
            f"Labels without colons (not in exceptions): {violations}"
        )

    def test_no_spaces_in_label_names(self) -> None:
        """Label names must not contain spaces."""
        all_labels = get_all_labels()
        with_spaces = [l for l in all_labels if " " in l]
        assert with_spaces == [], f"Labels with spaces: {with_spaces}"


# =============================================================================
# Colors
# =============================================================================

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class TestColors:
    """Tests that colors are valid hex codes."""

    def test_colors_valid_hex(self) -> None:
        """All defined colors are valid 6-digit hex codes."""
        taxonomy = load_taxonomy()
        invalid: list[tuple[str, str]] = []

        # Dimension-level colors
        for dim_name, dim_data in taxonomy.get("dimensions", {}).items():
            dim_color = dim_data.get("color")
            if dim_color and not HEX_COLOR_RE.match(dim_color):
                invalid.append((f"dimension:{dim_name}", dim_color))

            # Label-level colors
            for label in dim_data.get("labels", []):
                label_color = label.get("color")
                if label_color and not HEX_COLOR_RE.match(label_color):
                    invalid.append((label["name"], label_color))

        # Standalone colors
        for label in taxonomy.get("standalone", []):
            label_color = label.get("color")
            if label_color and not HEX_COLOR_RE.match(label_color):
                invalid.append((label["name"], label_color))

        assert invalid == [], f"Invalid hex colors: {invalid}"

    def test_every_label_has_resolvable_color(self) -> None:
        """Every label resolves to a color (own or dimension default)."""
        all_labels = get_all_labels()
        missing: list[str] = []
        for label in all_labels:
            color = get_label_color(label)
            if not color:
                missing.append(label)
        assert missing == [], f"Labels with no resolvable color: {missing}"


# =============================================================================
# Validation API
# =============================================================================


class TestValidation:
    """Tests for the validate_labels() function."""

    def test_validate_labels_known(self) -> None:
        """Known labels are returned in the valid list."""
        valid, invalid = validate_labels(["bug:visual", "origin:agent", "ai-authored"])
        assert valid == ["bug:visual", "origin:agent", "ai-authored"]
        assert invalid == []

    def test_validate_labels_unknown(self) -> None:
        """Unknown labels are detected and returned in the invalid list."""
        valid, invalid = validate_labels(["bug:visual", "totally-fake", "nope:nope"])
        assert valid == ["bug:visual"]
        assert invalid == ["totally-fake", "nope:nope"]

    def test_validate_labels_empty(self) -> None:
        """Empty input produces empty output."""
        valid, invalid = validate_labels([])
        assert valid == []
        assert invalid == []


# =============================================================================
# Dimension Lookup
# =============================================================================


class TestDimensionLookup:
    """Tests for get_dimension_for_label()."""

    def test_get_dimension(self) -> None:
        """Correct dimension returned for known labels."""
        assert get_dimension_for_label("origin:user") == "origin"
        assert get_dimension_for_label("bug:visual") == "type"
        assert get_dimension_for_label("area:sbs:graph") == "area_sbs"
        assert get_dimension_for_label("area:devtools:cli") == "area_devtools"
        assert get_dimension_for_label("area:lean:dress") == "area_lean"
        assert get_dimension_for_label("loop:work") == "loop"
        assert get_dimension_for_label("impact:visual") == "impact"
        assert get_dimension_for_label("scope:single-repo") == "scope"
        assert get_dimension_for_label("pillar:user-effectiveness") == "pillar"
        assert get_dimension_for_label("project:sbs-test") == "project"
        assert get_dimension_for_label("friction:context-loss") == "friction"

    def test_get_dimension_standalone(self) -> None:
        """Standalone labels return 'standalone'."""
        assert get_dimension_for_label("ai-authored") == "standalone"

    def test_get_dimension_unknown(self) -> None:
        """Unknown labels return None."""
        assert get_dimension_for_label("nonexistent:label") is None


# =============================================================================
# Label Count Sanity
# =============================================================================


class TestLabelCount:
    """Sanity check on total label count."""

    def test_label_count(self) -> None:
        """Total label count is between 100 and 150 (sanity check)."""
        all_labels = get_all_labels()
        count = len(all_labels)
        assert 100 <= count <= 150, (
            f"Expected 100-150 labels, got {count}. "
            f"Taxonomy may have drifted significantly."
        )
