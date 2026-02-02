"""Rubric-based validation.

Evaluates a project against a user-defined rubric, producing a weighted overall
score based on individual metric results. The rubric must be loaded before
validation can proceed.

Metric IDs are mapped to validators via METRIC_VALIDATOR_MAP. Supported metrics:
- t3-dashboard-clarity: AI-based dashboard clarity check
- t4-toggle-discoverability: AI-based toggle findability check
- t5-color-match: Deterministic status color verification
- t6-css-coverage: Deterministic CSS variable coverage
- t7-jarring: AI-based jarring element detection
- t8-professional: AI-based professional polish assessment
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from .base import BaseValidator, ValidationContext, ValidatorResult
from .registry import register_validator, registry, discover_validators

if TYPE_CHECKING:
    from sbs.tests.rubrics.rubric import MetricResult, Rubric, RubricEvaluation, RubricMetric

log = logging.getLogger(__name__)

# Default paths
RUBRICS_DIR = Path(__file__).parent.parent.parent.parent / "storage" / "rubrics"


# =============================================================================
# Metric to Validator Mapping
# =============================================================================

# Maps rubric metric IDs to validator names in the registry.
# Deterministic validators (T5, T6) run directly.
# AI-based validators (T3, T4, T7, T8) require ai_responses in context.extra.
METRIC_VALIDATOR_MAP: dict[str, str] = {
    # Deterministic validators
    "t5-color-match": "status-color-match",
    "t6-css-coverage": "css-variable-coverage",
    # AI-based validators
    "t3-dashboard-clarity": "dashboard-clarity",
    "t4-toggle-discoverability": "toggle-discoverability",
    "t7-jarring": "jarring-check",
    "t8-professional": "professional-score",
}

# Validators that require AI responses to produce real results
AI_VALIDATORS = {
    "dashboard-clarity",
    "toggle-discoverability",
    "jarring-check",
    "professional-score",
}


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
        from sbs.tests.rubrics.rubric import Rubric

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
        from sbs.tests.rubrics.rubric import Rubric

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
        from sbs.tests.rubrics.rubric import RubricEvaluation

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
        """Evaluate a single metric by dispatching to the appropriate validator.

        Looks up the validator for this metric in METRIC_VALIDATOR_MAP and
        invokes it. For AI-based validators, checks if ai_responses are
        provided in context.extra; if not, returns a result indicating
        AI evaluation is needed.

        Args:
            metric: The metric to evaluate
            context: Validation context

        Returns:
            MetricResult with score and findings
        """
        from sbs.tests.rubrics.rubric import MetricResult

        log.debug(f"Evaluating metric: {metric.id}")

        # Look up validator for this metric
        validator_name = METRIC_VALIDATOR_MAP.get(metric.id)

        if not validator_name:
            # No validator mapped for this metric
            return MetricResult(
                metric_id=metric.id,
                value=0.0,
                passed=False,
                findings=[
                    f"No validator mapped for metric '{metric.id}'. "
                    f"Available metrics: {', '.join(sorted(METRIC_VALIDATOR_MAP.keys()))}"
                ],
                evaluated_at=datetime.now().isoformat(),
            )

        # Ensure validators are discovered
        if validator_name not in registry:
            discover_validators()

        # Get the validator
        validator = registry.get(validator_name)
        if not validator:
            return MetricResult(
                metric_id=metric.id,
                value=0.0,
                passed=False,
                findings=[
                    f"Validator '{validator_name}' not found in registry. "
                    f"Available validators: {', '.join(registry.list_names())}"
                ],
                evaluated_at=datetime.now().isoformat(),
            )

        # Check if this is an AI validator without responses
        if validator_name in AI_VALIDATORS:
            ai_responses = context.extra.get("ai_responses")
            if not ai_responses:
                return MetricResult(
                    metric_id=metric.id,
                    value=0.0,
                    passed=False,
                    findings=[
                        f"AI validator '{validator_name}' requires ai_responses in context. "
                        "Run with --interactive or provide AI responses manually."
                    ],
                    evaluated_at=datetime.now().isoformat(),
                )

        # Run the validator
        try:
            result = validator.validate(context)
        except Exception as e:
            log.exception(f"Validator {validator_name} raised exception")
            return MetricResult(
                metric_id=metric.id,
                value=0.0,
                passed=False,
                findings=[f"Validator error: {e}"],
                evaluated_at=datetime.now().isoformat(),
            )

        # Extract score from validator result
        # Different validators report scores differently
        value = self._extract_score(validator_name, result, metric)
        passed = result.passed if metric.scoring_type == "pass_fail" else value >= metric.threshold

        return MetricResult(
            metric_id=metric.id,
            value=value,
            passed=passed,
            findings=result.findings,
            evaluated_at=datetime.now().isoformat(),
        )

    def _extract_score(
        self, validator_name: str, result: ValidatorResult, metric: RubricMetric
    ) -> float:
        """Extract a normalized score from a validator result.

        Different validators report their results in different ways.
        This method normalizes them to a 0.0-1.0 scale.

        Args:
            validator_name: Name of the validator
            result: The validator result
            metric: The metric being evaluated (for scoring_type)

        Returns:
            Normalized score between 0.0 and 1.0
        """
        # For pass/fail metrics, return 1.0 for pass, 0.0 for fail
        if metric.scoring_type == "pass_fail":
            return 1.0 if result.passed else 0.0

        # Check metrics dict for specific score fields
        metrics = result.metrics

        # CSS variable coverage returns "coverage"
        if "coverage" in metrics:
            return float(metrics["coverage"])

        # Color match returns colors_matched / colors_checked
        if "colors_matched" in metrics and "colors_checked" in metrics:
            checked = metrics["colors_checked"]
            if checked > 0:
                return float(metrics["colors_matched"]) / float(checked)
            return 1.0 if result.passed else 0.0

        # AI validators return confidence or questions_passed/questions_total
        if "confidence" in metrics:
            # For AI validators, use passed status * confidence
            if result.passed:
                return float(metrics.get("confidence", 1.0))
            return 0.0

        if "questions_passed" in metrics and "questions_total" in metrics:
            total = metrics["questions_total"]
            if total > 0:
                return float(metrics["questions_passed"]) / float(total)

        # Default: binary based on passed
        return 1.0 if result.passed else 0.0

    def get_evaluation(self) -> Optional[RubricEvaluation]:
        """Get the most recent evaluation as a RubricEvaluation object.

        Returns:
            RubricEvaluation if validate() was called, None otherwise
        """
        return self._last_evaluation
