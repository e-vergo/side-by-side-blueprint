"""
Tests for the ledger health validator (T2).

T2: (Functional, Deterministic, Gradient)
Measures field population rate in archive entries.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sbs.archive.entry import ArchiveEntry, ArchiveIndex
from sbs.tests.validators.base import ValidationContext
from sbs.tests.validators.ledger_health import (
    DECLARED_FIELDS,
    LedgerHealthValidator,
    analyze_archive,
    analyze_entry,
    is_populated,
)


class TestIsPopulated:
    """Tests for the is_populated helper function."""

    def test_none_not_populated(self):
        """None is not populated."""
        assert is_populated(None) is False

    def test_empty_string_not_populated(self):
        """Empty string is not populated."""
        assert is_populated("") is False

    def test_empty_list_not_populated(self):
        """Empty list is not populated."""
        assert is_populated([]) is False

    def test_empty_dict_not_populated(self):
        """Empty dict is not populated."""
        assert is_populated({}) is False

    def test_false_is_populated(self):
        """False is a valid boolean value, so it's populated."""
        assert is_populated(False) is True

    def test_true_is_populated(self):
        """True is populated."""
        assert is_populated(True) is True

    def test_zero_is_populated(self):
        """Zero is a valid numeric value, so it's populated."""
        assert is_populated(0) is True

    def test_string_is_populated(self):
        """Non-empty string is populated."""
        assert is_populated("hello") is True

    def test_list_with_items_is_populated(self):
        """List with items is populated."""
        assert is_populated(["item"]) is True

    def test_dict_with_items_is_populated(self):
        """Dict with items is populated."""
        assert is_populated({"key": "value"}) is True


class TestAnalyzeEntry:
    """Tests for the analyze_entry function."""

    def test_fully_populated_entry(self):
        """Entry with all fields populated returns all True."""
        entry = {
            "entry_id": "123",
            "created_at": "2026-01-31T10:00:00",
            "project": "TestProject",
            "build_run_id": "build_456",
            "notes": "Some notes",
            "tags": ["tag1", "tag2"],
            "screenshots": ["screenshot.png"],
            "repo_commits": {"repo": "abc123"},
            "synced_to_icloud": True,
            "sync_timestamp": "2026-01-31T11:00:00",
            "sync_error": "Some error",
        }
        result = analyze_entry(entry)
        assert all(result.values())
        assert len(result) == len(DECLARED_FIELDS)

    def test_minimal_entry(self):
        """Entry with only required fields has correct population status."""
        entry = {
            "entry_id": "123",
            "created_at": "2026-01-31T10:00:00",
            "project": "TestProject",
            "build_run_id": None,
            "notes": "",
            "tags": [],
            "screenshots": [],
            "repo_commits": {},
            "synced_to_icloud": False,
            "sync_timestamp": None,
            "sync_error": None,
        }
        result = analyze_entry(entry)

        # Required fields are populated
        assert result["entry_id"] is True
        assert result["created_at"] is True
        assert result["project"] is True

        # Optional fields are not populated
        assert result["build_run_id"] is False
        assert result["notes"] is False
        assert result["tags"] is False
        assert result["screenshots"] is False
        assert result["repo_commits"] is False
        assert result["sync_timestamp"] is False
        assert result["sync_error"] is False

        # Boolean False counts as populated
        assert result["synced_to_icloud"] is True


