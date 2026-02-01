"""Rubric-based validation.

Evaluates a project against a user-defined rubric, producing a weighted overall
score based on individual metric results. The rubric must be loaded before
validation can proceed.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .base import BaseValidator, ValidationContext, ValidatorResult
from .registry import register_validator

if TYPE_CHECKING:
    from ..rubric import MetricResult, Rubric, RubricEvaluation, RubricMetric

log = logging.getLogger(__name__)

# Default paths
RUBRICS_DIR = Path(__file__).parent.parent.parent.parent / "archive" / "rubrics"


@register_validator
class RubricValidator(BaseValidator):
    """Validate against a custom rubric.

    This validator evaluates project state against a user-defined rubric,
    producing a weighted overall score based on individual metric results.

    Usage:
        validator = registry.get("rubric")
        validator.set_rubric(rubric)  # Load rubric first
        result = validator.validate(context)
    """

    def __init__(self) -> None:
        super().__init__("rubric", "code")
        self._rubric: Optional[Rubric] = None
        self._rubric_id: Optional[str] = None
        self._last_evaluation: Optional[RubricEvaluation] = None

    def set_rubric(self, rubric: Rubric) -> None:
        """Configure which rubric to validate against.

        Args:
            rubric: The Rubric object to use for evaluation
        """
        from ..rubric import Rubric

        if not isinstance(rubric, Rubric):
            raise TypeError(f"Expected Rubric, got {type(rubric)}")
        self._rubric = rubric
        self._rubric_id = rubric.id

    def load_rubric(self, rubric_id: str) -> bool:
        """Load a rubric by ID from the archive/rubrics directory.

        Args:
            rubric_id: The rubric ID to load

        Returns:
            True if loaded successfully, False otherwise
        """
        from ..rubric import Rubric

        rubric_path = RUBRICS_DIR / f"{rubric_id}.json"
        if not rubric_path.exists():
            log.error(f"Rubric not found: {rubric_id}")
            return False

        try:
            with open(rubric_path) as f:
                data = json.load(f)
            self._rubric = Rubric.from_dict(data)
            self._rubric_id = rubric_id
            return True
        except Exception as e:
            log.error(f"Failed to load rubric {rubric_id}: {e}")
            return False

    def validate(self, context: ValidationContext) -> ValidatorResult:
        """Evaluate all rubric metrics against current state.

        Args:
            context: Validation context with project info and paths

        Returns:
            ValidatorResult with overall score and per-metric details
        """
        from ..rubric import RubricEvaluation

        if not self._rubric:
            return self._make_fail(
                ["No rubric configured. Call set_rubric() or load_rubric() first."]
            )

        # Create evaluation object
        evaluation = RubricEvaluation(
            rubric_id=self._rubric.id,
            evaluator="validator",
        )

        # Evaluate each metric
        results: dict[str, dict] = {}
        findings: list[str] = []

        for metric in self._rubric.metrics:
            result = self._evaluate_metric(metric, context)
            results[metric.id] = result.to_dict()
            evaluation.add_result(result)

            if not result.passed:
                findings.append(
                    f"{metric.name}: Failed (score: {result.value:.2f}, "
                    f"threshold: {metric.threshold})"
                )

            if result.findings:
                for finding in result.findings:
                    findings.append(f"  - {finding}")

        # Update evaluation with calculated score
        evaluation.update_from_rubric(self._rubric)
        self._last_evaluation = evaluation

        # Calculate overall score
        overall_score = evaluation.overall_score
        passed = evaluation.passed

        return ValidatorResult(
            validator=self.name,
            passed=passed,
            findings=findings if not passed else [],
            metrics={
                "rubric_id": self._rubric_id,
                "overall_score": overall_score,
                "metrics_passed": sum(1 for r in results.values() if r["passed"]),
                "metrics_total": len(results),
            },
            details={
                "rubric_name": self._rubric.name,
                "metric_results": results,
            },
        )

    def _evaluate_metric(
        self, metric: RubricMetric, context: ValidationContext
    ) -> MetricResult:
        """Evaluate a single metric.

        This is a placeholder implementation. In practice, each metric would
        need custom evaluation logic or delegate to specific validators.

        Args:
            metric: The metric to evaluate
            context: Validation context

        Returns:
            MetricResult with score and findings
        """
        from ..rubric import MetricResult

        # Placeholder: try to find a matching validator
        # In real usage, metrics would map to specific validator logic
        log.debug(f"Evaluating metric: {metric.id}")

        # Default: return a placeholder result indicating manual evaluation needed
        return MetricResult(
            metric_id=metric.id,
            value=0.0,
            passed=False,
            findings=[
                f"Metric '{metric.name}' requires manual evaluation "
                "or specific validator integration"
            ],
            evaluated_at=datetime.now().isoformat(),
        )

    def get_evaluation(self) -> Optional[RubricEvaluation]:
        """Get the most recent evaluation as a RubricEvaluation object.

        Returns:
            RubricEvaluation if validate() was called, None otherwise
        """
        return self._last_evaluation
