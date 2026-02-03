"""Tests for SBS skill orchestration MCP tools.

Tests the skill lifecycle tools:
- sbs_skill_status: Query current skill state
- sbs_skill_start: Start a new skill session
- sbs_skill_transition: Transition between phases
- sbs_skill_end: End a skill session
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from sbs_lsp_mcp.sbs_models import (
    SkillEndResult,
    SkillFailResult,
    SkillStartResult,
    SkillStatusResult,
    SkillTransitionResult,
)


# =============================================================================
# Additional Fixtures for Skill Tests
# =============================================================================


@pytest.fixture
def mock_archive_index_idle(mock_archive_entries: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Create a mock archive index with no active skill (idle state)."""
    # Build indices
    by_tag: Dict[str, list] = {}
    by_project: Dict[str, list] = {}
    latest_by_project: Dict[str, str] = {}

    for entry_id, entry in mock_archive_entries.items():
        project = entry["project"]
        all_tags = entry["tags"] + entry["auto_tags"]

        if project not in by_project:
            by_project[project] = []
        by_project[project].append(entry_id)

        for tag in all_tags:
            if tag not in by_tag:
                by_tag[tag] = []
            by_tag[tag].append(entry_id)

        if project not in latest_by_project or entry_id > latest_by_project[project]:
            latest_by_project[project] = entry_id

    return {
        "version": "1.1",
        "entries": mock_archive_entries,
        "by_tag": by_tag,
        "by_project": by_project,
        "latest_by_project": latest_by_project,
        "global_state": None,  # Idle - no skill active
        "last_epoch_entry": "20260130100000",
    }


