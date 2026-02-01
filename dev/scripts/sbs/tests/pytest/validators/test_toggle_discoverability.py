"""
Tests for the toggle discoverability validator (T4).

Tests cover:
- Prompt generation mode (no AI responses)
- Response parsing mode (with AI responses)
- JSON response parsing
- Fallback pattern extraction
- Score aggregation across pages
- Threshold configuration
- Breakdown preservation
- Recommendations capture
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from sbs.tests.validators.design.toggle_discoverability import (
    ToggleDiscoverabilityValidator,
    TOGGLE_DISCOVERABILITY_PROMPT,
    DEFAULT_PAGES,
    DEFAULT_THRESHOLD,
)
from sbs.tests.validators.base import ValidationContext


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def validator() -> ToggleDiscoverabilityValidator:
    """Create a ToggleDiscoverabilityValidator instance."""
    return ToggleDiscoverabilityValidator()


@pytest.fixture
def temp_screenshots_dir() -> Path:
    """Create a temporary directory with mock screenshots."""
    with tempfile.TemporaryDirectory(prefix="sbs_toggle_test_") as tmpdir:
        path = Path(tmpdir)
        # Create mock screenshot files for default pages
        for page in DEFAULT_PAGES:
            (path / f"{page}.png").touch()
        yield path


@pytest.fixture
def single_page_screenshots_dir() -> Path:
    """Create a temporary directory with only chapter screenshot."""
    with tempfile.TemporaryDirectory(prefix="sbs_toggle_single_") as tmpdir:
        path = Path(tmpdir)
        (path / "chapter.png").touch()
        yield path


@pytest.fixture
def empty_screenshots_dir() -> Path:
    """Create an empty temporary directory."""
    with tempfile.TemporaryDirectory(prefix="sbs_toggle_empty_") as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# Validator Properties Tests
# =============================================================================


class TestValidatorProperties:
    """Tests for validator name and category."""

    def test_name(self, validator: ToggleDiscoverabilityValidator) -> None:
        """Verify validator name."""
        assert validator.name == "toggle-discoverability"

    def test_category(self, validator: ToggleDiscoverabilityValidator) -> None:
        """Verify validator category is visual."""
        assert validator.category == "visual"


# =============================================================================
# Prompt Generation Tests (Mode 1)
# =============================================================================


class TestPromptGeneration:
    """Tests for prompt generation mode."""

    def test_generates_prompts_for_chapter_pages(
        self,
        validator: ToggleDiscoverabilityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify prompts are generated for chapter pages."""
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
        validator: ToggleDiscoverabilityValidator,
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
        validator: ToggleDiscoverabilityValidator,
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
            assert prompt_data["prompt"] == TOGGLE_DISCOVERABILITY_PROMPT

    def test_handles_single_page(
        self,
        validator: ToggleDiscoverabilityValidator,
        single_page_screenshots_dir: Path,
    ) -> None:
        """Verify works with just one chapter page."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=single_page_screenshots_dir,
        )

        result = validator.validate(context)

        assert result.metrics["pages_to_check"] == 1
        assert "chapter" in result.details["prompts"]
        assert result.metrics["missing_screenshots"] == 1

    def test_handles_no_chapter_screenshots(
        self,
        validator: ToggleDiscoverabilityValidator,
        empty_screenshots_dir: Path,
    ) -> None:
        """Verify handling when no chapter screenshots exist."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=empty_screenshots_dir,
        )

        result = validator.validate(context)

        assert result.passed is False
        assert result.metrics["status"] == "error"
        assert result.metrics["error"] == "no_chapter_screenshots"
        assert "No chapter screenshots found" in result.findings[0]

    def test_handles_missing_directory(
        self,
        validator: ToggleDiscoverabilityValidator,
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

    def test_custom_pages_list(
        self,
        validator: ToggleDiscoverabilityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify custom pages list is respected."""
        # Add an extra page
        (temp_screenshots_dir / "custom_page.png").touch()

        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={"pages": ["chapter", "custom_page"]},
        )

        result = validator.validate(context)

        assert result.metrics["pages_to_check"] == 2
        assert set(result.details["prompts"].keys()) == {"chapter", "custom_page"}


# =============================================================================
# Response Parsing Tests (Mode 2)
# =============================================================================


class TestResponseParsing:
    """Tests for AI response parsing mode."""

    def test_parses_valid_score_response(
        self,
        validator: ToggleDiscoverabilityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify valid JSON with score is parsed correctly."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "chapter": json.dumps({
                        "score": 7.5,
                        "breakdown": {
                            "visibility": 3.0,
                            "familiarity": 2.5,
                            "clarity": 2.0,
                        },
                        "findings": ["Toggle clearly visible"],
                        "recommendations": ["Add icon for clarity"],
                        "confidence": 0.9,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.passed is True  # 7.5 >= 7.0 default threshold
        assert result.metrics["status"] == "evaluated"
        assert result.metrics["average_score"] == 7.5
        assert result.metrics["page_scores"]["chapter"] == 7.5

    def test_aggregates_page_scores(
        self,
        validator: ToggleDiscoverabilityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify scores from multiple pages are averaged."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "chapter": json.dumps({
                        "score": 8.0,
                        "breakdown": {},
                        "findings": [],
                        "recommendations": [],
                        "confidence": 0.9,
                    }),
                    "blueprint_verso": json.dumps({
                        "score": 6.0,
                        "breakdown": {},
                        "findings": [],
                        "recommendations": [],
                        "confidence": 0.8,
                    }),
                }
            },
        )

        result = validator.validate(context)

        # Average of 8.0, 6.0 = 7.0
        assert result.metrics["average_score"] == 7.0
        assert result.metrics["pages_checked"] == 2
        assert result.passed is True  # 7.0 >= 7.0 threshold

    def test_threshold_configurable(
        self,
        validator: ToggleDiscoverabilityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify score threshold is configurable."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "chapter": json.dumps({
                        "score": 7.5,
                        "breakdown": {},
                        "findings": [],
                        "recommendations": [],
                        "confidence": 0.9,
                    }),
                },
                "score_threshold": 8.0,  # Higher threshold
            },
        )

        result = validator.validate(context)

        assert result.passed is False  # 7.5 < 8.0
        assert result.metrics["threshold"] == 8.0

    def test_passes_with_lower_threshold(
        self,
        validator: ToggleDiscoverabilityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify pass with lower threshold."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "chapter": json.dumps({
                        "score": 5.5,
                        "breakdown": {},
                        "findings": [],
                        "recommendations": [],
                        "confidence": 0.9,
                    }),
                },
                "score_threshold": 5.0,  # Lower threshold
            },
        )

        result = validator.validate(context)

        assert result.passed is True  # 5.5 >= 5.0
        assert result.metrics["threshold"] == 5.0

    def test_includes_recommendations(
        self,
        validator: ToggleDiscoverabilityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify recommendations are captured from AI response."""
        recommendations = [
            "Add chevron icon next to toggle text",
            "Increase contrast of toggle text",
            "Use consistent toggle styling",
        ]

        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "chapter": json.dumps({
                        "score": 6.5,
                        "breakdown": {},
                        "findings": [],
                        "recommendations": recommendations,
                        "confidence": 0.9,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.metrics["recommendations"] == recommendations

    def test_deduplicates_recommendations(
        self,
        validator: ToggleDiscoverabilityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify duplicate recommendations are removed."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "chapter": json.dumps({
                        "score": 6.5,
                        "recommendations": ["Add icon", "Increase contrast"],
                        "confidence": 0.9,
                    }),
                    "blueprint_verso": json.dumps({
                        "score": 7.0,
                        "recommendations": ["Add icon", "Improve spacing"],
                        "confidence": 0.8,
                    }),
                }
            },
        )

        result = validator.validate(context)

        # Should deduplicate "Add icon"
        assert len(result.metrics["recommendations"]) == 3
        assert result.metrics["recommendations"].count("Add icon") == 1

    def test_breakdown_preserved(
        self,
        validator: ToggleDiscoverabilityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify visibility/familiarity/clarity breakdown is preserved."""
        breakdown = {
            "visibility": 3.5,
            "familiarity": 2.0,
            "clarity": 2.5,
        }

        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "chapter": json.dumps({
                        "score": 8.0,
                        "breakdown": breakdown,
                        "findings": [],
                        "recommendations": [],
                        "confidence": 0.9,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.details["page_results"]["chapter"]["breakdown"] == breakdown

    def test_clamps_score_to_max(
        self,
        validator: ToggleDiscoverabilityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify scores above 10 are clamped to 10."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "chapter": json.dumps({
                        "score": 15.0,  # Over max
                        "breakdown": {},
                        "findings": [],
                        "recommendations": [],
                        "confidence": 0.9,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.metrics["page_scores"]["chapter"] == 10.0

    def test_clamps_score_to_min(
        self,
        validator: ToggleDiscoverabilityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify negative scores are clamped to 0."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "chapter": json.dumps({
                        "score": -5.0,  # Below min
                        "breakdown": {},
                        "findings": [],
                        "recommendations": [],
                        "confidence": 0.9,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.metrics["page_scores"]["chapter"] == 0.0

    def test_collects_findings_from_pages(
        self,
        validator: ToggleDiscoverabilityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify findings from all pages are collected with prefixes."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "chapter": json.dumps({
                        "score": 7.5,
                        "findings": ["Toggle visible but small", "Good text clarity"],
                        "recommendations": [],
                        "confidence": 0.9,
                    }),
                    "blueprint_verso": json.dumps({
                        "score": 8.0,
                        "findings": ["Chevron icon clear"],
                        "recommendations": [],
                        "confidence": 0.8,
                    }),
                }
            },
        )

        result = validator.validate(context)

        # Check findings are prefixed with page names
        assert any("[chapter]" in f and "visible" in f for f in result.findings)
        assert any("[blueprint_verso]" in f and "Chevron" in f for f in result.findings)


# =============================================================================
# Fallback Parsing Tests
# =============================================================================


class TestFallbackParsing:
    """Tests for pattern-based fallback parsing."""

    def test_extracts_score_from_x_out_of_10(
        self,
        validator: ToggleDiscoverabilityValidator,
    ) -> None:
        """Verify score extraction from 'X/10' format."""
        response = "I would rate toggle discoverability 6.5/10."
        parsed = validator.parse_ai_response(response)

        assert parsed["score"] == 6.5
        assert parsed["confidence"] == 0.5  # Low confidence for fallback

    def test_extracts_score_from_out_of_10(
        self,
        validator: ToggleDiscoverabilityValidator,
    ) -> None:
        """Verify score extraction from 'X out of 10' format."""
        response = "The toggle scores 7 out of 10 for discoverability."
        parsed = validator.parse_ai_response(response)

        assert parsed["score"] == 7.0

    def test_extracts_score_from_score_colon(
        self,
        validator: ToggleDiscoverabilityValidator,
    ) -> None:
        """Verify score extraction from 'score: X' format."""
        response = "Overall score: 8.2"
        parsed = validator.parse_ai_response(response)

        assert parsed["score"] == 8.2

    def test_clamps_extracted_score(
        self,
        validator: ToggleDiscoverabilityValidator,
    ) -> None:
        """Verify extracted scores are clamped."""
        response = "This deserves 12/10!"
        parsed = validator.parse_ai_response(response)

        assert parsed["score"] == 10.0

    def test_handles_malformed_json(
        self,
        validator: ToggleDiscoverabilityValidator,
    ) -> None:
        """Verify graceful handling of malformed JSON."""
        malformed = '{"score": 6.5, "breakdown": [incomplete'
        parsed = validator.parse_ai_response(malformed)

        # Should return default with low confidence
        assert parsed["score"] == 5.0
        assert parsed["confidence"] == 0.3
        assert "Could not parse" in parsed["findings"][0]

    def test_handles_no_score_in_response(
        self,
        validator: ToggleDiscoverabilityValidator,
    ) -> None:
        """Verify handling of response without any score."""
        response = "The toggle looks okay but I can't quantify."
        parsed = validator.parse_ai_response(response)

        # Should return default mid-range score
        assert parsed["score"] == 5.0
        assert parsed["confidence"] == 0.3

    def test_fallback_returns_empty_recommendations(
        self,
        validator: ToggleDiscoverabilityValidator,
    ) -> None:
        """Verify fallback parsing returns empty recommendations."""
        response = "Rating: 7/10"
        parsed = validator.parse_ai_response(response)

        assert parsed["recommendations"] == []

    def test_handles_json_with_surrounding_text(
        self,
        validator: ToggleDiscoverabilityValidator,
    ) -> None:
        """Verify JSON extraction works with surrounding text."""
        response_with_text = """
        Here's my analysis:

        {"score": 7.5, "breakdown": {"visibility": 3.0}, "findings": ["Good"], "recommendations": ["Add icon"], "confidence": 0.88}

        The toggle is reasonably visible.
        """

        parsed = validator.parse_ai_response(response_with_text)

        assert parsed["score"] == 7.5
        assert parsed["confidence"] == 0.88
        assert parsed["recommendations"] == ["Add icon"]


# =============================================================================
# Static Method Tests
# =============================================================================


class TestStaticMethods:
    """Tests for static utility methods."""

    def test_get_prompt(self) -> None:
        """Verify get_prompt returns the standard prompt."""
        prompt = ToggleDiscoverabilityValidator.get_prompt()
        assert prompt == TOGGLE_DISCOVERABILITY_PROMPT
        assert "discoverable" in prompt.lower()
        assert "visibility" in prompt.lower()
        assert "familiarity" in prompt.lower()
        assert "clarity" in prompt.lower()

    def test_get_default_pages(self) -> None:
        """Verify get_default_pages returns expected pages."""
        pages = ToggleDiscoverabilityValidator.get_default_pages()
        assert pages == DEFAULT_PAGES
        assert "chapter" in pages
        assert "blueprint_verso" in pages

    def test_get_default_threshold(self) -> None:
        """Verify get_default_threshold returns 7.0."""
        threshold = ToggleDiscoverabilityValidator.get_default_threshold()
        assert threshold == DEFAULT_THRESHOLD
        assert threshold == 7.0


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for the full validation flow."""

    def test_full_flow_prompt_then_parse(
        self,
        validator: ToggleDiscoverabilityValidator,
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
            page: json.dumps({
                "score": 7.5,
                "breakdown": {
                    "visibility": 3.0,
                    "familiarity": 2.5,
                    "clarity": 2.0,
                },
                "findings": ["Toggle is visible"],
                "recommendations": ["Consider adding icon"],
                "confidence": 0.85,
            })
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
        assert result2.metrics["average_score"] == 7.5

    def test_confidence_calculation(
        self,
        validator: ToggleDiscoverabilityValidator,
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
                    "chapter": json.dumps({"score": 8.0, "confidence": 1.0}),
                    "blueprint_verso": json.dumps({"score": 7.0, "confidence": 0.5}),
                }
            },
        )

        result = validator.validate(context)

        # Average of 1.0 and 0.5 = 0.75
        assert abs(result.confidence - 0.75) < 0.01

    def test_edge_case_exactly_at_threshold(
        self,
        validator: ToggleDiscoverabilityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify score exactly at threshold passes."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "chapter": json.dumps({"score": 7.0, "confidence": 0.9}),
                },
                "score_threshold": 7.0,
            },
        )

        result = validator.validate(context)

        assert result.passed is True  # 7.0 >= 7.0

    def test_counts_pages_above_threshold(
        self,
        validator: ToggleDiscoverabilityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify pages_above_threshold is calculated correctly."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "chapter": json.dumps({"score": 8.0, "confidence": 0.9}),
                    "blueprint_verso": json.dumps({"score": 6.0, "confidence": 0.8}),
                },
                "score_threshold": 7.0,
            },
        )

        result = validator.validate(context)

        # 8.0 is >= 7.0, 6.0 is not
        assert result.metrics["pages_above_threshold"] == 1
