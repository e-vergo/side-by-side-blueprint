"""Tests for wall-clock time optimization infrastructure (#155)."""

import pytest
from pathlib import Path

from sbs.core.timing import TimingContext, format_duration, timing_summary
from sbs.build.caching import get_lean_sources_hash, has_lean_changes, save_lean_hash, load_lean_hash
from sbs.archive.entry import ArchiveEntry


@pytest.mark.evergreen
class TestTimingContext:
    """Tests for TimingContext context manager."""

    def test_basic_usage(self):
        """TimingContext records duration into dict."""
        import time
        timings = {}
        with TimingContext(timings, "test_op"):
            time.sleep(0.01)
        assert "test_op" in timings
        assert timings["test_op"] >= 0.01
        assert isinstance(timings["test_op"], float)

    def test_records_on_exception(self):
        """TimingContext records duration even when exception occurs."""
        timings = {}
        with pytest.raises(ValueError):
            with TimingContext(timings, "failing_op"):
                raise ValueError("test error")
        assert "failing_op" in timings
        assert timings["failing_op"] >= 0.0

    def test_multiple_keys(self):
        """Multiple TimingContext calls populate different keys."""
        timings = {}
        with TimingContext(timings, "op1"):
            pass
        with TimingContext(timings, "op2"):
            pass
        assert "op1" in timings
        assert "op2" in timings
        assert len(timings) == 2


@pytest.mark.evergreen
class TestFormatDuration:
    """Tests for format_duration utility."""

    def test_seconds_only(self):
        assert format_duration(0.5) == "0.5s"
        assert format_duration(45.3) == "45.3s"

    def test_minutes(self):
        result = format_duration(65.3)
        assert result == "1m 5.3s"

    def test_hours(self):
        result = format_duration(3661.0)
        assert result == "1h 1m 1.0s"

    def test_zero(self):
        assert format_duration(0.0) == "0.0s"


@pytest.mark.evergreen
class TestTimingSummary:
    """Tests for timing_summary utility."""

    def test_empty(self):
        assert timing_summary({}) == "(no timing data)"

    def test_single_entry(self):
        result = timing_summary({"extraction": 2.1})
        assert "extraction: 2.1s" in result
        assert "total: 2.1s" in result

    def test_multiple_entries(self):
        result = timing_summary({"a": 1.0, "b": 2.0})
        assert "a: 1.0s" in result
        assert "b: 2.0s" in result
        assert "total: 3.0s" in result


@pytest.mark.evergreen
class TestLeanSourceHash:
    """Tests for lean source change detection."""

    def test_hash_real_repo(self):
        """get_lean_sources_hash returns non-empty hash for Dress repo."""
        dress_path = Path(__file__).resolve().parents[5] / "toolchain" / "Dress"
        if dress_path.exists():
            result = get_lean_sources_hash(dress_path)
            assert len(result) == 16
            assert all(c in "0123456789abcdef" for c in result)

    def test_hash_empty_dir(self, tmp_path):
        """get_lean_sources_hash returns empty string for dir with no .lean files."""
        result = get_lean_sources_hash(tmp_path)
        assert result == ""

    def test_hash_deterministic(self):
        """Same repo path returns same hash."""
        dress_path = Path(__file__).resolve().parents[5] / "toolchain" / "Dress"
        if dress_path.exists():
            h1 = get_lean_sources_hash(dress_path)
            h2 = get_lean_sources_hash(dress_path)
            assert h1 == h2


@pytest.mark.evergreen
class TestLeanHashPersistence:
    """Tests for lean hash save/load."""

    def test_save_load_roundtrip(self, tmp_path):
        """save_lean_hash + load_lean_hash preserves hash."""
        save_lean_hash(tmp_path, "test_repo", "abc123def456")
        loaded = load_lean_hash(tmp_path, "test_repo")
        assert loaded == "abc123def456"

    def test_load_missing(self, tmp_path):
        """load_lean_hash returns None for non-existent hash."""
        result = load_lean_hash(tmp_path, "nonexistent")
        assert result is None

    def test_has_lean_changes_first_build(self, tmp_path):
        """has_lean_changes returns True on first build (no saved hash)."""
        import subprocess
        # Create a git repo with a tracked .lean file so get_lean_sources_hash finds it
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        lean_file = tmp_path / "Test.lean"
        lean_file.write_text("-- test")
        subprocess.run(["git", "add", "Test.lean"], cwd=tmp_path, capture_output=True, check=True)
        result = has_lean_changes(tmp_path, tmp_path / "cache", "test_repo")
        assert result is True

    def test_has_lean_changes_no_change(self, tmp_path):
        """has_lean_changes returns False when hash matches."""
        import subprocess
        # Create a git repo with a tracked .lean file
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        lean_file = tmp_path / "Test.lean"
        lean_file.write_text("-- test content")
        subprocess.run(["git", "add", "Test.lean"], cwd=tmp_path, capture_output=True, check=True)

        cache_dir = tmp_path / "cache"
        # Compute and save the hash
        from sbs.build.caching import get_lean_sources_hash
        h = get_lean_sources_hash(tmp_path)
        save_lean_hash(cache_dir, "test_repo", h)

        # Check again -- should show no changes
        result = has_lean_changes(tmp_path, cache_dir, "test_repo")
        assert result is False


@pytest.mark.evergreen
class TestArchiveEntryTimings:
    """Tests for archive_timings field on ArchiveEntry."""

    def test_default_empty(self):
        """New ArchiveEntry has empty archive_timings."""
        entry = ArchiveEntry(entry_id="1", created_at="2025-01-01", project="test")
        assert entry.archive_timings == {}

    def test_roundtrip_serialization(self):
        """archive_timings survives to_dict/from_dict."""
        entry = ArchiveEntry(
            entry_id="1", created_at="2025-01-01", project="test",
            archive_timings={"extraction": 2.1, "porcelain": 5.3},
        )
        d = entry.to_dict()
        assert d["archive_timings"] == {"extraction": 2.1, "porcelain": 5.3}

        restored = ArchiveEntry.from_dict(d)
        assert restored.archive_timings == {"extraction": 2.1, "porcelain": 5.3}

    def test_old_entry_compat(self):
        """Entries without archive_timings deserialize with empty dict."""
        d = {
            "entry_id": "1",
            "created_at": "2025-01-01",
            "project": "test",
            # No archive_timings key
        }
        entry = ArchiveEntry.from_dict(d)
        assert entry.archive_timings == {}
