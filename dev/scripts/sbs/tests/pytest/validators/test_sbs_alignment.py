"""
Tests for SBS side-by-side alignment properties (#230).

Verifies:
- Lean column toggle is removed (no sbs-toggle-indicator in CSS/JS)
- Proof content spacing: .proof_content margin-top is 0.25rem
- Lean declaration alignment: .sbs-lean-column pre.lean-code has padding-top
- Lean proof body alignment: .lean-proof-body has margin-top
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
    # Escape special regex chars in selector but keep dots and hyphens
    escaped = re.escape(selector)
    # Match the selector followed by a { ... } block
    pattern = re.compile(
        escaped + r'\s*\{([^}]*)\}',
        re.DOTALL,
    )
    matches = list(pattern.finditer(css))
    if not matches:
        return None

    # Check all matches (last one wins for overrides)
    for match in reversed(matches):
        block = match.group(1)
        # Extract the property value
        prop_pattern = re.compile(
            r'(?:^|;)\s*' + re.escape(prop) + r'\s*:\s*([^;]+)',
            re.MULTILINE,
        )
        prop_match = prop_pattern.search(block)
        if prop_match:
            return prop_match.group(1).strip()

    return None


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
    """Verify Lean declaration code has top padding for alignment."""

    def test_lean_code_has_padding_top(self, blueprint_css: str) -> None:
        """blueprint.css .sbs-lean-column pre.lean-code should have padding-top."""
        value = extract_css_property(
            blueprint_css, ".sbs-lean-column pre.lean-code", "padding-top"
        )
        assert value is not None, (
            ".sbs-lean-column pre.lean-code must define padding-top "
            "in blueprint.css for vertical alignment with LaTeX statement"
        )

    def test_lean_code_padding_top_value(self, blueprint_css: str) -> None:
        """padding-top should be 0.35rem."""
        value = extract_css_property(
            blueprint_css, ".sbs-lean-column pre.lean-code", "padding-top"
        )
        assert value == "0.35rem", (
            f".sbs-lean-column pre.lean-code padding-top should be 0.35rem, "
            f"got: {value}"
        )


# =============================================================================
# 4. Lean Proof Body Alignment Tests
# =============================================================================


@pytest.mark.evergreen
class TestLeanProofBodyAlignment:
    """Verify Lean proof body has top margin for alignment."""

    def test_lean_proof_body_has_margin_top(self, common_css: str) -> None:
        """.lean-proof-body should have margin-top defined."""
        value = extract_css_property(common_css, ".lean-proof-body", "margin-top")
        assert value is not None, (
            ".lean-proof-body must define margin-top in common.css "
            "for vertical alignment with LaTeX proof content"
        )

    def test_lean_proof_body_margin_top_value(self, common_css: str) -> None:
        """margin-top should be 0.25rem."""
        value = extract_css_property(common_css, ".lean-proof-body", "margin-top")
        assert value == "0.25rem", (
            f".lean-proof-body margin-top should be 0.25rem, got: {value}"
        )
