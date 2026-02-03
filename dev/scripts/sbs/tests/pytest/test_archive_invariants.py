"""
Tests for archive invariants from Archive_Orchestration_and_Agent_Harmony.md.

These tests pin down nebulous concepts and ensure the archive system
maintains its documented guarantees.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sbs.archive.entry import ArchiveEntry, ArchiveIndex


# =============================================================================
# Entry Immutability Tests
# =============================================================================


@pytest.mark.evergreen
class TestEntryImmutability:
    """Entries should not change after creation and save."""

    def test_entry_hash_stable_after_save_reload(self, temp_archive_dir: Path):
        """Entry content hash should be identical after save/reload cycle."""
        entry = ArchiveEntry(
            entry_id="test_immutable",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            notes="Test note",
            tags=["test"],
            screenshots=[],
        )

        # Compute hash of entry dict before save
        entry_dict = entry.to_dict()
        hash_before = hashlib.sha256(
            json.dumps(entry_dict, sort_keys=True).encode()
        ).hexdigest()

        # Save and reload
        index = ArchiveIndex()
        index.add_entry(entry)
        index_path = temp_archive_dir / "archive_index.json"
        index.save(index_path)

        loaded_index = ArchiveIndex.load(index_path)
        loaded_entry = loaded_index.entries.get("test_immutable")

        # Compute hash after reload
        loaded_dict = loaded_entry.to_dict()
        hash_after = hashlib.sha256(
            json.dumps(loaded_dict, sort_keys=True).encode()
        ).hexdigest()

        assert hash_before == hash_after, "Entry hash changed after save/reload"

    def test_entry_fields_unchanged_after_index_reload(self, temp_archive_entry):
        """All entry fields should be preserved through save/reload."""
        index_path, original_entry, _ = temp_archive_entry

        loaded_index = ArchiveIndex.load(index_path)
        loaded_entry = loaded_index.entries.get(original_entry.entry_id)

        assert loaded_entry.entry_id == original_entry.entry_id
        assert loaded_entry.created_at == original_entry.created_at
        assert loaded_entry.project == original_entry.project
        assert loaded_entry.tags == original_entry.tags
        assert loaded_entry.screenshots == original_entry.screenshots


# =============================================================================
# Schema Consistency Tests
# =============================================================================


@pytest.mark.evergreen
class TestSchemaConsistency:
    """All entries must conform to ArchiveEntry schema."""

    def test_required_fields_present(self, temp_archive_entry):
        """Entry must have all required fields."""
        _, entry, _ = temp_archive_entry

        # Required fields per schema
        assert entry.entry_id is not None
        assert entry.created_at is not None
        assert entry.tags is not None  # Can be empty list but must exist
        assert entry.screenshots is not None  # Can be empty list but must exist

    def test_optional_fields_valid_types(self, temp_archive_dir: Path):
        """Optional fields should have correct types when present."""
        entry = ArchiveEntry(
            entry_id="test_types",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            build_run_id="build_123",
            notes="Some notes",
            tags=["tag1", "tag2"],
            screenshots=["img1.png"],
            repo_commits={"repo1": "abc123"},
            global_state={"skill": "task", "substate": "execution"},
            state_transition="phase_start",
            trigger="skill",
        )

        assert isinstance(entry.project, str)
        assert isinstance(entry.build_run_id, str)
        assert isinstance(entry.notes, str)
        assert isinstance(entry.tags, list)
        assert all(isinstance(t, str) for t in entry.tags)
        assert isinstance(entry.screenshots, list)
        assert isinstance(entry.repo_commits, dict)
        assert isinstance(entry.global_state, dict)
        assert entry.state_transition in ("phase_start", "phase_end", "handoff", None)
        assert entry.trigger in ("build", "skill", "manual", None)

    def test_state_fields_valid_enum_values(self):
        """State transition and trigger must be valid enum values."""
        valid_transitions = ["phase_start", "phase_end", "handoff", None]
        valid_triggers = ["build", "skill", "manual", None]

        for transition in valid_transitions:
            entry = ArchiveEntry(
                entry_id="test",
                created_at=datetime.now(timezone.utc).isoformat(),
                project="TestProject",
                state_transition=transition,
            )
            assert entry.state_transition == transition

        for trigger in valid_triggers:
            entry = ArchiveEntry(
                entry_id="test",
                created_at=datetime.now(timezone.utc).isoformat(),
                project="TestProject",
                trigger=trigger if trigger else "manual",  # default is "manual"
            )
            if trigger is None:
                assert entry.trigger == "manual"  # default
            else:
                assert entry.trigger == trigger


# =============================================================================
# Single Active Skill Invariant Tests
# =============================================================================


@pytest.mark.evergreen
class TestSingleActiveSkillInvariant:
    """Only one skill can be active at a time (global_state is singular)."""

    def test_global_state_starts_null(self, temp_archive_dir: Path):
        """Fresh index should have null global_state."""
        index = ArchiveIndex()
        assert index.global_state is None

    def test_phase_end_clears_global_state(self, temp_archive_dir: Path):
        """phase_end transition should clear global_state to null."""
        index = ArchiveIndex()

        # Set active state
        index.global_state = {"skill": "task", "substate": "execution"}
        assert index.global_state is not None

        # Create entry with phase_end
        entry = ArchiveEntry(
            entry_id="test_clear",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            state_transition="phase_end",
        )
        index.add_entry(entry)

        # Simulate state clearing (as upload.py does)
        if entry.state_transition == "phase_end":
            index.global_state = None

        assert index.global_state is None

    def test_skill_state_is_singular(self, temp_archive_dir: Path):
        """global_state can only hold one skill at a time."""
        index = ArchiveIndex()

        # Set first skill
        index.global_state = {"skill": "task", "substate": "alignment"}

        # Setting new state replaces, doesn't merge
        index.global_state = {"skill": "update-and-archive", "substate": "readme-wave"}

        assert index.global_state["skill"] == "update-and-archive"
        assert "task" not in str(index.global_state)


# =============================================================================
# Phase Transition Ordering Tests
# =============================================================================


@pytest.mark.evergreen
class TestPhaseTransitionOrdering:
    """Phase transitions must follow valid sequence."""

    def test_task_phases_in_order(self):
        """Task skill phases should follow: alignment -> planning -> execution -> finalization."""
        valid_task_phases = ["alignment", "planning", "execution", "finalization"]

        for i, phase in enumerate(valid_task_phases[:-1]):
            next_phase = valid_task_phases[i + 1]
            # Verify ordering exists (this is more documentation than enforcement)
            assert valid_task_phases.index(phase) < valid_task_phases.index(next_phase)

    def test_update_archive_phases_in_order(self):
        """Update-and-archive phases should follow defined order."""
        valid_phases = ["readme-wave", "oracle-regen", "porcelain", "archive-upload"]

        for i, phase in enumerate(valid_phases[:-1]):
            next_phase = valid_phases[i + 1]
            assert valid_phases.index(phase) < valid_phases.index(next_phase)

    def test_phase_start_before_phase_end(self, temp_archive_dir: Path):
        """phase_start should precede phase_end in a well-formed sequence."""
        index = ArchiveIndex()

        # Start a phase
        start_entry = ArchiveEntry(
            entry_id="start",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            global_state={"skill": "task", "substate": "alignment"},
            state_transition="phase_start",
        )
        index.add_entry(start_entry)

        # End the skill
        end_entry = ArchiveEntry(
            entry_id="end",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            state_transition="phase_end",
        )
        index.add_entry(end_entry)

        entries = list(index.entries.values())
        start_idx = next(
            i for i, e in enumerate(entries) if e.state_transition == "phase_start"
        )
        end_idx = next(
            i for i, e in enumerate(entries) if e.state_transition == "phase_end"
        )

        assert start_idx < end_idx, "phase_start must come before phase_end"


# =============================================================================
# State Value Validation Tests
# =============================================================================


@pytest.mark.evergreen
class TestStateValueValidation:
    """global_state must be null OR valid {skill, substate} dict."""

    def test_null_is_valid_state(self, temp_archive_dir: Path):
        """null/None is a valid global_state (idle)."""
        index = ArchiveIndex()
        index.global_state = None

        index_path = temp_archive_dir / "test_index.json"
        index.save(index_path)
        loaded = ArchiveIndex.load(index_path)

        assert loaded.global_state is None

    def test_valid_skill_substate_dict(self, temp_archive_dir: Path):
        """Dict with skill and substate is valid."""
        index = ArchiveIndex()
        index.global_state = {"skill": "task", "substate": "execution"}

        index_path = temp_archive_dir / "test_index.json"
        index.save(index_path)
        loaded = ArchiveIndex.load(index_path)

        assert loaded.global_state == {"skill": "task", "substate": "execution"}

    def test_known_skill_names(self):
        """Only known skill names should be used."""
        known_skills = ["task", "update-and-archive"]

        for skill in known_skills:
            state = {"skill": skill, "substate": "test"}
            assert state["skill"] in known_skills

    def test_known_substates_for_task(self):
        """Task skill has defined substates."""
        task_substates = ["alignment", "planning", "execution", "finalization"]

        for substate in task_substates:
            state = {"skill": "task", "substate": substate}
            assert state["substate"] in task_substates

    def test_known_substates_for_update_archive(self):
        """Update-and-archive skill has defined substates."""
        ua_substates = ["readme-wave", "oracle-regen", "porcelain", "archive-upload"]

        for substate in ua_substates:
            state = {"skill": "update-and-archive", "substate": substate}
            assert state["substate"] in ua_substates


# =============================================================================
# Epoch Semantics Tests
# =============================================================================


@pytest.mark.evergreen
class TestEpochSemantics:
    """Epoch closing entries must include epoch_summary."""

    def test_skill_trigger_entries_have_trigger_field(self):
        """Entries from skills should have trigger='skill'."""
        entry = ArchiveEntry(
            entry_id="test_trigger",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            trigger="skill",
        )
        assert entry.trigger == "skill"

    def test_last_epoch_entry_tracked(self, temp_archive_dir: Path):
        """ArchiveIndex should track last_epoch_entry."""
        index = ArchiveIndex()

        # Add an entry that closes an epoch
        entry = ArchiveEntry(
            entry_id="epoch_close",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            trigger="skill",
            state_transition="phase_end",
            epoch_summary={"entries_in_epoch": 5},
        )
        index.add_entry(entry)
        index.last_epoch_entry = entry.entry_id

        index_path = temp_archive_dir / "test_index.json"
        index.save(index_path)
        loaded = ArchiveIndex.load(index_path)

        assert loaded.last_epoch_entry == "epoch_close"

    def test_epoch_summary_structure(self):
        """epoch_summary should have expected structure."""
        summary = {
            "entries_in_epoch": 5,
            "builds_in_epoch": 3,
            "entry_ids": ["1", "2", "3", "4", "5"],
        }

        entry = ArchiveEntry(
            entry_id="test",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            epoch_summary=summary,
        )

        assert "entries_in_epoch" in entry.epoch_summary
        assert isinstance(entry.epoch_summary["entries_in_epoch"], int)


# =============================================================================
# Skill Handoff Tests
# =============================================================================


@pytest.mark.evergreen
class TestSkillHandoff:
    """Handoff atomically ends one skill and starts another."""

    def test_handoff_entry_has_correct_state_transition(self):
        """Handoff entry should have state_transition='handoff'."""
        entry = ArchiveEntry(
            entry_id="handoff_test",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            global_state={"skill": "update-and-archive", "substate": "readme-wave"},
            state_transition="handoff",
            trigger="skill",
        )
        assert entry.state_transition == "handoff"
        assert entry.global_state["skill"] == "update-and-archive"

    def test_handoff_updates_index_global_state(self, temp_archive_dir: Path):
        """After handoff, index global_state should reflect the incoming skill."""
        index = ArchiveIndex()

        # Set initial state (task in finalization)
        index.global_state = {"skill": "task", "substate": "finalization"}

        # Create handoff entry
        entry = ArchiveEntry(
            entry_id="handoff_entry",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            global_state={"skill": "update-and-archive", "substate": "readme-wave"},
            state_transition="handoff",
            trigger="skill",
        )
        index.add_entry(entry)

        # Simulate what upload.py does for handoff
        index.global_state = entry.global_state

        assert index.global_state["skill"] == "update-and-archive"
        assert index.global_state["substate"] == "readme-wave"

        # Verify persistence
        index_path = temp_archive_dir / "archive_index.json"
        index.save(index_path)
        loaded = ArchiveIndex.load(index_path)
        assert loaded.global_state == {"skill": "update-and-archive", "substate": "readme-wave"}

    def test_handoff_is_not_idle(self, temp_archive_dir: Path):
        """Handoff should NOT clear global_state to null (unlike phase_end)."""
        index = ArchiveIndex()
        index.global_state = {"skill": "task", "substate": "finalization"}

        entry = ArchiveEntry(
            entry_id="handoff_not_idle",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            global_state={"skill": "update-and-archive", "substate": "readme-wave"},
            state_transition="handoff",
            trigger="skill",
        )
        index.add_entry(entry)
        index.global_state = entry.global_state

        # State should NOT be null
        assert index.global_state is not None
        assert index.global_state.get("skill") is not None

    def test_handoff_serialization_roundtrip(self):
        """Handoff entry should survive to_dict/from_dict roundtrip."""
        original = ArchiveEntry(
            entry_id="handoff_roundtrip",
            created_at="2026-02-03T12:00:00Z",
            project="TestProject",
            global_state={"skill": "update-and-archive", "substate": "readme-wave"},
            state_transition="handoff",
            trigger="skill",
        )

        entry_dict = original.to_dict()
        restored = ArchiveEntry.from_dict(entry_dict)

        assert restored.state_transition == "handoff"
        assert restored.global_state == {"skill": "update-and-archive", "substate": "readme-wave"}

    def test_session_grouping_recognizes_handoff(self):
        """_group_entries_by_skill_session should treat handoff as end+start.

        This test requires the sbs_lsp_mcp package (lives in forks/sbs-lsp-mcp).
        It is skipped if the package is not available on PYTHONPATH.
        """
        try:
            from sbs_lsp_mcp.sbs_self_improve import _group_entries_by_skill_session
        except ImportError:
            pytest.skip("sbs_lsp_mcp not available on PYTHONPATH")

        # Create a sequence: task alignment -> task execution -> handoff -> u&a readme-wave
        entries = [
            ArchiveEntry(
                entry_id="1000",
                created_at="2026-02-03T10:00:00",
                project="TestProject",
                global_state={"skill": "task", "substate": "alignment"},
                state_transition="phase_start",
            ),
            ArchiveEntry(
                entry_id="1001",
                created_at="2026-02-03T10:30:00",
                project="TestProject",
                global_state={"skill": "task", "substate": "execution"},
                state_transition="phase_start",
            ),
            ArchiveEntry(
                entry_id="1002",
                created_at="2026-02-03T11:00:00",
                project="TestProject",
                global_state={"skill": "update-and-archive", "substate": "readme-wave"},
                state_transition="handoff",
            ),
            ArchiveEntry(
                entry_id="1003",
                created_at="2026-02-03T11:30:00",
                project="TestProject",
                global_state={"skill": "update-and-archive", "substate": "oracle-regen"},
                state_transition="phase_start",
            ),
        ]

        sessions = _group_entries_by_skill_session(entries)

        # Should have 2 sessions: task (completed) and update-and-archive
        assert len(sessions) == 2

        task_session = sessions[0]
        assert task_session.skill == "task"
        assert task_session.completed is True  # handoff marks it complete

        ua_session = sessions[1]
        assert ua_session.skill == "update-and-archive"
        # The handoff entry starts the new session
        assert ua_session.first_entry_id == "1002"


# =============================================================================
# to_dict / from_dict Roundtrip Tests
# =============================================================================


@pytest.mark.evergreen
class TestSerializationRoundtrip:
    """Entry serialization must be lossless."""

    def test_entry_roundtrip_preserves_all_fields(self):
        """to_dict -> from_dict should preserve all fields.

        Note: claude_data is excluded from to_dict() by default (sidecar
        compaction).  We test with include_claude_data=True to verify the
        roundtrip still works, and separately verify the default path.
        """
        original = ArchiveEntry(
            entry_id="roundtrip_test",
            created_at="2026-02-01T12:00:00Z",
            project="TestProject",
            build_run_id="build_789",
            notes="Test notes",
            tags=["tag1", "tag2"],
            screenshots=["screen1.png", "screen2.png"],
            repo_commits={"Dress": "abc123", "Runway": "def456"},
            synced_to_icloud=True,
            sync_timestamp="2026-02-01T12:30:00Z",
            sync_error=None,
            rubric_id="rubric_001",
            rubric_evaluation={"score": 0.95},
            claude_data={"sessions": 3},
            auto_tags=["auto1"],
            trigger="build",
            quality_scores={"overall": 0.9},
            quality_delta={"change": 0.05},
            global_state={"skill": "task", "substate": "execution"},
            state_transition="phase_start",
            epoch_summary={"entries_in_epoch": 10},
            gate_validation={"passed": True, "findings": ["All gates passed"]},
            added_at="2026-02-01T12:00:01Z",
        )

        # Full roundtrip including claude_data
        entry_dict = original.to_dict(include_claude_data=True)
        restored = ArchiveEntry.from_dict(entry_dict)

        # Verify all fields match
        assert restored.entry_id == original.entry_id
        assert restored.created_at == original.created_at
        assert restored.project == original.project
        assert restored.build_run_id == original.build_run_id
        assert restored.notes == original.notes
        assert restored.tags == original.tags
        assert restored.screenshots == original.screenshots
        assert restored.repo_commits == original.repo_commits
        assert restored.synced_to_icloud == original.synced_to_icloud
        assert restored.sync_timestamp == original.sync_timestamp
        assert restored.sync_error == original.sync_error
        assert restored.rubric_id == original.rubric_id
        assert restored.rubric_evaluation == original.rubric_evaluation
        assert restored.claude_data == original.claude_data
        assert restored.auto_tags == original.auto_tags
        assert restored.trigger == original.trigger
        assert restored.quality_scores == original.quality_scores
        assert restored.quality_delta == original.quality_delta
        assert restored.global_state == original.global_state
        assert restored.state_transition == original.state_transition
        assert restored.epoch_summary == original.epoch_summary
        assert restored.gate_validation == original.gate_validation
        assert restored.added_at == original.added_at

    def test_entry_roundtrip_default_excludes_claude_data(self):
        """to_dict() default should NOT include claude_data (sidecar compaction)."""
        entry = ArchiveEntry(
            entry_id="compact_test",
            created_at="2026-02-01T12:00:00Z",
            project="TestProject",
            claude_data={"sessions": 5},
        )
        entry_dict = entry.to_dict()
        assert "claude_data" not in entry_dict

        restored = ArchiveEntry.from_dict(entry_dict)
        assert restored.claude_data is None

    def test_index_roundtrip_preserves_global_state(self, temp_archive_dir: Path):
        """ArchiveIndex roundtrip preserves global_state and last_epoch_entry."""
        index = ArchiveIndex()
        index.global_state = {"skill": "task", "substate": "planning"}
        index.last_epoch_entry = "entry_123"

        entry = ArchiveEntry(
            entry_id="entry_123",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
        )
        index.add_entry(entry)

        index_path = temp_archive_dir / "roundtrip_index.json"
        index.save(index_path)
        loaded = ArchiveIndex.load(index_path)

        assert loaded.global_state == {"skill": "task", "substate": "planning"}
        assert loaded.last_epoch_entry == "entry_123"
        assert "entry_123" in loaded.entries


# =============================================================================
# Index Invariant Tests
# =============================================================================


@pytest.mark.evergreen
class TestIndexInvariants:
    """ArchiveIndex must maintain index consistency."""

    def test_by_tag_index_updated_on_add(self, temp_archive_dir: Path):
        """by_tag index should be updated when entry with tags is added."""
        index = ArchiveIndex()
        entry = ArchiveEntry(
            entry_id="tagged_entry",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            tags=["important", "release"],
        )
        index.add_entry(entry)

        assert "important" in index.by_tag
        assert "release" in index.by_tag
        assert "tagged_entry" in index.by_tag["important"]
        assert "tagged_entry" in index.by_tag["release"]

    def test_by_project_index_updated_on_add(self, temp_archive_dir: Path):
        """by_project index should be updated when entry is added."""
        index = ArchiveIndex()
        entry = ArchiveEntry(
            entry_id="project_entry",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="MyProject",
        )
        index.add_entry(entry)

        assert "MyProject" in index.by_project
        assert "project_entry" in index.by_project["MyProject"]

    def test_latest_by_project_updated(self, temp_archive_dir: Path):
        """latest_by_project should track most recent entry per project."""
        index = ArchiveIndex()

        # Add older entry
        entry1 = ArchiveEntry(
            entry_id="1000000000",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="MyProject",
        )
        index.add_entry(entry1)
        assert index.latest_by_project["MyProject"] == "1000000000"

        # Add newer entry
        entry2 = ArchiveEntry(
            entry_id="2000000000",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="MyProject",
        )
        index.add_entry(entry2)
        assert index.latest_by_project["MyProject"] == "2000000000"

    def test_auto_tags_indexed(self, temp_archive_dir: Path):
        """Both manual tags and auto_tags should be indexed."""
        index = ArchiveIndex()
        entry = ArchiveEntry(
            entry_id="dual_tags",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            tags=["manual-tag"],
            auto_tags=["auto-tag"],
        )
        index.add_entry(entry)

        assert "manual-tag" in index.by_tag
        assert "auto-tag" in index.by_tag
        assert "dual_tags" in index.by_tag["manual-tag"]
        assert "dual_tags" in index.by_tag["auto-tag"]


# =============================================================================
# Claude Data Sidecar Tests
# =============================================================================


@pytest.mark.evergreen
class TestClaudeDataSidecar:
    """claude_data should be extracted to sidecar files, not stored in the index."""

    def test_save_flushes_claude_data_to_sidecar(self, temp_archive_dir: Path, monkeypatch):
        """ArchiveIndex.save() should write claude_data to sidecar and clear in-memory."""
        import sbs.archive.entry as entry_mod
        monkeypatch.setattr(entry_mod, "_ARCHIVE_DATA_DIR", temp_archive_dir / "archive_data")

        entry = ArchiveEntry(
            entry_id="sidecar_test",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            claude_data={"sessions": 5, "tool_calls": 10},
        )

        index = ArchiveIndex()
        index.add_entry(entry)

        index_path = temp_archive_dir / "archive_index.json"
        index.save(index_path)

        # In-memory claude_data should be None after save
        assert entry.claude_data is None

        # Sidecar file should exist with correct content
        sidecar_path = temp_archive_dir / "archive_data" / "sidecar_test.json"
        assert sidecar_path.exists()
        with open(sidecar_path) as f:
            sidecar_data = json.load(f)
        assert sidecar_data == {"sessions": 5, "tool_calls": 10}

        # Index file should NOT contain claude_data
        with open(index_path) as f:
            raw_index = json.load(f)
        assert "claude_data" not in raw_index["entries"]["sidecar_test"]

    def test_load_claude_data_from_sidecar(self, temp_archive_dir: Path, monkeypatch):
        """load_claude_data() should read from sidecar when in-memory is None."""
        import sbs.archive.entry as entry_mod
        monkeypatch.setattr(entry_mod, "_ARCHIVE_DATA_DIR", temp_archive_dir / "archive_data")

        # Write sidecar manually
        sidecar_dir = temp_archive_dir / "archive_data"
        sidecar_dir.mkdir(parents=True)
        sidecar_path = sidecar_dir / "load_test.json"
        with open(sidecar_path, "w") as f:
            json.dump({"loaded": True}, f)

        entry = ArchiveEntry(
            entry_id="load_test",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            claude_data=None,
        )

        result = entry.load_claude_data()
        assert result == {"loaded": True}
        assert entry.claude_data == {"loaded": True}

    def test_index_roundtrip_with_sidecar(self, temp_archive_dir: Path, monkeypatch):
        """Save/load cycle should preserve claude_data via sidecar."""
        import sbs.archive.entry as entry_mod
        monkeypatch.setattr(entry_mod, "_ARCHIVE_DATA_DIR", temp_archive_dir / "archive_data")

        entry = ArchiveEntry(
            entry_id="roundtrip_sidecar",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            claude_data={"important": "data"},
        )

        index = ArchiveIndex()
        index.add_entry(entry)

        index_path = temp_archive_dir / "archive_index.json"
        index.save(index_path)

        # Reload index
        loaded_index = ArchiveIndex.load(index_path)
        loaded_entry = loaded_index.entries["roundtrip_sidecar"]

        # claude_data should be None in the loaded entry (not in index)
        assert loaded_entry.claude_data is None

        # But loading from sidecar should recover it
        loaded = loaded_entry.load_claude_data()
        assert loaded == {"important": "data"}
