"""
Tests for SBS side-by-side alignment properties (#230, #244).

Verifies:
- Lean column toggle is removed (no sbs-toggle-indicator in CSS/JS)
- Proof content spacing: .proof_content margin-top is 0.25rem
- Grid structure: .sbs-container uses 3-row grid layout (#244)
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
class TestGridStructure:
    """Verify .sbs-container uses 3-row grid layout (#244).

    The 3-row grid aligns LaTeX statements with Lean signatures and
    LaTeX proofs with Lean proof bodies without padding hacks."""

    def test_sbs_container_has_grid_rows(self, common_css: str) -> None:
        """common.css .sbs-container should define grid-template-rows."""
        value = extract_css_property(common_css, ".sbs-container", "grid-template-rows")
        assert value is not None, (
            ".sbs-container must define grid-template-rows for 3-row layout (#244)"
        )
        assert "auto" in value, (
            f".sbs-container grid-template-rows should use 'auto' rows, got: {value}"
        )

    def test_sbs_heading_grid_placement(self, common_css: str) -> None:
        """.sbs-heading should be placed in row 1, column 1."""
        row = extract_css_property(common_css, ".sbs-heading", "grid-row")
        col = extract_css_property(common_css, ".sbs-heading", "grid-column")
        assert row is not None and "1" in row, (
            f".sbs-heading must be in grid-row 1, got: {row}"
        )
        assert col is not None and "1" in col, (
            f".sbs-heading must be in grid-column 1, got: {col}"
        )

    def test_sbs_statement_grid_placement(self, common_css: str) -> None:
        """.sbs-statement should be placed in row 2, column 1."""
        row = extract_css_property(common_css, ".sbs-statement", "grid-row")
        col = extract_css_property(common_css, ".sbs-statement", "grid-column")
        assert row is not None and "2" in row, (
            f".sbs-statement must be in grid-row 2, got: {row}"
        )
        assert col is not None and "1" in col, (
            f".sbs-statement must be in grid-column 1, got: {col}"
        )

    def test_sbs_signature_grid_placement(self, common_css: str) -> None:
        """.sbs-signature should be placed in row 2, column 2."""
        row = extract_css_property(common_css, ".sbs-signature", "grid-row")
        col = extract_css_property(common_css, ".sbs-signature", "grid-column")
        assert row is not None and "2" in row, (
            f".sbs-signature must be in grid-row 2, got: {row}"
        )
        assert col is not None and "2" in col, (
            f".sbs-signature must be in grid-column 2, got: {col}"
        )
