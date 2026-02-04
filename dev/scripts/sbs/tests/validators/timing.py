"""
Timing validator for build phase metrics collection and threshold enforcement.

This validator records build phase timings for analysis and optionally validates
against configured thresholds. Primarily used for metrics collection - it passes
by default unless explicit thresholds are exceeded.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from .base import BaseValidator, ValidationContext, ValidatorResult
from .registry import register_validator


def _parse_build_log_timings(log_path: Path) -> dict[str, float]:
    """Parse phase timings from a build log file.

    Looks for lines matching patterns like:
        - "Phase 'name' completed in X.XXs"
        - "[name] X.XX seconds"
        - "name: X.XXs"

    Args:
        log_path: Path to the build log file.

    Returns:
        Dictionary mapping phase names to durations in seconds.
    """
    if not log_path.exists():
        return {}

    timings: dict[str, float] = {}

    # Common timing patterns in build logs
    patterns = [
        # "Phase 'name' completed in 12.34s"
        re.compile(r"Phase '([^']+)' completed in ([\d.]+)s"),
        # "[name] 12.34 seconds"
        re.compile(r"\[([^\]]+)\]\s+([\d.]+)\s*seconds?"),
        # "name: 12.34s"
        re.compile(r"^(\w[\w\s-]*?):\s*([\d.]+)s\s*$", re.MULTILINE),
        # "name took 12.34s"
        re.compile(r"(\w[\w\s-]*?)\s+took\s+([\d.]+)s"),
    ]

    try:
        content = log_path.read_text()
        for pattern in patterns:
            for match in pattern.finditer(content):
                phase_name = match.group(1).strip()
                duration = float(match.group(2))
                # Keep first occurrence if duplicate
                if phase_name not in timings:
                    timings[phase_name] = duration
    except (OSError, ValueError):
        pass

    return timings


@register_validator
class TimingValidator(BaseValidator):
    """Validates and records build phase timing metrics.

    This validator collects timing data from either:
    1. Pre-computed phase_timings in context.extra
    2. Parsed from the build log file

    It always passes unless timing_thresholds are specified in context.extra
    and one or more phases exceed their threshold.

    Expected context.extra keys:
        phase_timings: dict[str, float] - Phase name to seconds mapping
        archive_timings: dict[str, float] - Archive operation timings
        timing_thresholds: dict[str, float] - Optional max seconds per phase
            Keys prefixed with "archive_" check archive_timings instead.

    Recorded metrics:
        phase_timings: dict[str, float] - All build phase durations
        total_seconds: float - Sum of all build phase times
        slowest_phase: str - Name of the slowest build phase
        slowest_duration: float - Duration of the slowest build phase
        archive_phase_timings: dict[str, float] - Archive operation durations
        archive_total_seconds: float - Sum of all archive phase times
        archive_slowest_phase: str - Name of the slowest archive phase
        archive_slowest_duration: float - Duration of the slowest archive phase
        threshold_violations: list[dict] - Phases exceeding thresholds
    """

    def __init__(self) -> None:
        super().__init__("timing", "timing")

    def validate(self, context: ValidationContext) -> ValidatorResult:
        """Collect timing metrics and validate against thresholds.

        Args:
            context: Validation context with optional phase_timings and
                timing_thresholds in the extra dict.

        Returns:
            ValidatorResult with timing metrics. Passes unless thresholds
            are defined and exceeded.
        """
        # Get timing data from context or parse from build log
        phase_timings: dict[str, float] = context.extra.get("phase_timings", {})

        if not phase_timings and context.build_log:
            phase_timings = _parse_build_log_timings(context.build_log)

        # Get archive timing data
        archive_timings: dict[str, float] = context.extra.get("archive_timings", {})

        # Calculate aggregate metrics for build phases
        total_seconds = sum(phase_timings.values()) if phase_timings else 0.0

        slowest_phase = ""
        slowest_duration = 0.0
        if phase_timings:
            slowest_phase = max(phase_timings, key=phase_timings.get)  # type: ignore
            slowest_duration = phase_timings[slowest_phase]

        # Check thresholds (split between build and archive phases)
        thresholds: dict[str, float] = context.extra.get("timing_thresholds", {})
        violations: list[dict[str, Any]] = []
        findings: list[str] = []

        for phase, threshold in thresholds.items():
            if phase.startswith("archive_"):
                # Archive phase threshold
                archive_phase = phase[len("archive_"):]
                actual = archive_timings.get(archive_phase, 0.0)
                if actual > threshold:
                    violations.append(
                        {
                            "phase": phase,
                            "actual": actual,
                            "threshold": threshold,
                            "exceeded_by": actual - threshold,
                        }
                    )
                    findings.append(
                        f"Archive phase '{archive_phase}' took {actual:.2f}s "
                        f"(threshold: {threshold:.2f}s, exceeded by {actual - threshold:.2f}s)"
                    )
            else:
                # Build phase threshold
                actual = phase_timings.get(phase)
                if actual is not None and actual > threshold:
                    violations.append(
                        {
                            "phase": phase,
                            "actual": actual,
                            "threshold": threshold,
                            "exceeded_by": actual - threshold,
                        }
                    )
                    findings.append(
                        f"Phase '{phase}' took {actual:.2f}s "
                        f"(threshold: {threshold:.2f}s, exceeded by {actual - threshold:.2f}s)"
                    )

        # Build metrics dict
        metrics: dict[str, Any] = {
            "phase_timings": phase_timings,
            "total_seconds": total_seconds,
            "slowest_phase": slowest_phase,
            "slowest_duration": slowest_duration,
            "threshold_violations": violations,
            "phase_count": len(phase_timings),
            "archive_phase_timings": archive_timings,
        }

        # Add archive aggregate metrics
        if archive_timings:
            metrics["archive_total_seconds"] = round(sum(archive_timings.values()), 3)
            archive_slowest = max(archive_timings, key=archive_timings.get)  # type: ignore
            metrics["archive_slowest_phase"] = archive_slowest
            metrics["archive_slowest_duration"] = archive_timings[archive_slowest]

        # Add summary findings even when passing
        if phase_timings and not violations:
            findings.append(
                f"Total build time: {total_seconds:.2f}s across {len(phase_timings)} phases"
            )
            if slowest_phase:
                findings.append(
                    f"Slowest phase: '{slowest_phase}' at {slowest_duration:.2f}s"
                )
        if archive_timings and not violations:
            archive_total = sum(archive_timings.values())
            findings.append(
                f"Archive time: {archive_total:.2f}s across {len(archive_timings)} phases"
            )

        # Pass if no thresholds violated (or no thresholds defined)
        passed = len(violations) == 0

        return self._make_result(
            passed=passed,
            findings=findings,
            metrics=metrics,
            confidence=1.0,  # Timing data is deterministic
            details={
                "thresholds_checked": len(thresholds),
                "phases_recorded": len(phase_timings),
            },
        )
