"""
Compliance ledger management.

Tracks pass/fail status per page in dual format (JSON + Markdown).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .utils import get_sbs_root, get_git_commit, log


# =============================================================================
# Data Classes
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


@dataclass
class ComplianceLedger:
    """The complete compliance ledger."""

    version: str = "1.1"  # Bumped for stats tracking
    last_run: Optional[str] = None
    project: str = ""
    commit: str = ""
    repo_commits: dict[str, str] = field(default_factory=dict)
    pages: dict[str, PageResult] = field(default_factory=dict)
    summary: LedgerSummary = field(default_factory=LedgerSummary)
    history: list[dict] = field(default_factory=list)

    # Statistics tracking (the strange loop meta-data)
    current_run: RunStatistics = field(default_factory=RunStatistics)
    run_history: list[RunStatistics] = field(default_factory=list)  # Last 20 runs
    lifetime_stats: HistoricalStats = field(default_factory=HistoricalStats)


# =============================================================================
# Paths
# =============================================================================

# All archive data lives in archive/ at the repo root:
#   archive/{project}/           - Per-project screenshots and compliance
#   archive/unified_ledger.json  - Cross-project metrics
#   archive/lifetime_stats.json  - Historical statistics
#   archive/charts/              - Generated chart outputs
#   archive/manifests/           - Interaction manifests


def get_archive_root() -> Path:
    """Get path to archive directory (repo root level)."""
    return get_sbs_root() / "archive"


def get_images_dir() -> Path:
    """Get path to images directory (alias for archive root)."""
    return get_archive_root()


def get_project_dir(project: str) -> Path:
    """Get path to project's screenshot/compliance directory."""
    return get_archive_root() / project


def get_ledger_path(project: str = "") -> Path:
    """Get path to compliance ledger JSON.

    If project specified, returns per-project path: archive/{project}/latest/compliance.json
    Otherwise returns global path: archive/compliance_ledger.json
    """
    if project:
        return get_project_dir(project) / "latest" / "compliance.json"
    return get_archive_root() / "compliance_ledger.json"


def get_status_md_path(project: str = "") -> Path:
    """Get path to compliance status markdown.

    If project specified, returns per-project path: archive/{project}/latest/COMPLIANCE.md
    Otherwise returns global path: archive/COMPLIANCE_STATUS.md
    """
    if project:
        return get_project_dir(project) / "latest" / "COMPLIANCE.md"
    return get_archive_root() / "COMPLIANCE_STATUS.md"


def get_lifetime_stats_path() -> Path:
    """Get path to lifetime statistics (cross-project)."""
    archive_dir = get_archive_root()
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir / "lifetime_stats.json"


def get_manifests_dir() -> Path:
    """Get path to interaction manifests directory."""
    manifests_dir = get_archive_root() / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    return manifests_dir


def get_unified_ledger_path() -> Path:
    """Get path to unified ledger JSON (archive/unified_ledger.json)."""
    archive_dir = get_archive_root()
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir / "unified_ledger.json"


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


def _serialize_ledger(ledger: ComplianceLedger) -> dict:
    """Convert ledger to JSON-serializable dict."""
    data = {
        "version": ledger.version,
        "last_run": ledger.last_run,
        "project": ledger.project,
        "commit": ledger.commit,
        "repo_commits": ledger.repo_commits,
        "pages": {},
        "summary": asdict(ledger.summary),
        "history": ledger.history[-10:],  # Keep last 10 entries
        # Statistics
        "current_run": _serialize_run_stats(ledger.current_run),
        "run_history": [_serialize_run_stats(r) for r in ledger.run_history[-20:]],
        "lifetime_stats": asdict(ledger.lifetime_stats),
    }

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


def _deserialize_ledger(data: dict) -> ComplianceLedger:
    """Convert JSON dict to ComplianceLedger."""
    ledger = ComplianceLedger(
        version=data.get("version", "1.0"),
        last_run=data.get("last_run"),
        project=data.get("project", ""),
        commit=data.get("commit", ""),
        repo_commits=data.get("repo_commits", {}),
        history=data.get("history", []),
    )

    # Parse summary
    summary_data = data.get("summary", {})
    ledger.summary = LedgerSummary(
        total_checks=summary_data.get("total_checks", 0),
        passed=summary_data.get("passed", 0),
        failed=summary_data.get("failed", 0),
        pending=summary_data.get("pending", 0),
        skipped=summary_data.get("skipped", 0),
        compliance_percent=summary_data.get("compliance_percent", 0.0),
    )

    # Parse pages
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

    # Parse statistics
    current_run_data = data.get("current_run", {})
    if current_run_data:
        ledger.current_run = _deserialize_run_stats(current_run_data)

    run_history_data = data.get("run_history", [])
    ledger.run_history = [_deserialize_run_stats(r) for r in run_history_data]

    lifetime_data = data.get("lifetime_stats", {})
    if lifetime_data:
        ledger.lifetime_stats = _deserialize_historical_stats(lifetime_data)

    return ledger


