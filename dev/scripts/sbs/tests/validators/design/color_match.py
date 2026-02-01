"""
Status color match validator.

Validates that CSS status color variables match the canonical hex values
defined in Lean (Dress/Graph/Svg.lean). This ensures visual consistency
between the graph rendering and CSS styling.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base import BaseValidator, ValidationContext, ValidatorResult
from ..registry import register_validator
from .css_parser import extract_css_variables, normalize_hex_color


# =============================================================================
# Canonical Color Definitions
# =============================================================================

# Source of truth: Dress/Dress/Graph/Svg.lean
# These hex values MUST match the Lean definitions exactly.
CANONICAL_COLORS: dict[str, str] = {
    "notReady": "#F4A460",  # Sandy Brown
    "ready": "#20B2AA",  # Light Sea Green
    "sorry": "#8B0000",  # Dark Red
    "proven": "#90EE90",  # Light Green
    "fullyProven": "#228B22",  # Forest Green
    "mathlibReady": "#87CEEB",  # Light Blue
}

# Mapping from CSS variable names (kebab-case) to canonical keys (camelCase)
CSS_TO_CANONICAL: dict[str, str] = {
    "--sbs-status-not-ready": "notReady",
    "--sbs-status-ready": "ready",
    "--sbs-status-sorry": "sorry",
    "--sbs-status-proven": "proven",
    "--sbs-status-fully-proven": "fullyProven",
    "--sbs-status-mathlib-ready": "mathlibReady",
}


# =============================================================================
# Default CSS Path
# =============================================================================


def _get_default_css_path() -> Path:
    """Get the default path to common.css.

    Returns the path relative to this file's location in the repository.
    """
    # This file is at: dev/scripts/sbs/tests/validators/design/color_match.py
    # common.css is at: toolchain/dress-blueprint-action/assets/common.css
    this_file = Path(__file__).resolve()
    repo_root = this_file.parent.parent.parent.parent.parent.parent.parent
    return repo_root / "toolchain" / "dress-blueprint-action" / "assets" / "common.css"


# =============================================================================
# Validator
# =============================================================================


@register_validator
class StatusColorValidator(BaseValidator):
    """Validates that CSS status colors match canonical Lean definitions.

    This is a deterministic binary validator (T5 in the test suite).
    It parses common.css, extracts the 6 status color variables, and
    compares each against the canonical hex values from Lean.

    Expected context.extra keys:
        css_path: Path | str - Path to CSS file (default: common.css in repo)

    Validation criteria:
        - All 6 status variables must be present
        - Each must exactly match the canonical hex value (case-insensitive)

    Recorded metrics:
        colors_checked: int - Number of colors validated (always 6)
        colors_matched: int - Number of colors that matched
        mismatches: list[dict] - Details of any mismatches
    """

    def __init__(self) -> None:
        super().__init__("status-color-match", "visual")

    def validate(self, context: ValidationContext) -> ValidatorResult:
        """Validate status colors in CSS match canonical Lean values.

        Args:
            context: Validation context. May contain 'css_path' in extra.

        Returns:
            ValidatorResult with pass/fail and mismatch details.
        """
        # Determine CSS path
        css_path_raw = context.extra.get("css_path")
        if css_path_raw:
            css_path = Path(css_path_raw) if isinstance(css_path_raw, str) else css_path_raw
        else:
            css_path = _get_default_css_path()

        # Check file exists
        if not css_path.exists():
            return self._make_fail(
                findings=[f"CSS file not found: {css_path}"],
                metrics={
                    "colors_checked": 0,
                    "colors_matched": 0,
                    "mismatches": [],
                    "error": "file_not_found",
                },
                confidence=1.0,
            )

        # Parse CSS and extract variables
        try:
            css_content = css_path.read_text(encoding="utf-8")
        except OSError as e:
            return self._make_fail(
                findings=[f"Failed to read CSS file: {e}"],
                metrics={
                    "colors_checked": 0,
                    "colors_matched": 0,
                    "mismatches": [],
                    "error": "read_error",
                },
                confidence=1.0,
            )

        variables = extract_css_variables(css_content)

        # Compare each status color
        mismatches: list[dict[str, Any]] = []

        for css_var, canonical_key in CSS_TO_CANONICAL.items():
            actual_raw = variables.get(css_var, "")
            expected = CANONICAL_COLORS[canonical_key]

            # Normalize both for comparison
            actual_normalized = normalize_hex_color(actual_raw) if actual_raw else ""
            expected_normalized = normalize_hex_color(expected)

            if actual_normalized != expected_normalized:
                mismatches.append(
                    {
                        "variable": css_var,
                        "canonical_key": canonical_key,
                        "expected": expected_normalized,
                        "actual": actual_normalized if actual_normalized else "NOT FOUND",
                        "actual_raw": actual_raw,
                    }
                )

        # Build result
        passed = len(mismatches) == 0
        num_matched = len(CSS_TO_CANONICAL) - len(mismatches)

        findings: list[str] = []
        if passed:
            findings.append(f"All {len(CSS_TO_CANONICAL)} status colors match canonical values")
        else:
            for m in mismatches:
                findings.append(
                    f"{m['variable']}: expected {m['expected']}, got {m['actual']}"
                )

        return self._make_result(
            passed=passed,
            findings=findings,
            metrics={
                "colors_checked": len(CSS_TO_CANONICAL),
                "colors_matched": num_matched,
                "mismatches": mismatches,
                "css_path": str(css_path),
            },
            confidence=1.0,  # Deterministic check
            details={
                "canonical_colors": CANONICAL_COLORS,
                "css_variables_found": {
                    k: v for k, v in variables.items() if k.startswith("--sbs-status-")
                },
            },
        )
