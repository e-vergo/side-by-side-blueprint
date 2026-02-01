"""Rubric data model for quality evaluation and scoring.

This module provides dataclasses for defining quality rubrics, evaluating
projects against them, and tracking results over time.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import uuid


@dataclass
class RubricMetric:
    """A single metric within a rubric.

    Represents one measurable aspect of quality, such as "CSS alignment score"
    or "status color match". Each metric has a threshold that must be met
    for the metric to pass, and a weight that determines its contribution
    to the overall rubric score.

    Attributes:
        id: Unique identifier, e.g., "css-alignment-score"
        name: Human-readable name for display
        description: Detailed explanation of what this metric measures
        category: User-defined category from brainstorm, e.g., "visual", "code"
        threshold: Minimum acceptable value (0.0-1.0 for percentage, varies by type)
        weight: Contribution to overall score, 0.0-1.0
        scoring_type: How values are interpreted: "pass_fail", "percentage", "score_0_10"
    """

    id: str
    name: str
    description: str
    category: str
    threshold: float
    weight: float
    scoring_type: str  # "pass_fail", "percentage", "score_0_10"

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "threshold": self.threshold,
            "weight": self.weight,
            "scoring_type": self.scoring_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RubricMetric":
        """Create a RubricMetric from a dict.

        Handles backward compatibility for missing fields by providing defaults.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            category=data.get("category", "uncategorized"),
            threshold=data.get("threshold", 0.0),
            weight=data.get("weight", 0.0),
            scoring_type=data.get("scoring_type", "percentage"),
        )

    def normalize_value(self, value: float) -> float:
        """Normalize a raw value to 0.0-1.0 scale based on scoring_type.

        Args:
            value: Raw score value

        Returns:
            Normalized value between 0.0 and 1.0
        """
        if self.scoring_type == "pass_fail":
            return 1.0 if value >= self.threshold else 0.0
        elif self.scoring_type == "percentage":
            return min(max(value, 0.0), 1.0)
        elif self.scoring_type == "score_0_10":
            return min(max(value / 10.0, 0.0), 1.0)
        else:
            return value


@dataclass
class MetricResult:
    """Result of evaluating a single metric.

    Captures the raw score, whether the threshold was met, and any
    observations or issues found during evaluation.

    Attributes:
        metric_id: ID of the metric this result is for
        value: Raw score value
        passed: Whether the threshold was met
        findings: List of observations or issues found
        evaluated_at: ISO timestamp of when evaluation occurred
    """

    metric_id: str
    value: float
    passed: bool
    findings: list[str] = field(default_factory=list)
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "metric_id": self.metric_id,
            "value": self.value,
            "passed": self.passed,
            "findings": self.findings,
            "evaluated_at": self.evaluated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MetricResult":
        """Create a MetricResult from a dict.

        Handles backward compatibility for missing fields.
        """
        return cls(
            metric_id=data["metric_id"],
            value=data["value"],
            passed=data["passed"],
            findings=data.get("findings", []),
            evaluated_at=data.get("evaluated_at", datetime.now().isoformat()),
        )


