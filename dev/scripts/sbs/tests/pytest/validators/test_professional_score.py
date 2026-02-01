"""
Tests for the professional score validator (T8).

Tests cover:
- Prompt generation mode (no AI responses)
- Response parsing mode (with AI responses)
- JSON response parsing
- Fallback pattern extraction
- Score aggregation across pages
- Threshold configuration
- Score clamping
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from sbs.tests.validators.design.professional_score import (
    ProfessionalScoreValidator,
    PROFESSIONAL_SCORE_PROMPT,
    DEFAULT_PAGES,
    DEFAULT_THRESHOLD,
)
from sbs.tests.validators.base import ValidationContext


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def validator() -> ProfessionalScoreValidator:
    """Create a ProfessionalScoreValidator instance."""
    return ProfessionalScoreValidator()


@pytest.fixture
def temp_screenshots_dir() -> Path:
    """Create a temporary directory with mock screenshots."""
    with tempfile.TemporaryDirectory(prefix="sbs_prof_test_") as tmpdir:
        path = Path(tmpdir)
        # Create mock screenshot files
        for page in DEFAULT_PAGES:
            (path / f"{page}.png").touch()
        yield path


@pytest.fixture
def partial_screenshots_dir() -> Path:
    """Create a temporary directory with some screenshots missing."""
    with tempfile.TemporaryDirectory(prefix="sbs_prof_partial_") as tmpdir:
        path = Path(tmpdir)
        # Only create some screenshots
        (path / "dashboard.png").touch()
        (path / "dep_graph.png").touch()
        # Missing: chapter.png, paper_tex.png, blueprint_verso.png
        yield path


@pytest.fixture
def empty_screenshots_dir() -> Path:
    """Create an empty temporary directory."""
    with tempfile.TemporaryDirectory(prefix="sbs_prof_empty_") as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# Validator Properties Tests
# =============================================================================


class TestValidatorProperties:
    """Tests for validator name and category."""

    def test_name(self, validator: ProfessionalScoreValidator) -> None:
        """Verify validator name."""
        assert validator.name == "professional-score"

    def test_category(self, validator: ProfessionalScoreValidator) -> None:
        """Verify validator category is visual."""
        assert validator.category == "visual"


# =============================================================================
# Prompt Generation Tests (Mode 1)
# =============================================================================


class TestPromptGeneration:
    """Tests for prompt generation mode."""

    def test_generates_prompts_without_ai_response(
        self,
        validator: ProfessionalScoreValidator,
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
        validator: ProfessionalScoreValidator,
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
        validator: ProfessionalScoreValidator,
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
            assert prompt_data["prompt"] == PROFESSIONAL_SCORE_PROMPT

    def test_handles_missing_screenshots(
        self,
        validator: ProfessionalScoreValidator,
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
        validator: ProfessionalScoreValidator,
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
        validator: ProfessionalScoreValidator,
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
        validator: ProfessionalScoreValidator,
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
        validator: ProfessionalScoreValidator,
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
        validator: ProfessionalScoreValidator,
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
                        "score": 8.5,
                        "breakdown": {
                            "whitespace": 1.8,
                            "alignment": 1.7,
                            "hierarchy": 2.0,
                            "typography": 1.5,
                            "polish": 1.5,
                        },
                        "findings": ["Good hierarchy"],
                        "confidence": 0.9,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.passed is True  # 8.5 >= 8.0 default threshold
        assert result.metrics["status"] == "evaluated"
        assert result.metrics["average_score"] == 8.5
        assert result.metrics["page_scores"]["dashboard"] == 8.5

    def test_handles_json_with_surrounding_text(
        self,
        validator: ProfessionalScoreValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify JSON extraction works with surrounding text."""
        response_with_text = """
        Here's my analysis of the screenshot:

        {"score": 9.0, "breakdown": {}, "findings": [], "confidence": 0.88}

        The page looks professionally designed.
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
        assert result.details["page_results"]["dashboard"]["score"] == 9.0
        assert result.details["page_results"]["dashboard"]["confidence"] == 0.88

    def test_aggregates_page_scores(
        self,
        validator: ProfessionalScoreValidator,
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
                    "dashboard": json.dumps({
                        "score": 9.0,
                        "breakdown": {},
                        "findings": [],
                        "confidence": 0.9,
                    }),
                    "dep_graph": json.dumps({
                        "score": 7.0,
                        "breakdown": {},
                        "findings": [],
                        "confidence": 0.8,
                    }),
                    "chapter": json.dumps({
                        "score": 8.0,
                        "breakdown": {},
                        "findings": [],
                        "confidence": 0.85,
                    }),
                }
            },
        )

        result = validator.validate(context)

        # Average of 9.0, 7.0, 8.0 = 8.0
        assert result.metrics["average_score"] == 8.0
        assert result.metrics["pages_checked"] == 3
        assert result.passed is True  # 8.0 >= 8.0 threshold

    def test_threshold_configurable(
        self,
        validator: ProfessionalScoreValidator,
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
                    "dashboard": json.dumps({
                        "score": 8.5,
                        "breakdown": {},
                        "findings": [],
                        "confidence": 0.9,
                    }),
                },
                "score_threshold": 9.0,  # Higher threshold
            },
        )

        result = validator.validate(context)

        assert result.passed is False  # 8.5 < 9.0
        assert result.metrics["threshold"] == 9.0

    def test_passes_with_lower_threshold(
        self,
        validator: ProfessionalScoreValidator,
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
                    "dashboard": json.dumps({
                        "score": 7.0,
                        "breakdown": {},
                        "findings": [],
                        "confidence": 0.9,
                    }),
                },
                "score_threshold": 6.0,  # Lower threshold
            },
        )

        result = validator.validate(context)

        assert result.passed is True  # 7.0 >= 6.0
        assert result.metrics["threshold"] == 6.0

    def test_clamps_score_to_max(
        self,
        validator: ProfessionalScoreValidator,
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
                    "dashboard": json.dumps({
                        "score": 15.0,  # Over max
                        "breakdown": {},
                        "findings": [],
                        "confidence": 0.9,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.metrics["page_scores"]["dashboard"] == 10.0

    def test_clamps_score_to_min(
        self,
        validator: ProfessionalScoreValidator,
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
                    "dashboard": json.dumps({
                        "score": -5.0,  # Below min
                        "breakdown": {},
                        "findings": [],
                        "confidence": 0.9,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.metrics["page_scores"]["dashboard"] == 0.0

    def test_counts_pages_above_threshold(
        self,
        validator: ProfessionalScoreValidator,
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
                    "dashboard": json.dumps({"score": 9.0, "confidence": 0.9}),
                    "dep_graph": json.dumps({"score": 7.5, "confidence": 0.8}),
                    "chapter": json.dumps({"score": 8.5, "confidence": 0.85}),
                },
                "score_threshold": 8.0,
            },
        )

        result = validator.validate(context)

        # 9.0 and 8.5 are >= 8.0, 7.5 is not
        assert result.metrics["pages_above_threshold"] == 2

    def test_collects_findings_from_pages(
        self,
        validator: ProfessionalScoreValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify findings from all pages are collected."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": json.dumps({
                        "score": 9.0,
                        "findings": ["Excellent whitespace", "Clean typography"],
                        "confidence": 0.9,
                    }),
                    "dep_graph": json.dumps({
                        "score": 8.0,
                        "findings": ["Good alignment"],
                        "confidence": 0.8,
                    }),
                }
            },
        )

        result = validator.validate(context)

        # Check findings are prefixed with page names
        assert any("[dashboard]" in f and "whitespace" in f for f in result.findings)
        assert any("[dep_graph]" in f and "alignment" in f for f in result.findings)


# =============================================================================
# Fallback Parsing Tests
# =============================================================================


class TestFallbackParsing:
    """Tests for pattern-based fallback parsing."""

    def test_extracts_score_from_x_out_of_10(
        self,
        validator: ProfessionalScoreValidator,
    ) -> None:
        """Verify score extraction from 'X/10' format."""
        response = "I would rate this page 8.5/10 for professional appearance."
        parsed = validator.parse_ai_response(response)

        assert parsed["score"] == 8.5
        assert parsed["confidence"] == 0.5  # Low confidence for fallback

    def test_extracts_score_from_out_of_10(
        self,
        validator: ProfessionalScoreValidator,
    ) -> None:
        """Verify score extraction from 'X out of 10' format."""
        response = "This design scores 7 out of 10."
        parsed = validator.parse_ai_response(response)

        assert parsed["score"] == 7.0

    def test_extracts_score_from_score_colon(
        self,
        validator: ProfessionalScoreValidator,
    ) -> None:
        """Verify score extraction from 'score: X' format."""
        response = "Overall score: 9.2"
        parsed = validator.parse_ai_response(response)

        assert parsed["score"] == 9.2

    def test_extracts_score_from_points(
        self,
        validator: ProfessionalScoreValidator,
    ) -> None:
        """Verify score extraction from 'X points' format."""
        response = "I give this design 8 points."
        parsed = validator.parse_ai_response(response)

        assert parsed["score"] == 8.0

    def test_clamps_extracted_score(
        self,
        validator: ProfessionalScoreValidator,
    ) -> None:
        """Verify extracted scores are clamped."""
        response = "This deserves 12/10!"
        parsed = validator.parse_ai_response(response)

        assert parsed["score"] == 10.0

    def test_handles_malformed_json(
        self,
        validator: ProfessionalScoreValidator,
    ) -> None:
        """Verify graceful handling of malformed JSON."""
        malformed = '{"score": 8.5, "breakdown": [incomplete'
        parsed = validator.parse_ai_response(malformed)

        # Should return default with low confidence
        assert parsed["score"] == 5.0
        assert parsed["confidence"] == 0.3
        assert "Could not parse" in parsed["findings"][0]

    def test_handles_no_score_in_response(
        self,
        validator: ProfessionalScoreValidator,
    ) -> None:
        """Verify handling of response without any score."""
        response = "The design looks nice but I can't give a specific rating."
        parsed = validator.parse_ai_response(response)

        # Should return default mid-range score
        assert parsed["score"] == 5.0
        assert parsed["confidence"] == 0.3

    def test_fallback_adds_parsing_note(
        self,
        validator: ProfessionalScoreValidator,
    ) -> None:
        """Verify fallback adds note about extraction method."""
        response = "Rating: 8.5/10"
        parsed = validator.parse_ai_response(response)

        assert any("extracted" in f.lower() for f in parsed["findings"])


# =============================================================================
# Static Method Tests
# =============================================================================


class TestStaticMethods:
    """Tests for static utility methods."""

    def test_get_prompt(self) -> None:
        """Verify get_prompt returns the standard prompt."""
        prompt = ProfessionalScoreValidator.get_prompt()
        assert prompt == PROFESSIONAL_SCORE_PROMPT
        assert "professional" in prompt.lower()
        assert "0-10" in prompt
        assert "Response Format" in prompt

    def test_get_default_pages(self) -> None:
        """Verify get_default_pages returns expected pages."""
        pages = ProfessionalScoreValidator.get_default_pages()
        assert pages == DEFAULT_PAGES
        assert "dashboard" in pages
        assert "dep_graph" in pages
        assert "chapter" in pages

    def test_get_default_threshold(self) -> None:
        """Verify get_default_threshold returns 8.0."""
        threshold = ProfessionalScoreValidator.get_default_threshold()
        assert threshold == DEFAULT_THRESHOLD
        assert threshold == 8.0


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for the full validation flow."""

    def test_full_flow_prompt_then_parse(
        self,
        validator: ProfessionalScoreValidator,
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
                "score": 8.5,
                "breakdown": {},
                "findings": ["Looks professional"],
                "confidence": 0.9,
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
        assert result2.metrics["average_score"] == 8.5

    def test_confidence_calculation(
        self,
        validator: ProfessionalScoreValidator,
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
                    "dashboard": json.dumps({"score": 9.0, "confidence": 1.0}),
                    "dep_graph": json.dumps({"score": 8.0, "confidence": 0.5}),
                }
            },
        )

        result = validator.validate(context)

        # Average of 1.0 and 0.5 = 0.75
        assert abs(result.confidence - 0.75) < 0.01

    def test_edge_case_exactly_at_threshold(
        self,
        validator: ProfessionalScoreValidator,
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
                    "dashboard": json.dumps({"score": 8.0, "confidence": 0.9}),
                },
                "score_threshold": 8.0,
            },
        )

        result = validator.validate(context)

        assert result.passed is True  # 8.0 >= 8.0

    def test_breakdown_preserved_in_results(
        self,
        validator: ProfessionalScoreValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify breakdown details are preserved in page results."""
        breakdown = {
            "whitespace": 1.8,
            "alignment": 1.7,
            "hierarchy": 2.0,
            "typography": 1.5,
            "polish": 1.5,
        }

        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": json.dumps({
                        "score": 8.5,
                        "breakdown": breakdown,
                        "findings": [],
                        "confidence": 0.9,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.details["page_results"]["dashboard"]["breakdown"] == breakdown
