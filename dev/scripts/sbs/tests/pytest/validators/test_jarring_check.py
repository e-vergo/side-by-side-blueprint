"""
Tests for the jarring element check validator (T7).

Tests cover:
- Prompt generation mode (no AI responses)
- Response parsing mode (with AI responses)
- JSON response parsing
- Fallback keyword parsing
- Result aggregation across pages
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from sbs.tests.validators.design.jarring_check import (
    JarringCheckValidator,
    JARRING_CHECK_PROMPT,
    DEFAULT_PAGES,
)
from sbs.tests.validators.base import ValidationContext


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def validator() -> JarringCheckValidator:
    """Create a JarringCheckValidator instance."""
    return JarringCheckValidator()


@pytest.fixture
def temp_screenshots_dir() -> Path:
    """Create a temporary directory with mock screenshots."""
    with tempfile.TemporaryDirectory(prefix="sbs_jarring_test_") as tmpdir:
        path = Path(tmpdir)
        # Create mock screenshot files
        for page in DEFAULT_PAGES:
            (path / f"{page}.png").touch()
        yield path


@pytest.fixture
def partial_screenshots_dir() -> Path:
    """Create a temporary directory with some screenshots missing."""
    with tempfile.TemporaryDirectory(prefix="sbs_jarring_partial_") as tmpdir:
        path = Path(tmpdir)
        # Only create some screenshots
        (path / "dashboard.png").touch()
        (path / "dep_graph.png").touch()
        # Missing: chapter.png, paper_tex.png, blueprint_verso.png
        yield path


@pytest.fixture
def empty_screenshots_dir() -> Path:
    """Create an empty temporary directory."""
    with tempfile.TemporaryDirectory(prefix="sbs_jarring_empty_") as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# Validator Properties Tests
# =============================================================================


class TestValidatorProperties:
    """Tests for validator name and category."""

    def test_name(self, validator: JarringCheckValidator) -> None:
        """Verify validator name."""
        assert validator.name == "jarring-check"

    def test_category(self, validator: JarringCheckValidator) -> None:
        """Verify validator category is visual."""
        assert validator.category == "visual"


# =============================================================================
# Prompt Generation Tests (Mode 1)
# =============================================================================


class TestPromptGeneration:
    """Tests for prompt generation mode."""

    def test_generates_prompts_without_ai_response(
        self,
        validator: JarringCheckValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify prompts are generated when no AI response provided."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
        )

        result = validator.validate(context)

        assert result.passed is False  # Not yet evaluated
        assert result.confidence == 0.0
        assert result.metrics["status"] == "needs_ai_evaluation"
        assert "prompts" in result.details
        assert len(result.details["prompts"]) == len(DEFAULT_PAGES)

    def test_prompt_contains_screenshot_path(
        self,
        validator: JarringCheckValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify each prompt includes the screenshot path."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
        )

        result = validator.validate(context)
        prompts = result.details["prompts"]

        for page, prompt_data in prompts.items():
            assert "screenshot" in prompt_data
            assert page in prompt_data["screenshot"]
            assert prompt_data["screenshot"].endswith(".png")

    def test_prompt_text_is_standard(
        self,
        validator: JarringCheckValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify the standard prompt text is used."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
        )

        result = validator.validate(context)
        prompts = result.details["prompts"]

        for page, prompt_data in prompts.items():
            assert prompt_data["prompt"] == JARRING_CHECK_PROMPT

    def test_handles_missing_screenshots(
        self,
        validator: JarringCheckValidator,
        partial_screenshots_dir: Path,
    ) -> None:
        """Verify missing screenshots are reported."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=partial_screenshots_dir,
        )

        result = validator.validate(context)

        assert result.metrics["missing_screenshots"] == 3
        assert result.details["missing_screenshots"] == [
            "chapter",
            "paper_tex",
            "blueprint_verso",
        ]
        # Should still generate prompts for available screenshots
        assert result.metrics["pages_to_check"] == 2

    def test_handles_empty_directory(
        self,
        validator: JarringCheckValidator,
        empty_screenshots_dir: Path,
    ) -> None:
        """Verify handling of directory with no screenshots."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=empty_screenshots_dir,
        )

        result = validator.validate(context)

        assert result.metrics["pages_to_check"] == 0
        assert result.metrics["missing_screenshots"] == len(DEFAULT_PAGES)

    def test_handles_missing_directory(
        self,
        validator: JarringCheckValidator,
    ) -> None:
        """Verify handling of nonexistent screenshots directory."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=Path("/nonexistent/path"),
        )

        result = validator.validate(context)

        assert result.passed is False
        assert result.metrics["status"] == "error"
        assert result.metrics["error"] == "no_screenshots_dir"

    def test_handles_no_screenshots_dir(
        self,
        validator: JarringCheckValidator,
    ) -> None:
        """Verify handling when screenshots_dir is None."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
        )

        result = validator.validate(context)

        assert result.passed is False
        assert result.metrics["status"] == "error"

    def test_custom_pages_list(
        self,
        validator: JarringCheckValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify custom pages list is respected."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={"pages": ["dashboard", "dep_graph"]},
        )

        result = validator.validate(context)

        assert result.metrics["pages_to_check"] == 2
        assert set(result.details["prompts"].keys()) == {"dashboard", "dep_graph"}


# =============================================================================
# Response Parsing Tests (Mode 2)
# =============================================================================


class TestResponseParsing:
    """Tests for AI response parsing mode."""

    def test_parses_valid_json_response(
        self,
        validator: JarringCheckValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify valid JSON responses are parsed correctly."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": json.dumps({
                        "passed": True,
                        "issues": [],
                        "confidence": 0.95,
                    }),
                    "dep_graph": json.dumps({
                        "passed": True,
                        "issues": [],
                        "confidence": 0.9,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.passed is True
        assert result.metrics["status"] == "evaluated"
        assert result.metrics["pages_checked"] == 2
        assert result.metrics["pages_passed"] == 2
        assert result.metrics["pages_failed"] == 0

    def test_handles_json_with_surrounding_text(
        self,
        validator: JarringCheckValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify JSON extraction works with surrounding text."""
        response_with_text = """
        Here's my analysis of the screenshot:

        {"passed": true, "issues": [], "confidence": 0.88}

        The page looks good overall.
        """

        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": response_with_text,
                }
            },
        )

        result = validator.validate(context)

        assert result.passed is True
        assert result.details["page_results"]["dashboard"]["confidence"] == 0.88

    def test_detects_major_issues_fail(
        self,
        validator: JarringCheckValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify major issues cause failure."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": json.dumps({
                        "passed": False,
                        "issues": [
                            {
                                "category": "color_clash",
                                "description": "Status colors clash badly",
                                "severity": "major",
                            }
                        ],
                        "confidence": 0.85,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.passed is False
        assert result.metrics["pages_failed"] == 1
        assert result.metrics["total_major_issues"] == 1
        assert "[dashboard] color_clash: Status colors clash badly" in result.findings

    def test_minor_issues_pass(
        self,
        validator: JarringCheckValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify minor issues don't cause failure."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": json.dumps({
                        "passed": True,
                        "issues": [
                            {
                                "category": "alignment",
                                "description": "Slight misalignment",
                                "severity": "minor",
                            }
                        ],
                        "confidence": 0.9,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.passed is True
        assert result.metrics["total_minor_issues"] == 1
        assert result.metrics["total_major_issues"] == 0

    def test_aggregates_multiple_page_results(
        self,
        validator: JarringCheckValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify results from multiple pages are aggregated."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": json.dumps({
                        "passed": True,
                        "issues": [],
                        "confidence": 0.9,
                    }),
                    "dep_graph": json.dumps({
                        "passed": True,
                        "issues": [
                            {"category": "spacing", "description": "Tight", "severity": "minor"}
                        ],
                        "confidence": 0.8,
                    }),
                    "chapter": json.dumps({
                        "passed": False,
                        "issues": [
                            {"category": "contrast", "description": "Low contrast", "severity": "major"}
                        ],
                        "confidence": 0.85,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.passed is False  # One page failed
        assert result.metrics["pages_checked"] == 3
        assert result.metrics["pages_passed"] == 2
        assert result.metrics["pages_failed"] == 1
        assert result.metrics["total_major_issues"] == 1
        assert result.metrics["total_minor_issues"] == 1
        # Average confidence: (0.9 + 0.8 + 0.85) / 3 = 0.85
        assert abs(result.confidence - 0.85) < 0.01

    def test_all_pages_pass(
        self,
        validator: JarringCheckValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify overall pass when all pages pass."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    page: json.dumps({
                        "passed": True,
                        "issues": [],
                        "confidence": 0.9,
                    })
                    for page in DEFAULT_PAGES
                }
            },
        )

        result = validator.validate(context)

        assert result.passed is True
        assert result.metrics["pages_passed"] == len(DEFAULT_PAGES)
        assert result.metrics["pages_failed"] == 0
        assert "No major jarring issues found" in result.findings


# =============================================================================
# Fallback Parsing Tests
# =============================================================================


class TestFallbackParsing:
    """Tests for keyword-based fallback parsing."""

    def test_fallback_detects_pass(
        self,
        validator: JarringCheckValidator,
    ) -> None:
        """Verify fallback parsing detects 'pass' keyword."""
        response = "The page looks good and passes the jarring check."
        parsed = validator.parse_ai_response(response)

        assert parsed["passed"] is True
        assert parsed["confidence"] == 0.5  # Low confidence for fallback

    def test_fallback_detects_fail(
        self,
        validator: JarringCheckValidator,
    ) -> None:
        """Verify fallback parsing detects 'fail' keyword."""
        response = "This page fails the jarring check due to color issues."
        parsed = validator.parse_ai_response(response)

        assert parsed["passed"] is False

    def test_fallback_detects_major_issue(
        self,
        validator: JarringCheckValidator,
    ) -> None:
        """Verify fallback parsing detects 'major issue' pattern."""
        response = "There is a major issue with the color scheme."
        parsed = validator.parse_ai_response(response)

        assert parsed["passed"] is False

    def test_fallback_handles_ambiguous(
        self,
        validator: JarringCheckValidator,
    ) -> None:
        """Verify fallback handles ambiguous responses."""
        response = "The design is acceptable."
        parsed = validator.parse_ai_response(response)

        # Ambiguous without issue keywords should default to pass
        assert parsed["passed"] is True
        assert parsed["confidence"] == 0.5

    def test_fallback_notes_parsing_method(
        self,
        validator: JarringCheckValidator,
    ) -> None:
        """Verify fallback adds note about parsing method."""
        response = "Looks fine to me."
        parsed = validator.parse_ai_response(response)

        assert "fallback" in parsed.get("notes", "").lower()

    def test_handles_malformed_json(
        self,
        validator: JarringCheckValidator,
    ) -> None:
        """Verify graceful handling of malformed JSON."""
        malformed = '{"passed": true, "issues": [incomplete'
        parsed = validator.parse_ai_response(malformed)

        # Should fall back to keyword parsing
        assert parsed["confidence"] == 0.5
        assert "fallback" in parsed.get("notes", "").lower()


# =============================================================================
# Static Method Tests
# =============================================================================


class TestStaticMethods:
    """Tests for static utility methods."""

    def test_get_prompt(self) -> None:
        """Verify get_prompt returns the standard prompt."""
        prompt = JarringCheckValidator.get_prompt()
        assert prompt == JARRING_CHECK_PROMPT
        assert "jarring" in prompt.lower()
        assert "Response Format" in prompt

    def test_get_default_pages(self) -> None:
        """Verify get_default_pages returns expected pages."""
        pages = JarringCheckValidator.get_default_pages()
        assert pages == DEFAULT_PAGES
        assert "dashboard" in pages
        assert "dep_graph" in pages
        assert "chapter" in pages

    def test_format_criteria(self) -> None:
        """Verify format_criteria returns guidance text."""
        criteria = JarringCheckValidator.format_criteria()
        assert "Color Clash" in criteria or "color_clash" in criteria.lower()
        assert len(criteria) > 100  # Should be substantial


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for the full validation flow."""

    def test_full_flow_prompt_then_parse(
        self,
        validator: JarringCheckValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Test the full flow: generate prompts, then parse responses."""
        # Step 1: Generate prompts
        context1 = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
        )

        result1 = validator.validate(context1)
        assert result1.metrics["status"] == "needs_ai_evaluation"
        prompts = result1.details["prompts"]

        # Step 2: Simulate AI responses
        ai_responses = {
            page: json.dumps({"passed": True, "issues": [], "confidence": 0.9})
            for page in prompts.keys()
        }

        context2 = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={"ai_responses": ai_responses},
        )

        result2 = validator.validate(context2)
        assert result2.metrics["status"] == "evaluated"
        assert result2.passed is True

    def test_confidence_calculation(
        self,
        validator: JarringCheckValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify confidence is averaged across pages."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": json.dumps({"passed": True, "issues": [], "confidence": 1.0}),
                    "dep_graph": json.dumps({"passed": True, "issues": [], "confidence": 0.5}),
                }
            },
        )

        result = validator.validate(context)

        # Average of 1.0 and 0.5 = 0.75
        assert abs(result.confidence - 0.75) < 0.01
