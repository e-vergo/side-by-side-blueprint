"""
Design-specific criteria for aesthetic validation.

Separates design/aesthetic criteria from functional criteria in criteria.py.
These criteria are subjective and evaluated by AI vision analysis.

The jarring check (T7) is an (Aesthetic, Heuristic, Binary) test that uses
AI to detect visually jarring elements that would make a professional
designer wince.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DesignCriterion:
    """A design/aesthetic criterion for AI evaluation.

    Unlike functional Criterion, these are evaluated subjectively by AI
    and include guidance for the evaluator.
    """

    id: str
    """Unique identifier for this criterion."""

    description: str
    """Human-readable description of what to check."""

    category: str
    """Category: 'color', 'typography', 'spacing', 'visual_hierarchy', 'consistency'."""

    guidance: str = ""
    """Detailed guidance for AI evaluator on how to assess this criterion."""

    examples_pass: list[str] = field(default_factory=list)
    """Examples of what would pass this criterion."""

    examples_fail: list[str] = field(default_factory=list)
    """Examples of what would fail this criterion."""


# =============================================================================
# Jarring Element Criteria
# =============================================================================

JARRING_CHECK_CRITERIA: list[DesignCriterion] = [
    DesignCriterion(
        id="color_clash",
        description="No color combinations that fight each other or create optical vibration",
        category="color",
        guidance="""
        Check for colors placed adjacent to each other that create:
        - Optical vibration (high-saturation complementary colors touching)
        - Visual confusion (similar colors that should be distinct)
        - Uncomfortable contrast ratios (too bright or clashing hues)

        The 6 status colors (Sandy Brown, Light Sea Green, Dark Red, Light Green,
        Forest Green, Light Blue) should work harmoniously with backgrounds.
        """,
        examples_pass=[
            "Status colors are visually distinct but not clashing",
            "Dark red 'sorry' status is readable against backgrounds",
            "Forest green and light green are distinguishable",
        ],
        examples_fail=[
            "Two saturated colors touch and create shimmer effect",
            "Text color fights with background color",
            "Adjacent status dots blur together",
        ],
    ),
    DesignCriterion(
        id="contrast_problems",
        description="Adequate contrast for readability without causing eye strain",
        category="color",
        guidance="""
        Check that:
        - Text is readable against its background (sufficient contrast)
        - Nothing is so high-contrast it causes eye strain
        - Dark mode and light mode both have appropriate contrast

        Pay special attention to:
        - Code blocks and syntax highlighting
        - Status dots and their labels
        - Navigation links
        """,
        examples_pass=[
            "All text is clearly readable",
            "Dark mode text is not blindingly white",
            "Light mode uses comfortable contrast levels",
        ],
        examples_fail=[
            "Text fades into background",
            "White text on light gray is hard to read",
            "Pure white on pure black causes eye strain",
        ],
    ),
    DesignCriterion(
        id="inconsistent_styling",
        description="All elements follow a consistent design language",
        category="consistency",
        guidance="""
        Check that:
        - Similar elements have similar styling
        - Fonts, sizes, and weights are consistent
        - Spacing patterns repeat predictably
        - Colors are used systematically

        Look for outliers that don't match the rest of the interface.
        """,
        examples_pass=[
            "All headers use the same font weight",
            "All buttons have consistent styling",
            "Code blocks all look the same",
        ],
        examples_fail=[
            "One button looks completely different",
            "Font sizes vary randomly",
            "Some borders are sharp, others rounded, without pattern",
        ],
    ),
    DesignCriterion(
        id="visual_noise",
        description="Clear visual hierarchy without overwhelming detail",
        category="visual_hierarchy",
        guidance="""
        Check that:
        - There's a clear hierarchy of importance
        - Not too many competing focal points
        - Whitespace is used effectively
        - The eye knows where to look first

        The page should feel organized, not chaotic.
        """,
        examples_pass=[
            "Main content is clearly the focus",
            "Navigation is present but not overwhelming",
            "Adequate breathing room between elements",
        ],
        examples_fail=[
            "Too many things demand attention at once",
            "Dense walls of text or elements",
            "No clear starting point for the eye",
        ],
    ),
    DesignCriterion(
        id="inappropriate_emphasis",
        description="Visual emphasis matches content importance",
        category="visual_hierarchy",
        guidance="""
        Check that:
        - Important things look important
        - Unimportant things don't demand attention
        - Decoration doesn't overshadow content
        - Status indicators are noticeable but not overwhelming
        """,
        examples_pass=[
            "Main theorem statement is more prominent than helpers",
            "Error indicators are noticeable without screaming",
            "Navigation fades appropriately into background",
        ],
        examples_fail=[
            "Minor detail draws more attention than main content",
            "Decorative element is more eye-catching than actual content",
            "All elements compete equally for attention",
        ],
    ),
    DesignCriterion(
        id="broken_alignment",
        description="Elements are properly aligned and balanced",
        category="spacing",
        guidance="""
        Check that:
        - Things that should be aligned are aligned
        - Columns line up across rows
        - No obvious off-by-few-pixels issues
        - Layouts are balanced and intentional

        Small alignment issues are okay; obviously broken alignment is not.
        """,
        examples_pass=[
            "Side-by-side panels align at the top",
            "List items line up consistently",
            "Graph nodes form a coherent visual pattern",
        ],
        examples_fail=[
            "Text blocks are obviously misaligned",
            "Columns don't line up across rows",
            "Elements appear randomly placed",
        ],
    ),
]


# =============================================================================
# Future Design Criteria Categories
# =============================================================================

# Typography criteria (future T8+)
TYPOGRAPHY_CRITERIA: list[DesignCriterion] = []

# Spacing criteria (future T8+)
SPACING_CRITERIA: list[DesignCriterion] = []


# =============================================================================
# Utility Functions
# =============================================================================


def get_jarring_criteria() -> list[DesignCriterion]:
    """Get all jarring check criteria."""
    return JARRING_CHECK_CRITERIA.copy()


def get_jarring_criteria_ids() -> list[str]:
    """Get IDs of all jarring check criteria."""
    return [c.id for c in JARRING_CHECK_CRITERIA]


def format_jarring_criteria_for_prompt() -> str:
    """Format jarring criteria as guidance text for AI prompts.

    Returns a formatted string suitable for inclusion in AI vision prompts.
    """
    lines = ["## Jarring Element Categories\n"]

    for criterion in JARRING_CHECK_CRITERIA:
        lines.append(f"### {criterion.id.replace('_', ' ').title()}")
        lines.append(f"{criterion.description}\n")

        if criterion.guidance:
            lines.append("**Guidance:**")
            lines.append(criterion.guidance.strip())
            lines.append("")

        if criterion.examples_fail:
            lines.append("**Would FAIL:**")
            for ex in criterion.examples_fail:
                lines.append(f"- {ex}")
            lines.append("")

    return "\n".join(lines)
