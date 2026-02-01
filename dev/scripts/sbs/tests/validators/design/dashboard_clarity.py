"""
Dashboard clarity validator (T3).

A (Functional, Heuristic, Binary) test that uses AI vision to verify the
dashboard clearly communicates project health. Unlike T7/T8 which are aesthetic,
this is functional - it tests whether the dashboard serves its purpose.

This validator operates in two modes:
1. Prompt generation: When no AI responses provided, returns prompt for dashboard
2. Result parsing: When AI responses provided, parses and evaluates answers

The validator asks three key questions about the dashboard:
1. Can you determine proof progress (proven vs unproven)?
2. Can you identify blocking issues or items needing attention?
3. Can you assess overall project status/health?

PASS requires ALL THREE questions to be clearly answerable.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..base import BaseValidator, ValidationContext, ValidatorResult
from ..registry import register_validator


# =============================================================================
# AI Prompt Template
# =============================================================================

DASHBOARD_CLARITY_PROMPT = """
Look at this dashboard screenshot and answer three questions about the project's status.

## Questions to Answer

1. **Proof Progress**: Can you determine how many theorems are proven vs. unproven?
   - Look for progress indicators, pie charts, status counts, or similar
   - Answer: Yes (with approximate numbers) or No (can't determine)

2. **Blocking Issues**: Can you identify if there are any blocking issues or items needing attention?
   - Look for warnings, attention flags, "blocked" indicators, or priority items
   - Answer: Yes (describe what you see) or No (can't determine)

3. **Overall Status**: Can you assess the overall project health/status?
   - Look for summary stats, completion percentages, or status overviews
   - Answer: Yes (healthy/in-progress/concerning) or No (can't determine)

## Response Format
Return a JSON object:
{
  "questions_answerable": [true, true, false],
  "answers": {
    "proof_progress": "15 proven out of 33 total (45%)",
    "blocking_issues": "2 items flagged as needing attention",
    "overall_status": "cannot determine - no clear summary"
  },
  "passed": false,
  "reasoning": "Two of three questions were answerable from the dashboard. The overall status was unclear because...",
  "confidence": 0.85
}

PASS if ALL THREE questions are clearly answerable from the dashboard alone.
FAIL if ANY question requires guessing or is ambiguous.
"""


# Question labels for metrics
QUESTION_LABELS = [
    "proof_progress",
    "blocking_issues",
    "overall_status",
]


# =============================================================================
# Validator
# =============================================================================


@register_validator
class DashboardClarityValidator(BaseValidator):
    """Dashboard clarity check using AI vision analysis.

    This validator checks whether the dashboard clearly communicates project
    health by asking three key questions:
    1. Can you determine proof progress?
    2. Can you identify blocking issues?
    3. Can you assess overall status?

    This is a FUNCTIONAL test, not an aesthetic one. The dashboard must
    communicate its purpose effectively.

    The validator operates in two modes:

    1. **Prompt Generation Mode** (default):
       When `context.extra["ai_responses"]` is not provided, the validator
       checks for the dashboard screenshot and returns the prompt.
       The result includes:
       - `metrics["status"] = "needs_ai_evaluation"`
       - `details["prompts"]` = dict with dashboard prompt

    2. **Result Parsing Mode**:
       When `context.extra["ai_responses"]` is provided (dict with dashboard response),
       the validator parses the response and determines pass/fail.
       The result includes:
       - `metrics["status"] = "evaluated"`
       - `metrics["questions_answerable"]` = list of bool per question
       - `metrics["questions_passed"]` = count of answerable questions
       - `metrics["answers"]` = dict of question -> answer text

    Usage:
        # Mode 1: Generate prompt
        context = ValidationContext(
            project="SBSTest",
            project_root=Path("/path"),
            commit="abc123",
            screenshots_dir=Path("/path/to/screenshots"),
        )
        result = validator.validate(context)
        prompts = result.details["prompts"]  # Send to AI

        # Mode 2: Parse response
        context.extra["ai_responses"] = {
            "dashboard": '{"questions_answerable": [true, true, true], ...}',
        }
        result = validator.validate(context)
        assert result.passed  # True if all 3 questions answerable

    Context.extra keys:
        ai_responses: Optional[dict[str, str]] - AI response keyed by "dashboard"
    """

    def __init__(self) -> None:
        super().__init__("dashboard-clarity", "visual")

    def validate(self, context: ValidationContext) -> ValidatorResult:
        """Execute dashboard clarity check.

        Args:
            context: Validation context with screenshots_dir and optional ai_responses.

        Returns:
            ValidatorResult with prompt (mode 1) or parsed result (mode 2).
        """
        screenshots_dir = context.screenshots_dir
        if not screenshots_dir or not screenshots_dir.exists():
            return self._make_fail(
                findings=["No screenshots directory provided or directory doesn't exist"],
                metrics={
                    "status": "error",
                    "error": "no_screenshots_dir",
                    "screenshots_dir": str(screenshots_dir) if screenshots_dir else None,
                },
                confidence=1.0,
            )

        # Check if AI responses are provided
        ai_responses = context.extra.get("ai_responses")

        if not ai_responses:
            # Mode 1: Generate prompt
            return self._generate_prompt(screenshots_dir)
        else:
            # Mode 2: Parse response
            return self._parse_response(ai_responses)

    def _generate_prompt(
        self,
        screenshots_dir: Path,
    ) -> ValidatorResult:
        """Generate AI prompt for dashboard screenshot.

        Args:
            screenshots_dir: Directory containing screenshots.

        Returns:
            ValidatorResult with prompt in details.
        """
        dashboard_screenshot = screenshots_dir / "dashboard.png"

        if not dashboard_screenshot.exists():
            return self._make_fail(
                findings=["Dashboard screenshot not found"],
                metrics={
                    "status": "error",
                    "error": "no_dashboard_screenshot",
                    "screenshots_dir": str(screenshots_dir),
                },
                confidence=1.0,
            )

        return ValidatorResult(
            validator=self.name,
            passed=False,  # Not yet evaluated
            findings=["AI evaluation required for dashboard clarity check"],
            confidence=0.0,  # No evaluation done yet
            metrics={
                "status": "needs_ai_evaluation",
                "pages_to_check": 1,
            },
            details={
                "prompts": {
                    "dashboard": {
                        "screenshot": str(dashboard_screenshot),
                        "prompt": DASHBOARD_CLARITY_PROMPT,
                    }
                },
            },
        )

    def _parse_response(
        self,
        ai_responses: dict[str, str],
    ) -> ValidatorResult:
        """Parse AI response and determine pass/fail.

        Args:
            ai_responses: Dict with "dashboard" key -> AI response string.

        Returns:
            ValidatorResult based on whether all 3 questions were answerable.
        """
        dashboard_response = ai_responses.get("dashboard", "")

        if not dashboard_response:
            return self._make_fail(
                findings=["No dashboard response provided"],
                metrics={
                    "status": "error",
                    "error": "no_dashboard_response",
                },
                confidence=1.0,
            )

        parsed = self.parse_ai_response(dashboard_response)

        questions = parsed.get("questions_answerable", [])
        answers = parsed.get("answers", {})
        reasoning = parsed.get("reasoning", "No reasoning provided")
        confidence = parsed.get("confidence", 0.8)

        # Ensure we have exactly 3 question results
        while len(questions) < 3:
            questions.append(False)
        questions = questions[:3]

        all_answerable = all(questions)
        questions_passed = sum(1 for q in questions if q)

        # Build findings based on what failed
        findings = [reasoning]
        if not all_answerable:
            failed_questions = []
            for i, (label, answered) in enumerate(zip(QUESTION_LABELS, questions)):
                if not answered:
                    failed_questions.append(label.replace("_", " "))
            if failed_questions:
                findings.append(
                    f"Could not determine: {', '.join(failed_questions)}"
                )

        # Build per-question results for criteria_results
        criteria_results = {
            f"dashboard_{label}": answered
            for label, answered in zip(QUESTION_LABELS, questions)
        }

        return ValidatorResult(
            validator=self.name,
            passed=all_answerable,
            findings=findings,
            confidence=confidence,
            metrics={
                "status": "evaluated",
                "questions_answerable": questions,
                "questions_passed": questions_passed,
                "questions_total": 3,
                "answers": answers,
            },
            criteria_results=criteria_results,
            details={
                "parsed_response": parsed,
            },
        )

    @staticmethod
    def parse_ai_response(response: str) -> dict[str, Any]:
        """Parse an AI response string into structured result.

        Attempts to extract JSON from the response. Falls back to keyword
        analysis if JSON parsing fails.

        Args:
            response: Raw response text from AI vision analysis.

        Returns:
            Dict with keys: questions_answerable, answers, passed, reasoning, confidence.
        """
        # Try to extract JSON from response
        try:
            # Look for JSON object in response
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                parsed = json.loads(json_match.group())
                # Validate expected structure
                if "questions_answerable" in parsed:
                    questions = parsed.get("questions_answerable", [])
                    # Handle various formats
                    if isinstance(questions, list):
                        questions = [bool(q) for q in questions]
                    else:
                        questions = []

                    return {
                        "questions_answerable": questions,
                        "answers": parsed.get("answers", {}),
                        "passed": bool(parsed.get("passed", False)),
                        "reasoning": str(parsed.get("reasoning", "")),
                        "confidence": float(parsed.get("confidence", 0.8)),
                    }
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        # Fallback: keyword analysis
        response_lower = response.lower()

        # Try to detect answers for each question
        questions_answerable = []

        # Q1: Proof progress - look for numbers/percentages
        has_progress = any(
            term in response_lower
            for term in ["proven", "progress", "completed", "done", "/"]
        ) and any(char.isdigit() for char in response)
        questions_answerable.append(has_progress)

        # Q2: Blocking issues - look for blocking/attention keywords
        has_blocking = any(
            term in response_lower
            for term in ["blocking", "blocked", "attention", "warning", "priority", "issue"]
        )
        questions_answerable.append(has_blocking)

        # Q3: Overall status - look for status/health keywords
        has_status = any(
            term in response_lower
            for term in ["status", "health", "overall", "summary", "healthy", "concerning"]
        )
        questions_answerable.append(has_status)

        passed = all(questions_answerable)

        return {
            "questions_answerable": questions_answerable,
            "answers": {},
            "passed": passed,
            "reasoning": "Parsed from keywords (no structured JSON response)",
            "confidence": 0.5,
        }

    @staticmethod
    def get_prompt() -> str:
        """Get the dashboard clarity prompt template.

        Returns:
            The prompt string for AI vision analysis.
        """
        return DASHBOARD_CLARITY_PROMPT

    @staticmethod
    def get_question_labels() -> list[str]:
        """Get the labels for the three questions.

        Returns:
            List of question labels.
        """
        return QUESTION_LABELS.copy()