# =============================================================================
# Read/Write
# =============================================================================


def load_ledger(project: str = "") -> ComplianceLedger:
    """Load ledger from disk, or create empty one if not exists.

    Args:
        project: If specified, loads from archive/{project}/latest/compliance.json
                 Otherwise loads from archive/compliance_ledger.json
    """
    path = get_ledger_path(project)

    if path.exists():
        try:
            data = json.loads(path.read_text())
            ledger = _deserialize_ledger(data)

            # Also load lifetime stats if they exist
            lifetime_path = get_lifetime_stats_path()
            if lifetime_path.exists():
                try:
                    lifetime_data = json.loads(lifetime_path.read_text())
                    ledger.lifetime_stats = _deserialize_historical_stats(lifetime_data)
                except Exception:
                    pass  # Keep defaults if lifetime stats can't be loaded

            return ledger
        except Exception as e:
            log.warning(f"Failed to load ledger: {e}")
            return ComplianceLedger()

    # Try loading just lifetime stats for new project
    ledger = ComplianceLedger()
    lifetime_path = get_lifetime_stats_path()
    if lifetime_path.exists():
        try:
            lifetime_data = json.loads(lifetime_path.read_text())
            ledger.lifetime_stats = _deserialize_historical_stats(lifetime_data)
        except Exception:
            pass

    return ledger


def save_ledger(ledger: ComplianceLedger, project: str = "") -> None:
    """Save ledger to disk (both JSON and Markdown).

    Saves to:
    - archive/{project}/latest/compliance.json (if project specified)
    - archive/{project}/latest/COMPLIANCE.md
    - archive/lifetime_stats.json (always, for cross-project stats)
    """
    # Update timestamp
    ledger.last_run = datetime.now().isoformat()

    # Ensure directory exists
    json_path = get_ledger_path(project)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    # Save JSON
    json_path.write_text(json.dumps(_serialize_ledger(ledger), indent=2))

    # Save Markdown
    md_path = get_status_md_path(project)
    md_path.write_text(_generate_markdown(ledger))

    # Save lifetime stats separately (cross-project)
    save_lifetime_stats(ledger.lifetime_stats)


def save_lifetime_stats(stats: HistoricalStats) -> None:
    """Save lifetime stats to archive/lifetime_stats.json."""
    path = get_lifetime_stats_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(stats), indent=2))


def load_lifetime_stats() -> HistoricalStats:
    """Load lifetime stats from archive/lifetime_stats.json."""
    path = get_lifetime_stats_path()
    if path.exists():
        try:
            data = json.loads(path.read_text())
            return _deserialize_historical_stats(data)
        except Exception:
            pass
    return HistoricalStats()


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


def _generate_markdown(ledger: ComplianceLedger) -> str:
    """Generate markdown report from ledger."""
    lines = [
        "# Visual Compliance Status",
        "",
        f"**Project:** {ledger.project} | **Commit:** {ledger.commit[:12] if ledger.commit else 'unknown'} | **Last Run:** {ledger.last_run or 'never'}",
        "",
    ]

    # Summary
    s = ledger.summary
    if s.total_checks > 0:
        lines.append(f"## Summary: {s.compliance_percent:.1f}% ({s.passed}/{s.total_checks} checks)")
    else:
        lines.append("## Summary: No checks run yet")

    lines.append("")

    # Page table
    lines.append("| Page | Status | Interactive States |")
    lines.append("|------|--------|-------------------|")

    for page_name, page_result in sorted(ledger.pages.items()):
        status_icon = _status_icon(page_result.status)

        # Format interactive states
        int_parts = []
        for int_name, int_result in page_result.interactions.items():
            int_icon = _status_icon(int_result.status)
            int_parts.append(f"{int_name} {int_icon}")

        int_str = ", ".join(int_parts) if int_parts else "-"

        lines.append(f"| {page_name} | {status_icon} | {int_str} |")

    lines.append("")

    # Failures section
    failures = [(name, res) for name, res in ledger.pages.items() if res.status == "fail"]
    if failures:
        lines.append("## Failures")
        lines.append("")

        for page_name, page_result in failures:
            lines.append(f"### {page_name}")

            for finding in page_result.findings:
                lines.append(f"- **Finding:** {finding}")

            for int_name, int_result in page_result.interactions.items():
                if int_result.status == "fail":
                    for finding in int_result.findings:
                        lines.append(f"- **Interactive ({int_name}):** {finding}")

            lines.append("")

    # Statistics section (the strange loop meta-data)
    lines.extend(_generate_stats_markdown(ledger))

    # History section
    if ledger.history:
        lines.append("## Recent Changes")
        lines.append("")
        for entry in ledger.history[-5:]:
            lines.append(f"- {entry.get('date', 'unknown')}: {entry.get('message', '')}")
        lines.append("")

    return "\n".join(lines)