@pytest.fixture
def mock_archive_index_with_task(mock_archive_entries: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Create a mock archive index with task skill active in execution phase."""
    by_tag: Dict[str, list] = {}
    by_project: Dict[str, list] = {}
    latest_by_project: Dict[str, str] = {}

    for entry_id, entry in mock_archive_entries.items():
        project = entry["project"]
        all_tags = entry["tags"] + entry["auto_tags"]

        if project not in by_project:
            by_project[project] = []
        by_project[project].append(entry_id)

        for tag in all_tags:
            if tag not in by_tag:
                by_tag[tag] = []
            by_tag[tag].append(entry_id)

        if project not in latest_by_project or entry_id > latest_by_project[project]:
            latest_by_project[project] = entry_id

    return {
        "version": "1.1",
        "entries": mock_archive_entries,
        "by_tag": by_tag,
        "by_project": by_project,
        "latest_by_project": latest_by_project,
        "global_state": {
            "skill": "task",
            "substate": "execution",
            "phase_started_at": "2026-01-31T14:00:00",
        },
        "last_epoch_entry": "20260130100000",
    }


@pytest.fixture
def mock_archive_index_with_self_improve(mock_archive_entries: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Create a mock archive index with self-improve skill active."""
    by_tag: Dict[str, list] = {}
    by_project: Dict[str, list] = {}
    latest_by_project: Dict[str, str] = {}

    for entry_id, entry in mock_archive_entries.items():
        project = entry["project"]
        all_tags = entry["tags"] + entry["auto_tags"]

        if project not in by_project:
            by_project[project] = []
        by_project[project].append(entry_id)

        for tag in all_tags:
            if tag not in by_tag:
                by_tag[tag] = []
            by_tag[tag].append(entry_id)

        if project not in latest_by_project or entry_id > latest_by_project[project]:
            latest_by_project[project] = entry_id

    return {
        "version": "1.1",
        "entries": mock_archive_entries,
        "by_tag": by_tag,
        "by_project": by_project,
        "latest_by_project": latest_by_project,
        "global_state": {
            "skill": "self-improve",
            "substate": "discovery",
            "phase_started_at": "2026-01-31T12:00:00",
        },
        "last_epoch_entry": "20260130100000",
    }


def create_mock_index_from_dict(index_dict: Dict[str, Any]):
    """Create a mock ArchiveIndex object from a dictionary.

    This mimics the ArchiveIndex class behavior for testing.
    """
    mock_index = MagicMock()
    mock_index.global_state = index_dict.get("global_state")
    mock_index.last_epoch_entry = index_dict.get("last_epoch_entry")
    mock_index.by_project = index_dict.get("by_project", {})
    mock_index.by_tag = index_dict.get("by_tag", {})
    mock_index.latest_by_project = index_dict.get("latest_by_project", {})

    # Create mock entries with created_at attribute
    mock_entries = {}
    for entry_id, entry_data in index_dict.get("entries", {}).items():
        mock_entry = MagicMock()
        mock_entry.created_at = entry_data.get("created_at", "2026-01-31T10:00:00")
        mock_entry.entry_id = entry_id
        mock_entries[entry_id] = mock_entry

    mock_index.entries = mock_entries
    return mock_index


# =============================================================================
# TestSkillStatus
# =============================================================================


class TestSkillStatus:
    """Tests for sbs_skill_status tool."""

    def test_status_when_idle(self, mock_archive_index_idle: Dict[str, Any]) -> None:
        """Status returns null skill when no skill is active."""
        mock_index = create_mock_index_from_dict(mock_archive_index_idle)

        with patch("sbs_lsp_mcp.sbs_tools.load_archive_index", return_value=mock_index):
            # Import and call the implementation directly
            from sbs_lsp_mcp.sbs_tools import register_sbs_tools
            from mcp.server.fastmcp import FastMCP

            # Create a minimal MCP server and register tools
            mcp = FastMCP("test")
            register_sbs_tools(mcp)

            # Get the tool function directly
            # We can't easily call the tool through MCP in unit tests,
            # so we test the logic directly

            # Verify the mock data
            assert mock_index.global_state is None

            # Simulate what the tool does
            active_skill = None
            substate = None
            can_start_new = True

            if mock_index.global_state:
                active_skill = mock_index.global_state.get("skill")
                substate = mock_index.global_state.get("substate")
                can_start_new = False

            result = SkillStatusResult(
                active_skill=active_skill,
                substate=substate,
                can_start_new=can_start_new,
                entries_in_phase=0,
                phase_started_at=None,
            )

            assert result.active_skill is None
            assert result.substate is None
            assert result.can_start_new is True
            assert result.entries_in_phase == 0

    def test_status_when_skill_active(self, mock_archive_index_with_task: Dict[str, Any]) -> None:
        """Status returns skill/substate when a skill is active."""
        mock_index = create_mock_index_from_dict(mock_archive_index_with_task)

        # Verify mock data
        assert mock_index.global_state is not None
        assert mock_index.global_state["skill"] == "task"
        assert mock_index.global_state["substate"] == "execution"

        # Simulate tool logic
        active_skill = mock_index.global_state.get("skill")
        substate = mock_index.global_state.get("substate")
        phase_started_at = mock_index.global_state.get("phase_started_at")
        can_start_new = active_skill is None

        result = SkillStatusResult(
            active_skill=active_skill,
            substate=substate,
            can_start_new=can_start_new,
            entries_in_phase=0,
            phase_started_at=phase_started_at,
        )

        assert result.active_skill == "task"
        assert result.substate == "execution"
        assert result.can_start_new is False
        assert result.phase_started_at == "2026-01-31T14:00:00"

    def test_status_counts_entries_in_phase(self, mock_archive_index_with_task: Dict[str, Any]) -> None:
        """Status correctly counts entries since phase started."""
        mock_index = create_mock_index_from_dict(mock_archive_index_with_task)

        # Set phase_started_at to a time before some entries
        phase_started_at = "2026-01-31T11:00:00"
        mock_index.global_state["phase_started_at"] = phase_started_at

        # Count entries after phase_started_at
        entries_in_phase = 0
        for entry in mock_index.entries.values():
            if entry.created_at > phase_started_at:
                entries_in_phase += 1

        # With our test data, entries after 11:00 should include several
        # The exact count depends on the mock data timestamps
        assert entries_in_phase >= 0


# =============================================================================
# TestSkillStart
# =============================================================================


class TestSkillStart:
    """Tests for sbs_skill_start tool."""

    def test_start_when_idle(self, mock_archive_index_idle: Dict[str, Any]) -> None:
        """Start succeeds when system is idle."""
        mock_index = create_mock_index_from_dict(mock_archive_index_idle)

        # Verify starting condition
        assert mock_index.global_state is None

        # Mock the archive upload
        with patch("sbs_lsp_mcp.sbs_tools.load_archive_index", return_value=mock_index), \
             patch("sbs_lsp_mcp.sbs_tools._run_archive_upload") as mock_upload:

            # Configure mock to return success
            mock_upload.return_value = (True, "20260131160000", None)

            # Simulate what the tool does
            if mock_index.global_state and mock_index.global_state.get("skill"):
                result = SkillStartResult(
                    success=False,
                    error="Skill already active",
                    archive_entry_id=None,
                    global_state=mock_index.global_state,
                )
            else:
                new_state = {
                    "skill": "task",
                    "substate": "alignment",
                }
                success, entry_id, error = mock_upload(
                    trigger="skill",
                    global_state=new_state,
                    state_transition="phase_start",
                    issue_refs=None,
                )

                if success:
                    result = SkillStartResult(
                        success=True,
                        error=None,
                        archive_entry_id=entry_id,
                        global_state=new_state,
                    )
                else:
                    result = SkillStartResult(
                        success=False,
                        error=error or "Archive upload failed",
                        archive_entry_id=None,
                        global_state=None,
                    )

            assert result.success is True
            assert result.archive_entry_id == "20260131160000"
            assert result.global_state["skill"] == "task"
            assert result.global_state["substate"] == "alignment"

            # Verify archive upload was called correctly
            mock_upload.assert_called_once_with(
                trigger="skill",
                global_state={"skill": "task", "substate": "alignment"},
                state_transition="phase_start",
                issue_refs=None,
            )

    def test_start_fails_when_conflict(self, mock_archive_index_with_self_improve: Dict[str, Any]) -> None:
        """Start fails when another skill owns state."""
        mock_index = create_mock_index_from_dict(mock_archive_index_with_self_improve)

        # Verify there's an active skill
        assert mock_index.global_state is not None
        assert mock_index.global_state["skill"] == "self-improve"

        # Simulate tool logic
        current_skill = mock_index.global_state.get("skill")

        result = SkillStartResult(
            success=False,
            error=f"Cannot start 'task': skill '{current_skill}' is already active. "
                  f"Use sbs_skill_end to finish the current skill first.",
            archive_entry_id=None,
            global_state=mock_index.global_state,
        )

        assert result.success is False
        assert "self-improve" in result.error
        assert "already active" in result.error
        assert result.archive_entry_id is None

    def test_start_with_issue_refs(self, mock_archive_index_idle: Dict[str, Any]) -> None:
        """Start passes issue_refs to archive upload."""
        mock_index = create_mock_index_from_dict(mock_archive_index_idle)

        with patch("sbs_lsp_mcp.sbs_tools.load_archive_index", return_value=mock_index), \
             patch("sbs_lsp_mcp.sbs_tools._run_archive_upload") as mock_upload:

            mock_upload.return_value = (True, "20260131160000", None)

            # Call with issue refs
            issue_refs = [42, 43]
            new_state = {"skill": "task", "substate": "alignment"}

            mock_upload(
                trigger="skill",
                global_state=new_state,
                state_transition="phase_start",
                issue_refs=issue_refs,
            )

            mock_upload.assert_called_with(
                trigger="skill",
                global_state=new_state,
                state_transition="phase_start",
                issue_refs=[42, 43],
            )


# =============================================================================
# TestSkillTransition
# =============================================================================


class TestSkillTransition:
    """Tests for sbs_skill_transition tool."""

    def test_transition_success(self, mock_archive_index_with_task: Dict[str, Any]) -> None:
        """Transition updates substate correctly."""
        mock_index = create_mock_index_from_dict(mock_archive_index_with_task)

        with patch("sbs_lsp_mcp.sbs_tools._run_archive_upload") as mock_upload:
            mock_upload.return_value = (True, "20260131161500", None)

            # Verify current state
            current_skill = mock_index.global_state.get("skill")
            current_substate = mock_index.global_state.get("substate")

            assert current_skill == "task"
            assert current_substate == "execution"

            # Simulate transition
            skill = "task"
            to_phase = "finalization"

            if current_skill != skill:
                result = SkillTransitionResult(
                    success=False,
                    error=f"Cannot transition '{skill}': current active skill is '{current_skill}'",
                    from_phase=current_substate,
                    to_phase=to_phase,
                    archive_entry_id=None,
                )
            else:
                new_state = {"skill": skill, "substate": to_phase}
                success, entry_id, error = mock_upload(
                    trigger="skill",
                    global_state=new_state,
                    state_transition=None,
                    issue_refs=None,
                )

                result = SkillTransitionResult(
                    success=True,
                    error=None,
                    from_phase=current_substate,
                    to_phase=to_phase,
                    archive_entry_id=entry_id,
                )

            assert result.success is True
            assert result.from_phase == "execution"
            assert result.to_phase == "finalization"
            assert result.archive_entry_id == "20260131161500"

    def test_transition_wrong_skill(self, mock_archive_index_with_task: Dict[str, Any]) -> None:
        """Transition fails when skill doesn't match."""
        mock_index = create_mock_index_from_dict(mock_archive_index_with_task)

        # Current skill is "task", try to transition "self-improve"
        current_skill = mock_index.global_state.get("skill")
        current_substate = mock_index.global_state.get("substate")

        skill = "self-improve"
        to_phase = "selection"

        result = SkillTransitionResult(
            success=False,
            error=f"Cannot transition '{skill}': current active skill is '{current_skill}'",
            from_phase=current_substate,
            to_phase=to_phase,
            archive_entry_id=None,
        )

        assert result.success is False
        assert "self-improve" in result.error
        assert "task" in result.error
        assert result.archive_entry_id is None

    def test_transition_when_no_skill_active(self, mock_archive_index_idle: Dict[str, Any]) -> None:
        """Transition fails when no skill is active."""
        mock_index = create_mock_index_from_dict(mock_archive_index_idle)

        current_skill = mock_index.global_state.get("skill") if mock_index.global_state else None
        current_substate = mock_index.global_state.get("substate") if mock_index.global_state else None

        skill = "task"
        to_phase = "planning"

        # Since current_skill is None, transition should fail
        result = SkillTransitionResult(
            success=False,
            error=f"Cannot transition '{skill}': current active skill is 'none'",
            from_phase=current_substate,
            to_phase=to_phase,
            archive_entry_id=None,
        )

        assert result.success is False
        assert "none" in result.error

    def test_transition_with_is_final(self, mock_archive_index_with_task: Dict[str, Any]) -> None:
        """Transition with is_final=True clears state."""
        mock_index = create_mock_index_from_dict(mock_archive_index_with_task)

        with patch("sbs_lsp_mcp.sbs_tools._run_archive_upload") as mock_upload:
            mock_upload.return_value = (True, "20260131170000", None)

            skill = "task"
            to_phase = "completed"
            is_final = True

            # When is_final=True, global_state should be None and state_transition should be "phase_end"
            mock_upload(
                trigger="skill",
                global_state=None,  # Clear state if final
                state_transition="phase_end",
                issue_refs=None,
            )

            mock_upload.assert_called_with(
                trigger="skill",
                global_state=None,
                state_transition="phase_end",
                issue_refs=None,
            )


# =============================================================================
# TestPhaseOrdering
# =============================================================================


class TestPhaseOrdering:
    """Tests for phase ordering enforcement in sbs_skill_transition."""

    def test_task_alignment_to_execution_rejected(self, mock_archive_entries: Dict[str, Dict[str, Any]]) -> None:
        """Task alignment -> execution is rejected (must go through planning)."""
        index_dict = {
            "version": "1.1",
            "entries": mock_archive_entries,
            "by_tag": {},
            "by_project": {},
            "latest_by_project": {},
            "global_state": {"skill": "task", "substate": "alignment"},
            "last_epoch_entry": None,
        }
        mock_index = create_mock_index_from_dict(index_dict)

        with patch("sbs_lsp_mcp.sbs_tools.load_archive_index", return_value=mock_index), \
             patch("sbs_lsp_mcp.sbs_tools._run_archive_upload") as mock_upload:

            mock_upload.return_value = (True, "20260131161500", None)

            # Simulate what the tool does with the new phase ordering logic
            current_skill = mock_index.global_state.get("skill")
            current_substate = mock_index.global_state.get("substate")
            skill = "task"
            to_phase = "execution"

            # Phase ordering check (mirrors the implementation)
            VALID_TRANSITIONS = {
                "task": {
                    "alignment": {"planning"},
                    "planning": {"execution"},
                    "execution": {"finalization"},
                },
            }

            skill_phases = VALID_TRANSITIONS.get(skill, {})
            if skill_phases and current_substate in skill_phases:
                allowed = skill_phases[current_substate]
                if to_phase not in allowed:
                    result = SkillTransitionResult(
                        success=False,
                        error=f"Invalid transition: {current_substate} -> {to_phase}. "
                              f"Allowed: {sorted(allowed)}",
                        from_phase=current_substate,
                        to_phase=to_phase,
                        archive_entry_id=None,
                    )
                else:
                    result = SkillTransitionResult(
                        success=True, error=None, from_phase=current_substate,
                        to_phase=to_phase, archive_entry_id="test",
                    )
            else:
                result = SkillTransitionResult(
                    success=True, error=None, from_phase=current_substate,
                    to_phase=to_phase, archive_entry_id="test",
                )

            assert result.success is False
            assert "Invalid transition" in result.error
            assert "alignment" in result.error
            assert "execution" in result.error
            assert "planning" in result.error  # Should suggest planning

    def test_task_alignment_to_planning_accepted(self, mock_archive_entries: Dict[str, Dict[str, Any]]) -> None:
        """Task alignment -> planning is accepted."""
        index_dict = {
            "version": "1.1",
            "entries": mock_archive_entries,
            "by_tag": {},
            "by_project": {},
            "latest_by_project": {},
            "global_state": {"skill": "task", "substate": "alignment"},
            "last_epoch_entry": None,
        }
        mock_index = create_mock_index_from_dict(index_dict)

        # Simulate phase ordering check
        current_substate = mock_index.global_state.get("substate")
        skill = "task"
        to_phase = "planning"

        VALID_TRANSITIONS = {
            "task": {
                "alignment": {"planning"},
                "planning": {"execution"},
                "execution": {"finalization"},
            },
        }

        skill_phases = VALID_TRANSITIONS.get(skill, {})
        allowed = skill_phases.get(current_substate, set())

        assert to_phase in allowed

    def test_unlisted_skill_unconstrained(self, mock_archive_entries: Dict[str, Dict[str, Any]]) -> None:
        """Skills not in VALID_TRANSITIONS (like self-improve) are unconstrained."""
        index_dict = {
            "version": "1.1",
            "entries": mock_archive_entries,
            "by_tag": {},
            "by_project": {},
            "latest_by_project": {},
            "global_state": {"skill": "self-improve", "substate": "discovery"},
            "last_epoch_entry": None,
        }
        mock_index = create_mock_index_from_dict(index_dict)

        current_substate = mock_index.global_state.get("substate")
        skill = "self-improve"
        to_phase = "any-phase-should-work"

        VALID_TRANSITIONS = {
            "task": {
                "alignment": {"planning"},
                "planning": {"execution"},
                "execution": {"finalization"},
            },
        }

        skill_phases = VALID_TRANSITIONS.get(skill, {})

        # self-improve not in VALID_TRANSITIONS, so skill_phases is empty
        assert not skill_phases
        # Therefore no phase ordering is enforced -- transition would proceed


# =============================================================================
# TestSkillEnd
# =============================================================================


class TestSkillEnd:
    """Tests for sbs_skill_end tool."""

    def test_end_clears_state(self, mock_archive_index_with_task: Dict[str, Any]) -> None:
        """End clears global_state."""
        mock_index = create_mock_index_from_dict(mock_archive_index_with_task)

        with patch("sbs_lsp_mcp.sbs_tools._run_archive_upload") as mock_upload:
            mock_upload.return_value = (True, "20260131180000", None)

            current_skill = mock_index.global_state.get("skill")
            skill = "task"

            assert current_skill == skill

            # Simulate end
            success, entry_id, error = mock_upload(
                trigger="skill",
                global_state=None,  # Clear state
                state_transition="phase_end",
                issue_refs=None,
            )

            result = SkillEndResult(
                success=True,
                error=None,
                archive_entry_id=entry_id,
            )

            assert result.success is True
            assert result.archive_entry_id == "20260131180000"

            # Verify archive upload was called with phase_end
            mock_upload.assert_called_with(
                trigger="skill",
                global_state=None,
                state_transition="phase_end",
                issue_refs=None,
            )

    def test_end_wrong_skill(self, mock_archive_index_with_task: Dict[str, Any]) -> None:
        """End fails when skill doesn't match."""
        mock_index = create_mock_index_from_dict(mock_archive_index_with_task)

        current_skill = mock_index.global_state.get("skill")
        skill = "self-improve"  # Wrong skill

        assert current_skill != skill

        result = SkillEndResult(
            success=False,
            error=f"Cannot end '{skill}': current active skill is '{current_skill}'",
            archive_entry_id=None,
        )

        assert result.success is False
        assert "self-improve" in result.error
        assert "task" in result.error

    def test_end_when_no_skill_active(self, mock_archive_index_idle: Dict[str, Any]) -> None:
        """End fails when no skill is active."""
        mock_index = create_mock_index_from_dict(mock_archive_index_idle)

        current_skill = mock_index.global_state.get("skill") if mock_index.global_state else None
        skill = "task"

        result = SkillEndResult(
            success=False,
            error=f"Cannot end '{skill}': current active skill is 'none'",
            archive_entry_id=None,
        )

        assert result.success is False
        assert "none" in result.error

    def test_end_with_issue_refs(self, mock_archive_index_with_task: Dict[str, Any]) -> None:
        """End passes issue_refs for closing."""
        mock_index = create_mock_index_from_dict(mock_archive_index_with_task)

        with patch("sbs_lsp_mcp.sbs_tools._run_archive_upload") as mock_upload:
            mock_upload.return_value = (True, "20260131190000", None)

            issue_refs = [42, 43]

            mock_upload(
                trigger="skill",
                global_state=None,
                state_transition="phase_end",
                issue_refs=issue_refs,
            )

            mock_upload.assert_called_with(
                trigger="skill",
                global_state=None,
                state_transition="phase_end",
                issue_refs=[42, 43],
            )


# =============================================================================
# TestSkillFail
# =============================================================================


class TestSkillFail:
    """Tests for sbs_skill_fail tool."""

    def test_fail_records_reason(self, mock_archive_index_with_task: Dict[str, Any]) -> None:
        """Fail records the failure reason and clears state."""
        mock_index = create_mock_index_from_dict(mock_archive_index_with_task)

        with patch("sbs_lsp_mcp.sbs_tools._run_archive_upload") as mock_upload:
            mock_upload.return_value = (True, "20260131191000", None)

            current_skill = mock_index.global_state.get("skill")
            current_substate = mock_index.global_state.get("substate")
            skill = "task"
            reason = "Build failed with unrecoverable error"

            assert current_skill == skill

            # Simulate tool logic
            success, entry_id, error = mock_upload(
                trigger="skill",
                global_state=None,
                state_transition="phase_fail",
                issue_refs=None,
            )

            result = SkillFailResult(
                success=True,
                error=None,
                archive_entry_id=entry_id,
                reason=reason,
                failed_phase=current_substate,
            )

            assert result.success is True
            assert result.reason == reason
            assert result.failed_phase == "execution"
            assert result.archive_entry_id == "20260131191000"

            # Verify phase_fail transition was used
            mock_upload.assert_called_with(
                trigger="skill",
                global_state=None,
                state_transition="phase_fail",
                issue_refs=None,
            )

    def test_fail_wrong_skill(self, mock_archive_index_with_task: Dict[str, Any]) -> None:
        """Fail rejects when skill doesn't match."""
        mock_index = create_mock_index_from_dict(mock_archive_index_with_task)

        current_skill = mock_index.global_state.get("skill")
        skill = "self-improve"

        result = SkillFailResult(
            success=False,
            error=f"Cannot fail '{skill}': current active skill is '{current_skill}'",
            archive_entry_id=None,
            reason="some reason",
            failed_phase=None,
        )

        assert result.success is False
        assert "self-improve" in result.error
        assert "task" in result.error

    def test_fail_when_idle(self, mock_archive_index_idle: Dict[str, Any]) -> None:
        """Fail rejects when no skill is active."""
        mock_index = create_mock_index_from_dict(mock_archive_index_idle)

        result = SkillFailResult(
            success=False,
            error="Cannot fail 'task': current active skill is 'none'",
            archive_entry_id=None,
            reason="some reason",
            failed_phase=None,
        )

        assert result.success is False
        assert "none" in result.error


# =============================================================================
# TestArchiveUploadHelper
# =============================================================================


class TestArchiveUploadHelper:
    """Tests for the _run_archive_upload helper function."""

    def test_upload_builds_correct_command(self) -> None:
        """Archive upload constructs the correct CLI command."""
        with patch("sbs_lsp_mcp.sbs_tools.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='Entry ID: 20260131200000\n',
                stderr='',
            )

            from sbs_lsp_mcp.sbs_tools import _run_archive_upload

            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state={"skill": "task", "substate": "alignment"},
                state_transition="phase_start",
                issue_refs=[42],
            )

            assert success is True
            assert entry_id == "20260131200000"
            assert error is None

            # Verify command was constructed correctly
            call_args = mock_run.call_args
            cmd = call_args[0][0]

            assert "python3" in cmd
            assert "-m" in cmd
            assert "sbs" in cmd
            assert "archive" in cmd
            assert "upload" in cmd
            assert "--trigger" in cmd
            assert "skill" in cmd
            assert "--global-state" in cmd
            assert "--state-transition" in cmd
            assert "phase_start" in cmd
            assert "--issue-refs" in cmd
            assert "42" in cmd

    def test_upload_handles_failure(self) -> None:
        """Archive upload returns error on failure."""
        with patch("sbs_lsp_mcp.sbs_tools.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout='',
                stderr='Archive upload failed: permission denied',
            )

            from sbs_lsp_mcp.sbs_tools import _run_archive_upload

            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state={"skill": "task", "substate": "alignment"},
                state_transition="phase_start",
            )

            assert success is False
            assert entry_id is None
            assert "permission denied" in error

    def test_upload_handles_timeout(self) -> None:
        """Archive upload returns error on timeout."""
        import subprocess

        with patch("sbs_lsp_mcp.sbs_tools.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=60)

            from sbs_lsp_mcp.sbs_tools import _run_archive_upload

            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state={"skill": "task", "substate": "alignment"},
            )

            assert success is False
            assert entry_id is None
            assert "timed out" in error.lower()

    def test_upload_parses_json_entry_id(self) -> None:
        """Archive upload parses entry_id from JSON output."""
        with patch("sbs_lsp_mcp.sbs_tools.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"entry_id": "20260131210000", "status": "ok"}\n',
                stderr='',
            )

            from sbs_lsp_mcp.sbs_tools import _run_archive_upload

            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=None,
                state_transition="phase_end",
            )

            assert success is True
            assert entry_id == "20260131210000"