@dataclass
class Rubric:
    """A complete quality rubric with categories and metrics.

    A rubric defines how to evaluate a project's quality. It contains
    multiple metrics organized into categories, each with weights that
    should sum to 1.0.

    Attributes:
        id: Unique identifier (UUID or slugified name)
        name: Human-readable name for the rubric
        version: Semantic version string, e.g., "1.0.0"
        created_at: ISO timestamp of creation
        categories: List of user-defined category names
        metrics: List of RubricMetric instances
    """

    id: str
    name: str
    version: str = "1.0.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    categories: list[str] = field(default_factory=list)
    metrics: list[RubricMetric] = field(default_factory=list)

    @property
    def total_weight(self) -> float:
        """Calculate total weight of all metrics.

        Should sum to 1.0 for a valid rubric.
        """
        return sum(m.weight for m in self.metrics)

    def validate_weights(self) -> tuple[bool, str]:
        """Validate that metric weights sum to 1.0.

        Returns:
            Tuple of (is_valid, message)
        """
        total = self.total_weight
        if abs(total - 1.0) < 0.001:  # Allow small floating point error
            return True, f"Weights sum to {total:.3f}"
        else:
            return False, f"Weights sum to {total:.3f}, expected 1.0"

    def get_metrics_by_category(self, category: str) -> list[RubricMetric]:
        """Get all metrics in a given category."""
        return [m for m in self.metrics if m.category == category]

    def get_metric(self, metric_id: str) -> Optional[RubricMetric]:
        """Get a metric by ID."""
        for m in self.metrics:
            if m.id == metric_id:
                return m
        return None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "created_at": self.created_at,
            "categories": self.categories,
            "metrics": [m.to_dict() for m in self.metrics],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Rubric":
        """Create a Rubric from a dict.

        Handles backward compatibility for missing fields.
        """
        metrics = [RubricMetric.from_dict(m) for m in data.get("metrics", [])]
        return cls(
            id=data["id"],
            name=data["name"],
            version=data.get("version", "1.0.0"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            categories=data.get("categories", []),
            metrics=metrics,
        )

    def to_markdown(self) -> str:
        """Generate human-readable markdown representation.

        Returns:
            Markdown string suitable for documentation or review
        """
        lines = [
            f"# {self.name}",
            "",
            f"**ID:** {self.id}",
            f"**Version:** {self.version}",
            f"**Created:** {self.created_at}",
            "",
        ]

        # Weight validation
        valid, msg = self.validate_weights()
        status = "OK" if valid else "WARNING"
        lines.append(f"**Weight Validation:** {status} ({msg})")
        lines.append("")

        # Metrics by category
        for category in self.categories:
            category_metrics = self.get_metrics_by_category(category)
            if not category_metrics:
                continue

            lines.append(f"## {category.title()}")
            lines.append("")

            for m in category_metrics:
                lines.append(f"### {m.name}")
                lines.append(f"- **ID:** `{m.id}`")
                lines.append(f"- **Description:** {m.description}")
                lines.append(f"- **Type:** {m.scoring_type}")
                lines.append(f"- **Threshold:** {m.threshold}")
                lines.append(f"- **Weight:** {m.weight:.1%}")
                lines.append("")

        # Uncategorized metrics
        uncategorized = [m for m in self.metrics if m.category not in self.categories]
        if uncategorized:
            lines.append("## Uncategorized")
            lines.append("")
            for m in uncategorized:
                lines.append(f"### {m.name}")
                lines.append(f"- **ID:** `{m.id}`")
                lines.append(f"- **Description:** {m.description}")
                lines.append(f"- **Type:** {m.scoring_type}")
                lines.append(f"- **Threshold:** {m.threshold}")
                lines.append(f"- **Weight:** {m.weight:.1%}")
                lines.append("")

        return "\n".join(lines)

    @classmethod
    def create(cls, name: str, categories: Optional[list[str]] = None) -> "Rubric":
        """Create a new rubric with a generated UUID.

        Args:
            name: Human-readable name for the rubric
            categories: Optional list of category names

        Returns:
            New Rubric instance with generated ID and current timestamp
        """
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            categories=categories or [],
        )


