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
    ComparativeAnalysis,
    DiscriminatingFeature,
    SelfImproveEntries,
    SelfImproveEntrySummary,
    SuccessPattern,
    SuccessPatterns,
    SystemHealthMetric,
    SystemHealthReport,
    UserPatternAnalysis,
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


def sbs_successful_sessions_impl() -> SuccessPatterns:
    """Mine successful interaction patterns from archive data."""
    index = load_archive_index()

    if not index.entries:
        return SuccessPatterns()

    entries = list(index.entries.values())
    patterns: List[SuccessPattern] = []

    # Pattern 1: Sessions with skill entries that completed successfully (had phase_end)
    completed_skills = []
    for entry in entries:
        gs = entry.global_state or {}
        st = entry.state_transition or ""
        if gs.get("skill") == "task" and st == "phase_end":
            completed_skills.append(entry.entry_id)

    if completed_skills:
        patterns.append(SuccessPattern(
            pattern_type="completed_task",
            description=f"{len(completed_skills)} task(s) completed full lifecycle (alignment->finalization)",
            evidence=completed_skills[:10],
            frequency=len(completed_skills),
        ))

    # Pattern 2: Sessions with low auto-tag count (clean execution)
    clean_sessions = []
    for entry in entries:
        auto_tags = entry.auto_tags or []
        trigger = entry.trigger or ""
        if trigger == "skill" and len(auto_tags) <= 3:
            clean_sessions.append(entry.entry_id)

    if clean_sessions:
        patterns.append(SuccessPattern(
            pattern_type="clean_execution",
            description=f"{len(clean_sessions)} session(s) with minimal auto-tags (<=3), indicating clean execution",
            evidence=clean_sessions[:10],
            frequency=len(clean_sessions),
        ))

    # Pattern 3: Sessions with quality scores above threshold
    high_quality = []
    for entry in entries:
        qs = entry.quality_scores or {}
        overall = qs.get("overall", 0)
        if overall and float(overall) >= 0.9:
            high_quality.append(entry.entry_id)

    if high_quality:
        patterns.append(SuccessPattern(
            pattern_type="high_quality",
            description=f"{len(high_quality)} entry/entries with quality score >= 0.9",
            evidence=high_quality[:10],
            frequency=len(high_quality),
        ))

    return SuccessPatterns(
        patterns=patterns,
        total_sessions_analyzed=len(entries),
        summary=f"Analyzed {len(entries)} entries, found {len(patterns)} success pattern types",
    )


def sbs_comparative_analysis_impl() -> ComparativeAnalysis:
    """Compare approved vs rejected plans/proposals from archive data."""
    index = load_archive_index()

    if not index.entries:
        return ComparativeAnalysis()

    entries = list(index.entries.values())

    # Classify entries by phase transitions
    planning_entries = []
    execution_entries = []

    for entry in entries:
        gs = entry.global_state or {}
        st = entry.state_transition or ""
        skill = gs.get("skill", "")
        substate = gs.get("substate", "")

        if skill == "task" and st == "phase_start":
            if substate == "planning":
                planning_entries.append(entry)
            elif substate == "execution":
                execution_entries.append(entry)

    # Plans that reached execution = approved; plans without execution = potentially rejected
    approved_count = len(execution_entries)
    total_plans = len(planning_entries)
    rejected_count = max(0, total_plans - approved_count)

    features: List[DiscriminatingFeature] = []

    # Feature: completion rate
    if total_plans > 0:
        features.append(DiscriminatingFeature(
            feature="plan_approval_rate",
            approved_value=f"{approved_count}/{total_plans} ({100 * approved_count // max(total_plans, 1)}%)",
            rejected_value=f"{rejected_count}/{total_plans}",
            confidence="medium",
        ))

    # Feature: tag patterns in successful vs all entries
    successful_tags: dict[str, int] = {}
    all_tags: dict[str, int] = {}
    for entry in entries:
        tags = (entry.tags or []) + (entry.auto_tags or [])
        gs = entry.global_state or {}
        is_successful = gs.get("skill") == "task" and (entry.state_transition or "") == "phase_end"
        for tag in tags:
            all_tags[tag] = all_tags.get(tag, 0) + 1
            if is_successful:
                successful_tags[tag] = successful_tags.get(tag, 0) + 1

    # Find tags over-represented in successful sessions
    for tag, count in successful_tags.items():
        total = all_tags.get(tag, 1)
        if count > 1 and count / total > 0.3:
            features.append(DiscriminatingFeature(
                feature=f"tag:{tag}",
                approved_value=f"present in {count} successful entries",
                rejected_value=f"present in {total} total entries",
                confidence="low",
            ))

    return ComparativeAnalysis(
        approved_count=approved_count,
        rejected_count=rejected_count,
        features=features[:10],
        summary=f"Analyzed {total_plans} planning phases: {approved_count} reached execution, {rejected_count} did not",
    )


