"""Rubric data model and CLI commands for quality evaluation.

This module provides:
- RubricMetric: Individual metric definitions
- MetricResult: Results from evaluating a metric
- Rubric: Complete rubric with categories and metrics
- RubricEvaluation: Results of evaluating against a rubric
- RubricIndex: Registry of available rubrics
- cmd_rubric: CLI command handler
"""

from .rubric import (
    MetricResult,
    Rubric,
    RubricEvaluation,
    RubricIndex,
    RubricMetric,
)
from .cmd import (
    RUBRICS_DIR,
    INDEX_PATH,
    cmd_rubric,
    cmd_rubric_create,
    cmd_rubric_show,
    cmd_rubric_list,
    cmd_rubric_evaluate,
    cmd_rubric_delete,
)

__all__ = [
    # Data model
    "RubricMetric",
    "MetricResult",
    "Rubric",
    "RubricEvaluation",
    "RubricIndex",
    # CLI
    "RUBRICS_DIR",
    "INDEX_PATH",
    "cmd_rubric",
    "cmd_rubric_create",
    "cmd_rubric_show",
    "cmd_rubric_list",
    "cmd_rubric_evaluate",
    "cmd_rubric_delete",
]