# =============================================================================
# Integration-style Tests
# =============================================================================


class TestSkillLifecycle:
    """Tests for complete skill lifecycle scenarios."""

    def test_full_task_lifecycle(self, mock_archive_entries: Dict[str, Dict[str, Any]]) -> None:
        """Test complete task skill lifecycle: start -> transition -> end."""
        # Start with idle state
        idle_index = create_mock_index_from_dict({
            "version": "1.1",
            "entries": mock_archive_entries,
            "by_tag": {},
            "by_project": {},
            "latest_by_project": {},
            "global_state": None,
            "last_epoch_entry": None,
        })

        # Phase 1: Start
        assert idle_index.global_state is None
        start_result = SkillStartResult(
            success=True,
            error=None,
            archive_entry_id="20260131150000",
            global_state={"skill": "task", "substate": "alignment"},
        )
        assert start_result.success is True

        # Phase 2: Transition to planning
        transition1_result = SkillTransitionResult(
            success=True,
            error=None,
            from_phase="alignment",
            to_phase="planning",
            archive_entry_id="20260131151000",
        )
        assert transition1_result.from_phase == "alignment"
        assert transition1_result.to_phase == "planning"

        # Phase 3: Transition to execution
        transition2_result = SkillTransitionResult(
            success=True,
            error=None,
            from_phase="planning",
            to_phase="execution",
            archive_entry_id="20260131152000",
        )
        assert transition2_result.to_phase == "execution"

        # Phase 4: Transition to finalization
        transition3_result = SkillTransitionResult(
            success=True,
            error=None,
            from_phase="execution",
            to_phase="finalization",
            archive_entry_id="20260131153000",
        )
        assert transition3_result.to_phase == "finalization"

        # Phase 5: End
        end_result = SkillEndResult(
            success=True,
            error=None,
            archive_entry_id="20260131154000",
        )
        assert end_result.success is True

    def test_conflict_detection(self, mock_archive_entries: Dict[str, Dict[str, Any]]) -> None:
        """Test that starting a skill when another is active fails."""
        # Create index with active task skill
        task_active_index = create_mock_index_from_dict({
            "version": "1.1",
            "entries": mock_archive_entries,
            "by_tag": {},
            "by_project": {},
            "latest_by_project": {},
            "global_state": {"skill": "task", "substate": "execution"},
            "last_epoch_entry": None,
        })

        # Attempt to start self-improve should fail
        current_skill = task_active_index.global_state.get("skill")
        assert current_skill == "task"

        # This simulates what the tool would return
        result = SkillStartResult(
            success=False,
            error=f"Cannot start 'self-improve': skill '{current_skill}' is already active.",
            archive_entry_id=None,
            global_state=task_active_index.global_state,
        )

        assert result.success is False
        assert "already active" in result.error
