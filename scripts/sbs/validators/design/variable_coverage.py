"""
CSS variable coverage validator (T6).

Measures what percentage of color values in CSS files use CSS variables
(`var(--*)`) rather than hardcoded hex/rgb values. This enforces design
system consistency and makes theming (light/dark mode) easier.

This is an (Aesthetic, Deterministic, Gradient) test:
- Aesthetic: Evaluates design system adherence
- Deterministic: Produces consistent results given same input
- Gradient: Returns a coverage percentage (0.0-1.0)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..base import BaseValidator, ValidationContext, ValidatorResult
from ..registry import register_validator


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class ColorUsage:
    """Represents a color value used in a CSS property.

    Attributes:
        file: Name of the CSS file containing the usage.
        line_number: Line number where the color was found.
        property_name: CSS property name (e.g., 'background-color').
        value: The full property value.
        color_value: The extracted color value (hex, rgb, or var reference).
        uses_variable: Whether this usage references a CSS variable.
    """

    file: str
    line_number: int
    property_name: str
    value: str
    color_value: str
    uses_variable: bool


# =============================================================================
# Constants
# =============================================================================


# Named colors that are acceptable and don't count as violations
ACCEPTABLE_NAMED_COLORS = frozenset({
    # CSS named colors commonly used
    "transparent",
    "inherit",
    "initial",
    "unset",
    "currentcolor",
    "currentColor",
    # Basic colors that are often semantically meaningful
    "white",
    "black",
    "none",
})

# Properties that can contain color values
COLOR_PROPERTIES = frozenset({
    "color",
    "background-color",
    "background",
    "border-color",
    "border",
    "border-top-color",
    "border-right-color",
    "border-bottom-color",
    "border-left-color",
    "border-top",
    "border-right",
    "border-bottom",
    "border-left",
    "outline-color",
    "outline",
    "text-decoration-color",
    "box-shadow",
    "text-shadow",
    "fill",
    "stroke",
    "caret-color",
    "column-rule-color",
    "accent-color",
})


# =============================================================================
# Parsing Functions
# =============================================================================


def _remove_comments(content: str) -> str:
    """Remove CSS comments from content."""
    return re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)


def is_named_color(value: str) -> bool:
    """Check if a value is an acceptable named color.

    Args:
        value: Color value to check.

    Returns:
        True if the value is an acceptable named color.
    """
    return value.lower().strip() in {c.lower() for c in ACCEPTABLE_NAMED_COLORS}


def extract_color_usages(css_content: str, filename: str = "") -> list[ColorUsage]:
    """Extract all color usages from CSS content.

    This function finds all places where colors are used in CSS properties,
    distinguishing between:
    - CSS variable references: var(--sbs-*), var(--bp-*)
    - Hardcoded hex colors: #fff, #ffffff
    - Hardcoded rgb/rgba/hsl/hsla
    - Named colors: white, black, transparent

    Args:
        css_content: Raw CSS content string.
        filename: Name of the file for error reporting.

    Returns:
        List of ColorUsage objects.
    """
    usages: list[ColorUsage] = []

    # Remove comments first
    content = _remove_comments(css_content)

    # Patterns for color detection
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    rgb_pattern = re.compile(r"rgba?\s*\([^)]+\)")
    hsl_pattern = re.compile(r"hsla?\s*\([^)]+\)")
    var_pattern = re.compile(r"var\s*\(\s*--[^)]+\)")

    # Pattern to find property declarations (handles both single-line and multi-line)
    # Matches: property-name: value; or property-name: value}
    decl_pattern = re.compile(r"([\w-]+)\s*:\s*([^;{}]+?)(?:;|(?=\s*}))")

    # Track line numbers by position in the original content
    def get_line_number(pos: int) -> int:
        return content[:pos].count("\n") + 1

    for match in decl_pattern.finditer(content):
        prop_name = match.group(1).lower()
        prop_value = match.group(2).strip()
        line_num = get_line_number(match.start())

        # Skip CSS variable definitions (we only care about usages)
        if prop_name.startswith("--"):
            continue

        # Only check color-related properties
        if prop_name not in COLOR_PROPERTIES:
            continue

        # Find var() references
        var_matches = var_pattern.findall(prop_value)
        for var_ref in var_matches:
            usages.append(
                ColorUsage(
                    file=filename,
                    line_number=line_num,
                    property_name=prop_name,
                    value=prop_value,
                    color_value=var_ref,
                    uses_variable=True,
                )
            )

        # Find hex colors
        for hex_match in hex_pattern.finditer(prop_value):
            usages.append(
                ColorUsage(
                    file=filename,
                    line_number=line_num,
                    property_name=prop_name,
                    value=prop_value,
                    color_value=hex_match.group(),
                    uses_variable=False,
                )
            )

        # Find rgb/rgba
        for rgb_match in rgb_pattern.finditer(prop_value):
            usages.append(
                ColorUsage(
                    file=filename,
                    line_number=line_num,
                    property_name=prop_name,
                    value=prop_value,
                    color_value=rgb_match.group(),
                    uses_variable=False,
                )
            )

        # Find hsl/hsla
        for hsl_match in hsl_pattern.finditer(prop_value):
            usages.append(
                ColorUsage(
                    file=filename,
                    line_number=line_num,
                    property_name=prop_name,
                    value=prop_value,
                    color_value=hsl_match.group(),
                    uses_variable=False,
                )
            )

    return usages


# =============================================================================
# Validator
# =============================================================================


@register_validator
class CSSVariableCoverageValidator(BaseValidator):
    """Validates CSS variable usage coverage for colors.

    Measures what percentage of color values use CSS variables versus
    hardcoded values. Higher coverage indicates better design system
    adherence and easier theming support.

    Configuration via context.extra:
        - css_dir: Path to CSS directory (default: dress-blueprint-action/assets)
        - coverage_threshold: Minimum acceptable coverage (default: 0.95)

    Metrics returned:
        - coverage: Ratio of variable usages to total color usages (0.0-1.0)
        - total_color_usages: Total number of color usages found
        - variable_usages: Number of usages using CSS variables
        - hardcoded_count: Number of hardcoded color values
        - violations: List of violation details (file, line, value)
    """

    def __init__(self) -> None:
        super().__init__("css-variable-coverage", "visual")

    def validate(self, context: ValidationContext) -> ValidatorResult:
        """Validate CSS variable coverage.

        Args:
            context: Validation context with optional css_dir and coverage_threshold.

        Returns:
            ValidatorResult with coverage metrics and any violations.
        """
        # Get CSS directory from context or default
        css_dir = context.extra.get("css_dir")
        if css_dir is None:
            # Default to dress-blueprint-action/assets
            css_dir = (
                Path(__file__).parent.parent.parent.parent.parent
                / "dress-blueprint-action"
                / "assets"
            )
        elif isinstance(css_dir, str):
            css_dir = Path(css_dir)

        # Get coverage threshold
        threshold = context.extra.get("coverage_threshold", 0.95)

        # CSS files to analyze
        css_files = ["common.css", "blueprint.css", "paper.css", "dep_graph.css"]

        # Collect all color usages
        all_usages: list[ColorUsage] = []
        files_found: list[str] = []
        files_missing: list[str] = []

        for css_file in css_files:
            path = css_dir / css_file
            if not path.exists():
                files_missing.append(css_file)
                continue

            files_found.append(css_file)
            content = path.read_text(encoding="utf-8")
            usages = extract_color_usages(content, css_file)
            all_usages.extend(usages)

        if not files_found:
            return self._make_fail(
                findings=[f"No CSS files found in {css_dir}"],
                metrics={"error": "no_files_found", "searched_dir": str(css_dir)},
            )

        # Categorize usages
        variable_usages: list[ColorUsage] = []
        hardcoded_usages: list[ColorUsage] = []

        for usage in all_usages:
            if usage.uses_variable:
                variable_usages.append(usage)
            else:
                # Check if it's an acceptable named color
                if not is_named_color(usage.color_value):
                    hardcoded_usages.append(usage)
                # Named colors are not counted either way

        total_counted = len(variable_usages) + len(hardcoded_usages)

        # Calculate coverage
        if total_counted == 0:
            coverage = 1.0  # No color usages = perfect coverage
        else:
            coverage = len(variable_usages) / total_counted

        # Build violations list
        violations = [
            {
                "file": u.file,
                "line": u.line_number,
                "property": u.property_name,
                "value": u.color_value,
            }
            for u in hardcoded_usages
        ]

        # Build findings (limited to first 10)
        findings = [
            f"{v['file']}:{v['line']}: hardcoded {v['value']} in {v['property']}"
            for v in violations[:10]
        ]
        if len(violations) > 10:
            findings.append(f"... and {len(violations) - 10} more violations")

        passed = coverage >= threshold

        return self._make_result(
            passed=passed,
            findings=findings,
            metrics={
                "coverage": round(coverage, 4),
                "total_color_usages": total_counted,
                "variable_usages": len(variable_usages),
                "hardcoded_count": len(hardcoded_usages),
                "violations": violations,
                "threshold": threshold,
                "files_analyzed": files_found,
                "files_missing": files_missing,
            },
            confidence=1.0,
        )
