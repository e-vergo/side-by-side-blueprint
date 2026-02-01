"""
Design validators package.

Provides validators for design system consistency checks, including:
- CSS parsing utilities
- Status color matching against canonical Lean definitions
- CSS variable coverage validation
- Jarring element detection (AI-powered)
- Contrast ratio validation (future)
"""

from .css_parser import (
    ColorValue,
    CSSRule,
    extract_color_values,
    extract_css_variables,
    parse_css_file,
)
from .color_match import StatusColorValidator, CANONICAL_COLORS
from .variable_coverage import (
    CSSVariableCoverageValidator,
    ColorUsage,
    extract_color_usages,
    is_named_color,
)
from .jarring_check import JarringCheckValidator, JARRING_CHECK_PROMPT
from .dashboard_clarity import DashboardClarityValidator, DASHBOARD_CLARITY_PROMPT
from .toggle_discoverability import ToggleDiscoverabilityValidator, TOGGLE_DISCOVERABILITY_PROMPT
from .professional_score import ProfessionalScoreValidator, PROFESSIONAL_SCORE_PROMPT

__all__ = [
    # CSS parser utilities
    "CSSRule",
    "ColorValue",
    "parse_css_file",
    "extract_css_variables",
    "extract_color_values",
    # Color match validator
    "StatusColorValidator",
    "CANONICAL_COLORS",
    # Variable coverage validator
    "CSSVariableCoverageValidator",
    "ColorUsage",
    "extract_color_usages",
    "is_named_color",
    # Jarring check validator
    "JarringCheckValidator",
    "JARRING_CHECK_PROMPT",
    # Dashboard clarity validator
    "DashboardClarityValidator",
    "DASHBOARD_CLARITY_PROMPT",
    # Toggle discoverability validator
    "ToggleDiscoverabilityValidator",
    "TOGGLE_DISCOVERABILITY_PROMPT",
    # Professional score validator
    "ProfessionalScoreValidator",
    "PROFESSIONAL_SCORE_PROMPT",
]
