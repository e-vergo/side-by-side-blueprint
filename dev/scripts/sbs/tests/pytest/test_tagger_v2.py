"""Tests for the v2.0 agent-state tagging pipeline.

Integration tests covering:
- Context builder (build_tagging_context)
- Declarative rule evaluation (rules.yaml)
- Python hooks (session_profiler, signal_detector, outcome_tagger)
- Full pipeline integration (TaggingEngine end-to-end)

All tests marked @pytest.mark.evergreen.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from sbs.archive.entry import ArchiveEntry
from sbs.archive.session_data import SessionData, ToolCall, ThinkingBlock, MessageUsage
from sbs.archive.tagger import TaggingEngine, build_tagging_context

# All tests in this module are evergreen
pytestmark = pytest.mark.evergreen

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve()
while REPO_ROOT.parent != REPO_ROOT:
    if (REPO_ROOT / "CLAUDE.md").exists():
        break
    REPO_ROOT = REPO_ROOT.parent

RULES_PATH = REPO_ROOT / "dev" / "storage" / "tagging" / "rules.yaml"
HOOKS_DIR = REPO_ROOT / "dev" / "storage" / "tagging" / "hooks"

_NOW = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_entry(**kwargs) -> ArchiveEntry:
    """Create a minimal ArchiveEntry with defaults."""
    defaults = {
        "entry_id": "test_entry",
        "created_at": _NOW,
        "project": "TestProject",
    }
    defaults.update(kwargs)
    return ArchiveEntry(**defaults)


def make_session(**kwargs) -> SessionData:
    """Create a minimal SessionData with defaults."""
    defaults = {
        "session_id": "test_session",
        "project_path": "/test/path",
        "started_at": _NOW,
        "ended_at": _NOW,
    }
    defaults.update(kwargs)
    return SessionData(**defaults)


def make_tool_call(name: str = "Bash", success: bool = True, error: str | None = None, **kwargs) -> ToolCall:
    """Create a minimal ToolCall."""
    return ToolCall(
        tool_name=name,
        timestamp=_NOW,
        success=success,
        error=error,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine() -> TaggingEngine:
    """TaggingEngine loaded with production rules and hooks dir."""
    return TaggingEngine(rules_path=RULES_PATH, hooks_dir=HOOKS_DIR)


# =============================================================================
# 1. Context Builder Tests
# =============================================================================


class TestContextStateMachineFields:
    """build_tagging_context includes state machine fields."""

    def test_context_includes_state_machine_fields(self) -> None:
        entry = make_entry(
            global_state={"skill": "task", "substate": "execution"},
            state_transition="phase_start",
            epoch_summary={"entries": 5},
            gate_validation={"passed": True, "findings": []},
        )
        ctx = build_tagging_context(entry)
        assert ctx["skill"] == "task"
        assert ctx["substate"] == "execution"
        assert ctx["state_transition"] == "phase_start"
        assert ctx["has_epoch_summary"] is True
        assert ctx["gate_passed"] is True

    def test_context_includes_token_fields(self) -> None:
        entry = make_entry(
            claude_data={
                "session_ids": ["s1"],
                "tool_call_count": 10,
                "message_count": 50,
                "plan_files": [],
                "total_input_tokens": 120000,
                "total_output_tokens": 40000,
                "cache_read_tokens": 80000,
                "thinking_block_count": 3,
                "unique_tools_used": ["Read", "Edit"],
                "model_versions_used": ["opus-4.5"],
            },
        )
        ctx = build_tagging_context(entry)
        assert ctx["total_input_tokens"] == 120000
        assert ctx["total_output_tokens"] == 40000
        assert ctx["total_tokens"] == 160000
        assert ctx["cache_read_tokens"] == 80000
        assert ctx["thinking_block_count"] == 3
        assert ctx["unique_tools_count"] == 2
        assert ctx["model_versions"] == ["opus-4.5"]

    def test_context_defaults_without_claude_data(self) -> None:
        entry = make_entry(claude_data=None)
        ctx = build_tagging_context(entry)
        assert ctx["total_input_tokens"] == 0
        assert ctx["total_output_tokens"] == 0
        assert ctx["total_tokens"] == 0
        assert ctx["cache_read_tokens"] == 0
        assert ctx["thinking_block_count"] == 0
        assert ctx["unique_tools_count"] == 0
        assert ctx["model_versions"] == []

    def test_context_includes_quality_fields(self) -> None:
        entry = make_entry(
            quality_scores={"overall": 0.92, "scores": {}},
            quality_delta={"overall": 0.05},
        )
        ctx = build_tagging_context(entry)
        assert ctx["quality_overall"] == 0.92
        assert ctx["quality_delta"] == 0.05


# =============================================================================
# 2. Declarative Rule Tests
# =============================================================================


class TestDeclarativeRules:
    """Declarative rules from rules.yaml match expected contexts."""

    def test_phase_rules_match(self, engine: TaggingEngine) -> None:
        ctx = build_tagging_context(
            make_entry(global_state={"skill": "task", "substate": "execution"}),
        )
        tags = engine.evaluate(make_entry(), ctx)
        assert "phase:execution" in tags

    def test_skill_rules_match(self, engine: TaggingEngine) -> None:
        ctx = build_tagging_context(
            make_entry(global_state={"skill": "task", "substate": "alignment"}),
        )
        tags = engine.evaluate(make_entry(), ctx)
        assert "skill:task" in tags

    def test_trigger_rules_match(self, engine: TaggingEngine) -> None:
        entry = make_entry(trigger="build")
        ctx = build_tagging_context(entry)
        tags = engine.evaluate(entry, ctx)
        assert "trigger:build" in tags

    def test_scope_file_pattern_rules(self, engine: TaggingEngine) -> None:
        ctx = build_tagging_context(
            make_entry(),
            files_modified=["assets/common.css", "assets/plastex.js"],
        )
        tags = engine.evaluate(make_entry(), ctx)
        assert "scope:css-js" in tags

    def test_repo_rules_match(self, engine: TaggingEngine) -> None:
        ctx = build_tagging_context(
            make_entry(),
            files_modified=["toolchain/Dress/Graph/Layout.lean"],
        )
        tags = engine.evaluate(make_entry(), ctx)
        assert "repo:dress" in tags

    def test_linkage_rules_match(self, engine: TaggingEngine) -> None:
        entry = make_entry(issue_refs=["42", "57"])
        ctx = build_tagging_context(entry)
        tags = engine.evaluate(entry, ctx)
        assert "linkage:has-issue" in tags


# =============================================================================
# 3. Session Profiler Hook Tests
# =============================================================================


class TestSessionProfiler:
    """session_profiler.profile_session produces expected tags."""

    def test_session_profiler_edit_heavy(self) -> None:
        """Session with many edits relative to reads -> session:edit-heavy."""
        from importlib import import_module
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "session_profiler", HOOKS_DIR / "session_profiler.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        session = make_session(
            files_edited=[f"file_{i}.py" for i in range(30)],
            files_read=[f"read_{i}.py" for i in range(5)],
            tool_calls=[make_tool_call("Edit") for _ in range(35)],
        )
        entry = make_entry()
        tags = mod.profile_session(entry, [session])
        assert "session:edit-heavy" in tags

    def test_session_profiler_exploration_heavy(self) -> None:
        """Session with many reads relative to edits -> session:exploration-heavy."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "session_profiler", HOOKS_DIR / "session_profiler.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        session = make_session(
            files_read=[f"read_{i}.py" for i in range(50)],
            files_edited=[f"edit_{i}.py" for i in range(2)],
            tool_calls=[make_tool_call("Read") for _ in range(52)],
        )
        entry = make_entry()
        tags = mod.profile_session(entry, [session])
        assert "session:exploration-heavy" in tags

    def test_session_profiler_tool_dominant(self) -> None:
        """Session dominated by Read tool -> tool:read-dominant."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "session_profiler", HOOKS_DIR / "session_profiler.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        session = make_session(
            tool_calls=[make_tool_call("Read") for _ in range(20)]
            + [make_tool_call("Edit") for _ in range(3)],
        )
        entry = make_entry()
        tags = mod.profile_session(entry, [session])
        assert "tool:read-dominant" in tags

    def test_session_profiler_token_tags(self) -> None:
        """Entry with high token counts -> token:input-heavy or token:total-heavy."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "session_profiler", HOOKS_DIR / "session_profiler.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Use claude_data fallback path (sessions have no message_usage)
        entry = make_entry(
            claude_data={
                "total_input_tokens": 150000,
                "total_output_tokens": 80000,
                "cache_read_tokens": 0,
                "thinking_block_count": 0,
                "model_versions_used": [],
            },
        )
        session = make_session(
            tool_calls=[make_tool_call("Read") for _ in range(5)],
        )
        tags = mod.profile_session(entry, [session])
        assert "token:input-heavy" in tags
        assert "token:total-heavy" in tags


