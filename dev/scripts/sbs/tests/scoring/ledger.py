"""
Quality score ledger for T1-T8 metrics.

Provides persistent storage for quality scores with repo-change invalidation.
Mirrors the pattern from compliance/ledger_ops.py but for quality metrics.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sbs.core.utils import get_sbs_root, log


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class MetricScore:
    """Score for a single quality metric (T1-T8)."""

    metric_id: str
    value: float
    passed: bool
    evaluated_at: str
    repo_commits: dict[str, str] = field(default_factory=dict)  # Commits at evaluation time
    stale: bool = False
    findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "metric_id": self.metric_id,
            "value": self.value,
            "passed": self.passed,
            "evaluated_at": self.evaluated_at,
            "repo_commits": self.repo_commits,
            "stale": self.stale,
            "findings": self.findings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MetricScore:
        """Create from JSON dict."""
        return cls(
            metric_id=data.get("metric_id", ""),
            value=data.get("value", 0.0),
            passed=data.get("passed", False),
            evaluated_at=data.get("evaluated_at", ""),
            repo_commits=data.get("repo_commits", {}),
            stale=data.get("stale", False),
            findings=data.get("findings", []),
        )


@dataclass
class ScoreSnapshot:
    """Historical snapshot of overall quality score."""

    timestamp: str
    overall_score: float
    scores: dict[str, float] = field(default_factory=dict)  # metric_id -> score

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "timestamp": self.timestamp,
            "overall_score": self.overall_score,
            "scores": self.scores,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScoreSnapshot:
        """Create from JSON dict."""
        return cls(
            timestamp=data.get("timestamp", ""),
            overall_score=data.get("overall_score", 0.0),
            scores=data.get("scores", {}),
        )


@dataclass
class QualityScoreLedger:
    """Persistent storage for quality scores with change tracking."""

    version: str = "1.0"
    project: str = ""
    repo_commits: dict[str, str] = field(default_factory=dict)  # Current commits
    scores: dict[str, MetricScore] = field(default_factory=dict)  # metric_id -> score
    overall_score: float = 0.0
    last_evaluated: str = ""
    history: list[ScoreSnapshot] = field(default_factory=list)  # Last 20 snapshots

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "version": self.version,
            "project": self.project,
            "repo_commits": self.repo_commits,
            "scores": {k: v.to_dict() for k, v in self.scores.items()},
            "overall_score": self.overall_score,
            "last_evaluated": self.last_evaluated,
            "history": [h.to_dict() for h in self.history[-20:]],  # Keep last 20
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QualityScoreLedger:
        """Create from JSON dict."""
        ledger = cls(
            version=data.get("version", "1.0"),
            project=data.get("project", ""),
            repo_commits=data.get("repo_commits", {}),
            overall_score=data.get("overall_score", 0.0),
            last_evaluated=data.get("last_evaluated", ""),
        )

        # Parse scores
        for metric_id, score_data in data.get("scores", {}).items():
            ledger.scores[metric_id] = MetricScore.from_dict(score_data)

        # Parse history
        for snapshot_data in data.get("history", []):
            ledger.history.append(ScoreSnapshot.from_dict(snapshot_data))

        return ledger

    def recalculate_overall(self) -> None:
        """Recalculate overall score from individual metrics.

        Uses the T1-T8 weights from SCORING_RUBRIC.md:
        - Deterministic (T1, T2, T5, T6): 50% total (10%, 10%, 15%, 15%)
        - Heuristic (T3, T4, T7, T8): 50% total (10%, 10%, 15%, 15%)
        """
        weights = {
            "t1-cli-execution": 0.10,
            "t2-ledger-population": 0.10,
            "t3-dashboard-clarity": 0.10,
            "t4-toggle-discoverability": 0.10,
            "t5-color-match": 0.15,
            "t6-css-coverage": 0.15,
            "t7-jarring": 0.15,
            "t8-professional": 0.15,
        }

        total_weight = 0.0
        weighted_sum = 0.0

        for metric_id, score in self.scores.items():
            if not score.stale and metric_id in weights:
                weight = weights[metric_id]
                weighted_sum += score.value * weight
                total_weight += weight

        if total_weight > 0:
            # weighted_sum contains scores already in 0-100 range
            # Divide by total_weight to get weighted average (no additional *100)
            self.overall_score = round(weighted_sum / total_weight, 2)
        else:
            self.overall_score = 0.0


# =============================================================================
# Paths
# =============================================================================


def get_storage_root() -> Path:
    """Get path to storage directory."""
    return get_sbs_root() / "dev" / "storage"


def get_ledger_path(project: str = "") -> Path:
    """Get path to quality score ledger JSON.

    Args:
        project: If specified, returns per-project path: storage/{project}/quality_ledger.json
                 Otherwise returns global path: storage/quality_ledger.json
    """
    storage = get_storage_root()
    if project:
        return storage / project / "quality_ledger.json"
    return storage / "quality_ledger.json"


def get_status_md_path(project: str = "") -> Path:
    """Get path to quality score markdown report.

    Args:
        project: If specified, returns per-project path: storage/{project}/QUALITY_SCORE.md
                 Otherwise returns global path: storage/QUALITY_SCORE.md
    """
    storage = get_storage_root()
    if project:
        return storage / project / "QUALITY_SCORE.md"
    return storage / "QUALITY_SCORE.md"


# =============================================================================
# Read/Write
# =============================================================================


def load_ledger(project: str = "") -> QualityScoreLedger:
    """Load ledger from disk, or create empty one if not exists.

    Args:
        project: If specified, loads from storage/{project}/quality_ledger.json
                 Otherwise loads from storage/quality_ledger.json
    """
    path = get_ledger_path(project)

    if path.exists():
        try:
            data = json.loads(path.read_text())
            ledger = QualityScoreLedger.from_dict(data)
            return ledger
        except Exception as e:
            log.warning(f"Failed to load quality ledger: {e}")
            return QualityScoreLedger(project=project)

    return QualityScoreLedger(project=project)


def save_ledger(ledger: QualityScoreLedger, project: str = "") -> None:
    """Save ledger to disk (both JSON and Markdown).

    Saves to:
    - storage/{project}/quality_ledger.json (if project specified)
    - storage/{project}/QUALITY_SCORE.md
    """
    # Update timestamp
    ledger.last_evaluated = datetime.now().isoformat()

    # Recalculate overall score
    ledger.recalculate_overall()

    # Ensure directory exists
    json_path = get_ledger_path(project)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    # Save JSON
    json_path.write_text(json.dumps(ledger.to_dict(), indent=2))

    # Save Markdown
    md_path = get_status_md_path(project)
    md_path.write_text(_generate_markdown(ledger))


def _generate_markdown(ledger: QualityScoreLedger) -> str:
    """Generate markdown report from ledger."""
    lines = [
        "# Quality Score Report",
        "",
        f"**Project:** {ledger.project or 'global'} | **Last Evaluated:** {ledger.last_evaluated or 'never'}",
        "",
        f"## Overall Score: {ledger.overall_score:.2f}%",
        "",
    ]

    # Metric weights for reference
    weights = {
        "t1-cli-execution": ("CLI Execution", 10),
        "t2-ledger-population": ("Ledger Population", 10),
        "t3-dashboard-clarity": ("Dashboard Clarity", 10),
        "t4-toggle-discoverability": ("Toggle Discoverability", 10),
        "t5-color-match": ("Status Color Match", 15),
        "t6-css-coverage": ("CSS Variable Coverage", 15),
        "t7-jarring": ("Jarring-Free Check", 15),
        "t8-professional": ("Professional Score", 15),
    }

    # Metrics table
    lines.append("| Metric | Name | Weight | Score | Status |")
    lines.append("|--------|------|--------|-------|--------|")

    for metric_id in sorted(weights.keys()):
        name, weight = weights[metric_id]
        score = ledger.scores.get(metric_id)

        if score:
            status = _status_icon(score)
            value_str = f"{score.value:.1f}"
        else:
            status = "-"
            value_str = "-"

        lines.append(f"| {metric_id} | {name} | {weight}% | {value_str} | {status} |")

    lines.append("")

    # Stale metrics section
    stale = [s for s in ledger.scores.values() if s.stale]
    if stale:
        lines.append("## Stale Metrics")
        lines.append("")
        lines.append("The following metrics need re-evaluation due to repo changes:")
        lines.append("")
        for score in stale:
            lines.append(f"- **{score.metric_id}**: evaluated at {score.evaluated_at}")
        lines.append("")

    # Findings section
    metrics_with_findings = [(k, v) for k, v in ledger.scores.items() if v.findings]
    if metrics_with_findings:
        lines.append("## Findings")
        lines.append("")
        for metric_id, score in sorted(metrics_with_findings):
            lines.append(f"### {metric_id}")
            for finding in score.findings:
                lines.append(f"- {finding}")
            lines.append("")

    # History section
    if ledger.history:
        lines.append("## Score History")
        lines.append("")
        lines.append("| Timestamp | Overall Score |")
        lines.append("|-----------|---------------|")
        for snapshot in ledger.history[-10:]:  # Last 10
            lines.append(f"| {snapshot.timestamp[:19]} | {snapshot.overall_score:.2f}% |")
        lines.append("")

    return "\n".join(lines)


def _status_icon(score: MetricScore) -> str:
    """Get status icon for a metric score."""
    if score.stale:
        return "? (stale)"
    elif score.passed:
        return "PASS"
    else:
        return "FAIL"


# =============================================================================
# Update Operations
# =============================================================================


def update_score(
    ledger: QualityScoreLedger,
    metric_id: str,
    value: float,
    passed: bool,
    findings: list[str],
    repo_commits: dict[str, str],
) -> None:
    """Update the score for a metric.

    Args:
        ledger: The ledger to update
        metric_id: The metric identifier (e.g., "t5-color-match")
        value: The score value (0-100)
        passed: Whether the metric passed
        findings: List of findings/observations
        repo_commits: Current repo commits at evaluation time
    """
    now = datetime.now().isoformat()

    ledger.scores[metric_id] = MetricScore(
        metric_id=metric_id,
        value=value,
        passed=passed,
        evaluated_at=now,
        repo_commits=repo_commits,
        stale=False,
        findings=findings,
    )

    # Update repo commits
    ledger.repo_commits = repo_commits

    # Recalculate overall
    ledger.recalculate_overall()


def add_snapshot(ledger: QualityScoreLedger) -> None:
    """Add a snapshot of current scores to history."""
    snapshot = ScoreSnapshot(
        timestamp=datetime.now().isoformat(),
        overall_score=ledger.overall_score,
        scores={k: v.value for k, v in ledger.scores.items() if not v.stale},
    )
    ledger.history.append(snapshot)

    # Keep last 20
    if len(ledger.history) > 20:
        ledger.history = ledger.history[-20:]


def get_stale_metrics(ledger: QualityScoreLedger) -> list[str]:
    """Get list of metric IDs that are marked stale."""
    return [k for k, v in ledger.scores.items() if v.stale]


def get_pending_metrics(ledger: QualityScoreLedger) -> list[str]:
    """Get list of metric IDs that need evaluation.

    Includes metrics that are stale or have never been evaluated.
    """
    all_metrics = [
        "t1-cli-execution",
        "t2-ledger-population",
        "t3-dashboard-clarity",
        "t4-toggle-discoverability",
        "t5-color-match",
        "t6-css-coverage",
        "t7-jarring",
        "t8-professional",
    ]

    pending = []
    for metric_id in all_metrics:
        score = ledger.scores.get(metric_id)
        if score is None or score.stale:
            pending.append(metric_id)

    return pending
