"""
Core ledger data structures for build metrics tracking.

This module contains the fundamental data structures shared across the sbs package:
- BuildMetrics: Timing and stats for a single build run
- UnifiedLedger: Single source of truth for all metrics

Compliance-specific types (ComplianceLedger, PageResult, etc.) remain in sbs.ledger.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from sbs.core.utils import log


# =============================================================================
# Data Structures (shared with sbs.ledger for compliance)
# =============================================================================


@dataclass
class InteractionResult:
    """Result for a single interactive state."""

    status: str  # "pass", "fail", "pending", "skipped"
    screenshot: Optional[str] = None
    findings: list[str] = field(default_factory=list)
    last_checked: Optional[str] = None
    confidence: float = 0.0


@dataclass
class PageResult:
    """Result for a page (including interactive states)."""

    status: str  # "pass", "fail", "pending", "skipped"
    screenshot: Optional[str] = None
    findings: list[str] = field(default_factory=list)
    last_checked: Optional[str] = None
    confidence: float = 0.0
    interactions: dict[str, InteractionResult] = field(default_factory=dict)
    needs_revalidation: bool = False


@dataclass
class LedgerSummary:
    """Summary statistics for the ledger."""

    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    pending: int = 0
    skipped: int = 0
    compliance_percent: float = 0.0


@dataclass
class RunStatistics:
    """Statistics for a single compliance run.

    Tracks the meta-level data about our tooling testing itself.
    """

    run_id: str = ""  # ISO timestamp
    project: str = ""
    commit: str = ""

    # Criteria stats
    total_criteria: int = 0
    criteria_by_category: dict[str, int] = field(default_factory=dict)

    # Validation stats
    pages_checked: int = 0
    pages_passed: int = 0
    pages_failed: int = 0
    pages_skipped: int = 0

    # Interactive stats
    interactive_states_checked: int = 0
    interactive_states_passed: int = 0

    # Screenshot stats
    screenshots_captured: int = 0
    interactive_screenshots: int = 0

    # Iteration stats (for compliance loops)
    iteration_number: int = 1
    iterations_to_compliance: int = 0  # 0 = not yet compliant

    # Agent stats (when validation agents are used)
    validation_agents_spawned: int = 0

    # Outcome
    final_compliance_percent: float = 0.0
    achieved_100_percent: bool = False


@dataclass
class HistoricalStats:
    """Aggregate statistics across all runs.

    The "Hall of Fame" for our strange loops.
    """

    total_runs: int = 0
    total_pages_validated: int = 0
    total_screenshots_captured: int = 0
    total_agents_spawned: int = 0

    # Records
    best_first_run_compliance: float = 0.0  # Best % on first iteration
    fastest_to_100_percent: int = 0  # Fewest iterations to 100%
    most_iterations_needed: int = 0

    # Streaks
    consecutive_100_percent_runs: int = 0
    current_streak: int = 0

    # Dates
    first_run_date: str = ""
    last_run_date: str = ""
    last_100_percent_date: str = ""


# =============================================================================
# Build Metrics
# =============================================================================


@dataclass
class BuildMetrics:
    """Timing and stats for a single build run."""

    run_id: str = ""
    project: str = ""
    commit: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0

    # Phase timings
    phase_timings: dict[str, float] = field(default_factory=dict)

    # Git state
    repos_changed: list[str] = field(default_factory=list)
    commits_before: dict[str, str] = field(default_factory=dict)
    commits_after: dict[str, str] = field(default_factory=dict)
    total_files_changed: int = 0
    total_lines_added: int = 0
    total_lines_deleted: int = 0

    # Code stats
    loc_by_language: dict[str, int] = field(default_factory=dict)
    file_counts: dict[str, int] = field(default_factory=dict)

    # Build outcome
    success: bool = False
    error_message: Optional[str] = None


# =============================================================================
# Unified Ledger
# =============================================================================


@dataclass
class UnifiedLedger:
    """Single source of truth for all metrics.

    Combines build metrics with compliance tracking in one structure.
    """

    version: str = "2.0"
    project: str = ""

    # Build tracking
    current_build: Optional[BuildMetrics] = None
    build_history: list[BuildMetrics] = field(default_factory=list)

    # Compliance tracking (existing types)
    pages: dict[str, PageResult] = field(default_factory=dict)
    summary: LedgerSummary = field(default_factory=LedgerSummary)

    # Run statistics (existing types)
    current_run: Optional[RunStatistics] = None
    run_history: list[RunStatistics] = field(default_factory=list)
    lifetime_stats: HistoricalStats = field(default_factory=HistoricalStats)

    # Validator results
    validator_results: dict[str, Any] = field(default_factory=dict)

    # Rubric evaluations (quality scoring history)
    rubric_evaluations: list[dict] = field(default_factory=list)

    def add_build(self, build: BuildMetrics) -> None:
        """Add build to history, keeping last 20."""
        self.current_build = build
        self.build_history.append(build)
        if len(self.build_history) > 20:
            self.build_history = self.build_history[-20:]

    def add_rubric_evaluation(self, evaluation_dict: dict) -> None:
        """Add a rubric evaluation to history, keeping last 20.

        Args:
            evaluation_dict: The RubricEvaluation.to_dict() result
        """
        self.rubric_evaluations.append(evaluation_dict)
        if len(self.rubric_evaluations) > 20:
            self.rubric_evaluations = self.rubric_evaluations[-20:]

    def get_build(self, run_id: str) -> Optional[BuildMetrics]:
        """Get build by run_id."""
        for build in self.build_history:
            if build.run_id == run_id:
                return build
        return None

    def save(self, path: Path) -> None:
        """Save to JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_serialize_unified_ledger(self), indent=2))

    @classmethod
    def load(cls, path: Path) -> "UnifiedLedger":
        """Load from JSON."""
        if path.exists():
            try:
                data = json.loads(path.read_text())
                return _deserialize_unified_ledger(data)
            except Exception as e:
                log.warning(f"Failed to load unified ledger: {e}")
        return cls()


