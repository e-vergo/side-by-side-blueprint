"""
Ledger health validator: measures field population rate in archive entries.

T2: (Functional, Deterministic, Gradient)

This validator analyzes the archive_index.json to determine what percentage
of declared ArchiveEntry fields are actually populated. Fields that are
consistently empty represent either:
- Dead code (fields defined but never used)
- Missing functionality (fields that SHOULD be populated)

Population rate provides a gradient metric (0.0-1.0) indicating schema health.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .base import BaseValidator, ValidationContext, ValidatorResult
from .registry import register_validator


# All fields declared in ArchiveEntry (from archive/entry.py)
DECLARED_FIELDS = [
    "entry_id",
    "created_at",
    "project",
    "build_run_id",
    "compliance_run_id",
    "notes",
    "tags",
    "screenshots",
    "stats_snapshot",
    "chat_summary",
    "repo_commits",
    "synced_to_icloud",
    "sync_timestamp",
    "sync_error",
]


def is_populated(value: Any) -> bool:
    """Check if a field value is considered "populated".

    Populated means the field has meaningful content:
    - None -> not populated
    - "" (empty string) -> not populated
    - [] (empty list) -> not populated
    - {} (empty dict) -> not populated
    - False -> populated (valid boolean value)
    - 0 -> populated (valid numeric value)
    - Any other non-empty value -> populated
    """
    if value is None:
        return False
    if isinstance(value, str) and value == "":
        return False
    if isinstance(value, (list, dict)) and len(value) == 0:
        return False
    return True


def analyze_entry(entry: dict[str, Any]) -> dict[str, bool]:
    """Analyze a single entry and return field population status.

    Args:
        entry: Entry dict from archive_index.json

    Returns:
        Dict mapping field name to whether it's populated (True/False)
    """
    result = {}
    for field in DECLARED_FIELDS:
        value = entry.get(field)
        result[field] = is_populated(value)
    return result


def analyze_archive(archive_path: Path) -> dict[str, Any]:
    """Analyze archive_index.json and compute population metrics.

    Args:
        archive_path: Path to archive_index.json

    Returns:
        Dict with population metrics:
        - population_rate: float (0.0-1.0) overall population rate
        - entries_analyzed: int number of entries
        - field_population: dict mapping field -> population rate
        - unpopulated_fields: list of fields with 0% population
        - always_populated_fields: list of fields with 100% population
    """
    with open(archive_path) as f:
        data = json.load(f)

    entries = data.get("entries", {})
    if not entries:
        return {
            "population_rate": 0.0,
            "entries_analyzed": 0,
            "field_population": {},
            "unpopulated_fields": DECLARED_FIELDS.copy(),
            "always_populated_fields": [],
        }

    # Track counts per field
    field_counts: dict[str, int] = {field: 0 for field in DECLARED_FIELDS}
    total_entries = len(entries)

    for entry_id, entry in entries.items():
        field_status = analyze_entry(entry)
        for field, populated in field_status.items():
            if populated:
                field_counts[field] += 1

    # Compute per-field population rates
    field_population = {
        field: count / total_entries for field, count in field_counts.items()
    }

    # Identify problematic fields
    unpopulated_fields = [
        field for field, rate in field_population.items() if rate == 0.0
    ]
    always_populated_fields = [
        field for field, rate in field_population.items() if rate == 1.0
    ]

    # Overall population rate
    total_field_slots = total_entries * len(DECLARED_FIELDS)
    total_populated = sum(field_counts.values())
    population_rate = total_populated / total_field_slots if total_field_slots > 0 else 0.0

    return {
        "population_rate": population_rate,
        "entries_analyzed": total_entries,
        "field_population": field_population,
        "unpopulated_fields": sorted(unpopulated_fields),
        "always_populated_fields": sorted(always_populated_fields),
    }


@register_validator
class LedgerHealthValidator(BaseValidator):
    """Validator for measuring archive entry field population rate.

    This is a Gradient test - it returns a population_rate metric that
    can be tracked over time. The goal is to achieve 100% population rate
    by either populating all declared fields or removing unused ones.
    """

    def __init__(self) -> None:
        super().__init__("ledger-health", "code")

    def validate(self, context: ValidationContext) -> ValidatorResult:
        """Validate archive entry field population.

        Uses context.extra.get("archive_path") for the archive location,
        or falls back to the default archive directory.

        Configurable options via context.extra:
        - archive_path: Path to archive_index.json
        - population_threshold: Minimum required population rate (default: 0.7)

        Returns:
            ValidatorResult with population metrics and pass/fail status.
        """
        # Determine archive path
        archive_path: Optional[Path] = context.extra.get("archive_path")
        if archive_path is None:
            # Default to standard location relative to scripts directory
            from ..utils import ARCHIVE_DIR
            archive_path = ARCHIVE_DIR / "archive_index.json"

        if not archive_path.exists():
            return self._make_fail(
                findings=[f"Archive index not found: {archive_path}"],
                metrics={"population_rate": 0.0, "entries_analyzed": 0},
                confidence=1.0,
            )

        # Analyze the archive
        metrics = analyze_archive(archive_path)

        # Build findings
        findings: list[str] = []

        if metrics["unpopulated_fields"]:
            fields_str = ", ".join(metrics["unpopulated_fields"])
            findings.append(f"Fields never populated: {fields_str}")

        population_rate = metrics["population_rate"]
        threshold = context.extra.get("population_threshold", 0.7)
        passed = population_rate >= threshold

        if not passed:
            findings.append(
                f"Population rate {population_rate:.1%} below threshold {threshold:.1%}"
            )

        return self._make_result(
            passed=passed,
            findings=findings,
            metrics=metrics,
            confidence=1.0,  # Deterministic - exact same input always gives same output
            details={
                "threshold": threshold,
                "archive_path": str(archive_path),
            },
        )
