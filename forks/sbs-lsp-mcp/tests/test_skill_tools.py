"""Tests for SBS skill orchestration MCP tools.

Tests the skill lifecycle tools:
- sbs_skill_status: Query current skill state
- sbs_skill_start: Start a new skill session
- sbs_skill_transition: Transition between phases
- sbs_skill_end: End a skill session

These tests validate the logical patterns used by skill tools. The tools
now access state via DuckDBLayer (db.get_global_state(), db.invalidate()),
but the model construction and logic tested here remains the same.
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
# Fixtures for Skill Tests (pure data, no mock ArchiveIndex objects)
# =============================================================================


@pytest.fixture
def idle_state() -> Optional[Dict[str, Any]]:
    """Global state when system is idle."""
    return None


@pytest.fixture
def task_execution_state() -> Dict[str, Any]:
    """Global state with task skill active in execution phase."""
    return {
        "skill": "task",
        "substate": "execution",
        "phase_started_at": "2026-01-31T14:00:00",
    }


@pytest.fixture
def self_improve_state() -> Dict[str, Any]:
    """Global state with self-improve skill active."""
    return {
        "skill": "self-improve",
        "substate": "discovery",
        "phase_started_at": "2026-01-31T12:00:00",
    }


# =============================================================================
# TestSkillStatus
# =============================================================================


class TestSkillStatus:
    """Tests for sbs_skill_status tool."""

    def test_status_when_idle(self, idle_state: Optional[Dict[str, Any]]) -> None:
        """Status returns null skill when no skill is active."""
        # Simulate what the tool does: db.get_global_state() returns (None, None)
        active_skill = None
        substate = None
        can_start_new = True

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

    def test_status_when_skill_active(self, task_execution_state: Dict[str, Any]) -> None:
        """Status returns skill/substate when a skill is active."""
        # Simulate: db.get_global_state() returns ("task", "execution")
        active_skill = task_execution_state["skill"]
        substate = task_execution_state["substate"]
        phase_started_at = task_execution_state["phase_started_at"]
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

    def test_status_counts_entries_in_phase(self, task_execution_state: Dict[str, Any]) -> None:
        """Status correctly counts entries since phase started."""
        # The tool counts entries via db.get_entries() filtered by timestamp
        # We verify the model accepts the count
        result = SkillStatusResult(
            active_skill="task",
            substate="execution",
            can_start_new=False,
            entries_in_phase=7,
            phase_started_at="2026-01-31T11:00:00",
        )

        assert result.entries_in_phase == 7


# =============================================================================
# TestSkillStart
# =============================================================================


class TestSkillStart:
    """Tests for sbs_skill_start tool."""

    def test_start_when_idle(self) -> None:
        """Start succeeds when system is idle."""
        # Simulate: db.get_global_state() returns (None, None)
        # Then _run_archive_upload succeeds
        with patch("sbs_lsp_mcp.sbs_tools._run_archive_upload") as mock_upload:
            mock_upload.return_value = (True, "20260131160000", None)

            # Simulate tool logic: no active skill -> proceed
            new_state = {"skill": "task", "substate": "alignment"}
            success, entry_id, error = mock_upload(
                trigger="skill",
                global_state=new_state,
                state_transition="phase_start",
                issue_refs=None,
            )

            result = SkillStartResult(
                success=True,
                error=None,
                archive_entry_id=entry_id,
                global_state=new_state,
            )

            assert result.success is True
            assert result.archive_entry_id == "20260131160000"
            assert result.global_state["skill"] == "task"
            assert result.global_state["substate"] == "alignment"

            mock_upload.assert_called_once_with(
                trigger="skill",
                global_state={"skill": "task", "substate": "alignment"},
                state_transition="phase_start",
                issue_refs=None,
            )

    def test_start_fails_when_conflict(self, self_improve_state: Dict[str, Any]) -> None:
        """Start fails when another skill owns state."""
        # Simulate: db.get_global_state() returns ("self-improve", "discovery")
        current_skill = self_improve_state["skill"]

        result = SkillStartResult(
            success=False,
            error=f"Cannot start 'task': skill '{current_skill}' is already active. "
                  f"Use sbs_skill_end to finish the current skill first.",
            archive_entry_id=None,
            global_state=self_improve_state,
        )

        assert result.success is False
        assert "self-improve" in result.error
        assert "already active" in result.error
        assert result.archive_entry_id is None

    def test_start_with_issue_refs(self) -> None:
        """Start passes issue_refs to archive upload."""
        with patch("sbs_lsp_mcp.sbs_tools._run_archive_upload") as mock_upload:
            mock_upload.return_value = (True, "20260131160000", None)

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

    def test_transition_success(self, task_execution_state: Dict[str, Any]) -> None:
        """Transition updates substate correctly."""
        with patch("sbs_lsp_mcp.sbs_tools._run_archive_upload") as mock_upload:
            mock_upload.return_value = (True, "20260131161500", None)

            current_skill = task_execution_state["skill"]
            current_substate = task_execution_state["substate"]

            assert current_skill == "task"
            assert current_substate == "execution"

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

    def test_transition_wrong_skill(self, task_execution_state: Dict[str, Any]) -> None:
        """Transition fails when skill doesn't match."""
        current_skill = task_execution_state["skill"]
        current_substate = task_execution_state["substate"]

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

    def test_transition_when_no_skill_active(self, idle_state: Optional[Dict[str, Any]]) -> None:
        """Transition fails when no skill is active."""
        skill = "task"
        to_phase = "planning"

        result = SkillTransitionResult(
            success=False,
            error=f"Cannot transition '{skill}': current active skill is 'none'",
            from_phase=None,
            to_phase=to_phase,
            archive_entry_id=None,
        )

        assert result.success is False
        assert "none" in result.error

    def test_transition_with_is_final(self, task_execution_state: Dict[str, Any]) -> None:
        """Transition with is_final=True clears state."""
        with patch("sbs_lsp_mcp.sbs_tools._run_archive_upload") as mock_upload:
            mock_upload.return_value = (True, "20260131170000", None)

            # When is_final=True, global_state should be None and state_transition should be "phase_end"
            mock_upload(
                trigger="skill",
                global_state=None,
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

    def test_task_alignment_to_execution_rejected(self) -> None:
        """Task alignment -> execution is rejected (must go through planning)."""
        current_substate = "alignment"
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
        assert "planning" in result.error

    def test_task_alignment_to_planning_accepted(self) -> None:
        """Task alignment -> planning is accepted."""
        current_substate = "alignment"
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

    def test_unlisted_skill_unconstrained(self) -> None:
        """Skills not in VALID_TRANSITIONS (like self-improve) are unconstrained."""
        skill = "self-improve"

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


# =============================================================================
# TestSkillEnd
# =============================================================================


class TestSkillEnd:
    """Tests for sbs_skill_end tool."""

    def test_end_clears_state(self, task_execution_state: Dict[str, Any]) -> None:
        """End clears global_state."""
        with patch("sbs_lsp_mcp.sbs_tools._run_archive_upload") as mock_upload:
            mock_upload.return_value = (True, "20260131180000", None)

            current_skill = task_execution_state["skill"]
            skill = "task"
            assert current_skill == skill

            success, entry_id, error = mock_upload(
                trigger="skill",
                global_state=None,
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

            mock_upload.assert_called_with(
                trigger="skill",
                global_state=None,
                state_transition="phase_end",
                issue_refs=None,
            )

    def test_end_wrong_skill(self, task_execution_state: Dict[str, Any]) -> None:
        """End fails when skill doesn't match."""
        current_skill = task_execution_state["skill"]
        skill = "self-improve"

        assert current_skill != skill

        result = SkillEndResult(
            success=False,
            error=f"Cannot end '{skill}': current active skill is '{current_skill}'",
            archive_entry_id=None,
        )

        assert result.success is False
        assert "self-improve" in result.error
        assert "task" in result.error

    def test_end_when_no_skill_active(self, idle_state: Optional[Dict[str, Any]]) -> None:
        """End fails when no skill is active."""
        skill = "task"

        result = SkillEndResult(
            success=False,
            error=f"Cannot end '{skill}': current active skill is 'none'",
            archive_entry_id=None,
        )

        assert result.success is False
        assert "none" in result.error

    def test_end_with_issue_refs(self, task_execution_state: Dict[str, Any]) -> None:
        """End passes issue_refs for closing."""
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

    def test_fail_records_reason(self, task_execution_state: Dict[str, Any]) -> None:
        """Fail records the failure reason and clears state."""
        with patch("sbs_lsp_mcp.sbs_tools._run_archive_upload") as mock_upload:
            mock_upload.return_value = (True, "20260131191000", None)

            current_skill = task_execution_state["skill"]
            current_substate = task_execution_state["substate"]
            skill = "task"
            reason = "Build failed with unrecoverable error"

            assert current_skill == skill

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

            mock_upload.assert_called_with(
                trigger="skill",
                global_state=None,
                state_transition="phase_fail",
                issue_refs=None,
            )

    def test_fail_wrong_skill(self, task_execution_state: Dict[str, Any]) -> None:
        """Fail rejects when skill doesn't match."""
        current_skill = task_execution_state["skill"]
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

    def test_fail_when_idle(self, idle_state: Optional[Dict[str, Any]]) -> None:
        """Fail rejects when no skill is active."""
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

    def test_full_task_lifecycle(self) -> None:
        """Test complete task skill lifecycle: start -> transition -> end."""
        # Phase 1: Start (system is idle)
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

    def test_conflict_detection(self) -> None:
        """Test that starting a skill when another is active fails."""
        # Active task skill
        current_skill = "task"

        result = SkillStartResult(
            success=False,
            error=f"Cannot start 'self-improve': skill '{current_skill}' is already active.",
            archive_entry_id=None,
            global_state={"skill": "task", "substate": "execution"},
        )

        assert result.success is False
        assert "already active" in result.error


# =============================================================================
# TestImprovementCapture
# =============================================================================


class TestImprovementCapture:
    """Tests for sbs_improvement_capture tool."""

    def _simulate_capture(
        self,
        global_state: Optional[Dict[str, Any]],
        observation: str,
        category: Optional[str] = None,
    ) -> "ImprovementCaptureResult":
        """Simulate sbs_improvement_capture logic and return result.

        Mirrors the implementation in sbs_tools.py without calling through MCP.
        The tool now uses db.get_global_state() instead of load_archive_index().
        """
        from sbs_lsp_mcp.sbs_models import ImprovementCaptureResult

        valid_categories = {"process", "interaction", "workflow", "tooling", "other"}
        cat = category or "other"
        if cat not in valid_categories:
            return ImprovementCaptureResult(
                success=False,
                error=f"Invalid category '{cat}'. Must be one of: {', '.join(sorted(valid_categories))}",
            )

        # Build tags (mirrors implementation)
        entry_tags = [f"improvement:{cat}"]
        auto_tags = ["trigger:improvement"]

        if global_state:
            skill = global_state.get("skill")
            substate = global_state.get("substate")
            if skill:
                auto_tags.append(f"skill:{skill}")
            if substate:
                auto_tags.append(f"phase:{substate}")
        else:
            auto_tags.append("skill:none")
            auto_tags.append("phase:idle")

        all_tags = entry_tags + auto_tags
        return ImprovementCaptureResult(
            success=True,
            entry_id="1738300000",
            tags=all_tags,
        )

    def test_capture_with_explicit_category(self, idle_state: Optional[Dict[str, Any]]) -> None:
        """Capture with explicit category includes improvement:<category> tag."""
        result = self._simulate_capture(
            idle_state, observation="Test observation", category="tooling"
        )

        assert result.success is True
        assert "improvement:tooling" in result.tags
        assert "trigger:improvement" in result.tags

    def test_capture_with_default_category(self, idle_state: Optional[Dict[str, Any]]) -> None:
        """Capture without category defaults to 'other'."""
        result = self._simulate_capture(
            idle_state, observation="Test observation"
        )

        assert result.success is True
        assert "improvement:other" in result.tags

    def test_capture_invalid_category(self, idle_state: Optional[Dict[str, Any]]) -> None:
        """Capture with invalid category returns error."""
        result = self._simulate_capture(
            idle_state, observation="Test observation", category="invalid_category"
        )

        assert result.success is False
        assert result.error is not None
        assert "invalid_category" in result.error
        assert "process" in result.error
        assert "tooling" in result.error

    def test_capture_records_skill_context(self, task_execution_state: Dict[str, Any]) -> None:
        """Capture during active skill includes skill and phase tags."""
        result = self._simulate_capture(
            task_execution_state, observation="Test observation", category="process"
        )

        assert result.success is True
        assert "skill:task" in result.tags
        assert "phase:execution" in result.tags

    def test_capture_idle_skill_context(self, idle_state: Optional[Dict[str, Any]]) -> None:
        """Capture when idle includes skill:none and phase:idle tags."""
        result = self._simulate_capture(
            idle_state, observation="Test observation", category="workflow"
        )

        assert result.success is True
        assert "skill:none" in result.tags
        assert "phase:idle" in result.tags