class TestAnalyzeArchive:
    """Tests for the analyze_archive function."""

    def test_empty_archive(self, temp_archive_dir: Path):
        """Empty archive returns 0% population."""
        archive_path = temp_archive_dir / "archive_index.json"
        with open(archive_path, "w") as f:
            json.dump({"version": "1.0", "entries": {}}, f)

        result = analyze_archive(archive_path)

        assert result["population_rate"] == 0.0
        assert result["entries_analyzed"] == 0
        # All fields should be in unpopulated_fields (order-independent comparison)
        assert set(result["unpopulated_fields"]) == set(DECLARED_FIELDS)
        assert result["always_populated_fields"] == []

    def test_single_entry_archive(self, temp_archive_dir: Path):
        """Single entry archive calculates correct population rate."""
        entry = ArchiveEntry(
            entry_id="123",
            created_at="2026-01-31T10:00:00",
            project="TestProject",
            notes="Some notes",
            tags=["tag1"],
            screenshots=["screenshot.png"],
            repo_commits={"repo": "abc123"},
            synced_to_icloud=True,
            sync_timestamp="2026-01-31T11:00:00",
        )
        index = ArchiveIndex()
        index.add_entry(entry)
        archive_path = temp_archive_dir / "archive_index.json"
        index.save(archive_path)

        result = analyze_archive(archive_path)

        assert result["entries_analyzed"] == 1

        # Check specific field populations
        fp = result["field_population"]
        assert fp["entry_id"] == 1.0  # Always populated
        assert fp["created_at"] == 1.0  # Always populated
        assert fp["project"] == 1.0  # Always populated
        assert fp["notes"] == 1.0  # Populated in this entry
        assert fp["tags"] == 1.0  # Populated in this entry
        assert fp["screenshots"] == 1.0  # Populated in this entry
        assert fp["repo_commits"] == 1.0  # Populated in this entry
        assert fp["synced_to_icloud"] == 1.0  # Boolean True
        assert fp["sync_timestamp"] == 1.0  # Populated in this entry

        # Unpopulated fields
        assert fp["build_run_id"] == 0.0
        assert fp["sync_error"] == 0.0

        # Check population rate (9 populated / 11 total = 0.818...)
        assert 0.81 <= result["population_rate"] <= 0.82

    def test_identifies_unpopulated_fields(self, temp_archive_dir: Path):
        """Correctly identifies fields that are never populated."""
        # Create two entries, both missing compliance_run_id and stats_snapshot
        entries = []
        for i in range(2):
            entry = ArchiveEntry(
                entry_id=str(i),
                created_at="2026-01-31T10:00:00",
                project="TestProject",
                build_run_id="build_123",  # Populated
                notes="notes",
                tags=["tag"],
                screenshots=["screenshot.png"],
                repo_commits={"repo": "abc"},
                synced_to_icloud=True,
                sync_timestamp="2026-01-31T11:00:00",
            )
            entries.append(entry)

        index = ArchiveIndex()
        for entry in entries:
            index.add_entry(entry)
        archive_path = temp_archive_dir / "archive_index.json"
        index.save(archive_path)

        result = analyze_archive(archive_path)

        # sync_error should be identified as never populated
        assert "sync_error" in result["unpopulated_fields"]

    def test_mixed_population(self, temp_archive_dir: Path):
        """Fields partially populated have correct rates."""
        # First entry has notes, second doesn't
        entry1 = ArchiveEntry(
            entry_id="1",
            created_at="2026-01-31T10:00:00",
            project="TestProject",
            notes="Has notes",
        )
        entry2 = ArchiveEntry(
            entry_id="2",
            created_at="2026-01-31T11:00:00",
            project="TestProject",
            notes="",  # Empty
        )

        index = ArchiveIndex()
        index.add_entry(entry1)
        index.add_entry(entry2)
        archive_path = temp_archive_dir / "archive_index.json"
        index.save(archive_path)

        result = analyze_archive(archive_path)

        assert result["entries_analyzed"] == 2
        assert result["field_population"]["notes"] == 0.5  # 1 of 2


