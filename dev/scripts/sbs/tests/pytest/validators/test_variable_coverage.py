"""
Tests for CSS variable coverage validator (T6).

Tests cover:
- Coverage calculation
- Violation detection
- Named color exclusions
- Threshold configuration
- Real CSS file analysis
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from sbs.tests.validators.design.variable_coverage import (
    CSSVariableCoverageValidator,
    ColorUsage,
    extract_color_usages,
    is_named_color,
    ACCEPTABLE_NAMED_COLORS,
)
from sbs.tests.validators.base import ValidationContext


# =============================================================================
# Named Color Tests
# =============================================================================


class TestIsNamedColor:
    """Tests for named color detection."""

    def test_transparent_is_acceptable(self) -> None:
        """Verify 'transparent' is an acceptable named color."""
        assert is_named_color("transparent") is True

    def test_inherit_is_acceptable(self) -> None:
        """Verify 'inherit' is an acceptable named color."""
        assert is_named_color("inherit") is True

    def test_white_is_acceptable(self) -> None:
        """Verify 'white' is an acceptable named color."""
        assert is_named_color("white") is True

    def test_black_is_acceptable(self) -> None:
        """Verify 'black' is an acceptable named color."""
        assert is_named_color("black") is True

    def test_currentcolor_case_insensitive(self) -> None:
        """Verify currentColor matching is case-insensitive."""
        assert is_named_color("currentColor") is True
        assert is_named_color("currentcolor") is True
        assert is_named_color("CURRENTCOLOR") is True

    def test_none_is_acceptable(self) -> None:
        """Verify 'none' is acceptable."""
        assert is_named_color("none") is True

    def test_hex_is_not_named_color(self) -> None:
        """Verify hex values are not named colors."""
        assert is_named_color("#fff") is False
        assert is_named_color("#ffffff") is False

    def test_red_is_not_acceptable(self) -> None:
        """Verify non-neutral named colors are not acceptable."""
        # We only accept truly neutral/semantic names
        assert is_named_color("red") is False
        assert is_named_color("blue") is False
        assert is_named_color("green") is False

    def test_whitespace_stripped(self) -> None:
        """Verify whitespace is stripped before checking."""
        assert is_named_color("  white  ") is True
        assert is_named_color("\ttransparent\n") is True


# =============================================================================
# Color Usage Extraction Tests
# =============================================================================


class TestExtractColorUsages:
    """Tests for color usage extraction."""

    def test_extracts_hex_colors(self) -> None:
        """Verify hex colors are extracted."""
        css = """
        .element {
            color: #ff0000;
            background-color: #00ff00;
        }
        """
        usages = extract_color_usages(css, "test.css")
        hex_usages = [u for u in usages if not u.uses_variable]
        assert len(hex_usages) == 2
        assert any(u.color_value == "#ff0000" for u in hex_usages)
        assert any(u.color_value == "#00ff00" for u in hex_usages)

    def test_extracts_var_references(self) -> None:
        """Verify var() references are detected."""
        css = """
        .element {
            color: var(--sbs-text);
            background-color: var(--sbs-bg-surface);
        }
        """
        usages = extract_color_usages(css, "test.css")
        var_usages = [u for u in usages if u.uses_variable]
        assert len(var_usages) == 2
        assert all(u.uses_variable for u in var_usages)

    def test_ignores_variable_definitions(self) -> None:
        """Verify CSS variable definitions are not counted as usages."""
        css = """
        :root {
            --my-color: #ff0000;
        }
        .element {
            color: var(--my-color);
        }
        """
        usages = extract_color_usages(css, "test.css")
        # Should only find the var() usage, not the definition
        assert len(usages) == 1
        assert usages[0].uses_variable is True

    def test_extracts_rgb_colors(self) -> None:
        """Verify rgb/rgba colors are extracted."""
        css = """
        .element {
            color: rgb(255, 0, 0);
            background-color: rgba(0, 0, 0, 0.5);
        }
        """
        usages = extract_color_usages(css, "test.css")
        assert len(usages) == 2
        assert any("rgb(255, 0, 0)" in u.color_value for u in usages)
        assert any("rgba(0, 0, 0, 0.5)" in u.color_value for u in usages)

    def test_extracts_hsl_colors(self) -> None:
        """Verify hsl/hsla colors are extracted."""
        css = """
        .element {
            color: hsl(120, 100%, 50%);
            background-color: hsla(240, 100%, 50%, 0.5);
        }
        """
        usages = extract_color_usages(css, "test.css")
        assert len(usages) == 2
        assert all(not u.uses_variable for u in usages)

    def test_ignores_comments(self) -> None:
        """Verify colors in comments are not extracted."""
        css = """
        /* color: #ff0000; */
        .element {
            color: #00ff00;
        }
        """
        usages = extract_color_usages(css, "test.css")
        assert len(usages) == 1
        assert usages[0].color_value == "#00ff00"

    def test_ignores_non_color_properties(self) -> None:
        """Verify colors in non-color properties are ignored."""
        css = """
        .element {
            width: 100px;
            height: 50px;
            z-index: 10;
        }
        """
        usages = extract_color_usages(css, "test.css")
        assert len(usages) == 0

    def test_includes_box_shadow(self) -> None:
        """Verify box-shadow property is checked."""
        css = """
        .element {
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        }
        """
        usages = extract_color_usages(css, "test.css")
        assert len(usages) == 1
        assert usages[0].property_name == "box-shadow"

    def test_includes_fill_stroke(self) -> None:
        """Verify SVG fill and stroke are checked."""
        css = """
        .icon {
            fill: #333333;
            stroke: var(--sbs-border);
        }
        """
        usages = extract_color_usages(css, "test.css")
        assert len(usages) == 2
        fill_usage = next(u for u in usages if u.property_name == "fill")
        stroke_usage = next(u for u in usages if u.property_name == "stroke")
        assert fill_usage.uses_variable is False
        assert stroke_usage.uses_variable is True

    def test_mixed_var_and_hardcoded(self) -> None:
        """Verify both var and hardcoded in same value are detected."""
        css = """
        .element {
            border: 1px solid #ff0000;
            background: var(--sbs-bg-surface);
        }
        """
        usages = extract_color_usages(css, "test.css")
        assert len(usages) == 2
        hardcoded = [u for u in usages if not u.uses_variable]
        variable = [u for u in usages if u.uses_variable]
        assert len(hardcoded) == 1
        assert len(variable) == 1

    def test_records_line_numbers(self) -> None:
        """Verify line numbers are correctly recorded."""
        css = """
        .a { color: #111; }
        .b { color: #222; }
        .c { color: #333; }
        """
        usages = extract_color_usages(css, "test.css")
        assert len(usages) == 3
        lines = [u.line_number for u in usages]
        assert sorted(lines) == [2, 3, 4]


# =============================================================================
# Validator Tests
# =============================================================================


class TestCSSVariableCoverageValidator:
    """Tests for the CSS variable coverage validator."""

    @pytest.fixture
    def validator(self) -> CSSVariableCoverageValidator:
        """Create a validator instance."""
        return CSSVariableCoverageValidator()

    @pytest.fixture
    def temp_css_dir(self) -> Path:
        """Create a temporary directory for CSS files."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_validator_properties(self, validator: CSSVariableCoverageValidator) -> None:
        """Verify validator name and category."""
        assert validator.name == "css-variable-coverage"
        assert validator.category == "visual"

    def test_perfect_coverage(self, validator: CSSVariableCoverageValidator, temp_css_dir: Path) -> None:
        """Verify 100% coverage when all colors use variables."""
        css = """
        .element {
            color: var(--sbs-text);
            background-color: var(--sbs-bg-surface);
            border-color: var(--sbs-border);
        }
        """
        (temp_css_dir / "common.css").write_text(css)

        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            extra={"css_dir": temp_css_dir},
        )

        result = validator.validate(context)

        assert result.passed is True
        assert result.metrics["coverage"] == 1.0
        assert result.metrics["variable_usages"] == 3
        assert result.metrics["hardcoded_count"] == 0

    def test_zero_coverage(self, validator: CSSVariableCoverageValidator, temp_css_dir: Path) -> None:
        """Verify 0% coverage when all colors are hardcoded."""
        css = """
        .element {
            color: #ff0000;
            background-color: #00ff00;
            border-color: #0000ff;
        }
        """
        (temp_css_dir / "common.css").write_text(css)

        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            extra={"css_dir": temp_css_dir, "coverage_threshold": 0.95},
        )

        result = validator.validate(context)

        assert result.passed is False
        assert result.metrics["coverage"] == 0.0
        assert result.metrics["hardcoded_count"] == 3
        assert len(result.metrics["violations"]) == 3

    def test_partial_coverage(self, validator: CSSVariableCoverageValidator, temp_css_dir: Path) -> None:
        """Verify partial coverage is calculated correctly."""
        css = """
        .a { color: var(--sbs-text); }
        .b { color: var(--sbs-link); }
        .c { color: #ff0000; }
        .d { color: var(--sbs-heading); }
        """
        (temp_css_dir / "common.css").write_text(css)

        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            extra={"css_dir": temp_css_dir},
        )

        result = validator.validate(context)

        # 3 variables, 1 hardcoded = 75% coverage
        assert result.metrics["coverage"] == 0.75
        assert result.metrics["variable_usages"] == 3
        assert result.metrics["hardcoded_count"] == 1

    def test_named_colors_not_counted(self, validator: CSSVariableCoverageValidator, temp_css_dir: Path) -> None:
        """Verify named colors don't affect coverage calculation."""
        css = """
        .a { color: var(--sbs-text); }
        .b { background-color: transparent; }
        .c { border-color: inherit; }
        .d { color: white; }
        .e { color: #ff0000; }
        """
        (temp_css_dir / "common.css").write_text(css)

        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            extra={"css_dir": temp_css_dir},
        )

        result = validator.validate(context)

        # transparent, inherit, white are not counted
        # 1 variable + 1 hardcoded = 50% coverage
        assert result.metrics["variable_usages"] == 1
        assert result.metrics["hardcoded_count"] == 1
        assert result.metrics["coverage"] == 0.5

    def test_configurable_threshold(self, validator: CSSVariableCoverageValidator, temp_css_dir: Path) -> None:
        """Verify threshold is configurable."""
        css = """
        .a { color: var(--sbs-text); }
        .b { color: #ff0000; }
        """
        (temp_css_dir / "common.css").write_text(css)

        # With 50% threshold, 50% coverage should pass
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            extra={"css_dir": temp_css_dir, "coverage_threshold": 0.50},
        )

        result = validator.validate(context)
        assert result.passed is True

        # With 75% threshold, 50% coverage should fail
        context.extra["coverage_threshold"] = 0.75
        result = validator.validate(context)
        assert result.passed is False

    def test_multiple_files(self, validator: CSSVariableCoverageValidator, temp_css_dir: Path) -> None:
        """Verify analysis across multiple CSS files."""
        (temp_css_dir / "common.css").write_text(".a { color: var(--x); }")
        (temp_css_dir / "blueprint.css").write_text(".b { color: #ff0000; }")
        (temp_css_dir / "paper.css").write_text(".c { color: var(--y); }")
        (temp_css_dir / "dep_graph.css").write_text(".d { color: var(--z); }")

        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            extra={"css_dir": temp_css_dir},
        )

        result = validator.validate(context)

        # 3 variables, 1 hardcoded = 75% coverage
        assert result.metrics["coverage"] == 0.75
        assert len(result.metrics["files_analyzed"]) == 4

    def test_missing_files_handled(self, validator: CSSVariableCoverageValidator, temp_css_dir: Path) -> None:
        """Verify missing files are noted but don't cause failure."""
        (temp_css_dir / "common.css").write_text(".a { color: var(--x); }")
        # Other files are missing

        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            extra={"css_dir": temp_css_dir},
        )

        result = validator.validate(context)

        assert "common.css" in result.metrics["files_analyzed"]
        assert "blueprint.css" in result.metrics["files_missing"]

    def test_violations_include_details(self, validator: CSSVariableCoverageValidator, temp_css_dir: Path) -> None:
        """Verify violation details include file, line, and value."""
        css = """.element { color: #0000ff; }"""
        (temp_css_dir / "common.css").write_text(css)

        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            extra={"css_dir": temp_css_dir},
        )

        result = validator.validate(context)

        assert len(result.metrics["violations"]) == 1
        violation = result.metrics["violations"][0]
        assert violation["file"] == "common.css"
        assert violation["line"] == 1
        assert violation["value"] == "#0000ff"
        assert violation["property"] == "color"

    def test_findings_limited_to_ten(self, validator: CSSVariableCoverageValidator, temp_css_dir: Path) -> None:
        """Verify findings are limited to first 10 with overflow message."""
        # Create 15 violations
        lines = [f".e{i} {{ color: #{'%02x' % i}0000; }}" for i in range(15)]
        css = "\n".join(lines)
        (temp_css_dir / "common.css").write_text(css)

        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            extra={"css_dir": temp_css_dir},
        )

        result = validator.validate(context)

        assert len(result.metrics["violations"]) == 15
        assert len(result.findings) == 11  # 10 + 1 overflow message
        assert "5 more violations" in result.findings[-1]

    def test_no_css_files_fails(self, validator: CSSVariableCoverageValidator, temp_css_dir: Path) -> None:
        """Verify graceful failure when no CSS files found."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            extra={"css_dir": temp_css_dir},
        )

        result = validator.validate(context)

        assert result.passed is False
        assert "No CSS files found" in result.findings[0]

    def test_empty_css_is_perfect(self, validator: CSSVariableCoverageValidator, temp_css_dir: Path) -> None:
        """Verify empty CSS (no color usages) is considered perfect coverage."""
        css = ".element { width: 100px; }"
        (temp_css_dir / "common.css").write_text(css)

        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            extra={"css_dir": temp_css_dir},
        )

        result = validator.validate(context)

        assert result.passed is True
        assert result.metrics["coverage"] == 1.0
        assert result.metrics["total_color_values"] == 0


# =============================================================================
# Real CSS Files Tests
# =============================================================================


class TestWithRealCSSFiles:
    """Tests that analyze the actual CSS files in dress-blueprint-action."""

    @pytest.fixture
    def real_css_dir(self) -> Path:
        """Get path to the real CSS directory."""
        # Navigate from test file to CSS assets
        # After move: sbs/tests/pytest/validators/test_variable_coverage.py
        # Need 6 parents to get to dev/, then go up to monorepo and into toolchain
        test_file = Path(__file__).resolve()
        dev_dir = test_file.parent.parent.parent.parent.parent.parent
        return dev_dir.parent / "toolchain" / "dress-blueprint-action" / "assets"

    @pytest.fixture
    def validator(self) -> CSSVariableCoverageValidator:
        """Create a validator instance."""
        return CSSVariableCoverageValidator()

    def test_real_files_exist(self, real_css_dir: Path) -> None:
        """Verify all expected CSS files exist."""
        assert (real_css_dir / "common.css").exists()
        assert (real_css_dir / "blueprint.css").exists()
        assert (real_css_dir / "paper.css").exists()
        assert (real_css_dir / "dep_graph.css").exists()

    def test_can_analyze_real_files(self, validator: CSSVariableCoverageValidator, real_css_dir: Path) -> None:
        """Verify we can analyze the real CSS files without error."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            extra={"css_dir": real_css_dir},
        )

        result = validator.validate(context)

        # Should complete without error
        assert result.metrics["total_color_values"] > 0
        assert len(result.metrics["files_analyzed"]) == 4

    def test_reports_expected_violations(self, validator: CSSVariableCoverageValidator, real_css_dir: Path) -> None:
        """Verify expected hardcoded colors are detected.

        The CSS files have many hardcoded colors - most are intentional for
        Lean syntax highlighting (theme-specific colors). This test verifies
        the validator can detect them.
        """
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            extra={"css_dir": real_css_dir},
        )

        result = validator.validate(context)

        # Should have some hardcoded colors
        assert result.metrics["hardcoded_count"] > 0

        # Check that we're finding the #0000ff violations (Lean keyword blue)
        # These exist in both common.css (light mode) and blueprint.css (headers)
        blue_violations = [
            v for v in result.metrics["violations"]
            if "#0000ff" in v["value"].lower()
        ]
        # Verify we can detect this pattern
        assert len(blue_violations) > 0, "Should find at least one #0000ff violation"

        # The violations can be in common.css or blueprint.css
        files_with_blue = {v["file"] for v in blue_violations}
        assert files_with_blue.issubset({"common.css", "blueprint.css"})

    def test_coverage_is_reasonable(self, validator: CSSVariableCoverageValidator, real_css_dir: Path) -> None:
        """Verify coverage is reasonably high for the real CSS files."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            extra={"css_dir": real_css_dir},
        )

        result = validator.validate(context)

        # Coverage should be fairly high (most colors use variables)
        # Allow for some known violations
        assert result.metrics["coverage"] >= 0.5, (
            f"Coverage unexpectedly low: {result.metrics['coverage']}"
        )