def _generate_stats_markdown(ledger: ComplianceLedger) -> list[str]:
    """Generate the statistics section of the markdown report."""
    lines = []
    stats = ledger.lifetime_stats
    current = ledger.current_run

    # Only show if we have run data
    if stats.total_runs == 0 and not current.run_id:
        return lines

    lines.append("---")
    lines.append("")
    lines.append("## Compliance Statistics")
    lines.append("")
    lines.append("*Tracking the strange loop: our tooling testing itself.*")
    lines.append("")

    # Current run stats
    if current.run_id:
        lines.append("### Current Run")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Run ID | `{current.run_id[:19]}` |")
        lines.append(f"| Iteration | {current.iteration_number} |")
        lines.append(f"| Pages Checked | {current.pages_checked} |")
        lines.append(f"| Screenshots Captured | {current.screenshots_captured} |")
        lines.append(f"| Compliance | {current.final_compliance_percent:.1f}% |")
        if current.achieved_100_percent:
            lines.append(f"| Status | **100% Achieved** |")
        lines.append("")

    # Lifetime stats
    if stats.total_runs > 0:
        lines.append("### Lifetime Statistics")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Runs | {stats.total_runs} |")
        lines.append(f"| Total Pages Validated | {stats.total_pages_validated} |")
        lines.append(f"| Total Screenshots | {stats.total_screenshots_captured} |")
        lines.append(f"| Validation Agents Spawned | {stats.total_agents_spawned} |")
        lines.append("")

        # Records
        lines.append("### Records")
        lines.append("")
        lines.append(f"| Record | Value |")
        lines.append("|--------|-------|")
        if stats.best_first_run_compliance > 0:
            lines.append(f"| Best First-Run Compliance | {stats.best_first_run_compliance:.1f}% |")
        if stats.fastest_to_100_percent > 0:
            lines.append(f"| Fastest to 100% | {stats.fastest_to_100_percent} iteration(s) |")
        if stats.most_iterations_needed > 0:
            lines.append(f"| Most Iterations Needed | {stats.most_iterations_needed} |")
        if stats.consecutive_100_percent_runs > 0:
            lines.append(f"| Best 100% Streak | {stats.consecutive_100_percent_runs} runs |")
        if stats.current_streak > 0:
            lines.append(f"| Current Streak | {stats.current_streak} runs |")
        lines.append("")

        # Dates
        if stats.first_run_date:
            lines.append("### Timeline")
            lines.append("")
            lines.append(f"- **First Run:** {stats.first_run_date}")
            lines.append(f"- **Last Run:** {stats.last_run_date}")
            if stats.last_100_percent_date:
                lines.append(f"- **Last 100%:** {stats.last_100_percent_date}")
            lines.append("")

    return lines


def _status_icon(status: str) -> str:
    """Convert status to icon."""
    icons = {
        "pass": "\u2713",  # checkmark
        "fail": "\u2717",  # x mark
        "pending": "\u25cb",  # circle
        "skipped": "\u2014",  # em dash
    }
    return icons.get(status, "?")


# =============================================================================
# Update Operations
# =============================================================================


def update_page_result(
    ledger: ComplianceLedger,
    page: str,
    status: str,
    findings: list[str],
    screenshot: Optional[str] = None,
    confidence: float = 0.0,
) -> None:
    """Update the result for a page."""
    now = datetime.now().isoformat()

    if page not in ledger.pages:
        ledger.pages[page] = PageResult(status="pending")

    result = ledger.pages[page]
    result.status = status
    result.findings = findings
    result.screenshot = screenshot
    result.confidence = confidence
    result.last_checked = now
    result.needs_revalidation = False

    _recalculate_summary(ledger)


