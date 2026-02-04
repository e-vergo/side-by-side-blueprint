"""
Professional score validator (T8).

An (Aesthetic, Heuristic, Gradient) test that uses AI vision to score
professional appearance on a 0-10 scale.

This validator operates in two modes:
1. Prompt generation: When no AI responses provided, returns prompts for each page
2. Result parsing: When AI responses provided, parses and aggregates scores

This design allows integration with different AI backends (Claude, GPT-4V, etc.)
while keeping the validation logic centralized.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from ..base import BaseValidator, ValidationContext, ValidatorResult
from ..registry import register_validator


# =============================================================================
# AI Prompt Template
# =============================================================================

PROFESSIONAL_SCORE_PROMPT = """
Rate this page's professional appearance on a 0-10 scale.

## Scoring Criteria (2 points each, total 10):

1. **Whitespace & Breathing Room** (0-2 points)
   - Adequate margins and padding
   - Content not cramped
   - Visual breathing room between sections

2. **Alignment & Grid Consistency** (0-2 points)
   - Elements align to an invisible grid
   - Consistent horizontal and vertical alignment
   - No obviously misaligned elements

3. **Visual Hierarchy** (0-2 points)
   - Clear distinction between headings, body, and secondary text
   - Important elements stand out appropriately
   - Logical reading flow

4. **Typography Consistency** (0-2 points)
   - Consistent font usage
   - Appropriate font sizes
   - Good line height and letter spacing

5. **Polish & Attention to Detail** (0-2 points)
   - Consistent border radii
   - Smooth hover states (if visible)
   - No rough edges or visual glitches
   - Cohesive color usage

## Context
This is a page from a mathematical formalization documentation site.
The design should feel professional, calm, and focused on content.
Status colors (Sandy Brown, Light Sea Green, Dark Red, Light Green,
Forest Green, Light Blue) are intentional design elements.

