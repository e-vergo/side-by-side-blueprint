"""Self-improve tool implementations.

This module contains implementation functions for the self-improve MCP tools.
Separated from sbs_tools.py to avoid requiring MCP dependencies during testing.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from dataclasses import dataclass, field as dc_field

from .sbs_models import (
    AnalysisFinding,
    AnalysisSummary,
    ComparativeAnalysis,
    DiscriminatingFeature,
    GateFailureEntry,
    GateFailureReport,
    InterruptionAnalysisResult,
    InterruptionEvent,
    PhaseTransitionHealthResult,
    PhaseTransitionReport,
    QuestionAnalysisResult,
    QuestionInteraction,
    QuestionStatsResult,
    SelfImproveEntries,
    SelfImproveEntrySummary,
    SkillStatEntry,
    SkillStatsResult,
    SuccessPattern,
    SuccessPatterns,
    SystemHealthMetric,
    SystemHealthReport,
    TagEffectivenessEntry,
    TagEffectivenessResult,
    UserPatternAnalysis,
)
from .sbs_utils import load_archive_index


# =============================================================================
# Shared Helpers for Self-Improve Tools
# =============================================================================


@dataclass
class SkillSession:
    """A contiguous session of a single skill invocation."""

    skill: str
    entries: list = dc_field(default_factory=list)
    first_entry_id: str = ""
    last_entry_id: str = ""
    phases_visited: list = dc_field(default_factory=list)
    completed: bool = False
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    last_substate: str = ""  # Where incomplete sessions stopped


SKILL_PHASE_ORDERS: dict[str, list[str]] = {
    "task": ["alignment", "planning", "execution", "finalization"],
    "self-improve": ["discovery", "selection", "dialogue", "logging", "archive"],
}

CORRECTION_KEYWORDS = [
    "correction", "corrected", "redo", "retry", "revert",
    "wrong", "mistake", "back to", "restart", "redirected",
    "changed approach", "pivot", "scratch that",
]


def _group_entries_by_skill_session(entries: list) -> list[SkillSession]:
    """Group archive entries into skill sessions.

    A session starts with a phase_start entry and ends with a phase_end entry
    or when a different skill appears.

    Key invariants:
    - phase_end is checked FIRST (before global_state), because phase_end
      entries have global_state=null after the skill clears its state.
    - Null-state entries are absorbed silently into the current session;
      they do NOT close it (prevents session fragmentation).
    - last_substate tracks the most recent substate seen, so incomplete
      sessions report where they stopped even if the final entry has null state.
    """
    sorted_entries = sorted(entries, key=lambda e: e.entry_id)
    sessions: list[SkillSession] = []
    current_session: Optional[SkillSession] = None

    def _close_session(session: SkillSession) -> None:
        """Finalize and append a session to the results list."""
        if session.entries:
            session.last_entry_id = session.entries[-1].entry_id
            session.end_time = session.entries[-1].created_at
        sessions.append(session)

    for entry in sorted_entries:
        st = entry.state_transition or ""

        # 1. Check state_transition FIRST: phase_end closes the current session
        if st == "phase_end" and current_session is not None:
            current_session.entries.append(entry)
            current_session.completed = True
            current_session.last_entry_id = entry.entry_id
            current_session.end_time = entry.created_at
            sessions.append(current_session)
            current_session = None
            continue

        # 1b. Handoff: closes the current session AND starts a new one atomically.
        # The entry's global_state contains the incoming skill's state.
        if st == "handoff" and current_session is not None:
            # Close outgoing session
            current_session.entries.append(entry)
            current_session.completed = True
            current_session.last_entry_id = entry.entry_id
            current_session.end_time = entry.created_at
            sessions.append(current_session)

            # Start incoming session from the same entry
            gs = entry.global_state or {}
            new_skill = gs.get("skill", "")
            new_substate = gs.get("substate", "")
            current_session = SkillSession(
                skill=new_skill,
                entries=[entry],
                first_entry_id=entry.entry_id,
                phases_visited=[new_substate] if new_substate else [],
                start_time=entry.created_at,
                last_substate=new_substate,
            )
            continue

        # 2. Extract skill from global_state
        gs = entry.global_state or {}
        skill = gs.get("skill")
        substate = gs.get("substate", "")

        # 3. No skill: absorb silently (do NOT close current session)
        if not skill:
            continue

        # 4. phase_start: start or continue a session
        if st == "phase_start":
            if current_session is not None and current_session.skill == skill:
                # Same skill phase_start: add entry, track phase
                current_session.entries.append(entry)
                if substate and (not current_session.phases_visited or current_session.phases_visited[-1] != substate):
                    current_session.phases_visited.append(substate)
                if substate:
                    current_session.last_substate = substate
            else:
                # Different skill or no current session: close current, start new
                if current_session is not None:
                    _close_session(current_session)
                current_session = SkillSession(
                    skill=skill,
                    entries=[entry],
                    first_entry_id=entry.entry_id,
                    phases_visited=[substate] if substate else [],
                    start_time=entry.created_at,
                    last_substate=substate,
                )
            continue

        # 5. Skill matches current session: add entry
        if current_session is not None and current_session.skill == skill:
            current_session.entries.append(entry)
            if substate and (not current_session.phases_visited or current_session.phases_visited[-1] != substate):
                current_session.phases_visited.append(substate)
            if substate:
                current_session.last_substate = substate
            continue

        # 6. Different skill than current session: close current, start new
        if current_session is not None:
            _close_session(current_session)

        current_session = SkillSession(
            skill=skill,
            entries=[entry],
            first_entry_id=entry.entry_id,
            phases_visited=[substate] if substate else [],
            start_time=entry.created_at,
            last_substate=substate,
        )

    # Close any remaining session
    if current_session is not None:
        _close_session(current_session)

    return sessions


def _compute_session_duration(session: SkillSession) -> Optional[float]:
    """Compute duration of a session in seconds from ISO timestamps."""
    if not session.start_time or not session.end_time:
        return None
    try:
        start = datetime.fromisoformat(session.start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(session.end_time.replace("Z", "+00:00"))
        return (end - start).total_seconds()
    except (ValueError, TypeError):
        return None


def _detect_backward_transitions(
    session: SkillSession, expected_order: list[str]
) -> list[tuple[str, str, str]]:
    """Detect backward phase transitions within a session.

    Returns list of (entry_id, from_phase, to_phase) tuples.
    """
    backward = []
    prev_phase: Optional[str] = None
    prev_entry_id: Optional[str] = None

    for entry in session.entries:
        gs = entry.global_state or {}
        substate = gs.get("substate", "")
        if not substate:
            continue

        if prev_phase and substate != prev_phase:
            try:
                prev_idx = expected_order.index(prev_phase)
                curr_idx = expected_order.index(substate)
                if curr_idx < prev_idx:
                    backward.append((entry.entry_id, prev_phase, substate))
            except ValueError:
                pass  # Phase not in expected order

        prev_phase = substate
        prev_entry_id = entry.entry_id

    return backward


def _detect_skipped_phases(
    session: SkillSession, expected_order: list[str]
) -> list[str]:
    """Detect phases that were skipped in a session.

    A phase is skipped if it's in the expected order between two phases
    that were visited but was not visited itself.
    """
    visited = set(session.phases_visited)
    if not visited:
        return []

    # Find the range of visited phases in expected_order
    visited_indices = []
    for phase in session.phases_visited:
        try:
            visited_indices.append(expected_order.index(phase))
        except ValueError:
            continue

    if len(visited_indices) < 2:
        return []

    min_idx = min(visited_indices)
    max_idx = max(visited_indices)

    skipped = []
    for i in range(min_idx, max_idx + 1):
        if i < len(expected_order) and expected_order[i] not in visited:
            skipped.append(expected_order[i])

    return skipped


# =============================================================================
# New Self-Improve Tool Implementations
# =============================================================================


def sbs_skill_stats_impl(as_findings: bool = False) -> SkillStatsResult:
    """Get per-skill lifecycle metrics.

    Returns invocation count, completion rate, duration, and failure modes
    for each skill type.
    """
    from collections import Counter

    index = load_archive_index()
    if not index.entries:
        return SkillStatsResult(summary="No archive entries found.")

    entries = list(index.entries.values())
    sessions = _group_entries_by_skill_session(entries)

    if not sessions:
        return SkillStatsResult(
            total_sessions=0,
            summary="No skill sessions found in archive.",
        )

    # Group sessions by skill
    by_skill: dict[str, list[SkillSession]] = {}
    for session in sessions:
        by_skill.setdefault(session.skill, []).append(session)

    skills: dict[str, SkillStatEntry] = {}
    for skill_name, skill_sessions in by_skill.items():
        invocations = len(skill_sessions)
        completions = sum(1 for s in skill_sessions if s.completed)
        rate = completions / invocations if invocations > 0 else 0.0

        # Average duration
        durations = [_compute_session_duration(s) for s in skill_sessions]
        valid_durations = [d for d in durations if d is not None]
        avg_duration = (
            sum(valid_durations) / len(valid_durations) if valid_durations else None
        )

        # Average entries per session
        total_entries = sum(len(s.entries) for s in skill_sessions)
        avg_entries = total_entries / invocations if invocations > 0 else 0.0

        # Failure modes from incomplete sessions
        failure_substates: Counter = Counter()
        failure_tags: Counter = Counter()
        for s in skill_sessions:
            if not s.completed and s.entries:
                sub = s.last_substate  # Use session-tracked substate
                if sub:
                    failure_substates[sub] += 1
                last_entry = s.entries[-1]
                for tag in (last_entry.tags or []) + (last_entry.auto_tags or []):
                    failure_tags[tag] += 1

        skills[skill_name] = SkillStatEntry(
            skill=skill_name,
            invocation_count=invocations,
            completion_count=completions,
            completion_rate=round(rate, 3),
            avg_duration_seconds=round(avg_duration, 1) if avg_duration is not None else None,
            avg_entries_per_session=round(avg_entries, 1),
            common_failure_substates=[s for s, _ in failure_substates.most_common(3)],
            common_failure_tags=[t for t, _ in failure_tags.most_common(5)],
        )

    findings: list[AnalysisFinding] = []
    if as_findings:
        for skill_name, stat in skills.items():
            if stat.completion_rate < 0.5 and stat.invocation_count >= 2:
                findings.append(AnalysisFinding(
                    pillar="claude_execution",
                    category="skill_lifecycle",
                    severity="medium",
                    description=f"Skill '{skill_name}' has low completion rate: {stat.completion_rate:.0%} ({stat.completion_count}/{stat.invocation_count})",
                    recommendation=f"Investigate common failure substates: {stat.common_failure_substates}",
                    evidence=[],
                ))

    return SkillStatsResult(
        skills=skills,
        total_sessions=len(sessions),
        findings=findings,
        summary=f"Analyzed {len(sessions)} sessions across {len(skills)} skill types.",
    )


def sbs_phase_transition_health_impl(
    as_findings: bool = False,
) -> PhaseTransitionHealthResult:
    """Analyze phase transition patterns.

    Detects backward transitions, skipped phases, and time-in-phase distribution.
    """
    index = load_archive_index()
    if not index.entries:
        return PhaseTransitionHealthResult(summary="No archive entries found.")

    entries = list(index.entries.values())
    sessions = _group_entries_by_skill_session(entries)

    if not sessions:
        return PhaseTransitionHealthResult(
            summary="No skill sessions found in archive.",
        )

    # Group sessions by skill
    by_skill: dict[str, list[SkillSession]] = {}
    for session in sessions:
        by_skill.setdefault(session.skill, []).append(session)

    reports: list[PhaseTransitionReport] = []
    for skill_name, skill_sessions in by_skill.items():
        expected = SKILL_PHASE_ORDERS.get(skill_name, [])

        total_backward = 0
        all_backward_details: list[dict[str, str]] = []
        all_skipped: dict[str, int] = {}

        # Compute time-in-phase aggregates
        phase_times: dict[str, list[float]] = {}

        for session in skill_sessions:
            # Backward transitions
            backward = _detect_backward_transitions(session, expected)
            total_backward += len(backward)
            for entry_id, from_p, to_p in backward:
                all_backward_details.append({
                    "entry_id": entry_id,
                    "from": from_p,
                    "to": to_p,
                })

            # Skipped phases
            skipped = _detect_skipped_phases(session, expected)
            for phase in skipped:
                all_skipped[phase] = all_skipped.get(phase, 0) + 1

            # Time-in-phase: compute from consecutive entries with same substate
            prev_phase = None
            prev_time = None
            for entry in session.entries:
                gs = entry.global_state or {}
                substate = gs.get("substate", "")
                if not substate:
                    continue
                try:
                    entry_time = datetime.fromisoformat(
                        entry.created_at.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    continue

                if prev_phase and prev_phase != substate and prev_time:
                    delta = (entry_time - prev_time).total_seconds()
                    phase_times.setdefault(prev_phase, []).append(delta)

                if substate != prev_phase:
                    prev_time = entry_time
                prev_phase = substate

        # Average time-in-phase
        avg_time: dict[str, float] = {}
        for phase, times in phase_times.items():
            if times:
                avg_time[phase] = round(sum(times) / len(times), 1)

        reports.append(PhaseTransitionReport(
            skill=skill_name,
            expected_sequence=expected,
            total_sessions=len(skill_sessions),
            backward_transitions=total_backward,
            backward_details=all_backward_details[:20],
            skipped_phases=all_skipped,
            time_in_phase=avg_time,
        ))

    findings: list[AnalysisFinding] = []
    if as_findings:
        for report in reports:
            if report.total_sessions > 0 and report.backward_transitions > 0:
                rate = report.backward_transitions / report.total_sessions
                if rate > 0.3:
                    findings.append(AnalysisFinding(
                        pillar="alignment_patterns",
                        category="phase_transition",
                        severity="medium",
                        description=f"Skill '{report.skill}' has high backward transition rate: {rate:.0%}",
                        recommendation="Investigate causes of phase regressions",
                        evidence=[d["entry_id"] for d in report.backward_details[:5]],
                    ))

    return PhaseTransitionHealthResult(
        reports=reports,
        findings=findings,
        summary=f"Analyzed {len(sessions)} sessions across {len(reports)} skill types.",
    )


def sbs_interruption_analysis_impl(
    as_findings: bool = False,
) -> InterruptionAnalysisResult:
    """Detect user corrections and redirections in session data.

    Identifies backward transitions, retries, and correction keywords.
    """
    index = load_archive_index()
    if not index.entries:
        return InterruptionAnalysisResult(summary="No archive entries found.")

    entries = list(index.entries.values())
    sessions = _group_entries_by_skill_session(entries)

    if not sessions:
        return InterruptionAnalysisResult(
            summary="No skill sessions found in archive.",
        )

    events: list[InterruptionEvent] = []
    sessions_with_interruptions = 0

    for session in sessions:
        session_had_interruption = False
        expected = SKILL_PHASE_ORDERS.get(session.skill, [])

        # 1. Backward transitions
        backward = _detect_backward_transitions(session, expected)
        for entry_id, from_p, to_p in backward:
            events.append(InterruptionEvent(
                entry_id=entry_id,
                skill=session.skill,
                event_type="backward_transition",
                from_phase=from_p,
                to_phase=to_p,
                context=f"Phase went backward from '{from_p}' to '{to_p}'",
            ))
            session_had_interruption = True

        # 2. Retries: substate appears >2 times
        from collections import Counter
        substate_counts: Counter = Counter()
        for entry in session.entries:
            gs = entry.global_state or {}
            sub = gs.get("substate", "")
            if sub:
                substate_counts[sub] += 1

        for sub, count in substate_counts.items():
            if count > 2:
                events.append(InterruptionEvent(
                    entry_id=session.first_entry_id,
                    skill=session.skill,
                    event_type="retry",
                    from_phase=sub,
                    to_phase=sub,
                    context=f"Substate '{sub}' appeared {count} times (possible retry pattern)",
                ))
                session_had_interruption = True

        # 3. Correction keywords in notes
        for entry in session.entries:
            notes = (entry.notes or "").lower()
            if notes:
                for keyword in CORRECTION_KEYWORDS:
                    if keyword in notes:
                        events.append(InterruptionEvent(
                            entry_id=entry.entry_id,
                            skill=session.skill,
                            event_type="correction_keyword",
                            context=f"Correction keyword '{keyword}' found in notes",
                        ))
                        session_had_interruption = True
                        break  # One event per entry

        # 4. High churn: entry_count > 2 * len(phases_visited)
        num_phases = max(len(session.phases_visited), 1)
        if len(session.entries) > 2 * num_phases and len(session.entries) > 4:
            events.append(InterruptionEvent(
                entry_id=session.first_entry_id,
                skill=session.skill,
                event_type="high_entry_count",
                context=f"{len(session.entries)} entries for {num_phases} phases (ratio: {len(session.entries)/num_phases:.1f}x)",
            ))
            session_had_interruption = True

        if session_had_interruption:
            sessions_with_interruptions += 1

    findings: list[AnalysisFinding] = []
    if as_findings and sessions:
        interrupt_rate = sessions_with_interruptions / len(sessions)
        if interrupt_rate > 0.3:
            findings.append(AnalysisFinding(
                pillar="user_effectiveness",
                category="interruption",
                severity="medium",
                description=f"{sessions_with_interruptions}/{len(sessions)} sessions had interruptions ({interrupt_rate:.0%})",
                recommendation="Review common interruption types and address root causes",
                evidence=[e.entry_id for e in events[:5]],
            ))

    return InterruptionAnalysisResult(
        events=events,
        total_sessions_analyzed=len(sessions),
        sessions_with_interruptions=sessions_with_interruptions,
        findings=findings,
        summary=f"Found {len(events)} interruption events across {len(sessions)} sessions ({sessions_with_interruptions} had interruptions).",
    )


def sbs_gate_failures_impl(as_findings: bool = False) -> GateFailureReport:
    """Analyze gate validation failures.

    Reports failure rates, override patterns, and common failure types.
    """
    index = load_archive_index()
    if not index.entries:
        return GateFailureReport(summary="No archive entries found.")

    entries = list(index.entries.values())
    sessions = _group_entries_by_skill_session(entries)

    # Find all entries with gate_validation
    gate_entries = [e for e in entries if e.gate_validation is not None]
    if not gate_entries:
        return GateFailureReport(
            total_gate_checks=0,
            summary="No gate validation entries found in archive.",
        )

    total_checks = len(gate_entries)
    failures: list[GateFailureEntry] = []
    override_count = 0

    # Build a set of entry_ids per session for override detection
    session_entries_map: dict[str, SkillSession] = {}
    for session in sessions:
        for entry in session.entries:
            session_entries_map[entry.entry_id] = session

    from collections import Counter
    finding_counts: Counter = Counter()

    for entry in gate_entries:
        gv = entry.gate_validation or {}
        passed = gv.get("passed", True)
        if not passed:
            gs = entry.global_state or {}
            gate_findings_list = gv.get("findings", [])
            for f in gate_findings_list:
                finding_counts[f] += 1

            # Check for override: did a later entry in same session advance to next phase?
            continued = False
            session = session_entries_map.get(entry.entry_id)
            if session:
                current_substate = gs.get("substate", "")
                expected = SKILL_PHASE_ORDERS.get(gs.get("skill", ""), [])
                # Check if any later entry in session has a different (forward) phase
                found_entry = False
                for se in session.entries:
                    if se.entry_id == entry.entry_id:
                        found_entry = True
                        continue
                    if found_entry:
                        se_gs = se.global_state or {}
                        se_sub = se_gs.get("substate", "")
                        if se_sub and se_sub != current_substate:
                            try:
                                if expected.index(se_sub) > expected.index(current_substate):
                                    continued = True
                                    break
                            except ValueError:
                                pass

            if continued:
                override_count += 1

            failures.append(GateFailureEntry(
                entry_id=entry.entry_id,
                skill=gs.get("skill"),
                substate=gs.get("substate"),
                gate_findings=gate_findings_list,
                continued=continued,
            ))

    failure_rate = len(failures) / total_checks if total_checks > 0 else 0.0
    common_findings_list = [f for f, _ in finding_counts.most_common(10)]

    findings: list[AnalysisFinding] = []
    if as_findings:
        if failure_rate > 0.3:
            findings.append(AnalysisFinding(
                pillar="claude_execution",
                category="gate_validation",
                severity="high",
                description=f"High gate failure rate: {failure_rate:.0%} ({len(failures)}/{total_checks})",
                recommendation="Review common gate findings and address recurring issues",
                evidence=[f.entry_id for f in failures[:5]],
            ))
        if override_count > 0:
            findings.append(AnalysisFinding(
                pillar="alignment_patterns",
                category="gate_override",
                severity="medium",
                description=f"{override_count} gate failures were overridden (task continued despite failure)",
                recommendation="Evaluate whether gate checks are too strict or if overrides indicate quality risks",
                evidence=[f.entry_id for f in failures if f.continued][:5],
            ))

    return GateFailureReport(
        total_gate_checks=total_checks,
        total_failures=len(failures),
        failure_rate=round(failure_rate, 3),
        failures=failures,
        override_count=override_count,
        common_findings=common_findings_list,
        findings=findings,
        summary=f"{len(failures)} gate failures out of {total_checks} checks ({failure_rate:.0%}). {override_count} overrides.",
    )


def sbs_tag_effectiveness_impl(as_findings: bool = False) -> TagEffectivenessResult:
    """Analyze auto-tag signal-to-noise ratio.

    Identifies noisy tags and tags correlated with actual problems.
    """
    from collections import Counter

    index = load_archive_index()
    if not index.entries:
        return TagEffectivenessResult(summary="No archive entries found.")

    entries = list(index.entries.values())
    total_entries = len(entries)

    if total_entries == 0:
        return TagEffectivenessResult(summary="No entries to analyze.")

    sessions = _group_entries_by_skill_session(entries)

    # Collect all auto_tags with frequency
    tag_freq: Counter = Counter()
    for entry in entries:
        for tag in entry.auto_tags or []:
            tag_freq[tag] += 1

    if not tag_freq:
        return TagEffectivenessResult(
            summary="No auto-tags found in archive entries.",
        )

    # Build sets of entry_ids involved in problems
    gate_failure_ids: set[str] = set()
    for entry in entries:
        gv = entry.gate_validation or {}
        if gv and not gv.get("passed", True):
            gate_failure_ids.add(entry.entry_id)

    backward_ids: set[str] = set()
    for session in sessions:
        expected = SKILL_PHASE_ORDERS.get(session.skill, [])
        backward = _detect_backward_transitions(session, expected)
        for entry_id, _, _ in backward:
            backward_ids.add(entry_id)

    error_note_ids: set[str] = set()
    error_keywords = ["error", "fail", "bug", "broken", "crash", "exception"]
    for entry in entries:
        notes = (entry.notes or "").lower()
        if any(kw in notes for kw in error_keywords):
            error_note_ids.add(entry.entry_id)

    # Per-tag analysis
    tag_entries: list[TagEffectivenessEntry] = []
    noisy_tags: list[str] = []
    signal_tags: list[str] = []

    for tag, freq in tag_freq.most_common():
        freq_pct = freq / total_entries

        # Count co-occurrences
        co_gate = 0
        co_backward = 0
        co_error = 0
        for entry in entries:
            if tag in (entry.auto_tags or []):
                if entry.entry_id in gate_failure_ids:
                    co_gate += 1
                if entry.entry_id in backward_ids:
                    co_backward += 1
                if entry.entry_id in error_note_ids:
                    co_error += 1

        # signal_score = sum(co_occurrences) / (frequency * 3)
        signal_score = (co_gate + co_backward + co_error) / (freq * 3) if freq > 0 else 0.0
        signal_score = min(signal_score, 1.0)

        # Classify
        if freq_pct > 0.8:
            classification = "noise"
            noisy_tags.append(tag)
        elif signal_score > 0.3:
            classification = "signal"
            signal_tags.append(tag)
        else:
            classification = "neutral"

        tag_entries.append(TagEffectivenessEntry(
            tag=tag,
            frequency=freq,
            frequency_pct=round(freq_pct, 3),
            co_occurs_with_gate_failure=co_gate,
            co_occurs_with_backward_transition=co_backward,
            co_occurs_with_error_notes=co_error,
            signal_score=round(signal_score, 3),
            classification=classification,
        ))

    findings: list[AnalysisFinding] = []
    if as_findings:
        if noisy_tags:
            findings.append(AnalysisFinding(
                pillar="system_engineering",
                category="tagging",
                severity="medium",
                description=f"Noisy tags (>80% frequency, low signal): {', '.join(noisy_tags)}",
                recommendation="Consider raising thresholds or removing these auto-tags",
                evidence=[],
            ))
        if signal_tags:
            findings.append(AnalysisFinding(
                pillar="system_engineering",
                category="tagging",
                severity="low",
                description=f"Signal tags (correlated with problems): {', '.join(signal_tags)}",
                recommendation="These tags are effective problem indicators; preserve and leverage them",
                evidence=[],
            ))

    return TagEffectivenessResult(
        tags=tag_entries,
        noisy_tags=noisy_tags,
        signal_tags=signal_tags,
        findings=findings,
        summary=f"Analyzed {len(tag_freq)} auto-tags: {len(noisy_tags)} noisy, {len(signal_tags)} signal.",
    )


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


# =============================================================================
# AskUserQuestion Analysis (Issue #75)
# =============================================================================


def _get_session_jsonl_files() -> list[tuple[str, "Path"]]:
    """Find all SBS session JSONL files.

    Returns list of (session_id, path) tuples.
    """
    from pathlib import Path
    from sbs.archive.extractor import get_sbs_project_dirs

    results = []
    for project_dir in get_sbs_project_dirs():
        for session_file in project_dir.glob("*.jsonl"):
            results.append((session_file.stem, session_file))
    return results


def _correlate_with_archive(
    timestamp: Optional[str], index
) -> tuple[Optional[str], Optional[str]]:
    """Find the active skill/substate at a given timestamp from archive entries.

    Returns (skill, substate) or (None, None) if no match.
    """
    if not timestamp or not index.entries:
        return None, None

    # Sort entries chronologically
    sorted_entries = sorted(index.entries.values(), key=lambda e: e.entry_id)

    # Find the most recent entry before this timestamp
    best_skill = None
    best_substate = None
    for entry in sorted_entries:
        # Entry IDs are unix timestamps; compare with ISO timestamp
        try:
            entry_time = datetime.fromisoformat(
                entry.created_at.replace("Z", "+00:00")
            )
            question_time = datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )
            if entry_time <= question_time:
                gs = entry.global_state or {}
                if gs.get("skill"):
                    best_skill = gs.get("skill")
                    best_substate = gs.get("substate")
        except (ValueError, TypeError):
            continue

    return best_skill, best_substate


def sbs_question_analysis_impl(
    since: Optional[str] = None,
    until: Optional[str] = None,
    skill: Optional[str] = None,
    limit: int = 50,
) -> QuestionAnalysisResult:
    """Extract AskUserQuestion interactions from session files.

    Scans JSONL session files for AskUserQuestion tool calls, links them
    with their tool_result answers, and correlates with archive state.
    """
    from pathlib import Path
    from sbs.archive.extractor import extract_ask_user_questions

    index = load_archive_index()
    session_files = _get_session_jsonl_files()

    all_interactions: list[QuestionInteraction] = []
    sessions_searched = 0

    for session_id, session_path in session_files:
        sessions_searched += 1
        raw_interactions = extract_ask_user_questions(session_path)

        for raw in raw_interactions:
            ts = raw.get("timestamp")

            # Filter by time range
            if since and ts and ts < since:
                continue
            if until and ts and ts > until:
                continue

            # Correlate with archive state
            active_skill, active_substate = _correlate_with_archive(ts, index)

            # Filter by skill
            if skill and active_skill != skill:
                continue

            interaction = QuestionInteraction(
                session_id=session_id,
                timestamp=ts,
                questions=raw.get("questions", []),
                answers=raw.get("answers", {}),
                context_before=raw.get("context_before"),
                skill=active_skill,
                substate=active_substate,
            )
            all_interactions.append(interaction)

    # Sort by timestamp descending (most recent first)
    all_interactions.sort(
        key=lambda i: i.timestamp or "", reverse=True
    )

    # Apply limit
    limited = all_interactions[:limit]

    return QuestionAnalysisResult(
        interactions=limited,
        total_found=len(all_interactions),
        sessions_searched=sessions_searched,
    )


def sbs_question_stats_impl(
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> QuestionStatsResult:
    """Aggregate statistics about AskUserQuestion usage patterns."""
    from collections import Counter
    from pathlib import Path
    from sbs.archive.extractor import extract_ask_user_questions

    index = load_archive_index()
    session_files = _get_session_jsonl_files()

    total_questions = 0
    skill_counts: Counter = Counter()
    header_counts: Counter = Counter()
    option_counts: Counter = Counter()
    multi_select_count = 0
    sessions_with = 0
    sessions_without = 0

    for session_id, session_path in session_files:
        raw_interactions = extract_ask_user_questions(session_path)

        if raw_interactions:
            sessions_with += 1
        else:
            sessions_without += 1

        for raw in raw_interactions:
            ts = raw.get("timestamp")

            # Filter by time range
            if since and ts and ts < since:
                continue
            if until and ts and ts > until:
                continue

            total_questions += 1

            # Correlate skill
            active_skill, _ = _correlate_with_archive(ts, index)
            if active_skill:
                skill_counts[active_skill] += 1
            else:
                skill_counts["none"] += 1

            # Analyze questions
            for q in raw.get("questions", []):
                header = q.get("header", "")
                if header:
                    header_counts[header] += 1

                if q.get("multiSelect", False):
                    multi_select_count += 1

            # Track selected options
            for question_text, answer in raw.get("answers", {}).items():
                option_counts[answer] += 1

    # Build most common options selected
    most_common = [
        {"option": opt, "count": cnt}
        for opt, cnt in option_counts.most_common(15)
    ]

    return QuestionStatsResult(
        total_questions=total_questions,
        questions_by_skill=dict(skill_counts),
        questions_by_header=dict(header_counts),
        most_common_options_selected=most_common,
        multi_select_usage=multi_select_count,
        sessions_with_questions=sessions_with,
        sessions_without_questions=sessions_without,
    )
