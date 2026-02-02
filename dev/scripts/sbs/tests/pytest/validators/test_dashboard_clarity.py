"""
Tests for the dashboard clarity validator (T3).

Tests cover:
- Prompt generation mode (no AI responses)
- Response parsing mode (with AI responses)
- JSON response parsing
- Fallback keyword parsing
- All-pass and partial-pass scenarios
- Per-question failure reporting
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from sbs.tests.validators.design.dashboard_clarity import (
    DashboardClarityValidator,
    DASHBOARD_CLARITY_PROMPT,
    QUESTION_LABELS,
)
from sbs.tests.validators.base import ValidationContext


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def validator() -> DashboardClarityValidator:
    """Create a DashboardClarityValidator instance."""
    return DashboardClarityValidator()


@pytest.fixture
def temp_screenshots_dir() -> Path:
    """Create a temporary directory with dashboard screenshot."""
    with tempfile.TemporaryDirectory(prefix="sbs_dashboard_test_") as tmpdir:
        path = Path(tmpdir)
        # Create mock dashboard screenshot
        (path / "dashboard.png").touch()
        yield path


@pytest.fixture
def empty_screenshots_dir() -> Path:
    """Create an empty temporary directory."""
    with tempfile.TemporaryDirectory(prefix="sbs_dashboard_empty_") as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# Validator Properties Tests
# =============================================================================


@pytest.mark.evergreen
class TestValidatorProperties:
    """Tests for validator name and category."""

    def test_name(self, validator: DashboardClarityValidator) -> None:
        """Verify validator name."""
        assert validator.name == "dashboard-clarity"

    def test_category(self, validator: DashboardClarityValidator) -> None:
        """Verify validator category is visual."""
        assert validator.category == "visual"


# =============================================================================
# Prompt Generation Tests (Mode 1)
# =============================================================================


@pytest.mark.evergreen
class TestPromptGeneration:
    """Tests for prompt generation mode."""

    def test_generates_prompt_for_dashboard(
        self,
        validator: DashboardClarityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify prompt is generated for dashboard screenshot."""
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
        assert "dashboard" in result.details["prompts"]

    def test_prompt_contains_screenshot_path(
        self,
        validator: DashboardClarityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify prompt includes the screenshot path."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
        )

        result = validator.validate(context)
        prompt_data = result.details["prompts"]["dashboard"]

        assert "screenshot" in prompt_data
        assert "dashboard" in prompt_data["screenshot"]
        assert prompt_data["screenshot"].endswith(".png")

    def test_prompt_text_is_standard(
        self,
        validator: DashboardClarityValidator,
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
        prompt_data = result.details["prompts"]["dashboard"]

        assert prompt_data["prompt"] == DASHBOARD_CLARITY_PROMPT

    def test_fails_without_dashboard_screenshot(
        self,
        validator: DashboardClarityValidator,
        empty_screenshots_dir: Path,
    ) -> None:
        """Verify failure when dashboard.png is missing."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=empty_screenshots_dir,
        )

        result = validator.validate(context)

        assert result.passed is False
        assert result.metrics["status"] == "error"
        assert result.metrics["error"] == "no_dashboard_screenshot"
        assert "Dashboard screenshot not found" in result.findings

    def test_handles_missing_directory(
        self,
        validator: DashboardClarityValidator,
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
        validator: DashboardClarityValidator,
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

    def test_only_checks_dashboard(
        self,
        validator: DashboardClarityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify only dashboard is checked, not other pages."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
        )

        result = validator.validate(context)

        assert result.metrics["pages_to_check"] == 1
        assert len(result.details["prompts"]) == 1
        assert "dashboard" in result.details["prompts"]


# =============================================================================
# Response Parsing Tests (Mode 2)
# =============================================================================


@pytest.mark.evergreen
class TestResponseParsing:
    """Tests for AI response parsing mode."""

    def test_parses_all_answerable_response(
        self,
        validator: DashboardClarityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify pass when all 3 questions are answerable."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": json.dumps({
                        "questions_answerable": [True, True, True],
                        "answers": {
                            "proof_progress": "15 proven out of 33 total (45%)",
                            "blocking_issues": "2 items flagged as needing attention",
                            "overall_status": "Project is in progress",
                        },
                        "passed": True,
                        "reasoning": "All three questions were clearly answerable",
                        "confidence": 0.95,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.passed is True
        assert result.metrics["status"] == "evaluated"
        assert result.metrics["questions_passed"] == 3
        assert result.metrics["questions_total"] == 3
        assert all(result.metrics["questions_answerable"])

    def test_fails_partial_answerable(
        self,
        validator: DashboardClarityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify fail when only some questions are answerable."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": json.dumps({
                        "questions_answerable": [True, True, False],
                        "answers": {
                            "proof_progress": "15 proven out of 33 total",
                            "blocking_issues": "2 items needing attention",
                            "overall_status": "Cannot determine - no clear summary",
                        },
                        "passed": False,
                        "reasoning": "Only 2 of 3 questions answerable",
                        "confidence": 0.85,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.passed is False
        assert result.metrics["questions_passed"] == 2
        assert result.metrics["questions_answerable"] == [True, True, False]

    def test_fails_all_unanswerable(
        self,
        validator: DashboardClarityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify fail when no questions are answerable."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": json.dumps({
                        "questions_answerable": [False, False, False],
                        "answers": {},
                        "passed": False,
                        "reasoning": "Dashboard does not clearly communicate anything",
                        "confidence": 0.9,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.passed is False
        assert result.metrics["questions_passed"] == 0
        assert all(not q for q in result.metrics["questions_answerable"])

    def test_reports_which_questions_failed(
        self,
        validator: DashboardClarityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify metrics show which specific questions weren't answerable."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": json.dumps({
                        "questions_answerable": [True, False, True],
                        "answers": {
                            "proof_progress": "10/20 proven",
                            "blocking_issues": "unclear",
                            "overall_status": "healthy",
                        },
                        "passed": False,
                        "reasoning": "Blocking issues section unclear",
                        "confidence": 0.8,
                    }),
                }
            },
        )

        result = validator.validate(context)

        # Check per-question criteria results
        assert "dashboard_proof_progress" in result.criteria_results
        assert "dashboard_blocking_issues" in result.criteria_results
        assert "dashboard_overall_status" in result.criteria_results

        assert result.criteria_results["dashboard_proof_progress"] is True
        assert result.criteria_results["dashboard_blocking_issues"] is False
        assert result.criteria_results["dashboard_overall_status"] is True

        # Check findings mention the failed question
        assert any("blocking" in f.lower() for f in result.findings)

    def test_handles_json_with_surrounding_text(
        self,
        validator: DashboardClarityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify JSON extraction works with surrounding text."""
        response_with_text = """
        Here's my analysis of the dashboard:

        {"questions_answerable": [true, true, true], "answers": {"proof_progress": "50%"}, "passed": true, "reasoning": "All clear", "confidence": 0.88}

        The dashboard is well designed.
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
        assert result.confidence == 0.88

    def test_handles_empty_response(
        self,
        validator: DashboardClarityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify handling of empty AI response."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": "",
                }
            },
        )

        result = validator.validate(context)

        assert result.passed is False
        assert result.metrics["status"] == "error"
        assert result.metrics["error"] == "no_dashboard_response"

    def test_handles_missing_dashboard_key(
        self,
        validator: DashboardClarityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify handling when dashboard key is missing from responses."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "other_page": "some response",
                }
            },
        )

        result = validator.validate(context)

        assert result.passed is False
        assert result.metrics["status"] == "error"

    def test_includes_answers_in_metrics(
        self,
        validator: DashboardClarityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify answer text is included in metrics."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": json.dumps({
                        "questions_answerable": [True, True, True],
                        "answers": {
                            "proof_progress": "25 proven, 8 remaining",
                            "blocking_issues": "No blocking issues",
                            "overall_status": "Healthy",
                        },
                        "passed": True,
                        "reasoning": "Clear dashboard",
                        "confidence": 0.9,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert "answers" in result.metrics
        assert result.metrics["answers"]["proof_progress"] == "25 proven, 8 remaining"
        assert result.metrics["answers"]["blocking_issues"] == "No blocking issues"


# =============================================================================
# Fallback Parsing Tests
# =============================================================================


@pytest.mark.evergreen
class TestFallbackParsing:
    """Tests for keyword-based fallback parsing."""

    def test_fallback_detects_progress_with_numbers(
        self,
        validator: DashboardClarityValidator,
    ) -> None:
        """Verify fallback parsing detects progress indicators."""
        response = "The dashboard shows 15 proven theorems out of 33 total."
        parsed = validator.parse_ai_response(response)

        assert parsed["questions_answerable"][0] is True  # proof_progress
        assert parsed["confidence"] == 0.5  # Low confidence for fallback

    def test_fallback_detects_blocking_keywords(
        self,
        validator: DashboardClarityValidator,
    ) -> None:
        """Verify fallback parsing detects blocking issue keywords."""
        response = "There are 2 items marked as blocked in the attention column."
        parsed = validator.parse_ai_response(response)

        assert parsed["questions_answerable"][1] is True  # blocking_issues

    def test_fallback_detects_status_keywords(
        self,
        validator: DashboardClarityValidator,
    ) -> None:
        """Verify fallback parsing detects status/health keywords."""
        response = "The overall project status appears healthy based on the summary."
        parsed = validator.parse_ai_response(response)

        assert parsed["questions_answerable"][2] is True  # overall_status

    def test_fallback_handles_ambiguous_response(
        self,
        validator: DashboardClarityValidator,
    ) -> None:
        """Verify fallback handles ambiguous responses."""
        response = "The dashboard is visible but I cannot determine specifics."
        parsed = validator.parse_ai_response(response)

        # Should fail all questions if no clear indicators
        assert parsed["passed"] is False
        assert parsed["confidence"] == 0.5

    def test_fallback_notes_parsing_method(
        self,
        validator: DashboardClarityValidator,
    ) -> None:
        """Verify fallback adds note about parsing method."""
        response = "Some text without JSON."
        parsed = validator.parse_ai_response(response)

        assert "keyword" in parsed.get("reasoning", "").lower()

    def test_handles_malformed_json(
        self,
        validator: DashboardClarityValidator,
    ) -> None:
        """Verify graceful handling of malformed JSON."""
        malformed = '{"questions_answerable": [true, true, incomplete'
        parsed = validator.parse_ai_response(malformed)

        # Should fall back to keyword parsing
        assert parsed["confidence"] == 0.5
        assert "keyword" in parsed.get("reasoning", "").lower()

    def test_fallback_all_indicators_present(
        self,
        validator: DashboardClarityValidator,
    ) -> None:
        """Verify fallback pass when all indicators are present."""
        response = """
        I can see 10/20 proven theorems on the progress chart.
        There are 3 blocked items in the attention section.
        The overall project status is healthy according to the summary.
        """
        parsed = validator.parse_ai_response(response)

        assert all(parsed["questions_answerable"])
        assert parsed["passed"] is True


# =============================================================================
# Static Method Tests
# =============================================================================


@pytest.mark.evergreen
class TestStaticMethods:
    """Tests for static utility methods."""

    def test_get_prompt(self) -> None:
        """Verify get_prompt returns the standard prompt."""
        prompt = DashboardClarityValidator.get_prompt()
        assert prompt == DASHBOARD_CLARITY_PROMPT
        assert "Questions to Answer" in prompt
        assert "Proof Progress" in prompt
        assert "Blocking Issues" in prompt
        assert "Overall Status" in prompt
        assert "Response Format" in prompt

    def test_get_question_labels(self) -> None:
        """Verify get_question_labels returns expected labels."""
        labels = DashboardClarityValidator.get_question_labels()
        assert labels == QUESTION_LABELS
        assert "proof_progress" in labels
        assert "blocking_issues" in labels
        assert "overall_status" in labels
        assert len(labels) == 3


# =============================================================================
# Edge Cases Tests
# =============================================================================


@pytest.mark.evergreen
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_handles_fewer_than_3_questions(
        self,
        validator: DashboardClarityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify handling when response has fewer than 3 question results."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": json.dumps({
                        "questions_answerable": [True, True],  # Only 2
                        "passed": False,
                        "reasoning": "Missing third question",
                        "confidence": 0.7,
                    }),
                }
            },
        )

        result = validator.validate(context)

        # Should pad to 3 with False
        assert result.passed is False
        assert len(result.metrics["questions_answerable"]) == 3
        assert result.metrics["questions_answerable"][2] is False

    def test_handles_more_than_3_questions(
        self,
        validator: DashboardClarityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify handling when response has more than 3 question results."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": json.dumps({
                        "questions_answerable": [True, True, True, True, True],  # 5
                        "passed": True,
                        "reasoning": "Extra questions",
                        "confidence": 0.9,
                    }),
                }
            },
        )

        result = validator.validate(context)

        # Should truncate to 3
        assert result.passed is True
        assert len(result.metrics["questions_answerable"]) == 3
        assert result.metrics["questions_total"] == 3

    def test_confidence_passthrough(
        self,
        validator: DashboardClarityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify confidence from AI response is passed through."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": json.dumps({
                        "questions_answerable": [True, True, True],
                        "passed": True,
                        "reasoning": "Clear",
                        "confidence": 0.92,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert result.confidence == 0.92


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.evergreen
class TestIntegration:
    """Integration tests for the full validation flow."""

    def test_full_flow_prompt_then_parse(
        self,
        validator: DashboardClarityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Test the full flow: generate prompt, then parse response."""
        # Step 1: Generate prompt
        context1 = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
        )

        result1 = validator.validate(context1)
        assert result1.metrics["status"] == "needs_ai_evaluation"
        prompts = result1.details["prompts"]
        assert "dashboard" in prompts

        # Step 2: Simulate AI response
        ai_responses = {
            "dashboard": json.dumps({
                "questions_answerable": [True, True, True],
                "answers": {
                    "proof_progress": "15/33 proven",
                    "blocking_issues": "None",
                    "overall_status": "Healthy",
                },
                "passed": True,
                "reasoning": "All clear",
                "confidence": 0.9,
            })
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

    def test_parsed_response_in_details(
        self,
        validator: DashboardClarityValidator,
        temp_screenshots_dir: Path,
    ) -> None:
        """Verify parsed response is available in details."""
        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
            extra={
                "ai_responses": {
                    "dashboard": json.dumps({
                        "questions_answerable": [True, True, True],
                        "passed": True,
                        "reasoning": "Dashboard is clear",
                        "confidence": 0.85,
                    }),
                }
            },
        )

        result = validator.validate(context)

        assert "parsed_response" in result.details
        assert result.details["parsed_response"]["reasoning"] == "Dashboard is clear"
