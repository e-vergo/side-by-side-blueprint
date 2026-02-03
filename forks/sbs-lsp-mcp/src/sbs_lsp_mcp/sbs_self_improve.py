"""Self-improve tool implementations.

This module contains implementation functions for the self-improve MCP tools.
Separated from sbs_tools.py to avoid requiring MCP dependencies during testing.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from .sbs_models import (
    AnalysisFinding,
    AnalysisSummary,
    SelfImproveEntries,
    SelfImproveEntrySummary,
)
from .sbs_utils import load_archive_index


def sbs_analysis_summary_impl() -> AnalysisSummary:
    """Implementation of sbs_analysis_summary tool.

    Returns summary statistics useful for self-improvement:
    - Total entries and date range
    - Entries by trigger type
    - Quality metrics aggregates
    - Most common tags
    - Projects summary
    - Basic improvement findings
    """
    from collections import Counter

    index = load_archive_index()

    if not index.entries:
        return AnalysisSummary(
            total_entries=0,
            date_range="",
            entries_by_trigger={},
            quality_metrics=None,
            most_common_tags=[],
            projects_summary={},
            findings=[],
        )

    # Sort entries by entry_id (chronological)
    sorted_entries = sorted(index.entries.values(), key=lambda e: e.entry_id)

    # Date range
    first_entry = sorted_entries[0]
    last_entry = sorted_entries[-1]
    date_range = f"{first_entry.created_at} to {last_entry.created_at}"

    # Entries by trigger
    trigger_counts: Counter = Counter()
    for entry in sorted_entries:
        trigger_counts[entry.trigger] += 1

    # Tag frequency
    tag_counts: Counter = Counter()
    for entry in sorted_entries:
        for tag in entry.tags + entry.auto_tags:
            tag_counts[tag] += 1
    most_common_tags = [tag for tag, _ in tag_counts.most_common(10)]

    # Projects summary
    project_counts: Counter = Counter()
    for entry in sorted_entries:
        project_counts[entry.project] += 1

    # Quality metrics (average scores from entries that have them)
    quality_scores: List[float] = []
    for entry in sorted_entries:
        if entry.quality_scores and "overall" in entry.quality_scores:
            try:
                score = float(entry.quality_scores["overall"])
                quality_scores.append(score)
            except (ValueError, TypeError):
                pass

    quality_metrics = None
    if quality_scores:
        quality_metrics = {
            "average": sum(quality_scores) / len(quality_scores),
            "min": min(quality_scores),
            "max": max(quality_scores),
            "count": float(len(quality_scores)),
        }

    # Generate basic findings
    findings: List[AnalysisFinding] = []

    # Finding: high error rate in builds
    build_count = trigger_counts.get("build", 0)
    error_entries = [
        e for e in sorted_entries
        if "error" in " ".join(e.tags + e.auto_tags).lower()
    ]
    if build_count > 0 and len(error_entries) > build_count * 0.2:
        findings.append(
            AnalysisFinding(
                pillar="system_engineering",
                category="error_pattern",
                severity="medium",
                description=f"High error rate: {len(error_entries)} error entries out of {build_count} builds",
                recommendation="Investigate common error patterns and add safeguards",
                evidence=[e.entry_id for e in error_entries[:5]],
            )
        )

    # Finding: stale entries (no recent activity)
    if sorted_entries:
        try:
            last_time = datetime.fromisoformat(
                last_entry.created_at.replace("Z", "+00:00")
            )
            now = datetime.now(last_time.tzinfo)
            days_since = (now - last_time).days
            if days_since > 7:
                findings.append(
                    AnalysisFinding(
                        pillar="user_effectiveness",
                        category="workflow",
                        severity="low",
                        description=f"No archive entries in {days_since} days",
                        recommendation="Consider running a build to capture current state",
                        evidence=[last_entry.entry_id],
                    )
                )
        except (ValueError, TypeError):
            pass

    return AnalysisSummary(
        total_entries=len(sorted_entries),
        date_range=date_range,
        entries_by_trigger=dict(trigger_counts),
        quality_metrics=quality_metrics,
        most_common_tags=most_common_tags,
        projects_summary=dict(project_counts),
        findings=findings,
    )


def sbs_entries_since_self_improve_impl() -> SelfImproveEntries:
    """Implementation of sbs_entries_since_self_improve tool.

    Finds the most recent archive entry where global_state.skill == "self-improve"
    and returns all entries created after that point.
    """
    from collections import Counter

    index = load_archive_index()

    if not index.entries:
        return SelfImproveEntries(
            last_self_improve_entry=None,
            last_self_improve_timestamp=None,
            entries_since=[],
            count_by_trigger={},
            count=0,
        )

    # Sort entries by entry_id descending (most recent first)
    sorted_entries = sorted(
        index.entries.values(), key=lambda e: e.entry_id, reverse=True
    )

    # Find the most recent self-improve entry
    last_self_improve_entry: Optional[str] = None
    last_self_improve_timestamp: Optional[str] = None

    for entry in sorted_entries:
        if entry.global_state and entry.global_state.get("skill") == "self-improve":
            last_self_improve_entry = entry.entry_id
            last_self_improve_timestamp = getattr(entry, 'added_at', None) or entry.created_at
            break

    # Get entries since the last self-improve (or all if no self-improve found)
    entries_since: List[SelfImproveEntrySummary] = []
    trigger_counts: Counter = Counter()

    for entry in sorted_entries:
        # Stop when we reach the last self-improve entry
        if last_self_improve_entry and entry.entry_id <= last_self_improve_entry:
            break

        # Skip retroactive entries (backdated migrations)
        if "retroactive" in entry.tags + entry.auto_tags:
            continue

        # Extract quality score if available
        quality_score = None
        if entry.quality_scores and "overall" in entry.quality_scores:
            try:
                quality_score = float(entry.quality_scores["overall"])
            except (ValueError, TypeError):
                pass

        entries_since.append(
            SelfImproveEntrySummary(
                entry_id=entry.entry_id,
                created_at=entry.created_at,
                project=entry.project,
                trigger=entry.trigger,
                notes=entry.notes or "",
                tags=entry.tags + entry.auto_tags,
                quality_score=quality_score,
            )
        )
        trigger_counts[entry.trigger] += 1

    return SelfImproveEntries(
        last_self_improve_entry=last_self_improve_entry,
        last_self_improve_timestamp=last_self_improve_timestamp,
        entries_since=entries_since,
        count_by_trigger=dict(trigger_counts),
        count=len(entries_since),
    )
