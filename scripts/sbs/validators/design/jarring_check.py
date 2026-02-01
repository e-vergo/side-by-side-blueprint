"""
Jarring element check validator (T7).

An (Aesthetic, Heuristic, Binary) test that uses AI vision to detect
visually jarring elements - things that would make a professional designer
wince.

This validator operates in two modes:
1. Prompt generation: When no AI responses provided, returns prompts for each page
2. Result parsing: When AI responses provided, parses and aggregates results

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
from ...criteria_design import (
    format_jarring_criteria_for_prompt,
    get_jarring_criteria_ids,
)


# =============================================================================
# AI Prompt Template
# =============================================================================

JARRING_CHECK_PROMPT = """
Analyze this screenshot for jarring visual elements.

## Definition of "Jarring"
Jarring elements are visual features that:
- Create uncomfortable eye strain or fatigue
- Draw inappropriate attention away from content
- Break visual flow or consistency
- Would make a professional designer wince

## Check for:
1. **Color clashes**: Colors that fight each other or create vibration
2. **Contrast problems**: Too little contrast (hard to read) or too much (eye strain)
3. **Inconsistent styling**: Elements that don't match the design language
4. **Visual noise**: Too many distinct visual elements without hierarchy
5. **Inappropriate emphasis**: Elements that demand attention they don't deserve
6. **Broken alignment**: Elements that are obviously misaligned

## Context
This is a page from a mathematical formalization documentation site.
The design should feel professional, calm, and focused on content.
Status colors (Sandy Brown, Light Sea Green, Dark Red, Light Green,
Forest Green, Light Blue) are intentional - check that they work well together.

## Response Format
Return a JSON object:
{
  "passed": true/false,
  "issues": [
    {"category": "color_clash", "description": "...", "severity": "minor/major"},
    ...
  ],
  "confidence": 0.0-1.0,
  "notes": "optional overall assessment"
}

