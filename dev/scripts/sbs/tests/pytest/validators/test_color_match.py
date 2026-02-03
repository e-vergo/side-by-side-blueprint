"""
Tests for CSS parser and status color match validator.

Tests cover:
- CSS variable extraction
- Color value parsing
- Hex color normalization
- Status color validation against canonical Lean values
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from sbs.tests.validators.design.css_parser import (
    CSSRule,
    ColorValue,
    extract_color_values,
    extract_css_variables,
    normalize_hex_color,
    parse_css_file,
)
from sbs.tests.validators.design.color_match import (
    CANONICAL_COLORS,
    CSS_TO_CANONICAL,
    StatusColorValidator,
)
from sbs.tests.validators.base import ValidationContext

from .base_test import ValidatorPropertiesTestMixin


# =============================================================================
# CSS Parser Tests
# =============================================================================


@pytest.mark.evergreen
class TestNormalizeHexColor:
    """Tests for hex color normalization."""

    def test_six_digit_lowercase(self) -> None:
        """Normalize 6-digit lowercase hex."""
        assert normalize_hex_color("#f4a460") == "#F4A460"

    def test_six_digit_uppercase(self) -> None:
        """Preserve 6-digit uppercase hex."""
        assert normalize_hex_color("#F4A460") == "#F4A460"

    def test_six_digit_mixed_case(self) -> None:
        """Normalize mixed case to uppercase."""
        assert normalize_hex_color("#f4A460") == "#F4A460"

    def test_three_digit_expands(self) -> None:
        """Expand 3-digit hex to 6-digit."""
        assert normalize_hex_color("#abc") == "#AABBCC"
        assert normalize_hex_color("#ABC") == "#AABBCC"

    def test_without_hash_prefix(self) -> None:
        """Handle colors without # prefix."""
        assert normalize_hex_color("f4a460") == "#F4A460"
        assert normalize_hex_color("abc") == "#AABBCC"

    def test_whitespace_stripped(self) -> None:
        """Strip surrounding whitespace."""
        assert normalize_hex_color("  #f4a460  ") == "#F4A460"

    def test_empty_string(self) -> None:
        """Handle empty string."""
        assert normalize_hex_color("") == ""


@pytest.mark.evergreen
class TestExtractCssVariables:
    """Tests for CSS variable extraction."""

    def test_basic_root_variables(self) -> None:
        """Extract variables from :root block."""
        css = """
        :root {
            --color-primary: #ff0000;
            --color-secondary: #00ff00;
        }
        """
        variables = extract_css_variables(css)
        assert variables["--color-primary"] == "#ff0000"
        assert variables["--color-secondary"] == "#00ff00"

    def test_status_color_variables(self) -> None:
        """Extract status color variables matching real CSS pattern."""
        css = """
        :root {
            --sbs-status-not-ready: #F4A460;
            --sbs-status-ready: #20B2AA;
            --sbs-status-sorry: #8B0000;
            --sbs-status-proven: #90EE90;
            --sbs-status-fully-proven: #228B22;
            --sbs-status-mathlib-ready: #87CEEB;
        }
        """
        variables = extract_css_variables(css)
        assert len(variables) == 6
        assert variables["--sbs-status-not-ready"] == "#F4A460"
        assert variables["--sbs-status-mathlib-ready"] == "#87CEEB"

    def test_ignores_comments(self) -> None:
        """Variables in comments should be ignored."""
        css = """
        :root {
            /* --commented-out: #000000; */
            --actual-var: #ffffff;
        }
        """
        variables = extract_css_variables(css)
        assert "--commented-out" not in variables
        assert variables["--actual-var"] == "#ffffff"

    def test_first_definition_wins(self) -> None:
        """When variable is defined multiple times, first wins."""
        css = """
        :root {
            --my-color: #ff0000;
        }
        html[data-theme="dark"] {
            --my-color: #00ff00;
        }
        """
        variables = extract_css_variables(css)
        assert variables["--my-color"] == "#ff0000"

    def test_empty_css(self) -> None:
        """Handle empty CSS content."""
        variables = extract_css_variables("")
        assert variables == {}

    def test_no_variables(self) -> None:
        """Handle CSS without variables."""
        css = """
        body {
            color: black;
            background: white;
        }
        """
        variables = extract_css_variables(css)
        assert variables == {}


