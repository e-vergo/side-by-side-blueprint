"""
CSS parsing utilities for design system validation.

Provides functions to parse CSS files and extract relevant information such as
CSS variables, color values, and rule structures. Designed to be reusable
across multiple validators (color matching, contrast checking, etc.).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class CSSRule:
    """Represents a parsed CSS rule with selector and properties.

    Attributes:
        selector: The CSS selector string (e.g., ':root', '.status-dot').
        properties: Dictionary mapping property names to values.
        line_number: Line number where the rule begins in the source file.
    """

    selector: str
    properties: dict[str, str]
    line_number: int


@dataclass
class ColorValue:
    """Represents a color value found in CSS.

    Attributes:
        value: The color value (hex, rgb, var reference, etc.).
        line_number: Line number where the color was found.
        file: Path to the file containing the color.
        is_variable: Whether this is a CSS variable definition.
        variable_name: The CSS variable name if is_variable is True.
        property_name: The CSS property name (e.g., 'background-color').
    """

    value: str
    line_number: int
    file: str
    is_variable: bool = False
    variable_name: Optional[str] = None
    property_name: Optional[str] = None


# =============================================================================
# Parsing Functions
# =============================================================================


def parse_css_file(path: Path) -> list[CSSRule]:
    """Parse a CSS file into a list of CSS rules.

    This is a simplified parser that handles common CSS patterns. It does NOT
    handle nested rules (SCSS/LESS), @media queries properly, or complex
    selectors with embedded braces.

    Args:
        path: Path to the CSS file to parse.

    Returns:
        List of CSSRule objects representing the rules in the file.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        OSError: If the file can't be read.
    """
    content = path.read_text(encoding="utf-8")
    return _parse_css_content(content)


def _parse_css_content(content: str) -> list[CSSRule]:
    """Parse CSS content string into rules.

    Internal function used by parse_css_file.
    """
    rules: list[CSSRule] = []

    # Remove CSS comments
    content = _remove_comments(content)

    # Track line numbers - we need to count newlines to report accurate positions
    lines = content.split("\n")
    reconstructed = "\n".join(lines)

    # Pattern to match CSS rules: selector { properties }
    # This handles multi-line selectors and property blocks
    rule_pattern = re.compile(
        r"([^{}]+)\{([^{}]*)\}",
        re.DOTALL,
    )

    # Track position for line number calculation
    pos = 0

    for match in rule_pattern.finditer(reconstructed):
        # Calculate line number from position
        line_number = reconstructed[:match.start()].count("\n") + 1

        selector = match.group(1).strip()
        properties_block = match.group(2).strip()

        # Parse properties
        properties = _parse_properties(properties_block)

        if selector and properties:
            rules.append(
                CSSRule(
                    selector=selector,
                    properties=properties,
                    line_number=line_number,
                )
            )

    return rules


def _remove_comments(content: str) -> str:
    """Remove CSS comments from content.

    Handles both single-line and multi-line /* */ comments.
    """
    # Remove multi-line comments
    return re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)


def _parse_properties(block: str) -> dict[str, str]:
    """Parse a CSS properties block into a dictionary.

    Args:
        block: The content between { and } in a CSS rule.

    Returns:
        Dictionary mapping property names to values.
    """
    properties: dict[str, str] = {}

    # Split by semicolons and process each declaration
    declarations = block.split(";")

    for decl in declarations:
        decl = decl.strip()
        if not decl:
            continue

        # Split on first colon only (values may contain colons)
        if ":" not in decl:
            continue

        colon_pos = decl.index(":")
        prop_name = decl[:colon_pos].strip()
        prop_value = decl[colon_pos + 1 :].strip()

        if prop_name and prop_value:
            properties[prop_name] = prop_value

    return properties


def extract_css_variables(css_content: str) -> dict[str, str]:
    """Extract CSS custom property (variable) definitions from CSS content.

    Looks for :root declarations and extracts all --prefixed properties.
    Also handles html[data-theme="dark"] and similar theme overrides.

    Args:
        css_content: Raw CSS content string.

    Returns:
        Dictionary mapping variable names (with --) to their values.
        E.g., {'--sbs-status-ready': '#20B2AA'}

    Note:
        For variables defined in multiple places (e.g., :root and dark mode),
        only the first definition is returned. Use extract_themed_variables()
        if you need theme-specific values.
    """
    variables: dict[str, str] = {}

    # Parse the CSS
    rules = _parse_css_content(css_content)

    # Look for rules that define CSS variables (typically :root)
    for rule in rules:
        for prop_name, prop_value in rule.properties.items():
            if prop_name.startswith("--"):
                # Only keep first definition (skip theme overrides)
                if prop_name not in variables:
                    variables[prop_name] = prop_value

    return variables


def extract_color_values(css_content: str) -> list[ColorValue]:
    """Extract all color values from CSS content.

    Finds colors in:
    - CSS variable definitions (--name: #hex)
    - Color properties (color, background-color, border-color, etc.)
    - RGB/RGBA/HSL/HSLA function calls

    Args:
        css_content: Raw CSS content string.

    Returns:
        List of ColorValue objects representing found colors.
    """
    colors: list[ColorValue] = []

    # Remove comments first
    content = _remove_comments(css_content)
    lines = content.split("\n")

    # Patterns for different color formats
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    rgb_pattern = re.compile(r"rgba?\([^)]+\)")
    hsl_pattern = re.compile(r"hsla?\([^)]+\)")

    # Color-related properties
    color_props = {
        "color",
        "background-color",
        "background",
        "border-color",
        "border",
        "border-top-color",
        "border-right-color",
        "border-bottom-color",
        "border-left-color",
        "outline-color",
        "text-decoration-color",
        "fill",
        "stroke",
        "box-shadow",
    }

    for line_num, line in enumerate(lines, start=1):
        # Check for CSS variable definitions
        var_match = re.match(r"\s*(--[\w-]+)\s*:\s*(.+?)\s*;?\s*$", line)
        if var_match:
            var_name = var_match.group(1)
            var_value = var_match.group(2)

            # Check if value is a color
            if hex_pattern.search(var_value) or rgb_pattern.search(var_value) or hsl_pattern.search(var_value):
                colors.append(
                    ColorValue(
                        value=var_value,
                        line_number=line_num,
                        file="",  # To be filled by caller
                        is_variable=True,
                        variable_name=var_name,
                    )
                )
            continue

        # Check for color properties
        prop_match = re.match(r"\s*([\w-]+)\s*:\s*(.+?)\s*;?\s*$", line)
        if prop_match:
            prop_name = prop_match.group(1)
            prop_value = prop_match.group(2)

            if prop_name in color_props:
                # Extract color values from the property
                for hex_match in hex_pattern.finditer(prop_value):
                    colors.append(
                        ColorValue(
                            value=hex_match.group(),
                            line_number=line_num,
                            file="",
                            is_variable=False,
                            property_name=prop_name,
                        )
                    )
                for rgb_match in rgb_pattern.finditer(prop_value):
                    colors.append(
                        ColorValue(
                            value=rgb_match.group(),
                            line_number=line_num,
                            file="",
                            is_variable=False,
                            property_name=prop_name,
                        )
                    )
                for hsl_match in hsl_pattern.finditer(prop_value):
                    colors.append(
                        ColorValue(
                            value=hsl_match.group(),
                            line_number=line_num,
                            file="",
                            is_variable=False,
                            property_name=prop_name,
                        )
                    )

    return colors


def normalize_hex_color(color: str) -> str:
    """Normalize a hex color to uppercase 6-digit format.

    Args:
        color: A hex color string (with or without #, 3 or 6 digits).

    Returns:
        Normalized 6-digit hex color in uppercase with # prefix.
        Returns original string if not a valid hex color.
    """
    # Remove # prefix if present
    color = color.strip()
    if color.startswith("#"):
        color = color[1:]

    # Validate hex chars
    if not re.match(r"^[0-9a-fA-F]{3,6}$", color):
        return "#" + color.upper() if color else ""

    # Expand 3-digit to 6-digit
    if len(color) == 3:
        color = "".join(c * 2 for c in color)

    return "#" + color.upper()