def sbs_system_health_impl() -> SystemHealthReport:
    """Analyze system engineering health from archive data."""
    index = load_archive_index()

    if not index.entries:
        return SystemHealthReport()

    entries = list(index.entries.values())
    build_metrics: List[SystemHealthMetric] = []
    tool_errors: dict[str, float] = {}
    findings: List[AnalysisFinding] = []

    # Build timing analysis
    build_entries = [e for e in entries if (e.trigger or "") == "build"]
    if build_entries:
        build_metrics.append(SystemHealthMetric(
            metric="total_builds",
            value=float(len(build_entries)),
            trend="stable",
            details=f"{len(build_entries)} build entries in archive",
        ))

    # Quality score coverage
    entries_with_scores = [e for e in entries if e.quality_scores]
    score_coverage = len(entries_with_scores) / max(len(entries), 1)
    build_metrics.append(SystemHealthMetric(
        metric="quality_score_coverage",
        value=round(score_coverage, 3),
        trend="degrading" if score_coverage < 0.1 else "stable",
        details=f"{len(entries_with_scores)}/{len(entries)} entries have quality scores",
    ))

    if score_coverage < 0.1:
        findings.append(AnalysisFinding(
            pillar="system_engineering",
            category="data_quality",
            severity="high",
            description=f"Only {score_coverage * 100:.1f}% of entries have quality scores",
            recommendation="Ensure validators run automatically after builds (Issue #15)",
            evidence=[e.entry_id for e in entries_with_scores[:5]],
        ))

    # Auto-tag noise analysis
    tag_counts: dict[str, int] = {}
    skill_entries = [e for e in entries if (e.trigger or "") == "skill"]
    for entry in skill_entries:
        for tag in entry.auto_tags or []:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    noisy_tags = []
    for tag, count in tag_counts.items():
        if len(skill_entries) > 0 and count / len(skill_entries) > 0.8:
            noisy_tags.append(tag)

    if noisy_tags:
        findings.append(AnalysisFinding(
            pillar="system_engineering",
            category="tagging",
            severity="medium",
            description=f"Tags firing on >80% of skill entries (low signal): {', '.join(noisy_tags)}",
            recommendation="Review tag thresholds to ensure they flag anomalies, not normal behavior",
            evidence=[],
        ))

    # Archive friction
    archive_friction = {
        "total_entries": len(entries),
        "skill_entries": len(skill_entries),
        "build_entries": len(build_entries),
        "noisy_tags": noisy_tags,
    }

    overall = "healthy"
    if len(findings) >= 2:
        overall = "warning"
    if len(findings) >= 4:
        overall = "degraded"

    return SystemHealthReport(
        build_metrics=build_metrics,
        tool_error_rates=tool_errors,
        archive_friction=archive_friction,
        findings=findings,
        overall_health=overall,
    )


def sbs_user_patterns_impl() -> UserPatternAnalysis:
    """Analyze user communication patterns from archive session data."""
    index = load_archive_index()

    if not index.entries:
        return UserPatternAnalysis()

    entries = list(index.entries.values())

    effective_patterns: List[str] = []
    findings: List[AnalysisFinding] = []

    # Analyze skill entries for alignment patterns
    task_entries = [
        e for e in entries
        if (e.global_state or {}).get("skill") == "task"
    ]

    # Pattern: Tasks that complete quickly (few phase transitions)
    task_phases: dict[str, List[str]] = {}
    current_task_id: Optional[str] = None
    for entry in sorted(entries, key=lambda e: e.entry_id):
        gs = entry.global_state or {}
        if gs.get("skill") == "task":
            st = entry.state_transition or ""
            substate = gs.get("substate", "")
            if substate == "alignment" and st == "phase_start":
                current_task_id = entry.entry_id
                task_phases[current_task_id] = []
            if current_task_id:
                task_phases[current_task_id].append(substate)

    # Find tasks with efficient alignment (short alignment phase)
    efficient_tasks = 0
    total_tasks = len(task_phases)
    for task_id, phases in task_phases.items():
        alignment_count = phases.count("alignment")
        if alignment_count <= 2:
            efficient_tasks += 1

    if total_tasks > 0:
        efficiency_rate = efficient_tasks / total_tasks
        effective_patterns.append(
            f"Quick alignment (<=2 alignment entries): {efficient_tasks}/{total_tasks} tasks ({efficiency_rate * 100:.0f}%)"
        )

        if efficiency_rate > 0.7:
            findings.append(AnalysisFinding(
                pillar="user_effectiveness",
                category="alignment_efficiency",
                severity="low",
                description=f"Most tasks ({efficiency_rate * 100:.0f}%) achieve alignment quickly",
                recommendation="Current communication pattern is effective; maintain clear upfront context",
                evidence=list(task_phases.keys())[:5],
            ))

    # Pattern: Issue-driven vs freeform tasks
    issue_driven = [e for e in task_entries if e.issue_refs]
    freeform = [e for e in task_entries if not e.issue_refs]

    if issue_driven or freeform:
        effective_patterns.append(
            f"Issue-driven tasks: {len(issue_driven)}, Freeform tasks: {len(freeform)}"
        )

    return UserPatternAnalysis(
        total_sessions_analyzed=len(entries),
        effective_patterns=effective_patterns,
        findings=findings,
        summary=f"Analyzed {total_tasks} task sessions across {len(entries)} archive entries",
    )
