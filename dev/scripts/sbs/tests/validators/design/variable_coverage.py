"""
CSS variable coverage validator (T6).

Measures what percentage of color values in CSS files use CSS variables
(`var(--*)`) rather than hardcoded hex/rgb values. This enforces design
system consistency and makes theming (light/dark mode) easier.

This is an (Aesthetic, Deterministic, Gradient) test:
- Aesthetic: Evaluates design system adherence
- Deterministic: Produces consistent results given same input
- Gradient: Returns a coverage percentage (0.0-1.0)

Exclusions:
By default, intentional hardcoded colors are excluded from violation counts:
- Lean syntax highlighting classes (.lean-keyword, .lean-const, etc.)
- Rainbow bracket colors (.lean-bracket-1 through .lean-bracket-6)
- Token classes (.keyword.token, .const.token, etc.)
- CSS variable definitions in :root blocks
- Dark mode variable overrides in html[data-theme="dark"] blocks
- Verso/SubVerso highlighting classes (.hl.lean)

These are intentionally hardcoded because they implement syntax themes
that must remain consistent and are not meant to be overridden by the
design system's color variables.
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
        selector_context: The CSS selector(s) this rule applies to.
        is_variable_definition: Whether this is inside :root or similar.
        is_syntax_highlighting: Whether this is for Lean syntax highlighting.
    """

    file: str
    line_number: int
    property_name: str
    value: str
    color_value: str
    uses_variable: bool
    selector_context: str = ""
    is_variable_definition: bool = False
    is_syntax_highlighting: bool = False


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
# Syntax Highlighting Exclusion Patterns
# =============================================================================

# Regex patterns for selectors that are intentionally hardcoded for syntax
# highlighting. These should NOT be counted as violations because they
# implement language-specific themes that are independent of the design system.
SYNTAX_SELECTOR_PATTERNS = [
    # Lean syntax highlighting classes
    r"\.lean-keyword",
    r"\.lean-const",
    r"\.lean-var",
    r"\.lean-string",
    r"\.lean-option",
    r"\.lean-docstring",
    r"\.lean-sort",
    r"\.lean-level",
    r"\.lean-module",
    r"\.lean-expr",
    r"\.lean-text",
    r"\.lean-sorry",
    r"\.lean-number",
    r"\.lean-operator",
    r"\.lean-comment",
    # Rainbow bracket colors (6-depth cycling)
    r"\.lean-bracket-\d+",
    # Token classes (Verso/SubVerso highlighting)
    r"\.keyword\.token",
    r"\.const\.token",
    r"\.var\.token",
    r"\.literal\.token",
    r"\.option\.token",
    r"\.sort\.token",
    r"\.typed\.token",
    r"\.module-name\.token",
    r"\.sorry\.token",
    # Verso/SubVerso .hl.lean syntax classes
    r"\.hl\.lean\s+\.",  # .hl.lean followed by another class
    # Line comments
    r"\.line-comment",
    # Hypotheses in tactic state
    r"\.hypotheses\s+\.name",
    # Token binding highlight
    r"\.token\.binding-hl",
    # Docstring code
    r"\.docstring\s+code",
]

# Compile patterns for efficiency
_COMPILED_SYNTAX_PATTERNS = [re.compile(p) for p in SYNTAX_SELECTOR_PATTERNS]