class TestLedgerHealthValidator:
    """Tests for the LedgerHealthValidator class."""

    def test_validator_properties(self):
        """Validator has correct name and category."""
        validator = LedgerHealthValidator()
        assert validator.name == "ledger-health"
        assert validator.category == "code"

    def test_missing_archive_fails(self, temp_archive_dir: Path):
        """Validator fails gracefully when archive doesn't exist."""
        validator = LedgerHealthValidator()
        context = ValidationContext(
            project="TestProject",
            project_root=temp_archive_dir,
            commit="abc123",
            extra={"archive_path": temp_archive_dir / "nonexistent.json"},
        )

        result = validator.validate(context)

        assert result.passed is False
        assert "not found" in result.findings[0]
        assert result.metrics["population_rate"] == 0.0
        assert result.confidence == 1.0

    def test_passes_with_high_population(self, temp_archive_dir: Path):
        """Validator passes when population rate exceeds threshold."""
        # Create a well-populated entry
        entry = ArchiveEntry(
            entry_id="123",
            created_at="2026-01-31T10:00:00",
            project="TestProject",
            build_run_id="build_456",
            notes="Some notes",
            tags=["tag1", "tag2"],
            screenshots=["screenshot.png"],
            repo_commits={"repo": "abc123"},
            synced_to_icloud=True,
            sync_timestamp="2026-01-31T11:00:00",
        )
        index = ArchiveIndex()
        index.add_entry(entry)
        archive_path = temp_archive_dir / "archive_index.json"
        index.save(archive_path)

        validator = LedgerHealthValidator()
        context = ValidationContext(
            project="TestProject",
            project_root=temp_archive_dir,
            commit="abc123",
            extra={
                "archive_path": archive_path,
                "population_threshold": 0.7,
            },
        )

        result = validator.validate(context)

        assert result.passed is True
        assert result.metrics["population_rate"] >= 0.7
        assert result.confidence == 1.0

    def test_fails_with_low_population(self, temp_archive_dir: Path):
        """Validator fails when population rate is below threshold."""
        # Create a minimal entry
        entry = ArchiveEntry(
            entry_id="123",
            created_at="2026-01-31T10:00:00",
            project="TestProject",
        )
        index = ArchiveIndex()
        index.add_entry(entry)
        archive_path = temp_archive_dir / "archive_index.json"
        index.save(archive_path)

        validator = LedgerHealthValidator()
        context = ValidationContext(
            project="TestProject",
            project_root=temp_archive_dir,
            commit="abc123",
            extra={
                "archive_path": archive_path,
                "population_threshold": 0.9,  # Very high threshold
            },
        )

        result = validator.validate(context)

        assert result.passed is False
        assert any("below threshold" in f for f in result.findings)

    def test_reports_unpopulated_fields(self, temp_archive_dir: Path):
        """Validator reports which fields are never populated."""
        entry = ArchiveEntry(
            entry_id="123",
            created_at="2026-01-31T10:00:00",
            project="TestProject",
        )
        index = ArchiveIndex()
        index.add_entry(entry)
        archive_path = temp_archive_dir / "archive_index.json"
        index.save(archive_path)

        validator = LedgerHealthValidator()
        context = ValidationContext(
            project="TestProject",
            project_root=temp_archive_dir,
            commit="abc123",
            extra={
                "archive_path": archive_path,
                "population_threshold": 0.0,  # Don't fail on threshold
            },
        )

        result = validator.validate(context)

        # Should report unpopulated fields
        assert any("never populated" in f for f in result.findings)
        assert "sync_error" in result.metrics["unpopulated_fields"]

    def test_with_real_archive_data(self):
        """Run against actual archive_index.json (integration test)."""
        from sbs.core.utils import ARCHIVE_DIR

        archive_path = ARCHIVE_DIR / "archive_index.json"
        if not archive_path.exists():
            pytest.skip("Real archive_index.json not found")

        validator = LedgerHealthValidator()
        context = ValidationContext(
            project="SBSTest",
            project_root=ARCHIVE_DIR.parent,
            commit="test",
            extra={"archive_path": archive_path},
        )

        result = validator.validate(context)

        # Verify we got meaningful results
        assert result.metrics["entries_analyzed"] > 0
        assert 0.0 <= result.metrics["population_rate"] <= 1.0
        assert result.confidence == 1.0

        # Print findings for visibility during development
        print(f"\nReal archive analysis:")
        print(f"  Entries analyzed: {result.metrics['entries_analyzed']}")
        print(f"  Population rate: {result.metrics['population_rate']:.1%}")
        print(f"  Unpopulated fields: {result.metrics['unpopulated_fields']}")
        print(f"  Always populated: {result.metrics['always_populated_fields']}")
        print(f"  Field breakdown:")
        for field, rate in sorted(result.metrics["field_population"].items()):
            print(f"    {field}: {rate:.1%}")

    def test_deterministic_results(self, temp_archive_dir: Path):
        """Same input always produces same output (deterministic test)."""
        entry = ArchiveEntry(
            entry_id="123",
            created_at="2026-01-31T10:00:00",
            project="TestProject",
            notes="Some notes",
            tags=["tag1"],
        )
        index = ArchiveIndex()
        index.add_entry(entry)
        archive_path = temp_archive_dir / "archive_index.json"
        index.save(archive_path)

        validator = LedgerHealthValidator()
        context = ValidationContext(
            project="TestProject",
            project_root=temp_archive_dir,
            commit="abc123",
            extra={"archive_path": archive_path},
        )

        # Run multiple times
        results = [validator.validate(context) for _ in range(5)]

        # All results should be identical
        first = results[0]
        for result in results[1:]:
            assert result.passed == first.passed
            assert result.metrics == first.metrics
            assert result.findings == first.findings
            assert result.confidence == first.confidence

    def test_threshold_is_configurable(self, temp_archive_dir: Path):
        """Population threshold can be configured via context.extra."""
        entry = ArchiveEntry(
            entry_id="123",
            created_at="2026-01-31T10:00:00",
            project="TestProject",
            synced_to_icloud=True,  # Only 4 of 14 fields populated = ~28%
        )
        index = ArchiveIndex()
        index.add_entry(entry)
        archive_path = temp_archive_dir / "archive_index.json"
        index.save(archive_path)

        validator = LedgerHealthValidator()

        # With low threshold, passes
        context_low = ValidationContext(
            project="TestProject",
            project_root=temp_archive_dir,
            commit="abc123",
            extra={
                "archive_path": archive_path,
                "population_threshold": 0.2,
            },
        )
        result_low = validator.validate(context_low)
        assert result_low.passed is True

        # With high threshold, fails
        context_high = ValidationContext(
            project="TestProject",
            project_root=temp_archive_dir,
            commit="abc123",
            extra={
                "archive_path": archive_path,
                "population_threshold": 0.9,
            },
        )
        result_high = validator.validate(context_high)
        assert result_high.passed is False