def update_interaction_result(
    ledger: ComplianceLedger,
    page: str,
    interaction: str,
    status: str,
    findings: list[str],
    screenshot: Optional[str] = None,
    confidence: float = 0.0,
) -> None:
    """Update the result for an interactive state."""
    now = datetime.now().isoformat()

    if page not in ledger.pages:
        ledger.pages[page] = PageResult(status="pending")

    page_result = ledger.pages[page]
    page_result.interactions[interaction] = InteractionResult(
        status=status,
        findings=findings,
        screenshot=screenshot,
        confidence=confidence,
        last_checked=now,
    )

    # Update page status based on interactions
    _update_page_status_from_interactions(page_result)
    _recalculate_summary(ledger)


def _update_page_status_from_interactions(page_result: PageResult) -> None:
    """Update page status based on its interaction results."""
    if not page_result.interactions:
        return

    # If any interaction fails, page fails
    # If all pass, page passes
    # Otherwise pending
    statuses = [i.status for i in page_result.interactions.values()]

    if "fail" in statuses:
        # Don't override if page itself failed
        if page_result.status != "fail":
            page_result.status = "fail"
    elif all(s == "pass" for s in statuses) and page_result.status == "pending":
        page_result.status = "pass"


def _recalculate_summary(ledger: ComplianceLedger) -> None:
    """Recalculate summary statistics."""
    total = 0
    passed = 0
    failed = 0
    pending = 0
    skipped = 0

    for page_result in ledger.pages.values():
        # Count page itself
        total += 1
        if page_result.status == "pass":
            passed += 1
        elif page_result.status == "fail":
            failed += 1
        elif page_result.status == "skipped":
            skipped += 1
        else:
            pending += 1

        # Count interactions
        for int_result in page_result.interactions.values():
            total += 1
            if int_result.status == "pass":
                passed += 1
            elif int_result.status == "fail":
                failed += 1
            elif int_result.status == "skipped":
                skipped += 1
            else:
                pending += 1

    ledger.summary = LedgerSummary(
        total_checks=total,
        passed=passed,
        failed=failed,
        pending=pending,
        skipped=skipped,
        compliance_percent=round(100 * passed / total, 1) if total > 0 else 0.0,
    )


# =============================================================================
# Reset Operations
# =============================================================================


def mark_pages_for_revalidation(ledger: ComplianceLedger, pages: list[str]) -> None:
    """Mark specific pages as needing revalidation."""
    for page in pages:
        if page in ledger.pages:
            ledger.pages[page].needs_revalidation = True
            ledger.pages[page].status = "pending"

            # Also reset interactions
            for int_result in ledger.pages[page].interactions.values():
                int_result.status = "pending"

    _recalculate_summary(ledger)

    # Add history entry
    ledger.history.append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "message": f"Reset {len(pages)} page(s): {', '.join(pages)}",
    })


def reset_all(ledger: ComplianceLedger) -> None:
    """Reset all pages to pending."""
    for page_result in ledger.pages.values():
        page_result.status = "pending"
        page_result.needs_revalidation = True
        page_result.findings = []

        for int_result in page_result.interactions.values():
            int_result.status = "pending"
            int_result.findings = []

    _recalculate_summary(ledger)

    ledger.history.append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "message": "Full reset (all pages)",
    })


def get_pages_needing_validation(ledger: ComplianceLedger) -> list[str]:
    """Get list of pages that need validation."""
    pages = []

    for page_name, page_result in ledger.pages.items():
        if page_result.status == "pending" or page_result.needs_revalidation:
            pages.append(page_name)

    return pages


def get_failed_pages(ledger: ComplianceLedger) -> list[str]:
    """Get list of pages that failed validation."""
    return [name for name, result in ledger.pages.items() if result.status == "fail"]


def is_fully_compliant(ledger: ComplianceLedger) -> bool:
    """Check if all pages pass compliance."""
    if not ledger.pages:
        return False

    for page_result in ledger.pages.values():
        if page_result.status != "pass":
            return False

        for int_result in page_result.interactions.values():
            if int_result.status != "pass":
                return False

    return True


# =============================================================================
# Initialization
# =============================================================================


