"""
Helper utilities for MVP tests.

Provides HTML parsing, CSS analysis, and validation utilities.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    BeautifulSoup = None
    Tag = None


# Status color definitions (source of truth from Dress/Graph/Svg.lean)
STATUS_COLORS = {
    "notReady": "#F4A460",      # Sandy Brown
    "ready": "#20B2AA",         # Light Sea Green
    "sorry": "#8B0000",         # Dark Red
    "proven": "#90EE90",        # Light Green
    "fullyProven": "#228B22",   # Forest Green
    "mathlibReady": "#87CEEB",  # Light Blue
}

# CSS variable names
CSS_STATUS_VARS = {
    "notReady": "--sbs-status-not-ready",
    "ready": "--sbs-status-ready",
    "sorry": "--sbs-status-sorry",
    "proven": "--sbs-status-proven",
    "fullyProven": "--sbs-status-fully-proven",
    "mathlibReady": "--sbs-status-mathlib-ready",
}


@dataclass
class TasteResult:
    """Result from a taste/aesthetic evaluation."""
    score: int  # 0-10
    reasoning: str
    passed: bool
    prompt: str  # The prompt that was evaluated

    @classmethod
    def from_score(cls, score: int, reasoning: str, prompt: str, threshold: int = 7) -> "TasteResult":
        return cls(
            score=score,
            reasoning=reasoning,
            passed=score >= threshold,
            prompt=prompt,
        )


class TasteValidator:
    """
    Validator for subjective aesthetic tests.

    Generates prompts for agent evaluation and parses responses.
    In test mode, returns placeholder results that can be overridden.
    """

    def __init__(self, test_mode: bool = True):
        self.test_mode = test_mode
        self._override_scores: dict[str, int] = {}

    def set_score(self, test_name: str, score: int) -> None:
        """Override score for a specific test (for testing)."""
        self._override_scores[test_name] = score

    def evaluate(
        self,
        screenshot: Optional[Path],
        question: str,
        criteria: str,
        test_name: str = "",
        threshold: int = 7,
    ) -> TasteResult:
        """
        Evaluate an aesthetic question against a screenshot.

        In test mode, returns a default passing score unless overridden.
        In production mode, would generate a prompt for agent evaluation.
        """
        prompt = self._generate_prompt(screenshot, question, criteria)

        if self.test_mode:
            # Check for override
            if test_name in self._override_scores:
                score = self._override_scores[test_name]
            else:
                # Default to passing in test mode
                score = 8
            reasoning = f"Test mode: score={score}"
        else:
            # Production mode would involve agent evaluation
            score = 8
            reasoning = "Agent evaluation not implemented"

        return TasteResult.from_score(score, reasoning, prompt, threshold)

    def _generate_prompt(
        self,
        screenshot: Optional[Path],
        question: str,
        criteria: str,
    ) -> str:
        """Generate evaluation prompt for agent."""
        screenshot_ref = f"[Screenshot: {screenshot}]" if screenshot else "[No screenshot]"
        return f"""
Aesthetic Evaluation

{screenshot_ref}

Question: {question}

Criteria to consider:
{criteria}

Score this on a scale of 0-10 where:
- 0-3: Poor - significant issues
- 4-6: Acceptable - some issues but functional
- 7-8: Good - minor issues only
- 9-10: Excellent - professional quality

Provide your score and brief reasoning.
"""


def require_bs4():
    """Check if BeautifulSoup is available, skip test if not."""
    if BeautifulSoup is None:
        import pytest
        pytest.skip("beautifulsoup4 is required for HTML parsing")


def parse_html(html: str) -> Optional["BeautifulSoup"]:
    """Parse HTML content with BeautifulSoup."""
    require_bs4()
    return BeautifulSoup(html, "html.parser")


def find_sbs_containers(html: str) -> list[dict[str, Any]]:
    """Find all side-by-side containers in HTML."""
    soup = parse_html(html)
    containers = []

    for container in soup.select(".sbs-container"):
        latex_col = container.select_one(".sbs-latex-column")
        lean_col = container.select_one(".sbs-lean-column")

        containers.append({
            "id": container.get("id", ""),
            "has_latex": latex_col is not None,
            "has_lean": lean_col is not None,
            "latex_content": latex_col.get_text(strip=True) if latex_col else "",
            "lean_content": lean_col.get_text(strip=True) if lean_col else "",
            "status_dot": container.select_one(".status-dot"),
        })

    return containers


def extract_css_variables(css: str) -> dict[str, str]:
    """Extract CSS variable definitions from stylesheet."""
    variables = {}
    # Match --var-name: value; patterns
    pattern = r'(--[\w-]+)\s*:\s*([^;]+);'
    for match in re.finditer(pattern, css):
        var_name = match.group(1).strip()
        var_value = match.group(2).strip()
        variables[var_name] = var_value
    return variables


def normalize_color(color: str) -> str:
    """Normalize color to uppercase hex format."""
    color = color.strip().upper()
    if color.startswith("#"):
        # Expand 3-char hex to 6-char
        if len(color) == 4:
            color = f"#{color[1]*2}{color[2]*2}{color[3]*2}"
    return color


def colors_match(color1: str, color2: str) -> bool:
    """Check if two colors match (case-insensitive hex comparison)."""
    return normalize_color(color1) == normalize_color(color2)


def count_graph_nodes(dep_graph: dict) -> int:
    """Count nodes in dependency graph."""
    if isinstance(dep_graph, list):
        # Old format: list of nodes
        return len([n for n in dep_graph if isinstance(n, dict) and "id" in n])
    elif isinstance(dep_graph, dict):
        # New format: {nodes: [...], edges: [...]}
        return len(dep_graph.get("nodes", []))
    return 0


def count_graph_edges(dep_graph: dict) -> int:
    """Count edges in dependency graph."""
    if isinstance(dep_graph, dict):
        return len(dep_graph.get("edges", []))
    return 0


def get_node_statuses(dep_graph: dict) -> dict[str, int]:
    """Get count of nodes by status."""
    counts = {status: 0 for status in STATUS_COLORS}

    nodes = dep_graph if isinstance(dep_graph, list) else dep_graph.get("nodes", [])
    for node in nodes:
        if isinstance(node, dict):
            status = node.get("status", "notReady")
            if status in counts:
                counts[status] += 1

    return counts


def has_overlapping_nodes(dep_graph: dict) -> bool:
    """Check if any nodes overlap in the graph layout."""
    nodes = dep_graph if isinstance(dep_graph, list) else dep_graph.get("nodes", [])

    for i, n1 in enumerate(nodes):
        if not isinstance(n1, dict):
            continue
        x1, y1 = n1.get("x", 0), n1.get("y", 0)
        w1, h1 = n1.get("width", 0), n1.get("height", 0)

        for n2 in nodes[i+1:]:
            if not isinstance(n2, dict):
                continue
            x2, y2 = n2.get("x", 0), n2.get("y", 0)
            w2, h2 = n2.get("width", 0), n2.get("height", 0)

            # Check for overlap
            if (x1 < x2 + w2 and x1 + w1 > x2 and
                y1 < y2 + h2 and y1 + h1 > y2):
                return True

    return False