def is_syntax_highlighting_context(selector_line: str) -> bool:
    """Check if a CSS line is in a syntax highlighting context.

    Args:
        selector_line: The CSS selector line or rule context.

    Returns:
        True if the line matches syntax highlighting patterns.
    """
    for pattern in _COMPILED_SYNTAX_PATTERNS:
        if pattern.search(selector_line):
            return True
    return False


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

    It also tracks selector context to identify:
    - Variable definitions in :root blocks
    - Syntax highlighting rules (Lean, Verso/SubVerso)
    - Dark mode variable overrides

    Args:
        css_content: Raw CSS content string.
        filename: Name of the file for error reporting.

    Returns:
        List of ColorUsage objects with context metadata.
    """
    usages: list[ColorUsage] = []

    # Remove comments first
    content = _remove_comments(css_content)

    # Patterns for color detection
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    rgb_pattern = re.compile(r"rgba?\s*\([^)]+\)")
    hsl_pattern = re.compile(r"hsla?\s*\([^)]+\)")
    var_pattern = re.compile(r"var\s*\(\s*--[^)]+\)")

    # Pattern to find CSS rule blocks: selector { declarations }
    # We need to track which selector each declaration belongs to
    rule_pattern = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)

    # Pattern to find property declarations
    decl_pattern = re.compile(r"([\w-]+)\s*:\s*([^;{}]+?)(?:;|(?=\s*}))")

    # Patterns for variable definition contexts
    root_pattern = re.compile(r":root\b")
    dark_mode_pattern = re.compile(r'html\[data-theme\s*=\s*["\']dark["\']\]')

    # Track line numbers by position in the original content
    def get_line_number(pos: int) -> int:
        return content[:pos].count("\n") + 1

    for rule_match in rule_pattern.finditer(content):
        selector = rule_match.group(1).strip()
        declarations = rule_match.group(2)
        rule_start_pos = rule_match.start()

        # Determine context
        is_root = bool(root_pattern.search(selector))
        is_dark_mode_override = bool(dark_mode_pattern.search(selector))
        is_variable_def = is_root or is_dark_mode_override
        is_syntax = is_syntax_highlighting_context(selector)

        for decl_match in decl_pattern.finditer(declarations):
            prop_name = decl_match.group(1).lower()
            prop_value = decl_match.group(2).strip()

            # Calculate line number relative to rule start
            decl_pos_in_rule = rule_start_pos + rule_match.group(1).__len__() + 1 + decl_match.start()
            line_num = get_line_number(decl_pos_in_rule)

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
                        selector_context=selector,
                        is_variable_definition=is_variable_def,
                        is_syntax_highlighting=is_syntax,
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
                        selector_context=selector,
                        is_variable_definition=is_variable_def,
                        is_syntax_highlighting=is_syntax,
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
                        selector_context=selector,
                        is_variable_definition=is_variable_def,
                        is_syntax_highlighting=is_syntax,
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
                        selector_context=selector,
                        is_variable_definition=is_variable_def,
                        is_syntax_highlighting=is_syntax,
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
        - coverage_threshold: Minimum acceptable coverage (default: 0.90)
        - exclude_syntax_highlighting: Exclude intentional syntax colors (default: True)

    Metrics returned:
        - coverage: Adjusted coverage excluding syntax colors (0.0-1.0)
        - raw_coverage: Raw coverage including all colors (0.0-1.0)
        - total_color_values: Total controllable color usages
        - raw_total_color_values: Total including syntax colors
        - variable_usages: Number of usages using CSS variables
        - hardcoded_count: Number of controllable hardcoded values
        - syntax_colors_excluded: Count of excluded syntax colors
        - violations: List of violation details (file, line, value)
    """

    def __init__(self) -> None:
        super().__init__("css-variable-coverage", "visual")

    def validate(self, context: ValidationContext) -> ValidatorResult:
        """Validate CSS variable coverage.

        Args:
            context: Validation context with optional css_dir, coverage_threshold,
                     and exclude_syntax_highlighting options.

        Returns:
            ValidatorResult with coverage metrics and any violations.
        """
        # Get CSS directory from context or default
        css_dir = context.extra.get("css_dir")
        if css_dir is None:
            # Default to dress-blueprint-action/assets
            # This file: dev/scripts/sbs/tests/validators/design/variable_coverage.py
            # Repo root: 7 parents up
            repo_root = Path(__file__).parent.parent.parent.parent.parent.parent.parent
            css_dir = repo_root / "toolchain" / "dress-blueprint-action" / "assets"
        elif isinstance(css_dir, str):
            css_dir = Path(css_dir)

        # Get coverage threshold
        threshold = context.extra.get("coverage_threshold", 0.90)

        # Get exclusion setting (default: True)
        exclude_syntax = context.extra.get("exclude_syntax_highlighting", True)

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
        syntax_excluded: list[ColorUsage] = []
        vardef_excluded: list[ColorUsage] = []

        for usage in all_usages:
            # Check if it's an acceptable named color (skip entirely)
            if not usage.uses_variable and is_named_color(usage.color_value):
                continue

            if usage.uses_variable:
                variable_usages.append(usage)
            else:
                # Check if this is an excluded context
                if exclude_syntax:
                    if usage.is_syntax_highlighting:
                        syntax_excluded.append(usage)
                        continue
                    if usage.is_variable_definition:
                        vardef_excluded.append(usage)
                        continue

                hardcoded_usages.append(usage)

        # Calculate raw totals (before exclusions)
        raw_hardcoded = len(hardcoded_usages) + len(syntax_excluded) + len(vardef_excluded)
        raw_total = len(variable_usages) + raw_hardcoded

        # Calculate adjusted totals (after exclusions)
        total_counted = len(variable_usages) + len(hardcoded_usages)

        # Calculate coverages
        if raw_total == 0:
            raw_coverage = 1.0
        else:
            raw_coverage = len(variable_usages) / raw_total

        if total_counted == 0:
            coverage = 1.0  # No controllable color usages = perfect coverage
        else:
            coverage = len(variable_usages) / total_counted

        # Build violations list (only non-excluded hardcoded values)
        violations = [
            {
                "file": u.file,
                "line": u.line_number,
                "property": u.property_name,
                "value": u.color_value,
                "selector": u.selector_context[:80] if u.selector_context else "",
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

        # Add summary of exclusions if any
        if exclude_syntax and (syntax_excluded or vardef_excluded):
            excluded_count = len(syntax_excluded) + len(vardef_excluded)
            findings.insert(
                0,
                f"Excluded {excluded_count} intentional hardcoded colors "
                f"(syntax: {len(syntax_excluded)}, var defs: {len(vardef_excluded)})",
            )

        passed = coverage >= threshold

        return self._make_result(
            passed=passed,
            findings=findings,
            metrics={
                "coverage": round(coverage, 4),
                "raw_coverage": round(raw_coverage, 4),
                "total_color_values": total_counted,
                "raw_total_color_values": raw_total,
                "variable_usages": len(variable_usages),
                "hardcoded_count": len(hardcoded_usages),
                "syntax_colors_excluded": len(syntax_excluded),
                "vardef_colors_excluded": len(vardef_excluded),
                "violations": violations,
                "threshold": threshold,
                "exclude_syntax_highlighting": exclude_syntax,
                "files_analyzed": files_found,
                "files_missing": files_missing,
            },
            confidence=1.0,
        )
