"""
Tests for SBS side-by-side alignment properties (#230).

Verifies:
- Lean column toggle is removed (no sbs-toggle-indicator in CSS/JS)
- Proof content spacing: .proof_content margin-top is 0.25rem
- Lean declaration alignment: .sbs-lean-column pre.lean-code has padding-top >= 1rem
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def assets_dir() -> Path:
    """Get the path to the dress-blueprint-action/assets directory."""
    conftest_file = Path(__file__).resolve()
    dev_dir = conftest_file.parent.parent.parent.parent.parent.parent
    return dev_dir.parent / "toolchain" / "dress-blueprint-action" / "assets"


@pytest.fixture
def common_css(assets_dir: Path) -> str:
    """Read common.css content."""
    return (assets_dir / "common.css").read_text()


@pytest.fixture
def blueprint_css(assets_dir: Path) -> str:
    """Read blueprint.css content."""
    return (assets_dir / "blueprint.css").read_text()


@pytest.fixture
def plastex_js(assets_dir: Path) -> str:
    """Read plastex.js content."""
    return (assets_dir / "plastex.js").read_text()


# =============================================================================
# Helper: CSS rule parser
# =============================================================================


def extract_css_property(css: str, selector: str, prop: str) -> str | None:
    """Extract a CSS property value from a selector block.

    Finds the LAST matching selector block (to handle overrides) and
    extracts the specified property value.

    Returns the property value string, or None if not found.
    """
    escaped = re.escape(selector)
    pattern = re.compile(
        escaped + r'\s*\{([^}]*)\}',
        re.DOTALL,
    )
    matches = list(pattern.finditer(css))
    if not matches:
        return None

    for match in reversed(matches):
        block = match.group(1)
        prop_pattern = re.compile(
            r'(?:^|;)\s*' + re.escape(prop) + r'\s*:\s*([^;]+)',
            re.MULTILINE,
        )
        prop_match = prop_pattern.search(block)
        if prop_match:
            return prop_match.group(1).strip()

    return None


def parse_rem(value: str) -> float | None:
    """Parse a CSS rem value to a float. Returns None if not rem."""
    match = re.match(r'^([\d.]+)rem$', value.strip())
    return float(match.group(1)) if match else None


# =============================================================================
# 1. Toggle Removal Tests
# =============================================================================


@pytest.mark.evergreen
class TestToggleRemoval:
    """Verify the Lean column toggle has been removed (#230)."""

    def test_no_sbs_toggle_indicator_in_css(self, common_css: str) -> None:
        """common.css must not contain .sbs-toggle-indicator styles."""
        assert ".sbs-toggle-indicator" not in common_css, (
            "common.css should not contain .sbs-toggle-indicator "
            "(Lean column toggle was removed per #230)"
        )

    def test_no_sbs_collapsed_in_css(self, common_css: str) -> None:
        """common.css must not contain .sbs-collapsed styles."""
        assert ".sbs-collapsed" not in common_css, (
            "common.css should not contain .sbs-collapsed "
            "(Lean column toggle was removed per #230)"
        )

    def test_no_lean_column_toggle_in_js(self, plastex_js: str) -> None:
        """plastex.js must not contain the Lean column expand/collapse toggle."""
        assert "sbs-toggle-indicator" not in plastex_js, (
            "plastex.js should not inject .sbs-toggle-indicator "
            "(Lean column toggle was removed per #230)"
        )

    def test_no_sbs_expanded_class_in_js(self, plastex_js: str) -> None:
        """plastex.js must not add sbs-expanded/sbs-collapsed classes."""
        assert "sbs-expanded" not in plastex_js, (
            "plastex.js should not toggle sbs-expanded class "
            "(Lean column toggle was removed per #230)"
        )

    def test_proof_toggle_preserved_in_js(self, plastex_js: str) -> None:
        """plastex.js must still contain the proof body toggle."""
        assert "proof_wrapper" in plastex_js, (
            "plastex.js should still contain proof_wrapper toggle "
            "(only the Lean column toggle was removed, not the proof toggle)"
        )
        assert "lean-proof-body" in plastex_js, (
            "plastex.js should still sync lean-proof-body visibility"
        )


# =============================================================================
# 2. Proof Content Spacing Tests
# =============================================================================


@pytest.mark.evergreen
class TestProofContentSpacing:
    """Verify .proof_content has reduced top margin for equal spacing."""

    def test_proof_content_margin_top(self, common_css: str) -> None:
        """proof_content margin-top should be 0.25rem (not 0.5rem)."""
        value = extract_css_property(common_css, ".proof_content", "margin-top")
        assert value is not None, ".proof_content must define margin-top"
        assert value == "0.25rem", (
            f".proof_content margin-top should be 0.25rem for equal spacing "
            f"above/below [hide], got: {value}"
        )


# =============================================================================
# 3. Lean Declaration Alignment Tests
# =============================================================================


@pytest.mark.evergreen
class TestLeanDeclarationAlignment:
    """Verify Lean declaration code has sufficient top padding to align
    with the LaTeX statement text (below the theorem heading)."""

    def test_lean_code_has_padding_top(self, blueprint_css: str) -> None:
        """blueprint.css .sbs-lean-column pre.lean-code should have padding-top."""
        value = extract_css_property(
            blueprint_css, ".sbs-lean-column pre.lean-code", "padding-top"
        )
        assert value is not None, (
            ".sbs-lean-column pre.lean-code must define padding-top "
            "in blueprint.css for vertical alignment with LaTeX statement"
        )

    def test_lean_code_padding_top_sufficient(self, blueprint_css: str) -> None:
        """padding-top must be >= 1rem to clear the theorem heading height."""
        value = extract_css_property(
            blueprint_css, ".sbs-lean-column pre.lean-code", "padding-top"
        )
        rem_value = parse_rem(value) if value else None
        assert rem_value is not None, (
            f"padding-top should be in rem units, got: {value}"
        )
        assert rem_value >= 1.0, (
            f".sbs-lean-column pre.lean-code padding-top must be >= 1rem "
            f"to clear the theorem heading. Got {value}. "
            f"The heading is ~24px tall; values under 1rem leave the Lean code "
            f"visually above the LaTeX statement text."
        )
