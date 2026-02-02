"""
Compliance ledger operations.

Handles compliance-specific ledger operations including:
- ComplianceLedger dataclass
- Load/save operations
- Page result updates
- Statistics tracking

Note: Core data structures (BuildMetrics, UnifiedLedger, etc.) are defined in
sbs.core.ledger.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sbs.core.utils import get_sbs_root, get_git_commit, log, ARCHIVE_DIR

# Re-export core types for convenience
from sbs.core.ledger import (
    InteractionResult,
    PageResult,
    LedgerSummary,
    RunStatistics,
    HistoricalStats,
    BuildMetrics,
    UnifiedLedger,
    get_or_create_unified_ledger,
    # Serialization helpers (needed for compliance ledger)
    _serialize_run_stats,
    _deserialize_run_stats,
    _deserialize_historical_stats,
)


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


def get_archive_root() -> Path:
    """Get path to archive directory (dev/storage)."""
    return ARCHIVE_DIR


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
# Serialization (ComplianceLedger-specific)
# =============================================================================


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
