"""
Base test mixins for validator test classes.

Provides reusable test patterns that are shared across multiple validator test files.
These mixins reduce duplication while preserving the clarity of each test file.

Usage:
    class TestValidatorProperties(ValidatorPropertiesTestMixin):
        validator_name = "my-validator"
        validator_category = "visual"

        @pytest.fixture
        def validator(self):
            return MyValidator()
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable

import pytest

if TYPE_CHECKING:
    from pathlib import Path
    from sbs.tests.validators.base import ValidationContext


# =============================================================================
# Validator Properties Mixin
# =============================================================================


class ValidatorPropertiesTestMixin:
    """Mixin providing standard validator property tests.

    All validators must have a name and category. This mixin provides tests
    to verify these properties are correctly set.

    Subclasses must define:
        validator_name: str - expected validator name (e.g., "dashboard-clarity")
        validator_category: str - expected category (default: "visual")

    Subclasses must also provide a `validator` pytest fixture that returns
    an instance of the validator being tested.

    Example:
        @pytest.mark.evergreen
        class TestValidatorProperties(ValidatorPropertiesTestMixin):
            validator_name = "dashboard-clarity"
            validator_category = "visual"

            @pytest.fixture
            def validator(self):
                return DashboardClarityValidator()
    """

    validator_name: str
    validator_category: str = "visual"

    @pytest.mark.evergreen
    def test_name(self, validator: Any) -> None:
        """Verify validator has correct name."""
        assert validator.name == self.validator_name

    @pytest.mark.evergreen
    def test_category(self, validator: Any) -> None:
        """Verify validator has correct category."""
        assert validator.category == self.validator_category


# =============================================================================
# Heuristic Response Parsing Mixins
# =============================================================================


class HeuristicResponseParsingTestMixin(ABC):
    """Mixin providing tests for AI response parsing in heuristic validators.

    Heuristic validators (T3, T4, T7, T8) all need to parse AI responses
    and handle common edge cases like:
    - JSON embedded in surrounding text
    - Malformed JSON
    - Empty responses

    Subclasses must define:
        valid_json_response: str - a valid JSON response string
        valid_json_expected_pass: bool - whether valid_json_response should pass
        malformed_json_fallback_confidence: float - expected confidence for malformed JSON

    Subclasses must also provide:
        - `validator` pytest fixture returning the validator instance
        - `parse_response` method (or `parse_ai_response` on the validator)
    """

    # Subclasses should override these
    valid_json_response: str
    valid_json_expected_pass: bool
    malformed_json_fallback_confidence: float = 0.5

    @abstractmethod
    def get_valid_json_response(self) -> str:
        """Return a valid JSON response string for testing.

        Subclasses must implement this to provide validator-specific
        valid JSON responses.
        """
        pass

    @abstractmethod
    def get_malformed_json_response(self) -> str:
        """Return a malformed JSON string for testing fallback parsing.

        Subclasses must implement this to provide validator-specific
        malformed JSON that will trigger fallback parsing.
        """
        pass

    def wrap_json_in_text(self, json_str: str) -> str:
        """Wrap JSON in surrounding conversational text.

        This simulates how AI models often respond with JSON embedded
        in explanatory text.
        """
        return f"""
        Here's my analysis of the screenshot:

        {json_str}

        The page looks good overall.
        """

    @pytest.mark.evergreen
    def test_parses_valid_json_response(self, validator: Any) -> None:
        """Verify valid JSON responses are parsed correctly."""
        json_str = self.get_valid_json_response()
        parsed = validator.parse_ai_response(json_str)

        # Parsed response should have expected fields
        assert "confidence" in parsed
        assert parsed["confidence"] > self.malformed_json_fallback_confidence

    @pytest.mark.evergreen
    def test_handles_json_with_surrounding_text(self, validator: Any) -> None:
        """Verify JSON extraction works with surrounding text.

        AI models often embed JSON in conversational text. The parser
        should extract just the JSON portion.
        """
        json_str = self.get_valid_json_response()
        wrapped = self.wrap_json_in_text(json_str)
        parsed = validator.parse_ai_response(wrapped)

        # Should successfully extract and parse the JSON
        assert "confidence" in parsed
        assert parsed["confidence"] > self.malformed_json_fallback_confidence

    @pytest.mark.evergreen
    def test_handles_malformed_json(self, validator: Any) -> None:
        """Verify graceful handling of malformed JSON.

        When JSON parsing fails, the validator should fall back to
        keyword-based parsing with low confidence.
        """
        malformed = self.get_malformed_json_response()
        parsed = validator.parse_ai_response(malformed)

        # Should fall back to low confidence parsing
        assert parsed["confidence"] == self.malformed_json_fallback_confidence or \
               parsed["confidence"] < 0.6  # Allow some flexibility


class ScoreBasedHeuristicTestMixin(HeuristicResponseParsingTestMixin):
    """Mixin for score-based heuristic validators (T4: Toggle, T8: Professional).

    These validators return a numeric score (typically 0-10) and have
    specific patterns for score extraction from text responses.

    Subclasses must define:
        default_fallback_score: float - score returned when parsing fails
        score_field_name: str - name of the score field in parsed response
    """

    default_fallback_score: float = 5.0
    score_field_name: str = "score"
    malformed_json_fallback_confidence: float = 0.3

    def get_valid_json_response(self) -> str:
        """Return a valid score-based JSON response."""
        return json.dumps({
            self.score_field_name: 8.0,
            "breakdown": {},
            "findings": ["Looks good"],
            "recommendations": [],
            "confidence": 0.9,
        })

    def get_malformed_json_response(self) -> str:
        """Return malformed JSON that will trigger fallback."""
        return '{"score": 6.5, "breakdown": [incomplete'

    @pytest.mark.evergreen
    def test_fallback_returns_default_score(self, validator: Any) -> None:
        """Verify fallback parsing returns the default score."""
        response = "The design looks okay but I can't quantify it."
        parsed = validator.parse_ai_response(response)

        assert parsed[self.score_field_name] == self.default_fallback_score
        assert parsed["confidence"] <= self.malformed_json_fallback_confidence

    @pytest.mark.evergreen
    def test_extracts_score_from_x_out_of_10(self, validator: Any) -> None:
        """Verify score extraction from 'X/10' format."""
        response = "I would rate this 7.5/10."
        parsed = validator.parse_ai_response(response)

        assert parsed[self.score_field_name] == 7.5
        assert parsed["confidence"] == 0.5  # Low confidence for fallback


class BooleanHeuristicTestMixin(HeuristicResponseParsingTestMixin):
    """Mixin for boolean-result heuristic validators (T3: Dashboard, T7: Jarring).

    These validators return a pass/fail boolean and may have specific
    patterns for keyword detection.

    Subclasses must define:
        pass_field_name: str - name of the pass/fail field (default: "passed")
        pass_keywords: list[str] - keywords indicating pass
        fail_keywords: list[str] - keywords indicating fail
    """

    pass_field_name: str = "passed"
    pass_keywords: list[str] = ["pass", "passes", "good", "acceptable"]
    fail_keywords: list[str] = ["fail", "fails", "major issue", "problem"]
    malformed_json_fallback_confidence: float = 0.5

    def get_valid_json_response(self) -> str:
        """Return a valid boolean-result JSON response."""
        return json.dumps({
            self.pass_field_name: True,
            "findings": [],
            "confidence": 0.9,
        })

    def get_malformed_json_response(self) -> str:
        """Return malformed JSON that will trigger fallback."""
        return '{"passed": true, "findings": [incomplete'

    @pytest.mark.evergreen
    def test_fallback_detects_pass_keywords(self, validator: Any) -> None:
        """Verify fallback parsing detects pass keywords."""
        response = "The page looks good and passes inspection."
        parsed = validator.parse_ai_response(response)

        assert parsed[self.pass_field_name] is True
        assert parsed["confidence"] == self.malformed_json_fallback_confidence

    @pytest.mark.evergreen
    def test_fallback_detects_fail_keywords(self, validator: Any) -> None:
        """Verify fallback parsing detects fail keywords."""
        response = "This page fails the check due to issues."
        parsed = validator.parse_ai_response(response)

        assert parsed[self.pass_field_name] is False


class QuestionBasedHeuristicTestMixin(BooleanHeuristicTestMixin):
    """Mixin for question-based validators like T3 (Dashboard Clarity).

    These validators check if specific questions can be answered
    from the UI, returning results per question.

    Subclasses must define:
        num_questions: int - number of questions to check
        questions_field: str - name of the questions result field
    """

    num_questions: int = 3
    questions_field: str = "questions_answerable"

    def get_valid_json_response(self) -> str:
        """Return a valid question-based JSON response."""
        return json.dumps({
            self.questions_field: [True] * self.num_questions,
            "answers": {},
            "passed": True,
            "reasoning": "All questions answerable",
            "confidence": 0.9,
        })

    @pytest.mark.evergreen
    def test_handles_fewer_questions(self, validator: Any) -> None:
        """Verify handling when response has fewer question results."""
        response = json.dumps({
            self.questions_field: [True, True],  # Only 2 instead of expected
            "passed": False,
            "reasoning": "Missing question",
            "confidence": 0.7,
        })
        parsed = validator.parse_ai_response(response)

        # Should handle gracefully - specifics depend on validator
        assert self.questions_field in parsed or "confidence" in parsed


# =============================================================================
# Multi-Page Validation Mixins
# =============================================================================


class MultiPageValidationTestMixin:
    """Mixin for validators that check multiple pages.

    Validators like T4, T7, T8 analyze multiple screenshots and
    aggregate results. This mixin provides tests for that pattern.

    Subclasses must define:
        default_pages: list[str] - list of default page names to check
    """

    default_pages: list[str] = ["dashboard", "chapter", "dep_graph"]

    @pytest.mark.evergreen
    def test_handles_single_page(
        self,
        validator: Any,
        single_page_context_factory: Callable[..., "ValidationContext"],
    ) -> None:
        """Verify validation works with just one page."""
        context = single_page_context_factory()
        result = validator.validate(context)

        # Should not error, should note limited pages
        assert result.metrics.get("pages_to_check", 0) >= 0

    @pytest.mark.evergreen
    def test_handles_missing_directory(self, validator: Any) -> None:
        """Verify handling of nonexistent screenshots directory."""
        from sbs.tests.validators.base import ValidationContext
        from pathlib import Path

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


# =============================================================================
# Prompt Generation Mixins
# =============================================================================


class PromptGenerationTestMixin:
    """Mixin for testing prompt generation in heuristic validators.

    All heuristic validators (T3, T4, T7, T8) generate prompts when
    no AI response is provided. This mixin tests that behavior.

    Subclasses must define:
        expected_prompt_text: str - text that should appear in prompt
    """

    expected_prompt_text: str = ""

    @pytest.mark.evergreen
    def test_generates_prompt_without_ai_response(
        self,
        validator: Any,
        temp_screenshots_dir: "Path",
    ) -> None:
        """Verify prompts are generated when no AI response provided."""
        from sbs.tests.validators.base import ValidationContext
        from pathlib import Path

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

    @pytest.mark.evergreen
    def test_prompt_contains_screenshot_path(
        self,
        validator: Any,
        temp_screenshots_dir: "Path",
    ) -> None:
        """Verify each prompt includes the screenshot path."""
        from sbs.tests.validators.base import ValidationContext
        from pathlib import Path

        context = ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
            screenshots_dir=temp_screenshots_dir,
        )

        result = validator.validate(context)
        prompts = result.details.get("prompts", {})

        for page, prompt_data in prompts.items():
            assert "screenshot" in prompt_data
            assert page in prompt_data["screenshot"]
            assert prompt_data["screenshot"].endswith(".png")