# =============================================================================
# 4. Signal Detector Tests
# =============================================================================


class TestSignalDetector:
    """signal_detector.detect_signals produces expected tags."""

    def _load_hook(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "signal_detector", HOOKS_DIR / "signal_detector.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_signal_consecutive_bash_failures(self) -> None:
        """3+ consecutive bash failures -> signal:consecutive-bash-failures."""
        mod = self._load_hook()

        # 15 good calls followed by 5 consecutive bad calls
        good_calls = [make_tool_call("Bash") for _ in range(15)]
        bad_calls = [
            make_tool_call("Bash", success=False, error="command not found: foobar")
            for _ in range(5)
        ]
        session = make_session(tool_calls=good_calls + bad_calls)
        entry = make_entry()
        tags = mod.detect_signals(entry, [session])
        assert "signal:consecutive-bash-failures" in tags

    def test_signal_consecutive_bash_failures_not_triggered_when_interleaved(self) -> None:
        """Interleaved successes prevent consecutive-bash-failures."""
        mod = self._load_hook()

        # Alternate: fail, succeed, fail, succeed -- never 3 in a row
        calls = []
        for _ in range(5):
            calls.append(make_tool_call("Bash", success=False, error="error"))
            calls.append(make_tool_call("Bash"))
        session = make_session(tool_calls=calls)
        entry = make_entry()
        tags = mod.detect_signals(entry, [session])
        assert "signal:consecutive-bash-failures" not in tags

    def test_signal_same_command_retry(self) -> None:
        """Same command run 3+ times -> signal:same-command-retry."""
        mod = self._load_hook()

        calls = [
            make_tool_call("Read", input_full={"file_path": "/foo/bar.py"})
            for _ in range(3)
        ]
        session = make_session(tool_calls=calls)
        entry = make_entry()
        tags = mod.detect_signals(entry, [session])
        assert "signal:same-command-retry" in tags

    def test_signal_user_correction(self) -> None:
        """Entry notes with correction keyword -> signal:user-correction."""
        mod = self._load_hook()

        entry = make_entry(notes="correction needed for the sidebar layout")
        session = make_session(tool_calls=[make_tool_call("Read")])
        tags = mod.detect_signals(entry, [session])
        assert "signal:user-correction" in tags

    def test_signal_sync_error(self) -> None:
        """Entry with sync_error -> signal:sync-error."""
        mod = self._load_hook()

        entry = make_entry(sync_error="Connection failed: timeout")
        session = make_session(tool_calls=[make_tool_call("Read")])
        tags = mod.detect_signals(entry, [session])
        assert "signal:sync-error" in tags


# =============================================================================
# 5. Outcome Tagger Tests
# =============================================================================


class TestOutcomeTagger:
    """outcome_tagger.tag_outcomes produces expected tags.

    The outcome_tagger module uses a relative import from signal_detector,
    so we load both modules as a proper package to resolve the import.
    """

    def _load_hook(self):
        import importlib.util
        import sys
        import types

        # Create a package so relative imports work
        pkg_name = "_hooks_pkg"
        if pkg_name not in sys.modules:
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [str(HOOKS_DIR)]
            pkg.__package__ = pkg_name
            sys.modules[pkg_name] = pkg

            # Load signal_detector into the package first
            sd_spec = importlib.util.spec_from_file_location(
                f"{pkg_name}.signal_detector", HOOKS_DIR / "signal_detector.py"
            )
            sd_mod = importlib.util.module_from_spec(sd_spec)
            sd_mod.__package__ = pkg_name
            sys.modules[f"{pkg_name}.signal_detector"] = sd_mod
            sd_spec.loader.exec_module(sd_mod)

        # Load outcome_tagger in the package context
        ot_spec = importlib.util.spec_from_file_location(
            f"{pkg_name}.outcome_tagger", HOOKS_DIR / "outcome_tagger.py"
        )
        ot_mod = importlib.util.module_from_spec(ot_spec)
        ot_mod.__package__ = pkg_name
        sys.modules[f"{pkg_name}.outcome_tagger"] = ot_mod
        ot_spec.loader.exec_module(ot_mod)
        return ot_mod

    def test_outcome_clean_execution(self) -> None:
        """All successful tool calls, no anomalies -> outcome:clean-execution."""
        mod = self._load_hook()

        session = make_session(
            tool_calls=[make_tool_call("Read") for _ in range(10)],
            message_count=50,
        )
        entry = make_entry()
        tags = mod.tag_outcomes(entry, [session])
        assert "outcome:clean-execution" in tags

    def test_outcome_quality_improved(self) -> None:
        """Entry with positive quality_delta -> outcome:quality-improved."""
        mod = self._load_hook()

        entry = make_entry(quality_delta={"overall": 0.15})
        session = make_session(
            tool_calls=[make_tool_call("Read")],
            message_count=10,
        )
        tags = mod.tag_outcomes(entry, [session])
        assert "outcome:quality-improved" in tags

    def test_outcome_task_completed(self) -> None:
        """Entry with phase_end transition -> outcome:task-completed."""
        mod = self._load_hook()

        entry = make_entry(
            global_state={"skill": "task", "substate": "finalization"},
            state_transition="phase_end",
        )
        session = make_session(
            tool_calls=[make_tool_call("Read")],
            message_count=10,
        )
        tags = mod.tag_outcomes(entry, [session])
        assert "outcome:task-completed" in tags


# =============================================================================
# 6. Full Pipeline Integration Test
# =============================================================================


class TestFullPipeline:
    """End-to-end TaggingEngine evaluation with rules + hooks."""

    def test_full_pipeline_produces_multi_dimension_tags(self, engine: TaggingEngine) -> None:
        """Realistic entry + session produces tags spanning multiple dimensions."""
        entry = make_entry(
            trigger="skill",
            global_state={"skill": "task", "substate": "execution"},
            state_transition="phase_start",
            issue_refs=["42"],
            claude_data={
                "session_ids": ["s1"],
                "tool_call_count": 30,
                "message_count": 80,
                "plan_files": ["plan.md"],
                "total_input_tokens": 200000,
                "total_output_tokens": 50000,
                "cache_read_tokens": 100000,
                "thinking_block_count": 5,
                "unique_tools_used": ["Read", "Edit", "Bash"],
                "model_versions_used": ["opus-4.5"],
            },
        )
        session = make_session(
            tool_calls=(
                [make_tool_call("Read") for _ in range(15)]
                + [make_tool_call("Edit") for _ in range(10)]
                + [make_tool_call("Bash") for _ in range(5)]
            ),
            files_read=[f"file_{i}.lean" for i in range(15)],
            files_edited=[f"edit_{i}.lean" for i in range(10)],
            message_count=80,
            user_messages=25,
        )

        ctx = build_tagging_context(
            entry,
            files_modified=["toolchain/Dress/Graph/Layout.lean", "assets/common.css"],
        )
        tags = engine.evaluate(entry, ctx, sessions=[session])

        # Declarative rules should produce phase, skill, trigger tags
        assert "phase:execution" in tags
        assert "skill:task" in tags
        assert "trigger:skill" in tags

        # Linkage
        assert "linkage:has-issue" in tags

        # Scope/repo from files_modified
        assert "scope:css-js" in tags
        assert "repo:dress" in tags

        # Hooks should have run (session profiler, signal detector, outcome tagger)
        # At minimum, verify tags from more than 3 distinct dimensions
        prefixes = {t.split(":")[0] for t in tags}
        assert len(prefixes) >= 4, (
            f"Expected tags from at least 4 dimensions, got {len(prefixes)}: {prefixes}"
        )