@dataclass
class RubricEvaluation:
    """Results of evaluating a project against a rubric.

    Captures the complete evaluation results including individual metric
    results, overall score, and aggregate findings.

    Attributes:
        rubric_id: ID of the rubric used for evaluation
        evaluated_at: ISO timestamp of when evaluation occurred
        evaluator: How evaluation was performed: "manual", "validator", "ai-vision"
        results: Dict mapping metric_id to MetricResult
        overall_score: Weighted average of all metric scores (0.0-1.0)
        passed: Whether all thresholds were met
        findings: Aggregate list of all findings
    """

    rubric_id: str
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    evaluator: str = "manual"  # "manual", "validator", "ai-vision"
    results: dict[str, MetricResult] = field(default_factory=dict)
    overall_score: float = 0.0
    passed: bool = False
    findings: list[str] = field(default_factory=list)

    def add_result(self, result: MetricResult) -> None:
        """Add a metric result to this evaluation."""
        self.results[result.metric_id] = result

    def calculate_score(self, rubric: Rubric) -> float:
        """Calculate overall score from results and rubric weights.

        Args:
            rubric: The rubric used for evaluation (provides weights)

        Returns:
            Weighted average score between 0.0 and 1.0
        """
        if not self.results:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for metric_id, result in self.results.items():
            metric = rubric.get_metric(metric_id)
            if metric is None:
                continue

            normalized = metric.normalize_value(result.value)
            weighted_sum += normalized * metric.weight
            total_weight += metric.weight

        if total_weight == 0.0:
            return 0.0

        return weighted_sum / total_weight

    def update_from_rubric(self, rubric: Rubric) -> None:
        """Recalculate overall_score and passed from current results.

        Args:
            rubric: The rubric used for evaluation
        """
        self.overall_score = self.calculate_score(rubric)
        self.passed = all(r.passed for r in self.results.values())

        # Aggregate findings
        self.findings = []
        for result in self.results.values():
            self.findings.extend(result.findings)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "rubric_id": self.rubric_id,
            "evaluated_at": self.evaluated_at,
            "evaluator": self.evaluator,
            "results": {k: v.to_dict() for k, v in self.results.items()},
            "overall_score": self.overall_score,
            "passed": self.passed,
            "findings": self.findings,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RubricEvaluation":
        """Create a RubricEvaluation from a dict.

        Handles backward compatibility for missing fields.
        """
        results = {
            k: MetricResult.from_dict(v)
            for k, v in data.get("results", {}).items()
        }
        return cls(
            rubric_id=data["rubric_id"],
            evaluated_at=data.get("evaluated_at", datetime.now().isoformat()),
            evaluator=data.get("evaluator", "manual"),
            results=results,
            overall_score=data.get("overall_score", 0.0),
            passed=data.get("passed", False),
            findings=data.get("findings", []),
        )

    def to_markdown(self, rubric: Optional[Rubric] = None) -> str:
        """Generate human-readable markdown representation.

        Args:
            rubric: Optional rubric to include metric names

        Returns:
            Markdown string suitable for documentation or review
        """
        lines = [
            f"# Rubric Evaluation",
            "",
            f"**Rubric ID:** {self.rubric_id}",
            f"**Evaluated At:** {self.evaluated_at}",
            f"**Evaluator:** {self.evaluator}",
            f"**Overall Score:** {self.overall_score:.1%}",
            f"**Passed:** {'Yes' if self.passed else 'No'}",
            "",
            "## Results",
            "",
        ]

        for metric_id, result in self.results.items():
            metric_name = metric_id
            if rubric:
                metric = rubric.get_metric(metric_id)
                if metric:
                    metric_name = metric.name

            status = "PASS" if result.passed else "FAIL"
            lines.append(f"### {metric_name}")
            lines.append(f"- **Status:** {status}")
            lines.append(f"- **Value:** {result.value}")
            if result.findings:
                lines.append("- **Findings:**")
                for finding in result.findings:
                    lines.append(f"  - {finding}")
            lines.append("")

        if self.findings:
            lines.append("## Aggregate Findings")
            lines.append("")
            for finding in self.findings:
                lines.append(f"- {finding}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class RubricIndex:
    """Index of all rubrics with metadata for lookup.

    Provides a registry of available rubrics with their paths,
    supporting CRUD operations and persistence.

    Attributes:
        rubrics: Dict mapping rubric_id to metadata (name, created_at, path)
    """

    version: str = "1.0"
    rubrics: dict[str, dict] = field(default_factory=dict)

    def add_rubric(self, rubric: Rubric, path: str) -> None:
        """Add a rubric to the index.

        Args:
            rubric: The rubric to add
            path: Filesystem path where rubric is stored
        """
        self.rubrics[rubric.id] = {
            "name": rubric.name,
            "version": rubric.version,
            "created_at": rubric.created_at,
            "path": path,
        }

    def remove_rubric(self, rubric_id: str) -> bool:
        """Remove a rubric from the index.

        Args:
            rubric_id: ID of the rubric to remove

        Returns:
            True if rubric was found and removed, False otherwise
        """
        if rubric_id in self.rubrics:
            del self.rubrics[rubric_id]
            return True
        return False

    def get_rubric_path(self, rubric_id: str) -> Optional[str]:
        """Get the filesystem path for a rubric.

        Args:
            rubric_id: ID of the rubric

        Returns:
            Path string if found, None otherwise
        """
        entry = self.rubrics.get(rubric_id)
        if entry:
            return entry.get("path")
        return None

    def list_rubrics(self) -> list[dict]:
        """List all rubrics with their metadata.

        Returns:
            List of dicts with id, name, version, created_at, path
        """
        return [
            {"id": rubric_id, **metadata}
            for rubric_id, metadata in self.rubrics.items()
        ]

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "version": self.version,
            "rubrics": self.rubrics,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RubricIndex":
        """Create a RubricIndex from a dict.

        Handles backward compatibility for missing fields.
        """
        return cls(
            version=data.get("version", "1.0"),
            rubrics=data.get("rubrics", {}),
        )

    def save(self, path: Path) -> None:
        """Save index to JSON file.

        Args:
            path: Filesystem path to save to
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "RubricIndex":
        """Load index from JSON file.

        Args:
            path: Filesystem path to load from

        Returns:
            RubricIndex instance (empty if file doesn't exist)
        """
        if not path.exists():
            return cls()
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)