PASS if no major jarring issues are found.
FAIL if any major jarring issues are present.
Minor issues don't cause failure but should be noted.
"""


# Pages to validate for jarring elements
DEFAULT_PAGES = [
    "dashboard",
    "dep_graph",
    "chapter",
    "paper_tex",
    "blueprint_verso",
]


# =============================================================================
# Validator
# =============================================================================


@register_validator
class JarringCheckValidator(BaseValidator):
    """Jarring element check using AI vision analysis.

    This validator checks screenshots for visually jarring elements that
    would make a professional designer wince. It's a subjective, heuristic
    check that relies on AI vision analysis.

    The validator operates in two modes:

    1. **Prompt Generation Mode** (default):
       When `context.extra["ai_responses"]` is not provided, the validator
       checks for available screenshots and returns prompts for each page.
       The result includes:
       - `metrics["status"] = "needs_ai_evaluation"`
       - `details["prompts"]` = dict of page -> {screenshot, prompt}

    2. **Result Parsing Mode**:
       When `context.extra["ai_responses"]` is provided (dict of page -> response),
       the validator parses each response and aggregates results.
       The result includes:
       - `metrics["status"] = "evaluated"`
       - `metrics["page_results"]` = parsed results per page

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
            "dashboard": '{"passed": true, "issues": [], "confidence": 0.9}',
            ...
        }
        result = validator.validate(context)
        assert result.passed  # True if all pages pass

    Context.extra keys:
        pages: Optional[list[str]] - Pages to validate (default: DEFAULT_PAGES)
        ai_responses: Optional[dict[str, str]] - AI responses keyed by page name
    """

    def __init__(self) -> None:
        super().__init__("jarring-check", "visual")

    def validate(self, context: ValidationContext) -> ValidatorResult:
        """Execute jarring element check.

        Args:
            context: Validation context with screenshots_dir and optional ai_responses.

        Returns:
            ValidatorResult with prompts (mode 1) or parsed results (mode 2).
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
            return self._parse_responses(ai_responses, pages)

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
                    "prompt": JARRING_CHECK_PROMPT,
                }
            else:
                missing_screenshots.append(page)

        findings = ["AI evaluation required for jarring element check"]
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
                "criteria_checked": get_jarring_criteria_ids(),
            },
        )

    def _parse_responses(
        self,
        ai_responses: dict[str, str],
        pages: list[str],
    ) -> ValidatorResult:
        """Parse AI responses and aggregate results.

        Args:
            ai_responses: Dict of page name -> AI response string.
            pages: List of expected pages (for metrics).

        Returns:
            ValidatorResult with aggregated pass/fail.
        """
        all_passed = True
        all_issues: list[str] = []
        page_results: dict[str, dict[str, Any]] = {}
        total_confidence = 0.0

        for page, response in ai_responses.items():
            parsed = self.parse_ai_response(response)
            page_results[page] = parsed
            total_confidence += parsed.get("confidence", 0.5)

            if not parsed["passed"]:
                all_passed = False
                # Only report major issues in findings
                for issue in parsed.get("issues", []):
                    if issue.get("severity") == "major":
                        category = issue.get("category", "unknown")
                        description = issue.get("description", "no description")
                        all_issues.append(f"[{page}] {category}: {description}")

        # Calculate average confidence
        num_responses = len(ai_responses)
        avg_confidence = total_confidence / num_responses if num_responses > 0 else 0.0

        # Count statistics
        pages_passed = sum(1 for r in page_results.values() if r["passed"])
        pages_failed = num_responses - pages_passed
        total_major = sum(
            sum(1 for i in r.get("issues", []) if i.get("severity") == "major")
            for r in page_results.values()
        )
        total_minor = sum(
            sum(1 for i in r.get("issues", []) if i.get("severity") == "minor")
            for r in page_results.values()
        )

        return ValidatorResult(
            validator=self.name,
            passed=all_passed,
            findings=all_issues if all_issues else ["No major jarring issues found"],
            confidence=avg_confidence,
            metrics={
                "status": "evaluated",
                "pages_checked": num_responses,
                "pages_passed": pages_passed,
                "pages_failed": pages_failed,
                "total_major_issues": total_major,
                "total_minor_issues": total_minor,
            },
            details={
                "page_results": page_results,
                "criteria_checked": get_jarring_criteria_ids(),
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
            Dict with keys: passed, issues, confidence, notes (optional).
        """
        # Try to extract JSON from response
        try:
            # Look for JSON object in response
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                parsed = json.loads(json_match.group())
                # Validate expected structure
                if "passed" in parsed:
                    return {
                        "passed": bool(parsed.get("passed", False)),
                        "issues": parsed.get("issues", []),
                        "confidence": float(parsed.get("confidence", 0.8)),
                        "notes": parsed.get("notes", ""),
                    }
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: keyword analysis
        response_lower = response.lower()

        # Check for explicit pass/fail keywords
        has_pass = "pass" in response_lower
        has_fail = "fail" in response_lower
        has_major = "major" in response_lower
        has_issue = any(word in response_lower for word in ["issue", "problem", "error", "jarring"])

        # Determine pass/fail
        if has_fail or (has_major and has_issue):
            passed = False
        elif has_pass and not has_fail:
            passed = True
        else:
            # Ambiguous - default to pass with low confidence
            passed = not has_issue

        return {
            "passed": passed,
            "issues": [],
            "confidence": 0.5,  # Low confidence for fallback parsing
            "notes": "Parsed via keyword fallback",
        }

    @staticmethod
    def get_prompt() -> str:
        """Get the jarring check prompt template.

        Returns:
            The prompt string for AI vision analysis.
        """
        return JARRING_CHECK_PROMPT

    @staticmethod
    def get_default_pages() -> list[str]:
        """Get the default list of pages to check.

        Returns:
            List of page names.
        """
        return DEFAULT_PAGES.copy()

    @staticmethod
    def format_criteria() -> str:
        """Get formatted criteria guidance for prompts.

        Returns:
            Human-readable criteria text.
        """
        return format_jarring_criteria_for_prompt()
