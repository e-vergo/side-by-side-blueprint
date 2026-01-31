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
class ComplianceLedger:
    """The complete compliance ledger."""

    version: str = "1.0"
    last_run: Optional[str] = None
    project: str = ""
    commit: str = ""
    repo_commits: dict[str, str] = field(default_factory=dict)
    pages: dict[str, PageResult] = field(default_factory=dict)
    summary: LedgerSummary = field(default_factory=LedgerSummary)
    history: list[dict] = field(default_factory=list)


# =============================================================================
# Paths
# =============================================================================


def get_ledger_path() -> Path:
    """Get path to compliance ledger JSON."""
    return get_sbs_root() / "scripts" / "compliance_ledger.json"


def get_status_md_path() -> Path:
    """Get path to compliance status markdown."""
    return get_sbs_root() / "scripts" / "COMPLIANCE_STATUS.md"


def get_manifests_dir() -> Path:
    """Get path to interaction manifests directory."""
    manifests_dir = get_sbs_root() / "scripts" / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    return manifests_dir


# =============================================================================
# Serialization
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

    return ledger


# =============================================================================
# Read/Write
# =============================================================================


def load_ledger() -> ComplianceLedger:
    """Load ledger from disk, or create empty one if not exists."""
    path = get_ledger_path()

    if path.exists():
        try:
            data = json.loads(path.read_text())
            return _deserialize_ledger(data)
        except Exception as e:
            log.warning(f"Failed to load ledger: {e}")
            return ComplianceLedger()

    return ComplianceLedger()


def save_ledger(ledger: ComplianceLedger) -> None:
    """Save ledger to disk (both JSON and Markdown)."""
    # Update timestamp
    ledger.last_run = datetime.now().isoformat()

    # Save JSON
    json_path = get_ledger_path()
    json_path.write_text(json.dumps(_serialize_ledger(ledger), indent=2))

    # Save Markdown
    md_path = get_status_md_path()
    md_path.write_text(_generate_markdown(ledger))


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

    # History section
    if ledger.history:
        lines.append("## Recent Changes")
        lines.append("")
        for entry in ledger.history[-5:]:
            lines.append(f"- {entry.get('date', 'unknown')}: {entry.get('message', '')}")
        lines.append("")

    return "\n".join(lines)


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