# =============================================================================
# Serialization
# =============================================================================


def _serialize_run_stats(stats: RunStatistics) -> dict:
    """Convert RunStatistics to JSON-serializable dict."""
    return {
        "run_id": stats.run_id,
        "project": stats.project,
        "commit": stats.commit,
        "total_criteria": stats.total_criteria,
        "criteria_by_category": stats.criteria_by_category,
        "pages_checked": stats.pages_checked,
        "pages_passed": stats.pages_passed,
        "pages_failed": stats.pages_failed,
        "pages_skipped": stats.pages_skipped,
        "interactive_states_checked": stats.interactive_states_checked,
        "interactive_states_passed": stats.interactive_states_passed,
        "screenshots_captured": stats.screenshots_captured,
        "interactive_screenshots": stats.interactive_screenshots,
        "iteration_number": stats.iteration_number,
        "iterations_to_compliance": stats.iterations_to_compliance,
        "validation_agents_spawned": stats.validation_agents_spawned,
        "final_compliance_percent": stats.final_compliance_percent,
        "achieved_100_percent": stats.achieved_100_percent,
    }


def _deserialize_run_stats(data: dict) -> RunStatistics:
    """Convert JSON dict to RunStatistics."""
    return RunStatistics(
        run_id=data.get("run_id", ""),
        project=data.get("project", ""),
        commit=data.get("commit", ""),
        total_criteria=data.get("total_criteria", 0),
        criteria_by_category=data.get("criteria_by_category", {}),
        pages_checked=data.get("pages_checked", 0),
        pages_passed=data.get("pages_passed", 0),
        pages_failed=data.get("pages_failed", 0),
        pages_skipped=data.get("pages_skipped", 0),
        interactive_states_checked=data.get("interactive_states_checked", 0),
        interactive_states_passed=data.get("interactive_states_passed", 0),
        screenshots_captured=data.get("screenshots_captured", 0),
        interactive_screenshots=data.get("interactive_screenshots", 0),
        iteration_number=data.get("iteration_number", 1),
        iterations_to_compliance=data.get("iterations_to_compliance", 0),
        validation_agents_spawned=data.get("validation_agents_spawned", 0),
        final_compliance_percent=data.get("final_compliance_percent", 0.0),
        achieved_100_percent=data.get("achieved_100_percent", False),
    )


