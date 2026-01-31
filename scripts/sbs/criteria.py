"""
Compliance criteria definitions for visual validation.

Defines what to check on each page type and global requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Criterion:
    """A single compliance criterion."""

    id: str
    description: str
    category: str  # "layout", "color", "interaction", "content"
    severity: str = "required"  # "required", "recommended", "optional"


@dataclass
class PageCriteria:
    """Criteria for a specific page type."""

    page: str
    criteria: list[Criterion] = field(default_factory=list)
    interactive_elements: list[dict] = field(default_factory=list)


# =============================================================================
# Global Criteria (apply to all pages)
# =============================================================================

GLOBAL_CRITERIA = [
    Criterion(
        id="theme_toggle_visible",
        description="Theme toggle control is visible in header",
        category="interaction",
    ),
    Criterion(
        id="no_layout_overflow",
        description="No horizontal scrollbar or content overflow",
        category="layout",
    ),
    Criterion(
        id="sidebar_present",
        description="Sidebar navigation is present and visible",
        category="layout",
    ),
    Criterion(
        id="active_page_highlighted",
        description="Current page is highlighted in sidebar",
        category="layout",
    ),
]


# =============================================================================
# Page-Specific Criteria
# =============================================================================

DASHBOARD_CRITERIA = PageCriteria(
    page="dashboard",
    criteria=[
        Criterion(
            id="no_chapter_panel",
            description="Dashboard has NO secondary sidebar (chapter panel)",
            category="layout",
        ),
        Criterion(
            id="stats_panel_visible",
            description="Stats panel shows node counts by status",
            category="content",
        ),
        Criterion(
            id="key_theorems_panel",
            description="Key theorems panel is present",
            category="content",
        ),
        Criterion(
            id="two_column_layout",
            description="Dashboard uses 2-column grid layout",
            category="layout",
        ),
    ],
    interactive_elements=[
        {"id": "theme_toggle", "selector": "#theme-toggle, .theme-toggle", "type": "click"},
    ],
)


DEP_GRAPH_CRITERIA = PageCriteria(
    page="dep_graph",
    criteria=[
        Criterion(
            id="six_status_colors",
            description="All 6 status colors visible in legend (notReady, ready, sorry, proven, fullyProven, mathlibReady)",
            category="color",
        ),
        Criterion(
            id="graph_centered",
            description="Dependency graph is centered in viewport on load",
            category="layout",
        ),
        Criterion(
            id="zoom_controls_visible",
            description="Zoom in/out/fit controls are visible",
            category="interaction",
        ),
        Criterion(
            id="nodes_visible",
            description="Graph nodes are visible and labeled",
            category="content",
        ),
        Criterion(
            id="edges_visible",
            description="Graph edges connect nodes correctly",
            category="content",
        ),
    ],
    interactive_elements=[
        {"id": "theme_toggle", "selector": "#theme-toggle, .theme-toggle", "type": "click"},
        {"id": "zoom_in", "selector": "#graph-zoom-in", "type": "click"},
        {"id": "zoom_out", "selector": "#graph-zoom-out", "type": "click"},
        {"id": "zoom_fit", "selector": "#graph-fit", "type": "click"},
        {"id": "node_click", "selector": ".node", "type": "click", "sample_count": 2},
    ],
)


PAPER_TEX_CRITERIA = PageCriteria(
    page="paper_tex",
    criteria=[
        Criterion(
            id="paper_content_rendered",
            description="Paper content is rendered (not empty)",
            category="content",
        ),
        Criterion(
            id="math_rendered",
            description="Mathematical formulas are rendered (MathJax)",
            category="content",
        ),
        Criterion(
            id="sidebar_consistent",
            description="Sidebar matches other pages",
            category="layout",
        ),
    ],
    interactive_elements=[
        {"id": "theme_toggle", "selector": "#theme-toggle, .theme-toggle", "type": "click"},
        {"id": "proof_toggle", "selector": ".proof_heading, .expand-proof", "type": "click"},
    ],
)


PDF_TEX_CRITERIA = PageCriteria(
    page="pdf_tex",
    criteria=[
        Criterion(
            id="pdf_container_present",
            description="PDF container or embed element is present",
            category="layout",
            severity="recommended",  # PDF may not render in headless Chrome
        ),
    ],
    interactive_elements=[],  # PDF interactions limited in Playwright
)


PAPER_VERSO_CRITERIA = PageCriteria(
    page="paper_verso",
    criteria=[
        Criterion(
            id="verso_content_rendered",
            description="Verso paper content is rendered",
            category="content",
        ),
        Criterion(
            id="sidebar_consistent",
            description="Sidebar matches other pages",
            category="layout",
        ),
    ],
    interactive_elements=[
        {"id": "theme_toggle", "selector": "#theme-toggle, .theme-toggle", "type": "click"},
    ],
)


BLUEPRINT_VERSO_CRITERIA = PageCriteria(
    page="blueprint_verso",
    criteria=[
        Criterion(
            id="blueprint_content_rendered",
            description="Blueprint Verso content is rendered",
            category="content",
        ),
        Criterion(
            id="sidebar_consistent",
            description="Sidebar matches other pages",
            category="layout",
        ),
    ],
    interactive_elements=[
        {"id": "theme_toggle", "selector": "#theme-toggle, .theme-toggle", "type": "click"},
    ],
)


CHAPTER_CRITERIA = PageCriteria(
    page="chapter",
    criteria=[
        Criterion(
            id="side_by_side_aligned",
            description="Side-by-side theorem/proof displays are aligned",
            category="layout",
        ),
        Criterion(
            id="rainbow_brackets",
            description="Rainbow brackets visible with 6 depth colors",
            category="color",
        ),
        Criterion(
            id="lean_code_highlighted",
            description="Lean code has syntax highlighting",
            category="content",
        ),
        Criterion(
            id="latex_rendered",
            description="LaTeX content is properly rendered",
            category="content",
        ),
        Criterion(
            id="proof_collapse_sync",
            description="Proof expand/collapse syncs between LaTeX and Lean",
            category="interaction",
        ),
    ],
    interactive_elements=[
        {"id": "theme_toggle", "selector": "#theme-toggle, .theme-toggle", "type": "click"},
        {"id": "proof_toggle", "selector": ".proof_heading, .expand-proof", "type": "click"},
        {"id": "tactic_toggle", "selector": "input.tactic-toggle", "type": "click"},
        {"id": "hover_token", "selector": ".hl.lean .token", "type": "hover"},
    ],
)


# =============================================================================
# Criteria Registry
# =============================================================================

PAGE_CRITERIA: dict[str, PageCriteria] = {
    "dashboard": DASHBOARD_CRITERIA,
    "dep_graph": DEP_GRAPH_CRITERIA,
    "paper_tex": PAPER_TEX_CRITERIA,
    "pdf_tex": PDF_TEX_CRITERIA,
    "paper_verso": PAPER_VERSO_CRITERIA,
    "pdf_verso": PageCriteria(page="pdf_verso", criteria=[], interactive_elements=[]),  # Disabled
    "blueprint_verso": BLUEPRINT_VERSO_CRITERIA,
    "chapter": CHAPTER_CRITERIA,
}


def get_criteria_for_page(page: str) -> tuple[list[Criterion], list[Criterion]]:
    """Get criteria for a page.

    Returns (page_criteria, global_criteria).
    """
    page_criteria = PAGE_CRITERIA.get(page, PageCriteria(page=page))
    return page_criteria.criteria, GLOBAL_CRITERIA


def get_interactive_elements(page: str) -> list[dict]:
    """Get interactive elements to capture for a page."""
    page_criteria = PAGE_CRITERIA.get(page, PageCriteria(page=page))
    return page_criteria.interactive_elements


def format_criteria_for_prompt(page: str) -> str:
    """Format criteria as text for agent prompts.

    Returns a human-readable list of criteria to check.
    """
    page_specific, global_criteria = get_criteria_for_page(page)

    lines = ["## Global Criteria (all pages)"]
    for c in global_criteria:
        severity = f" [{c.severity}]" if c.severity != "required" else ""
        lines.append(f"- {c.description}{severity}")

    lines.append("")
    lines.append(f"## Page-Specific Criteria ({page})")

    if page_specific:
        for c in page_specific:
            severity = f" [{c.severity}]" if c.severity != "required" else ""
            lines.append(f"- {c.description}{severity}")
    else:
        lines.append("- (No page-specific criteria defined)")

    return "\n".join(lines)


def get_all_criteria_ids(page: str) -> list[str]:
    """Get all criterion IDs for a page (including global)."""
    page_specific, global_criteria = get_criteria_for_page(page)
    return [c.id for c in global_criteria] + [c.id for c in page_specific]