def initialize_ledger(project: str, pages: list[str], project_root: Path) -> ComplianceLedger:
    """Initialize a new ledger for a project."""
    ledger = ComplianceLedger(
        project=project,
        commit=get_git_commit(project_root, short=True),
    )

    for page in pages:
        ledger.pages[page] = PageResult(status="pending")

    ledger.history.append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "message": f"Initialized ledger for {project}",
    })

    return ledger


# =============================================================================
# Statistics Tracking
# =============================================================================


def start_run(ledger: ComplianceLedger, project: str, commit: str) -> None:
    """Start a new compliance run, initializing run statistics."""
    now = datetime.now()

    ledger.current_run = RunStatistics(
        run_id=now.isoformat(),
        project=project,
        commit=commit,
        iteration_number=1,
    )

    # Update lifetime stats
    if not ledger.lifetime_stats.first_run_date:
        ledger.lifetime_stats.first_run_date = now.strftime("%Y-%m-%d")
    ledger.lifetime_stats.last_run_date = now.strftime("%Y-%m-%d")


def record_iteration(ledger: ComplianceLedger) -> None:
    """Record completion of a validation iteration."""
    ledger.current_run.iteration_number += 1


def record_screenshots(ledger: ComplianceLedger, static: int, interactive: int) -> None:
    """Record screenshot capture counts."""
    ledger.current_run.screenshots_captured = static + interactive
    ledger.current_run.interactive_screenshots = interactive


def record_validation_agent(ledger: ComplianceLedger, count: int = 1) -> None:
    """Record spawning of validation agent(s)."""
    ledger.current_run.validation_agents_spawned += count


def record_criteria_stats(ledger: ComplianceLedger, total: int, by_category: dict[str, int]) -> None:
    """Record criteria statistics."""
    ledger.current_run.total_criteria = total
    ledger.current_run.criteria_by_category = by_category


def finalize_run(ledger: ComplianceLedger) -> None:
    """Finalize the current run and update lifetime statistics."""
    run = ledger.current_run
    stats = ledger.lifetime_stats
    now = datetime.now()

    # Calculate final stats from ledger state
    run.pages_checked = len(ledger.pages)
    run.pages_passed = sum(1 for p in ledger.pages.values() if p.status == "pass")
    run.pages_failed = sum(1 for p in ledger.pages.values() if p.status == "fail")
    run.pages_skipped = sum(1 for p in ledger.pages.values() if p.status == "skipped")

    run.interactive_states_checked = sum(
        len(p.interactions) for p in ledger.pages.values()
    )
    run.interactive_states_passed = sum(
        sum(1 for i in p.interactions.values() if i.status == "pass")
        for p in ledger.pages.values()
    )

    run.final_compliance_percent = ledger.summary.compliance_percent
    run.achieved_100_percent = is_fully_compliant(ledger)

    if run.achieved_100_percent:
        run.iterations_to_compliance = run.iteration_number

    # Update lifetime stats
    stats.total_runs += 1
    stats.total_pages_validated += run.pages_checked
    stats.total_screenshots_captured += run.screenshots_captured
    stats.total_agents_spawned += run.validation_agents_spawned

    # Update records
    if run.iteration_number == 1 and run.final_compliance_percent > stats.best_first_run_compliance:
        stats.best_first_run_compliance = run.final_compliance_percent

    if run.achieved_100_percent:
        stats.last_100_percent_date = now.strftime("%Y-%m-%d")
        stats.current_streak += 1

        if stats.fastest_to_100_percent == 0 or run.iteration_number < stats.fastest_to_100_percent:
            stats.fastest_to_100_percent = run.iteration_number

        if stats.current_streak > stats.consecutive_100_percent_runs:
            stats.consecutive_100_percent_runs = stats.current_streak
    else:
        stats.current_streak = 0

    if run.iteration_number > stats.most_iterations_needed:
        stats.most_iterations_needed = run.iteration_number

    # Add to run history (keep last 20)
    ledger.run_history.append(run)
    if len(ledger.run_history) > 20:
        ledger.run_history = ledger.run_history[-20:]


def get_run_summary(ledger: ComplianceLedger) -> str:
    """Get a one-line summary of the current run for logging."""
    run = ledger.current_run
    if not run.run_id:
        return "No run in progress"

    status = "100%" if run.achieved_100_percent else f"{run.final_compliance_percent:.1f}%"
    return (
        f"Run {run.run_id[:10]}: {status} compliance, "
        f"{run.pages_checked} pages, {run.screenshots_captured} screenshots, "
        f"iteration {run.iteration_number}"
    )