def _deserialize_historical_stats(data: dict) -> HistoricalStats:
    """Convert JSON dict to HistoricalStats."""
    return HistoricalStats(
        total_runs=data.get("total_runs", 0),
        total_pages_validated=data.get("total_pages_validated", 0),
        total_screenshots_captured=data.get("total_screenshots_captured", 0),
        total_agents_spawned=data.get("total_agents_spawned", 0),
        best_first_run_compliance=data.get("best_first_run_compliance", 0.0),
        fastest_to_100_percent=data.get("fastest_to_100_percent", 0),
        most_iterations_needed=data.get("most_iterations_needed", 0),
        consecutive_100_percent_runs=data.get("consecutive_100_percent_runs", 0),
        current_streak=data.get("current_streak", 0),
        first_run_date=data.get("first_run_date", ""),
        last_run_date=data.get("last_run_date", ""),
        last_100_percent_date=data.get("last_100_percent_date", ""),
    )


def _serialize_build_metrics(metrics: BuildMetrics) -> dict:
    """Convert BuildMetrics to JSON-serializable dict."""
    return {
        "run_id": metrics.run_id,
        "project": metrics.project,
        "commit": metrics.commit,
        "started_at": metrics.started_at,
        "completed_at": metrics.completed_at,
        "duration_seconds": metrics.duration_seconds,
        "phase_timings": metrics.phase_timings,
        "repos_changed": metrics.repos_changed,
        "commits_before": metrics.commits_before,
        "commits_after": metrics.commits_after,
        "total_files_changed": metrics.total_files_changed,
        "total_lines_added": metrics.total_lines_added,
        "total_lines_deleted": metrics.total_lines_deleted,
        "loc_by_language": metrics.loc_by_language,
        "file_counts": metrics.file_counts,
        "success": metrics.success,
        "error_message": metrics.error_message,
    }


def _deserialize_build_metrics(data: dict) -> BuildMetrics:
    """Convert JSON dict to BuildMetrics."""
    return BuildMetrics(
        run_id=data.get("run_id", ""),
        project=data.get("project", ""),
        commit=data.get("commit", ""),
        started_at=data.get("started_at", ""),
        completed_at=data.get("completed_at", ""),
        duration_seconds=data.get("duration_seconds", 0.0),
        phase_timings=data.get("phase_timings", {}),
        repos_changed=data.get("repos_changed", []),
        commits_before=data.get("commits_before", {}),
        commits_after=data.get("commits_after", {}),
        total_files_changed=data.get("total_files_changed", 0),
        total_lines_added=data.get("total_lines_added", 0),
        total_lines_deleted=data.get("total_lines_deleted", 0),
        loc_by_language=data.get("loc_by_language", {}),
        file_counts=data.get("file_counts", {}),
        success=data.get("success", False),
        error_message=data.get("error_message"),
    )


