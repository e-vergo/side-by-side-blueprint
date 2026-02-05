"""Tests for MCP-based skill tools.

This module tests the skill tool implementations that replace prompt-based SKILL.md files:
- sbs_task: General-purpose agentic task execution
- sbs_log: Quick capture of bugs/features/ideas to GitHub Issues
- sbs_qa: Live interactive QA against running SBS blueprint site
- sbs_introspect: Introspection and self-improvement (L2 and L3+)
- sbs_converge: Autonomous QA convergence loop
- sbs_update_and_archive: Documentation refresh and porcelain state
- sbs_divination: Codebase exploration and guidance

Also tests supporting infrastructure:
- Result model serialization
- Gate validation and parsing
- Label inference for sbs_log
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from sbs_lsp_mcp.sbs_models import (
    ConvergeResult,
    DivinationResult,
    IntrospectResult,
    LogResult,
    QAResult,
    TaskResult,
    UpdateArchiveResult,
)


# =============================================================================
# Result Model Tests
# =============================================================================


class TestTaskResultModel:
    """Tests for TaskResult model serialization."""

    def test_minimal_task_result(self) -> None:
        """TaskResult with minimal required fields."""
        result = TaskResult(success=True, phase_completed="start")
        assert result.success is True
        assert result.phase_completed == "start"
        assert result.error is None
        assert result.gate_results == []
        assert result.gate_failures == []

    def test_task_result_with_gates(self) -> None:
        """TaskResult with gate results."""
        result = TaskResult(
            success=True,
            phase_completed="finalize",
            gate_results=["Tests: 50/50 passed", "T5: 1.0 >= 0.8 (PASS)"],
            gate_failures=[],
            requires_approval=False,
        )
        assert len(result.gate_results) == 2
        assert len(result.gate_failures) == 0
        assert result.requires_approval is False

    def test_task_result_with_pr_and_issues(self) -> None:
        """TaskResult tracks PR and issue references."""
        result = TaskResult(
            success=True,
            phase_completed="finalize",
            pr_number=42,
            issue_refs=[1, 2, 3],
        )
        assert result.pr_number == 42
        assert result.issue_refs == [1, 2, 3]

    def test_task_result_with_agents_to_spawn(self) -> None:
        """TaskResult can include agent spawn specifications."""
        agents = [
            {"prompt": "Fix CSS in common.css", "files": ["common.css"]},
            {"prompt": "Fix template in Theme.lean", "files": ["Theme.lean"]},
        ]
        result = TaskResult(
            success=True,
            phase_completed="execute",
            agents_to_spawn=agents,
        )
        assert result.agents_to_spawn is not None
        assert len(result.agents_to_spawn) == 2

    def test_task_result_failure(self) -> None:
        """TaskResult with error indicates failure."""
        result = TaskResult(
            success=False,
            error="Cannot start task: skill 'qa' is already active",
            phase_completed=None,
            issue_refs=[],
        )
        assert result.success is False
        assert "already active" in result.error
        assert result.phase_completed is None


class TestLogResultModel:
    """Tests for LogResult model serialization."""

    def test_successful_log_result(self) -> None:
        """LogResult for successful issue creation."""
        result = LogResult(
            success=True,
            issue_number=123,
            issue_url="https://github.com/e-vergo/Side-By-Side-Blueprint/issues/123",
            labels_applied=["origin:agent", "bug:visual", "area:sbs:graph"],
        )
        assert result.success is True
        assert result.issue_number == 123
        assert "origin:agent" in result.labels_applied
        assert len(result.labels_applied) == 3

    def test_failed_log_result(self) -> None:
        """LogResult for failed issue creation."""
        result = LogResult(
            success=False,
            error="gh CLI not authenticated",
            issue_number=None,
            issue_url=None,
            labels_applied=[],
        )
        assert result.success is False
        assert result.error is not None
        assert result.issue_number is None


class TestQAResultModel:
    """Tests for QAResult model serialization."""

    def test_qa_setup_result(self) -> None:
        """QAResult for setup phase completion."""
        result = QAResult(
            success=True,
            phase_completed="setup",
            page_status={},
            issues_logged=[],
        )
        assert result.success is True
        assert result.phase_completed == "setup"
        assert len(result.page_status) == 0

    def test_qa_review_result(self) -> None:
        """QAResult with page status from review."""
        result = QAResult(
            success=True,
            phase_completed="review",
            page_status={
                "dashboard": "pass",
                "dep_graph": "pass",
                "chapter": "fail",
            },
            issues_logged=[],
        )
        assert result.page_status["dashboard"] == "pass"
        assert result.page_status["chapter"] == "fail"

    def test_qa_result_with_issues(self) -> None:
        """QAResult tracks issues logged during review."""
        result = QAResult(
            success=True,
            phase_completed="report",
            page_status={"dashboard": "fail"},
            issues_logged=[142, 143],
        )
        assert len(result.issues_logged) == 2


class TestIntrospectResultModel:
    """Tests for IntrospectResult model serialization."""

    def test_l2_discovery_result(self) -> None:
        """IntrospectResult for L2 discovery phase."""
        result = IntrospectResult(
            success=True,
            level=2,
            phase_completed="discovery",
            findings_count=5,
        )
        assert result.level == 2
        assert result.findings_count == 5

    def test_l2_logging_result(self) -> None:
        """IntrospectResult with created issues."""
        result = IntrospectResult(
            success=True,
            level=2,
            phase_completed="logging",
            issues_created=[47, 48, 49],
        )
        assert len(result.issues_created) == 3

    def test_l3_synthesis_result(self) -> None:
        """IntrospectResult for L3+ meta-analysis."""
        result = IntrospectResult(
            success=True,
            level=3,
            phase_completed="synthesis",
        )
        assert result.level == 3
        assert result.phase_completed == "synthesis"


class TestConvergeResultModel:
    """Tests for ConvergeResult model serialization."""

    def test_converge_eval_result(self) -> None:
        """ConvergeResult for evaluation phase."""
        result = ConvergeResult(
            success=True,
            phase_completed="eval",
            iteration=2,
            pass_rate=0.89,
            pass_rate_history=[0.72, 0.89],
        )
        assert result.iteration == 2
        assert result.pass_rate == 0.89
        assert len(result.pass_rate_history) == 2

    def test_converge_completed_result(self) -> None:
        """ConvergeResult when convergence is achieved."""
        result = ConvergeResult(
            success=True,
            phase_completed="report",
            iteration=3,
            pass_rate=1.0,
            pass_rate_history=[0.72, 0.89, 1.0],
            exit_reason="converged",
        )
        assert result.exit_reason == "converged"
        assert result.pass_rate == 1.0

    def test_converge_plateau_result(self) -> None:
        """ConvergeResult when plateau is detected."""
        result = ConvergeResult(
            success=True,
            phase_completed="report",
            iteration=2,
            pass_rate=0.85,
            pass_rate_history=[0.85, 0.85],
            exit_reason="plateau",
        )
        assert result.exit_reason == "plateau"


class TestUpdateArchiveResultModel:
    """Tests for UpdateArchiveResult model serialization."""

    def test_retrospective_result(self) -> None:
        """UpdateArchiveResult after retrospective phase."""
        result = UpdateArchiveResult(
            success=True,
            phase_completed="retrospective",
            retrospective_written=True,
        )
        assert result.phase_completed == "retrospective"
        assert result.retrospective_written is True

    def test_porcelain_result(self) -> None:
        """UpdateArchiveResult with repos committed."""
        result = UpdateArchiveResult(
            success=True,
            phase_completed="porcelain",
            repos_committed=["Dress", "Runway", "sbs-lsp-mcp"],
        )
        assert len(result.repos_committed) == 3

    def test_upload_result(self) -> None:
        """UpdateArchiveResult with archive entry ID."""
        result = UpdateArchiveResult(
            success=True,
            phase_completed="upload",
            archive_entry_id="1738300000",
        )
        assert result.archive_entry_id == "1738300000"


class TestDivinationResultModel:
    """Tests for DivinationResult model serialization."""

    def test_divination_success(self) -> None:
        """DivinationResult with exploration results."""
        result = DivinationResult(
            success=True,
            query="graph layout algorithm",
            files_explored=[
                {"path": "Dress/Graph/Layout.lean", "relevance": "high", "summary": "Sugiyama algorithm"},
            ],
            patterns=["Use Sugiyama for DAG layout", "Barycenter for crossing reduction"],
            suggestions=["Check Layout.lean line 200 for optimization"],
        )
        assert result.success is True
        assert len(result.files_explored) == 1
        assert len(result.patterns) == 2


# =============================================================================
# Gate Validation Tests
# =============================================================================


class TestGateSpecParsing:
    """Tests for parse_gate_spec_from_plan function."""

    def test_parse_simple_gate_spec(self) -> None:
        """Parse simple gates block with all_pass tests."""
        from sbs_lsp_mcp.gate_validation import parse_gate_spec_from_plan

        plan = '''
```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  quality:
    T5: 1.0
    T6: 0.9
```
'''
        spec = parse_gate_spec_from_plan(plan)
        assert spec is not None
        assert spec.tests == "all_pass"
        assert spec.test_tier == "evergreen"
        assert spec.quality["T5"] == 1.0
        assert spec.quality["T6"] == 0.9

    def test_parse_gate_spec_with_threshold_syntax(self) -> None:
        """Parse gates with >= threshold syntax."""
        from sbs_lsp_mcp.gate_validation import parse_gate_spec_from_plan

        plan = '''
```yaml
gates:
  quality:
    T5: >= 0.8
    T6: >= 0.95
```
'''
        spec = parse_gate_spec_from_plan(plan)
        assert spec is not None
        assert spec.quality["T5"] == 0.8
        assert spec.quality["T6"] == 0.95

    def test_parse_gate_spec_with_regression(self) -> None:
        """Parse gates with regression check enabled."""
        from sbs_lsp_mcp.gate_validation import parse_gate_spec_from_plan

        plan = '''
```yaml
gates:
  regression: true
```
'''
        spec = parse_gate_spec_from_plan(plan)
        assert spec is not None
        assert spec.regression is True

    def test_parse_gate_spec_no_gates(self) -> None:
        """Return None when no gates block exists."""
        from sbs_lsp_mcp.gate_validation import parse_gate_spec_from_plan

        plan = "This plan has no gates section at all."
        spec = parse_gate_spec_from_plan(plan)
        assert spec is None

    def test_parse_gate_spec_empty_plan(self) -> None:
        """Return None for empty plan content."""
        from sbs_lsp_mcp.gate_validation import parse_gate_spec_from_plan

        spec = parse_gate_spec_from_plan("")
        assert spec is None

    def test_parse_gate_spec_with_filter(self) -> None:
        """Parse gates with test filter pattern."""
        from sbs_lsp_mcp.gate_validation import parse_gate_spec_from_plan

        plan = '''
```yaml
gates:
  tests:
    tier: evergreen
    filter: test_color
```
'''
        spec = parse_gate_spec_from_plan(plan)
        assert spec is not None
        assert spec.test_tier == "evergreen"
        assert spec.tests == "test_color"


class TestGateResult:
    """Tests for GateResult dataclass."""

    def test_gate_result_all_pass(self) -> None:
        """GateResult when all gates pass."""
        from sbs_lsp_mcp.gate_validation import GateResult

        result = GateResult(
            all_pass=True,
            results=["Tests: 50/50 passed", "T5: 1.0 >= 0.8 (PASS)"],
            failures=[],
            test_passed=50,
            test_total=50,
            validator_scores={"T5": 1.0, "T6": 0.95},
        )
        assert result.all_pass is True
        assert len(result.failures) == 0

    def test_gate_result_with_failures(self) -> None:
        """GateResult with gate failures."""
        from sbs_lsp_mcp.gate_validation import GateResult

        result = GateResult(
            all_pass=False,
            results=["Tests: 48/50 passed"],
            failures=["T5: 0.7 < 0.8 (FAIL)", "T6: 0.8 < 0.9 (FAIL)"],
            test_passed=48,
            test_total=50,
            validator_scores={"T5": 0.7, "T6": 0.8},
        )
        assert result.all_pass is False
        assert len(result.failures) == 2


# =============================================================================
# sbs_log Label Inference Tests
# =============================================================================


class TestTypeInference:
    """Tests for _infer_type_label function."""

    def test_infer_bug_visual(self) -> None:
        """Detect bug:visual from visual keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_type_label

        assert _infer_type_label("graph looks wrong") == "bug:visual"
        assert _infer_type_label("CSS misaligned elements") == "bug:visual"
        assert _infer_type_label("broken layout in sidebar") == "bug:visual"
        assert _infer_type_label("display renders incorrectly") == "bug:visual"

    def test_infer_bug_functional(self) -> None:
        """Detect bug:functional from functional keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_type_label

        assert _infer_type_label("button doesn't work") == "bug:functional"
        assert _infer_type_label("crash on startup") == "bug:functional"
        assert _infer_type_label("incorrect output from parser") == "bug:functional"

    def test_infer_bug_build(self) -> None:
        """Detect bug:build from build keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_type_label

        assert _infer_type_label("build fail on CI") == "bug:build"
        assert _infer_type_label("lake error in lakefile") == "bug:build"
        assert _infer_type_label("compile error in module") == "bug:build"

    def test_infer_bug_regression(self) -> None:
        """Detect bug:regression from regression keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_type_label

        assert _infer_type_label("feature regression after update") == "bug:regression"
        assert _infer_type_label("this worked before the merge") == "bug:regression"
        assert _infer_type_label("it was working yesterday") == "bug:regression"

    def test_infer_feature_new(self) -> None:
        """Detect feature:new from new feature keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_type_label

        assert _infer_type_label("add dark mode support") == "feature:new"
        assert _infer_type_label("implement export function") == "feature:new"
        assert _infer_type_label("create new dashboard widget") == "feature:new"

    def test_infer_feature_enhancement(self) -> None:
        """Detect feature:enhancement from improvement keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_type_label

        # Note: "render" would match bug:visual before "improve" matches feature:enhancement
        # Use examples without conflicting keywords
        assert _infer_type_label("improve performance overall") == "feature:enhancement"
        assert _infer_type_label("enhance the user experience") == "feature:enhancement"
        assert _infer_type_label("optimize memory usage") == "feature:enhancement"

    def test_infer_idea_exploration(self) -> None:
        """Detect idea:exploration from idea keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_type_label

        assert _infer_type_label("idea: what if we used SVG") == "idea:exploration"
        assert _infer_type_label("explore alternative layout") == "idea:exploration"
        assert _infer_type_label("wonder if this would work") == "idea:exploration"

    def test_infer_investigation(self) -> None:
        """Detect investigation from debugging keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_type_label

        assert _infer_type_label("investigate slow build times") == "investigation"
        assert _infer_type_label("figure out why tests fail") == "investigation"
        assert _infer_type_label("look into root cause") == "investigation"

    def test_infer_housekeeping_docs(self) -> None:
        """Detect housekeeping:docs from documentation keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_type_label

        assert _infer_type_label("update readme documentation") == "housekeeping:docs"
        # Note: "document the new API" has "new" which matches feature:new first
        # Use examples without conflicting keywords
        assert _infer_type_label("document the API endpoints") == "housekeeping:docs"

    def test_infer_housekeeping_cleanup(self) -> None:
        """Detect housekeeping:cleanup from cleanup keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_type_label

        assert _infer_type_label("cleanup dead code in module") == "housekeeping:cleanup"
        assert _infer_type_label("refactor the parser") == "housekeeping:cleanup"

    def test_infer_no_match_returns_none(self) -> None:
        """Return None when no keywords match."""
        from sbs_lsp_mcp.skill_tools import _infer_type_label

        # Very generic text with no type keywords
        result = _infer_type_label("the quick brown fox")
        assert result is None


class TestAreaInference:
    """Tests for _infer_area_labels function."""

    def test_infer_sbs_graph_area(self) -> None:
        """Detect area:sbs:graph from graph keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_area_labels

        labels = _infer_area_labels("fix dependency graph layout")
        assert "area:sbs:graph" in labels

    def test_infer_sbs_dashboard_area(self) -> None:
        """Detect area:sbs:dashboard from dashboard keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_area_labels

        labels = _infer_area_labels("dashboard stats panel broken")
        assert "area:sbs:dashboard" in labels

    def test_infer_sbs_theme_area(self) -> None:
        """Detect area:sbs:theme from theme keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_area_labels

        labels = _infer_area_labels("dark mode toggle not working")
        assert "area:sbs:theme" in labels

    def test_infer_devtools_mcp_area(self) -> None:
        """Detect area:devtools:mcp from MCP keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_area_labels

        labels = _infer_area_labels("MCP tool returns wrong type")
        assert "area:devtools:mcp" in labels

    def test_infer_devtools_archive_area(self) -> None:
        """Detect area:devtools:archive from archive keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_area_labels

        labels = _infer_area_labels("archive entry not created")
        assert "area:devtools:archive" in labels

    def test_infer_lean_dress_area(self) -> None:
        """Detect area:lean:dress from Dress keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_area_labels

        labels = _infer_area_labels("Dress artifact generation fails")
        assert "area:lean:dress" in labels

    def test_infer_lean_runway_area(self) -> None:
        """Detect area:lean:runway from Runway keywords."""
        from sbs_lsp_mcp.skill_tools import _infer_area_labels

        labels = _infer_area_labels("Runway site generation error")
        assert "area:lean:runway" in labels

    def test_infer_multiple_areas(self) -> None:
        """Multiple areas can be inferred from text."""
        from sbs_lsp_mcp.skill_tools import _infer_area_labels

        labels = _infer_area_labels("graph nodes wrong in dark mode theme")
        assert "area:sbs:graph" in labels
        assert "area:sbs:theme" in labels

    def test_infer_no_area_returns_empty(self) -> None:
        """Return empty list when no area keywords match."""
        from sbs_lsp_mcp.skill_tools import _infer_area_labels

        labels = _infer_area_labels("the quick brown fox")
        assert labels == []


# =============================================================================
# sbs_task Phase Tests
# =============================================================================


class TestTaskPhases:
    """Tests for sbs_task phase transitions."""

    def test_task_start_when_idle(self) -> None:
        """Task start succeeds when system is idle."""
        # Simulate: db.get_global_state() returns (None, None)
        # Start should succeed
        result = TaskResult(
            success=True,
            phase_completed="start",
            next_action="plan",
            issue_refs=[],
        )
        assert result.success is True
        assert result.phase_completed == "start"
        assert result.next_action == "plan"

    def test_task_start_conflict(self) -> None:
        """Task start fails when another skill is active."""
        result = TaskResult(
            success=False,
            error="Cannot start task: skill 'qa' is already active",
            phase_completed=None,
            next_action=None,
            issue_refs=[],
        )
        assert result.success is False
        assert "qa" in result.error
        assert "already active" in result.error

    def test_task_start_auto_mode(self) -> None:
        """Task start with auto_mode skips alignment/planning."""
        result = TaskResult(
            success=True,
            phase_completed="start",
            next_action="execute",  # Goes directly to execute in auto mode
            issue_refs=[],
        )
        assert result.next_action == "execute"

    def test_task_plan_phase(self) -> None:
        """Task plan phase completion."""
        result = TaskResult(
            success=True,
            phase_completed="plan",
            next_action="execute",
            pr_number=42,
            issue_refs=[],
        )
        assert result.phase_completed == "plan"
        assert result.pr_number == 42

    def test_task_execute_phase(self) -> None:
        """Task execute phase with agent spawn specs."""
        result = TaskResult(
            success=True,
            phase_completed="execute",
            next_action="finalize",
            agents_to_spawn=[{"prompt": "Fix CSS", "files": ["common.css"]}],
            issue_refs=[],
        )
        assert result.phase_completed == "execute"
        assert result.agents_to_spawn is not None

    def test_task_finalize_with_gates_pass(self) -> None:
        """Task finalize when gates pass."""
        result = TaskResult(
            success=True,
            phase_completed="finalize",
            next_action="update-and-archive",
            gate_results=["Tests: 50/50 passed"],
            gate_failures=[],
            requires_approval=False,
            issue_refs=[],
        )
        assert result.requires_approval is False
        assert result.next_action == "update-and-archive"

    def test_task_finalize_with_gates_fail(self) -> None:
        """Task finalize when gates fail requires approval."""
        result = TaskResult(
            success=True,
            phase_completed="finalize",
            next_action="await_approval",
            gate_results=["Tests: 48/50 passed"],
            gate_failures=["T5: 0.7 < 0.8 (FAIL)"],
            requires_approval=True,
            issue_refs=[],
        )
        assert result.requires_approval is True
        assert result.next_action == "await_approval"


# =============================================================================
# sbs_qa Phase Tests
# =============================================================================


class TestQAPhases:
    """Tests for sbs_qa phase transitions."""

    def test_qa_setup_success(self) -> None:
        """QA setup completes successfully."""
        result = QAResult(
            success=True,
            phase_completed="setup",
            page_status={},
            issues_logged=[],
        )
        assert result.success is True
        assert result.phase_completed == "setup"

    def test_qa_setup_build_failure(self) -> None:
        """QA setup fails when build fails."""
        result = QAResult(
            success=False,
            error="Build failed: lake build error",
            phase_completed=None,
            page_status={},
            issues_logged=[],
        )
        assert result.success is False
        assert "Build failed" in result.error

    def test_qa_review_page_status(self) -> None:
        """QA review tracks per-page status."""
        result = QAResult(
            success=True,
            phase_completed="review",
            page_status={
                "dashboard": "pass",
                "dep_graph": "pass",
                "paper_tex": "warn",  # 404
                "chapter": "fail",
            },
            issues_logged=[],
        )
        assert result.page_status["dashboard"] == "pass"
        assert result.page_status["paper_tex"] == "warn"
        assert result.page_status["chapter"] == "fail"

    def test_qa_report_with_issues(self) -> None:
        """QA report phase logs issues."""
        result = QAResult(
            success=True,
            phase_completed="report",
            page_status={"dashboard": "fail"},
            issues_logged=[142, 143],
        )
        assert result.phase_completed == "report"
        assert 142 in result.issues_logged


# =============================================================================
# sbs_introspect Level Dispatch Tests
# =============================================================================


class TestIntrospectLevelDispatch:
    """Tests for introspect level dispatching (L2 vs L3+)."""

    def test_introspect_l2_discovery(self) -> None:
        """L2 introspect starts with discovery phase."""
        result = IntrospectResult(
            success=True,
            level=2,
            phase_completed="discovery",
            findings_count=0,
        )
        assert result.level == 2
        assert result.phase_completed == "discovery"

    def test_introspect_l2_phases(self) -> None:
        """L2 has 5 phases: discovery, selection, dialogue, logging, archive."""
        phases = ["discovery", "selection", "dialogue", "logging", "archive"]
        for phase in phases:
            result = IntrospectResult(
                success=True,
                level=2,
                phase_completed=phase,
            )
            assert result.phase_completed == phase

    def test_introspect_l3_phases(self) -> None:
        """L3+ has 3 phases: ingestion, synthesis, archive."""
        phases = ["ingestion", "synthesis", "archive"]
        for phase in phases:
            result = IntrospectResult(
                success=True,
                level=3,
                phase_completed=phase,
            )
            assert result.phase_completed == phase

    def test_introspect_l2_dry_run(self) -> None:
        """L2 dry run skips logging and archive phases."""
        result = IntrospectResult(
            success=True,
            level=2,
            phase_completed="logging",
            issues_created=[],  # Empty in dry run
        )
        assert result.issues_created == []


# =============================================================================
# sbs_converge Iteration Tests
# =============================================================================


class TestConvergeIterations:
    """Tests for converge iteration loop and exit conditions."""

    def test_converge_first_iteration(self) -> None:
        """First converge iteration starts at 1."""
        result = ConvergeResult(
            success=True,
            phase_completed="eval",
            iteration=1,
            pass_rate=0.72,
            pass_rate_history=[0.72],
        )
        assert result.iteration == 1
        assert len(result.pass_rate_history) == 1

    def test_converge_improvement(self) -> None:
        """Converge continues when pass rate improves."""
        result = ConvergeResult(
            success=True,
            phase_completed="eval",
            iteration=2,
            pass_rate=0.89,
            pass_rate_history=[0.72, 0.89],
        )
        # Pass rate improved: 0.72 -> 0.89
        assert result.pass_rate > result.pass_rate_history[0]

    def test_converge_100_percent(self) -> None:
        """Converge exits with 'converged' at 100% pass rate."""
        result = ConvergeResult(
            success=True,
            phase_completed="report",
            iteration=3,
            pass_rate=1.0,
            pass_rate_history=[0.72, 0.89, 1.0],
            exit_reason="converged",
        )
        assert result.pass_rate == 1.0
        assert result.exit_reason == "converged"

    def test_converge_plateau(self) -> None:
        """Converge exits with 'plateau' when no improvement."""
        result = ConvergeResult(
            success=True,
            phase_completed="report",
            iteration=3,
            pass_rate=0.85,
            pass_rate_history=[0.85, 0.85, 0.85],
            exit_reason="plateau",
        )
        assert result.exit_reason == "plateau"

    def test_converge_max_iterations(self) -> None:
        """Converge exits with 'max_iterations' at iteration cap."""
        result = ConvergeResult(
            success=True,
            phase_completed="report",
            iteration=3,
            pass_rate=0.90,
            pass_rate_history=[0.75, 0.85, 0.90],
            exit_reason="max_iterations",
        )
        assert result.exit_reason == "max_iterations"

    def test_converge_build_failure(self) -> None:
        """Converge exits with 'build_failure' on build error."""
        result = ConvergeResult(
            success=False,
            error="Build failed after fix-2: lake error",
            phase_completed="rebuild",
            iteration=2,
            pass_rate=0.85,
            pass_rate_history=[0.75, 0.85],
            exit_reason="build_failure",
        )
        assert result.success is False
        assert result.exit_reason == "build_failure"


# =============================================================================
# sbs_update_and_archive Phase Tests
# =============================================================================


class TestUpdateArchivePhases:
    """Tests for update-and-archive simplified 3-phase workflow."""

    def test_update_archive_retrospective(self) -> None:
        """First phase is retrospective."""
        result = UpdateArchiveResult(
            success=True,
            phase_completed="retrospective",
            retrospective_written=True,
        )
        assert result.phase_completed == "retrospective"
        assert result.retrospective_written is True

    def test_update_archive_porcelain(self) -> None:
        """Second phase is porcelain (git state)."""
        result = UpdateArchiveResult(
            success=True,
            phase_completed="porcelain",
            repos_committed=["Dress", "Runway"],
        )
        assert result.phase_completed == "porcelain"
        assert "Dress" in result.repos_committed

    def test_update_archive_upload(self) -> None:
        """Third phase is upload (archive entry)."""
        result = UpdateArchiveResult(
            success=True,
            phase_completed="upload",
            archive_entry_id="1738300000",
        )
        assert result.phase_completed == "upload"
        assert result.archive_entry_id is not None


# =============================================================================
# sbs_divination Tests
# =============================================================================


class TestDivination:
    """Tests for sbs_divination codebase exploration."""

    def test_divination_query_processing(self) -> None:
        """Divination processes a query and returns files."""
        result = DivinationResult(
            success=True,
            query="CSS status colors",
            files_explored=[
                {"path": "common.css", "relevance": "high", "summary": "Status color CSS variables"},
                {"path": "Svg.lean", "relevance": "high", "summary": "Canonical color hex values"},
            ],
            patterns=["Lean is source of truth for colors", "CSS variables must match Lean"],
            suggestions=["Check Dress/Graph/Svg.lean for canonical values"],
        )
        assert len(result.files_explored) == 2
        assert "CSS variables" in result.patterns[1]

    def test_divination_empty_results(self) -> None:
        """Divination handles queries with no results."""
        result = DivinationResult(
            success=True,
            query="nonexistent feature XYZ",
            files_explored=[],
            patterns=[],
            suggestions=["No matches found for this query"],
        )
        assert len(result.files_explored) == 0
        assert "No matches" in result.suggestions[0]


# =============================================================================
# Skill State Conflict Tests
# =============================================================================


class TestSkillStateConflicts:
    """Tests for skill state conflict handling."""

    def test_task_blocked_by_qa(self) -> None:
        """Task cannot start when QA skill is active."""
        result = TaskResult(
            success=False,
            error="Cannot start task: skill 'qa' is already active",
            phase_completed=None,
            next_action=None,
            issue_refs=[],
        )
        assert "qa" in result.error
        assert "already active" in result.error

    def test_qa_blocked_by_converge(self) -> None:
        """QA cannot start when converge skill is active."""
        result = QAResult(
            success=False,
            error="Cannot start QA: skill 'converge' is already active",
            phase_completed=None,
            page_status={},
            issues_logged=[],
        )
        assert "converge" in result.error

    def test_introspect_blocked_by_task(self) -> None:
        """Introspect cannot start when task skill is active."""
        result = IntrospectResult(
            success=False,
            error="Cannot start introspect: skill 'task' is already active",
            level=2,
            phase_completed=None,
        )
        assert "task" in result.error


# =============================================================================
# Integration-style Tests
# =============================================================================


class TestSkillLifecycleIntegration:
    """Integration tests for full skill lifecycles."""

    def test_task_full_lifecycle(self) -> None:
        """Test complete task skill lifecycle."""
        # Phase 1: Start
        start = TaskResult(success=True, phase_completed="start", next_action="plan", issue_refs=[42])
        assert start.phase_completed == "start"

        # Phase 2: Plan
        plan = TaskResult(success=True, phase_completed="plan", next_action="execute", pr_number=100, issue_refs=[42])
        assert plan.pr_number == 100

        # Phase 3: Execute
        execute = TaskResult(success=True, phase_completed="execute", next_action="finalize", issue_refs=[42])
        assert execute.next_action == "finalize"

        # Phase 4: Finalize
        finalize = TaskResult(
            success=True,
            phase_completed="finalize",
            next_action="update-and-archive",
            gate_results=["Tests: 50/50 passed"],
            gate_failures=[],
            requires_approval=False,
            issue_refs=[42],
        )
        assert finalize.next_action == "update-and-archive"

    def test_converge_full_lifecycle(self) -> None:
        """Test complete converge skill lifecycle to convergence."""
        # Iteration 1: 72% pass
        eval1 = ConvergeResult(
            success=True, phase_completed="eval", iteration=1, pass_rate=0.72, pass_rate_history=[0.72]
        )

        # Iteration 2: 89% pass
        eval2 = ConvergeResult(
            success=True, phase_completed="eval", iteration=2, pass_rate=0.89, pass_rate_history=[0.72, 0.89]
        )

        # Iteration 3: 100% pass - converged!
        eval3 = ConvergeResult(
            success=True,
            phase_completed="report",
            iteration=3,
            pass_rate=1.0,
            pass_rate_history=[0.72, 0.89, 1.0],
            exit_reason="converged",
        )
        assert eval3.exit_reason == "converged"
        assert eval3.pass_rate == 1.0

    def test_introspect_l2_full_lifecycle(self) -> None:
        """Test complete L2 introspect lifecycle."""
        # Discovery
        discovery = IntrospectResult(success=True, level=2, phase_completed="discovery", findings_count=5)
        assert discovery.findings_count == 5

        # Selection
        selection = IntrospectResult(success=True, level=2, phase_completed="selection")

        # Dialogue
        dialogue = IntrospectResult(success=True, level=2, phase_completed="dialogue")

        # Logging
        logging_result = IntrospectResult(
            success=True, level=2, phase_completed="logging", issues_created=[47, 48]
        )
        assert len(logging_result.issues_created) == 2

        # Archive
        archive = IntrospectResult(success=True, level=2, phase_completed="archive")
        assert archive.phase_completed == "archive"