@pytest.mark.evergreen
class TestParseCssFile:
    """Tests for CSS file parsing."""

    def test_parse_simple_file(self) -> None:
        """Parse a simple CSS file into rules."""
        css = """
        :root {
            --color: red;
        }
        .class {
            color: blue;
        }
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".css", delete=False) as f:
            f.write(css)
            f.flush()
            path = Path(f.name)

        try:
            rules = parse_css_file(path)
            assert len(rules) == 2
            assert rules[0].selector == ":root"
            assert rules[0].properties == {"--color": "red"}
            assert rules[1].selector == ".class"
            assert rules[1].properties == {"color": "blue"}
        finally:
            path.unlink()

    def test_file_not_found(self) -> None:
        """Raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            parse_css_file(Path("/nonexistent/file.css"))


@pytest.mark.evergreen
class TestExtractColorValues:
    """Tests for color value extraction."""

    def test_hex_colors(self) -> None:
        """Extract hex color values."""
        css = """
        :root {
            --primary: #ff0000;
        }
        .element {
            color: #00ff00;
            background-color: #0000ff;
        }
        """
        colors = extract_color_values(css)
        values = [c.value for c in colors]
        assert "#ff0000" in values
        assert "#00ff00" in values
        assert "#0000ff" in values

    def test_variable_colors_flagged(self) -> None:
        """CSS variable colors are flagged as is_variable."""
        css = """
        :root {
            --my-color: #ff0000;
        }
        """
        colors = extract_color_values(css)
        var_colors = [c for c in colors if c.is_variable]
        assert len(var_colors) == 1
        assert var_colors[0].variable_name == "--my-color"


@pytest.mark.evergreen
class TestParseRealCommonCss:
    """Tests that parse the actual common.css file.

    Uses shared common_css_path fixture from conftest.py.
    """

    def test_file_exists(self, common_css_path: Path) -> None:
        """Verify common.css exists at expected location."""
        assert common_css_path.exists(), f"common.css not found at {common_css_path}"

    def test_can_parse(self, common_css_path: Path) -> None:
        """Verify we can parse common.css without errors."""
        rules = parse_css_file(common_css_path)
        assert len(rules) > 0

    def test_contains_status_variables(self, common_css_path: Path) -> None:
        """Verify common.css contains all 6 status color variables."""
        content = common_css_path.read_text()
        variables = extract_css_variables(content)

        for css_var in CSS_TO_CANONICAL.keys():
            assert css_var in variables, f"Missing CSS variable: {css_var}"


# =============================================================================
# Status Color Validator Tests
# =============================================================================


@pytest.mark.evergreen
class TestStatusColorValidatorProperties(ValidatorPropertiesTestMixin):
    """Tests for validator name and category using mixin."""

    validator_name = "status-color-match"
    validator_category = "visual"

    @pytest.fixture
    def validator(self) -> StatusColorValidator:
        """Create a StatusColorValidator instance."""
        return StatusColorValidator()