def _serialize_unified_ledger(ledger: UnifiedLedger) -> dict:
    """Convert UnifiedLedger to JSON-serializable dict."""
    data: dict[str, Any] = {
        "version": ledger.version,
        "project": ledger.project,
        # Build tracking
        "current_build": (
            _serialize_build_metrics(ledger.current_build)
            if ledger.current_build else None
        ),
        "build_history": [
            _serialize_build_metrics(b) for b in ledger.build_history[-20:]
        ],
        # Compliance tracking
        "pages": {},
        "summary": asdict(ledger.summary),
        # Run statistics
        "current_run": (
            _serialize_run_stats(ledger.current_run)
            if ledger.current_run else None
        ),
        "run_history": [_serialize_run_stats(r) for r in ledger.run_history[-20:]],
        "lifetime_stats": asdict(ledger.lifetime_stats),
        # Validator results
        "validator_results": ledger.validator_results,
        # Rubric evaluations
        "rubric_evaluations": ledger.rubric_evaluations[-20:],
    }

    # Serialize pages
    for page_name, page_result in ledger.pages.items():
        page_data = {
            "status": page_result.status,
            "screenshot": page_result.screenshot,
            "findings": page_result.findings,
            "last_checked": page_result.last_checked,
            "confidence": page_result.confidence,
            "needs_revalidation": page_result.needs_revalidation,
            "interactions": {},
        }

        for int_name, int_result in page_result.interactions.items():
            page_data["interactions"][int_name] = {
                "status": int_result.status,
                "screenshot": int_result.screenshot,
                "findings": int_result.findings,
                "last_checked": int_result.last_checked,
                "confidence": int_result.confidence,
            }

        data["pages"][page_name] = page_data

    return data


def _deserialize_unified_ledger(data: dict) -> UnifiedLedger:
    """Convert JSON dict to UnifiedLedger."""
    ledger = UnifiedLedger(
        version=data.get("version", "2.0"),
        project=data.get("project", ""),
    )

    # Build tracking
    current_build_data = data.get("current_build")
    if current_build_data:
        ledger.current_build = _deserialize_build_metrics(current_build_data)

    build_history_data = data.get("build_history", [])
    ledger.build_history = [_deserialize_build_metrics(b) for b in build_history_data]

    # Compliance tracking - pages
    for page_name, page_data in data.get("pages", {}).items():
        page_result = PageResult(
            status=page_data.get("status", "pending"),
            screenshot=page_data.get("screenshot"),
            findings=page_data.get("findings", []),
            last_checked=page_data.get("last_checked"),
            confidence=page_data.get("confidence", 0.0),
            needs_revalidation=page_data.get("needs_revalidation", False),
        )

        for int_name, int_data in page_data.get("interactions", {}).items():
            page_result.interactions[int_name] = InteractionResult(
                status=int_data.get("status", "pending"),
                screenshot=int_data.get("screenshot"),
                findings=int_data.get("findings", []),
                last_checked=int_data.get("last_checked"),
                confidence=int_data.get("confidence", 0.0),
            )

        ledger.pages[page_name] = page_result

    # Summary
    summary_data = data.get("summary", {})
    ledger.summary = LedgerSummary(
        total_checks=summary_data.get("total_checks", 0),
        passed=summary_data.get("passed", 0),
        failed=summary_data.get("failed", 0),
        pending=summary_data.get("pending", 0),
        skipped=summary_data.get("skipped", 0),
        compliance_percent=summary_data.get("compliance_percent", 0.0),
    )

    # Run statistics
    current_run_data = data.get("current_run")
    if current_run_data:
        ledger.current_run = _deserialize_run_stats(current_run_data)

    run_history_data = data.get("run_history", [])
    ledger.run_history = [_deserialize_run_stats(r) for r in run_history_data]

    lifetime_data = data.get("lifetime_stats", {})
    if lifetime_data:
        ledger.lifetime_stats = _deserialize_historical_stats(lifetime_data)

    # Validator results
    ledger.validator_results = data.get("validator_results", {})

    # Rubric evaluations (backward compatible - defaults to empty list)
    ledger.rubric_evaluations = data.get("rubric_evaluations", [])

    return ledger


# =============================================================================
# Factory Functions
# =============================================================================


def get_or_create_unified_ledger(stats_dir: Path, project: str) -> UnifiedLedger:
    """Get or create a unified ledger for the given project.

    Args:
        stats_dir: Directory to store the ledger (typically archive/)
        project: Project name for the ledger

    Returns:
        Existing ledger if found, or new empty ledger with project set.
    """
    path = stats_dir / "unified_ledger.json"
    if path.exists():
        ledger = UnifiedLedger.load(path)
        # Update project if it was empty or different
        if not ledger.project:
            ledger.project = project
        return ledger

    # Create new ledger
    ledger = UnifiedLedger(project=project)
    return ledger
