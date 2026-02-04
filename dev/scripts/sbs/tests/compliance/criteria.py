"""
Compliance criteria definitions for visual validation.

Defines what to check on each page type and global requirements.

Criteria extracted from historical plan files:
- dapper-wondering-riddle.md (Verso Blueprint & Paper authoring)
- eager-soaring-cupcake.md (Compliance loop design)
- mighty-exploring-sunrise.md (Release plan with 12 phases)
- parsed-conjuring-torvalds.md (Chrome MCP testing patterns)
- wise-mapping-tarjan.md (Verso integration & features)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# =============================================================================
# 6-Status Color Model (Source of Truth)
# =============================================================================

STATUS_COLORS = {
    "notReady": "#F4A460",      # Sandy Brown
    "ready": "#20B2AA",         # Light Sea Green
    "sorry": "#8B0000",         # Dark Red
    "proven": "#90EE90",        # Light Green
    "fullyProven": "#228B22",   # Forest Green
    "mathlibReady": "#87CEEB",  # Light Blue
}

# Line comment styling
LINE_COMMENT_COLOR = "#6A9955"
LINE_COMMENT_STYLE = "italic"

# Bracket CSS classes (depth 0-5 maps to lean-bracket-1 through lean-bracket-6)
BRACKET_CLASSES = [f"lean-bracket-{i}" for i in range(1, 7)]


@dataclass
class Criterion:
    """A single compliance criterion."""

    id: str
    description: str
    category: str  # "layout", "color", "interaction", "content", "visual", "functional", "technical"
    severity: str = "required"  # "required", "recommended", "optional"
    selector: Optional[str] = None  # CSS selector if applicable
    hex_color: Optional[str] = None  # Expected hex color if applicable
    source: Optional[str] = None  # Source plan file


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
        selector="#theme-toggle, .theme-toggle",
        source="eager-soaring-cupcake.md",
    ),
    Criterion(
        id="theme_toggle_functional",
        description="Theme toggle switches between light and dark modes",
        category="interaction",
        selector="#theme-toggle, .theme-toggle",
        source="eager-soaring-cupcake.md",
    ),
    Criterion(
        id="no_layout_overflow",
        description="No horizontal scrollbar or content overflow",
        category="layout",
        source="eager-soaring-cupcake.md",
    ),
    Criterion(
        id="no_console_errors",
        description="No JavaScript console errors on page load",
        category="functional",
        source="eager-soaring-cupcake.md",
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
        selector=".active, .sidebar-active",
        source="eager-soaring-cupcake.md",
    ),
    Criterion(
        id="six_status_colors",
        description="All 6 status colors render correctly site-wide",
        category="color",
        source="mighty-exploring-sunrise.md",
    ),
]


# =============================================================================
# Sidebar Criteria (shared across pages)
# =============================================================================

SIDEBAR_CRITERIA = [
    Criterion(
        id="sidebar_consistent_all_pages",
        description="Sidebar identical across all blueprint pages",
        category="layout",
        source="eager-soaring-cupcake.md",
    ),
    Criterion(
        id="sidebar_highlight_full_width",
        description="Active highlight extends to viewport edge",
        category="layout",
        source="mighty-exploring-sunrise.md",
    ),
    Criterion(
        id="sidebar_disabled_greyed",
        description="Disabled items are greyed out correctly",
        category="visual",
        source="eager-soaring-cupcake.md",
    ),
    Criterion(
        id="sidebar_chapters_listed",
        description="All chapters listed in sidebar",
        category="content",
        source="mighty-exploring-sunrise.md",
    ),
    Criterion(
        id="sidebar_verso_docs_appear",
        description="Verso documents appear in sidebar when present",
        category="content",
        source="dapper-wondering-riddle.md",
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
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="stats_panel_visible",
            description="Stats panel shows node counts by status",
            category="content",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="stats_6_colors",
            description="Stats panel displays all 6 status colors",
            category="color",
            source="mighty-exploring-sunrise.md",
        ),
        Criterion(
            id="key_theorems_panel",
            description="Key theorems panel is present and populated",
            category="content",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="messages_panel",
            description="Messages panel shows @[blueprint message] content",
            category="content",
            source="mighty-exploring-sunrise.md",
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
            id="legend_6_colors",
            description="Legend shows all 6 status colors with labels",
            category="color",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="notReady_color",
            description="notReady nodes: Sandy Brown",
            category="color",
            hex_color="#F4A460",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="ready_color",
            description="ready nodes: Light Sea Green",
            category="color",
            hex_color="#20B2AA",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="sorry_color",
            description="sorry nodes: Dark Red",
            category="color",
            hex_color="#8B0000",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="proven_color",
            description="proven nodes: Light Green",
            category="color",
            hex_color="#90EE90",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="fullyProven_color",
            description="fullyProven nodes: Forest Green",
            category="color",
            hex_color="#228B22",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="mathlibReady_color",
            description="mathlibReady nodes: Light Blue",
            category="color",
            hex_color="#87CEEB",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="graph_centered",
            description="Dependency graph is centered in viewport on load",
            category="layout",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="zoom_controls_visible",
            description="Zoom in/out/fit controls are visible",
            category="interaction",
            selector="#graph-zoom-in, #graph-zoom-out, #graph-fit",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="pan_controls",
            description="Pan controls visible and functional",
            category="interaction",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="nodes_clickable",
            description="Clicking a node opens modal with details",
            category="interaction",
            selector=".node",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="modal_content",
            description="Modal shows label, status, statement, and proof",
            category="content",
            source="mighty-exploring-sunrise.md",
        ),
        Criterion(
            id="edges_visible",
            description="Graph edges connect nodes correctly",
            category="content",
            source="mighty-exploring-sunrise.md",
        ),
        Criterion(
            id="viewBox_origin",
            description="SVG viewBox starts at (0, 0)",
            category="technical",
            source="mighty-exploring-sunrise.md",
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
            id="leanStatement_renders",
            description=":::leanStatement hook renders formal statement",
            category="content",
            source="dapper-wondering-riddle.md",
        ),
        Criterion(
            id="leanProof_renders",
            description=":::leanProof hook renders formal proof",
            category="content",
            source="dapper-wondering-riddle.md",
        ),
        Criterion(
            id="sideBySide_renders",
            description=":::sideBySide hook renders side-by-side display",
            category="layout",
            source="dapper-wondering-riddle.md",
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
        Criterion(
            id="pdf_generated",
            description="PDF compiled from TeX source",
            category="functional",
            source="dapper-wondering-riddle.md",
        ),
    ],
    interactive_elements=[],  # PDF interactions limited in Playwright
)


CHAPTER_CRITERIA = PageCriteria(
    page="chapter",
    criteria=[
        Criterion(
            id="side_by_side_aligned",
            description="Side-by-side theorem/proof displays are aligned",
            category="layout",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="rainbow_brackets",
            description="Rainbow brackets visible with 6 depth colors",
            category="color",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="bracket_level_0_consistent",
            description="Level 0 brackets same color across ALL code blocks",
            category="color",
            source="mighty-exploring-sunrise.md",
        ),
        Criterion(
            id="bracket_level_1_consistent",
            description="Level 1 brackets same color across ALL code blocks",
            category="color",
            source="mighty-exploring-sunrise.md",
        ),
        Criterion(
            id="bracket_level_2_consistent",
            description="Level 2 brackets same color across ALL code blocks",
            category="color",
            source="mighty-exploring-sunrise.md",
        ),
        Criterion(
            id="bracket_level_3_consistent",
            description="Level 3 brackets same color across ALL code blocks",
            category="color",
            source="mighty-exploring-sunrise.md",
        ),
        Criterion(
            id="bracket_level_4_consistent",
            description="Level 4 brackets same color across ALL code blocks",
            category="color",
            source="mighty-exploring-sunrise.md",
        ),
        Criterion(
            id="bracket_level_5_consistent",
            description="Level 5 brackets same color across ALL code blocks",
            category="color",
            source="mighty-exploring-sunrise.md",
        ),
        Criterion(
            id="lean_code_highlighted",
            description="Lean code has syntax highlighting",
            category="content",
            source="wise-mapping-tarjan.md",
        ),
        Criterion(
            id="line_comments_styled",
            description="Line comments: #6A9955, italic",
            category="visual",
            hex_color="#6A9955",
            source="wise-mapping-tarjan.md",
        ),
        Criterion(
            id="line_comment_class",
            description="Line comments have class 'line-comment'",
            category="technical",
            selector=".line-comment",
            source="wise-mapping-tarjan.md",
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
            selector=".proof_heading, .expand-proof",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="hover_tooltips",
            description="Hover tooltips functional on Lean code tokens",
            category="interaction",
            selector=".hl.lean .token",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="tactic_state_toggle",
            description="Tactic state toggles work",
            category="interaction",
            selector="input.tactic-toggle",
            source="eager-soaring-cupcake.md",
        ),
        Criterion(
            id="zebra_striping_light",
            description="Zebra striping visible in light mode",
            category="visual",
            source="mighty-exploring-sunrise.md",
        ),
        Criterion(
            id="zebra_striping_dark",
            description="Zebra striping visible in dark mode",
            category="visual",
            source="mighty-exploring-sunrise.md",
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
    "chapter": CHAPTER_CRITERIA,
}


def get_criteria_for_page(page: str) -> tuple[list[Criterion], list[Criterion]]:
    """Get criteria for a page.

    Returns (page_criteria, global_criteria).
    """
    page_criteria = PAGE_CRITERIA.get(page, PageCriteria(page=page))
    return page_criteria.criteria, GLOBAL_CRITERIA


def get_sidebar_criteria() -> list[Criterion]:
    """Get sidebar-specific criteria."""
    return SIDEBAR_CRITERIA


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
        hex_info = f" ({c.hex_color})" if c.hex_color else ""
        lines.append(f"- {c.description}{hex_info}{severity}")

    # Include sidebar criteria for blueprint pages
    if page not in ["dashboard"]:
        lines.append("")
        lines.append("## Sidebar Criteria")
        for c in SIDEBAR_CRITERIA:
            severity = f" [{c.severity}]" if c.severity != "required" else ""
            lines.append(f"- {c.description}{severity}")

    lines.append("")
    lines.append(f"## Page-Specific Criteria ({page})")

    if page_specific:
        for c in page_specific:
            severity = f" [{c.severity}]" if c.severity != "required" else ""
            hex_info = f" ({c.hex_color})" if c.hex_color else ""
            lines.append(f"- {c.description}{hex_info}{severity}")
    else:
        lines.append("- (No page-specific criteria defined)")

    return "\n".join(lines)


def get_all_criteria_ids(page: str) -> list[str]:
    """Get all criterion IDs for a page (including global and sidebar)."""
    page_specific, global_criteria = get_criteria_for_page(page)
    ids = [c.id for c in global_criteria] + [c.id for c in page_specific]

    # Include sidebar criteria for non-dashboard pages
    if page != "dashboard":
        ids.extend([c.id for c in SIDEBAR_CRITERIA])

    return ids


def get_status_color(status: str) -> Optional[str]:
    """Get the hex color for a status."""
    return STATUS_COLORS.get(status)


def get_all_status_colors() -> dict[str, str]:
    """Get all status colors."""
    return STATUS_COLORS.copy()