@pytest.mark.evergreen
class TestStatusColorValidator:
    """Tests for the StatusColorValidator."""

    @pytest.fixture
    def validator(self) -> StatusColorValidator:
        """Create a StatusColorValidator instance."""
        return StatusColorValidator()

    @pytest.fixture
    def valid_css_content(self) -> str:
        """CSS content with all correct status colors."""
        return """
        :root {
            --sbs-status-not-ready: #F4A460;
            --sbs-status-ready: #20B2AA;
            --sbs-status-sorry: #8B0000;
            --sbs-status-proven: #90EE90;
            --sbs-status-fully-proven: #228B22;
            --sbs-status-mathlib-ready: #87CEEB;
        }
        """

    @pytest.fixture
    def temp_css_file(self, valid_css_content: str) -> Path:
        """Create a temporary CSS file with valid content."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".css", delete=False) as f:
            f.write(valid_css_content)
            f.flush()
            yield Path(f.name)
        Path(f.name).unlink(missing_ok=True)

    def test_all_colors_match(self, validator: StatusColorValidator, temp_css_file: Path) -> None:
        """Verify all 6 status colors match canonical hex."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            extra={"css_path": temp_css_file},
        )

        result = validator.validate(context)

        assert result.passed is True
        assert result.confidence == 1.0
        assert result.metrics["colors_checked"] == 6
        assert result.metrics["colors_matched"] == 6
        assert len(result.metrics["mismatches"]) == 0

    def test_detects_mismatch(self, validator: StatusColorValidator) -> None:
        """Verify we detect when a color doesn't match."""
        bad_css = """
        :root {
            --sbs-status-not-ready: #FF0000;
            --sbs-status-ready: #20B2AA;
            --sbs-status-sorry: #8B0000;
            --sbs-status-proven: #90EE90;
            --sbs-status-fully-proven: #228B22;
            --sbs-status-mathlib-ready: #87CEEB;
        }
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".css", delete=False) as f:
            f.write(bad_css)
            f.flush()
            path = Path(f.name)

        try:
            context = ValidationContext(
                project="test",
                project_root=Path("/tmp"),
                commit="abc123",
                extra={"css_path": path},
            )

            result = validator.validate(context)

            assert result.passed is False
            assert result.metrics["colors_matched"] == 5
            assert len(result.metrics["mismatches"]) == 1
            assert result.metrics["mismatches"][0]["variable"] == "--sbs-status-not-ready"
            assert result.metrics["mismatches"][0]["expected"] == "#F4A460"
            assert result.metrics["mismatches"][0]["actual"] == "#FF0000"
        finally:
            path.unlink()

    def test_detects_missing_variable(self, validator: StatusColorValidator) -> None:
        """Verify we detect when a variable is missing."""
        incomplete_css = """
        :root {
            --sbs-status-not-ready: #F4A460;
            --sbs-status-ready: #20B2AA;
            /* missing: --sbs-status-sorry */
            --sbs-status-proven: #90EE90;
            --sbs-status-fully-proven: #228B22;
            --sbs-status-mathlib-ready: #87CEEB;
        }
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".css", delete=False) as f:
            f.write(incomplete_css)
            f.flush()
            path = Path(f.name)

        try:
            context = ValidationContext(
                project="test",
                project_root=Path("/tmp"),
                commit="abc123",
                extra={"css_path": path},
            )

            result = validator.validate(context)

            assert result.passed is False
            assert result.metrics["colors_matched"] == 5
            mismatches = result.metrics["mismatches"]
            assert len(mismatches) == 1
            assert mismatches[0]["variable"] == "--sbs-status-sorry"
            assert mismatches[0]["actual"] == "NOT FOUND"
        finally:
            path.unlink()

    def test_case_insensitive_comparison(self, validator: StatusColorValidator) -> None:
        """Verify color comparison is case-insensitive."""
        lowercase_css = """
        :root {
            --sbs-status-not-ready: #f4a460;
            --sbs-status-ready: #20b2aa;
            --sbs-status-sorry: #8b0000;
            --sbs-status-proven: #90ee90;
            --sbs-status-fully-proven: #228b22;
            --sbs-status-mathlib-ready: #87ceeb;
        }
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".css", delete=False) as f:
            f.write(lowercase_css)
            f.flush()
            path = Path(f.name)

        try:
            context = ValidationContext(
                project="test",
                project_root=Path("/tmp"),
                commit="abc123",
                extra={"css_path": path},
            )

            result = validator.validate(context)

            assert result.passed is True
            assert result.metrics["colors_matched"] == 6
        finally:
            path.unlink()

    def test_handles_missing_file(self, validator: StatusColorValidator) -> None:
        """Verify graceful handling of missing CSS file."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            extra={"css_path": Path("/nonexistent/file.css")},
        )

        result = validator.validate(context)

        assert result.passed is False
        assert "not found" in result.findings[0].lower()
        assert result.metrics["error"] == "file_not_found"

    def test_uses_default_css_path(self, validator: StatusColorValidator) -> None:
        """Verify default CSS path is used when not specified."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
        )

        result = validator.validate(context)

        # Should find the real common.css
        assert result.metrics["colors_checked"] == 6
        # All colors should match (assuming CSS is correct)
        assert result.passed is True


@pytest.mark.evergreen
class TestCanonicalColors:
    """Tests for canonical color constants."""

    def test_all_statuses_defined(self) -> None:
        """Verify all 6 statuses have canonical colors."""
        expected_statuses = {
            "notReady",
            "ready",
            "sorry",
            "proven",
            "fullyProven",
            "mathlibReady",
        }
        assert set(CANONICAL_COLORS.keys()) == expected_statuses

    def test_all_css_mappings_exist(self) -> None:
        """Verify all CSS variable mappings point to valid canonical keys."""
        for css_var, canonical_key in CSS_TO_CANONICAL.items():
            assert canonical_key in CANONICAL_COLORS, (
                f"CSS variable {css_var} maps to unknown canonical key {canonical_key}"
            )

    def test_colors_are_valid_hex(self) -> None:
        """Verify all canonical colors are valid 6-digit hex."""
        import re
        hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for status, color in CANONICAL_COLORS.items():
            assert hex_pattern.match(color), f"Invalid hex for {status}: {color}"