## Response Format
Return a JSON object:
{
  "score": 8.5,
  "breakdown": {
    "whitespace": 1.8,
    "alignment": 1.7,
    "hierarchy": 2.0,
    "typography": 1.5,
    "polish": 1.5
  },
  "findings": [
    "Strong visual hierarchy with clear heading levels",
    "Minor alignment issue in sidebar",
    ...
  ],
  "confidence": 0.85
}
"""


# Pages to validate for professional appearance
DEFAULT_PAGES = [
    "dashboard",
    "dep_graph",
    "chapter",
    "paper_tex",
]

# Default threshold for passing
DEFAULT_THRESHOLD = 8.0


# =============================================================================
# Validator
# =============================================================================


@register_validator
class ProfessionalScoreValidator(BaseValidator):
    """Professional appearance scoring using AI vision analysis.

    This validator scores screenshots for professional appearance on a
    0-10 scale based on 5 criteria worth 2 points each:
    - Whitespace & Breathing Room
    - Alignment & Grid Consistency
    - Visual Hierarchy
    - Typography Consistency
    - Polish & Attention to Detail

    The validator operates in two modes:

    1. **Prompt Generation Mode** (default):
       When `context.extra["ai_responses"]` is not provided, the validator
       checks for available screenshots and returns prompts for each page.
       The result includes:
       - `metrics["status"] = "needs_ai_evaluation"`
       - `details["prompts"]` = dict of page -> {screenshot, prompt}

    2. **Result Parsing Mode**:
       When `context.extra["ai_responses"]` is provided (dict of page -> response),
       the validator parses each response and aggregates scores.
       The result includes:
       - `metrics["status"] = "evaluated"`
       - `metrics["average_score"]` = averaged score across pages
       - `metrics["page_scores"]` = individual page scores

    Usage:
        # Mode 1: Generate prompts
        context = ValidationContext(
            project="SBSTest",
            project_root=Path("/path"),
            commit="abc123",
            screenshots_dir=Path("/path/to/screenshots"),
        )
        result = validator.validate(context)
        prompts = result.details["prompts"]  # Send to AI

        # Mode 2: Parse responses
        context.extra["ai_responses"] = {
            "dashboard": '{"score": 8.5, "breakdown": {...}, "findings": [...]}',
            ...
        }
        context.extra["score_threshold"] = 8.0  # Optional, default 8.0
        result = validator.validate(context)
        assert result.passed  # True if average score >= threshold

    Context.extra keys:
        pages: Optional[list[str]] - Pages to validate (default: DEFAULT_PAGES)
        ai_responses: Optional[dict[str, str]] - AI responses keyed by page name
        score_threshold: Optional[float] - Minimum score to pass (default: 8.0)
    """

    def __init__(self) -> None:
        super().__init__("professional-score", "visual")

    def validate(self, context: ValidationContext) -> ValidatorResult:
        """Execute professional appearance scoring.

        Args:
            context: Validation context with screenshots_dir and optional ai_responses.

        Returns:
            ValidatorResult with prompts (mode 1) or parsed scores (mode 2).
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

        # Determine which pages to check
        pages = context.extra.get("pages", DEFAULT_PAGES)

        # Check if AI responses are provided
        ai_responses = context.extra.get("ai_responses")

        if not ai_responses:
            # Mode 1: Generate prompts
            return self._generate_prompts(screenshots_dir, pages)
        else:
            # Mode 2: Parse responses
            threshold = context.extra.get("score_threshold", DEFAULT_THRESHOLD)
            return self._parse_responses(ai_responses, pages, threshold)

    def _generate_prompts(
        self,
        screenshots_dir: Path,
        pages: list[str],
    ) -> ValidatorResult:
        """Generate AI prompts for each available page.

        Args:
            screenshots_dir: Directory containing screenshots.
            pages: List of page names to check.

        Returns:
            ValidatorResult with prompts in details.
        """
        prompts: dict[str, dict[str, str]] = {}
        missing_screenshots: list[str] = []

        for page in pages:
            screenshot = screenshots_dir / f"{page}.png"
            if screenshot.exists():
                prompts[page] = {
                    "screenshot": str(screenshot),
                    "prompt": PROFESSIONAL_SCORE_PROMPT,
                }
            else:
                missing_screenshots.append(page)

        findings = ["AI evaluation required for professional score"]
        if missing_screenshots:
            findings.append(f"Missing screenshots: {', '.join(missing_screenshots)}")

        return ValidatorResult(
            validator=self.name,
            passed=False,  # Not yet evaluated
            findings=findings,
            confidence=0.0,  # No evaluation done yet
            metrics={
                "status": "needs_ai_evaluation",
                "pages_to_check": len(prompts),
                "missing_screenshots": len(missing_screenshots),
            },
            details={
                "prompts": prompts,
                "missing_screenshots": missing_screenshots,
            },
        )

    def _parse_responses(
        self,
        ai_responses: dict[str, str],
        pages: list[str],
        threshold: float,
    ) -> ValidatorResult:
        """Parse AI responses and aggregate scores.

        Args:
            ai_responses: Dict of page name -> AI response string.
            pages: List of expected pages (for metrics).
            threshold: Minimum average score to pass.

        Returns:
            ValidatorResult with aggregated score.
        """
        page_results: dict[str, dict[str, Any]] = {}
        all_findings: list[str] = []
        total_confidence = 0.0

        for page, response in ai_responses.items():
            parsed = self.parse_ai_response(response)
            page_results[page] = parsed
            total_confidence += parsed.get("confidence", 0.5)

            # Collect findings with page prefix
            for finding in parsed.get("findings", []):
                all_findings.append(f"[{page}] {finding}")

        # Calculate aggregate metrics
        num_responses = len(ai_responses)
        avg_confidence = total_confidence / num_responses if num_responses > 0 else 0.0

        # Extract scores and calculate average
        scores = [r["score"] for r in page_results.values() if "score" in r]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Count pages above threshold
        pages_above_threshold = sum(1 for s in scores if s >= threshold)

        # Determine pass/fail
        passed = avg_score >= threshold

        # Build page_scores dict for metrics
        page_scores = {
            page: result["score"]
            for page, result in page_results.items()
            if "score" in result
        }

        # Summarize findings if too many
        display_findings = all_findings[:10]
        if len(all_findings) > 10:
            display_findings.append(f"... and {len(all_findings) - 10} more findings")

        if not display_findings:
            if passed:
                display_findings = [f"Average score {avg_score:.1f}/10 meets threshold {threshold}"]
            else:
                display_findings = [f"Average score {avg_score:.1f}/10 below threshold {threshold}"]

        return ValidatorResult(
            validator=self.name,
            passed=passed,
            findings=display_findings,
            confidence=avg_confidence,
            metrics={
                "status": "evaluated",
                "average_score": round(avg_score, 2),
                "page_scores": page_scores,
                "threshold": threshold,
                "pages_above_threshold": pages_above_threshold,
                "pages_checked": num_responses,
            },
            details={
                "page_results": page_results,
            },
        )

    @staticmethod
    def parse_ai_response(response: str) -> dict[str, Any]:
        """Parse an AI response string into structured result.

        Attempts to extract JSON from the response. Falls back to pattern
        matching if JSON parsing fails.

        Args:
            response: Raw response text from AI vision analysis.

        Returns:
            Dict with keys: score, breakdown, findings, confidence.
        """
        # Try to extract JSON from response
        try:
            # Look for JSON object in response
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                parsed = json.loads(json_match.group())
                # Validate and clamp score to 0-10 range
                if "score" in parsed:
                    score = float(parsed["score"])
                    parsed["score"] = max(0.0, min(10.0, score))
                    return {
                        "score": parsed["score"],
                        "breakdown": parsed.get("breakdown", {}),
                        "findings": parsed.get("findings", []),
                        "confidence": float(parsed.get("confidence", 0.8)),
                    }
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        # Fallback: try to extract score from text patterns
        # Pattern: "X/10" or "X out of 10" or "score: X" or "score of X"
        patterns = [
            r"\b(\d+(?:\.\d+)?)\s*/\s*10\b",  # 8.5/10
            r"\b(\d+(?:\.\d+)?)\s+out\s+of\s+10\b",  # 8.5 out of 10
            r"score[:\s]+(\d+(?:\.\d+)?)\b",  # score: 8.5 or score 8.5
            r"score\s+of\s+(\d+(?:\.\d+)?)\b",  # score of 8.5
            r"\b(\d+(?:\.\d+)?)\s+points?\b",  # 8.5 points
        ]

        for pattern in patterns:
            match = re.search(pattern, response.lower())
            if match:
                score = float(match.group(1))
                return {
                    "score": max(0.0, min(10.0, score)),
                    "breakdown": {},
                    "findings": ["Score extracted from text (no structured response)"],
                    "confidence": 0.5,
                }

        # Last resort: return default mid-range score with low confidence
        return {
            "score": 5.0,
            "breakdown": {},
            "findings": ["Could not parse AI response"],
            "confidence": 0.3,
        }

    @staticmethod
    def get_prompt() -> str:
        """Get the professional score prompt template.

        Returns:
            The prompt string for AI vision analysis.
        """
        return PROFESSIONAL_SCORE_PROMPT

    @staticmethod
    def get_default_pages() -> list[str]:
        """Get the default list of pages to check.

        Returns:
            List of page names.
        """
        return DEFAULT_PAGES.copy()

    @staticmethod
    def get_default_threshold() -> float:
        """Get the default score threshold for passing.

        Returns:
            Default threshold value (8.0).
        """
        return DEFAULT_THRESHOLD
