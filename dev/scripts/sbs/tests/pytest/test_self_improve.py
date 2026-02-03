"""
Tests for the /self-improve skill.

Validates:
- V1: Skill file exists and parses correctly (including framework content)
- V3: sbs_analysis_summary returns structured data
- V4: sbs_entries_since_self_improve returns entry count
- V5: Archive entries with self-improve tag work
- V7: Recovery from each phase works

Note: V2 (Agent file tests) removed after sbs-improver.md was consolidated
into the skill file in #29 (unified skill-agent architecture).
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from sbs.archive.entry import ArchiveEntry, ArchiveIndex

# Add sbs-lsp-mcp to path for MCP tool tests (using importlib to avoid __init__.py)
import importlib.util

_SBS_LSP_MCP_SRC = Path("/Users/eric/GitHub/Side-By-Side-Blueprint/forks/sbs-lsp-mcp/src")


def _load_module_directly(module_name: str, file_path: Path):
    """Load a module directly from file path, bypassing __init__.py."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {module_name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _get_self_improve_module():
    """Get the sbs_self_improve module, loading dependencies as needed."""
    # First load sbs_models (no external deps)
    if "sbs_lsp_mcp.sbs_models" not in sys.modules:
        _load_module_directly(
            "sbs_lsp_mcp.sbs_models",
            _SBS_LSP_MCP_SRC / "sbs_lsp_mcp" / "sbs_models.py"
        )
    # Then load sbs_utils (needs sbs.archive which is in scripts path)
    if "sbs_lsp_mcp.sbs_utils" not in sys.modules:
        _load_module_directly(
            "sbs_lsp_mcp.sbs_utils",
            _SBS_LSP_MCP_SRC / "sbs_lsp_mcp" / "sbs_utils.py"
        )
    # Finally load sbs_self_improve
    if "sbs_lsp_mcp.sbs_self_improve" not in sys.modules:
        _load_module_directly(
            "sbs_lsp_mcp.sbs_self_improve",
            _SBS_LSP_MCP_SRC / "sbs_lsp_mcp" / "sbs_self_improve.py"
        )
    return sys.modules["sbs_lsp_mcp.sbs_self_improve"]


# =============================================================================
# Paths
# =============================================================================

MONOREPO_ROOT = Path("/Users/eric/GitHub/Side-By-Side-Blueprint")
SKILL_FILE = MONOREPO_ROOT / ".claude" / "skills" / "self-improve" / "SKILL.md"


# =============================================================================
# V1: Skill File Tests
# =============================================================================


@pytest.mark.dev
class TestSkillFileExistsAndParses:
    """V1: Skill file exists and parses correctly."""

    def test_skill_file_exists(self):
        """Skill file must exist at expected path."""
        assert SKILL_FILE.exists(), f"Skill file not found at {SKILL_FILE}"

    def test_skill_file_has_yaml_frontmatter(self):
        """Skill file must have valid YAML frontmatter."""
        content = SKILL_FILE.read_text()

        # Must start with ---
        assert content.startswith("---"), "Skill file must start with YAML frontmatter (---)"

        # Extract frontmatter
        parts = content.split("---", 2)
        assert len(parts) >= 3, "Skill file must have closing --- for frontmatter"

        frontmatter = parts[1].strip()
        parsed = yaml.safe_load(frontmatter)

        assert isinstance(parsed, dict), "Frontmatter must parse to a dict"

    def test_skill_frontmatter_has_required_fields(self):
        """Skill frontmatter must have name, description, version."""
        content = SKILL_FILE.read_text()
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1].strip())

        assert "name" in frontmatter, "Frontmatter must have 'name'"
        assert frontmatter["name"] == "self-improve", "Name must be 'self-improve'"

        assert "description" in frontmatter, "Frontmatter must have 'description'"
        assert len(frontmatter["description"]) > 0, "Description must not be empty"

        assert "version" in frontmatter, "Frontmatter must have 'version'"
        # Version should match semver pattern
        version_pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(version_pattern, frontmatter["version"]), \
            f"Version '{frontmatter['version']}' must match semver (X.Y.Z)"

    def test_skill_has_five_phases(self):
        """Skill must define all 5 phases."""
        content = SKILL_FILE.read_text()

        required_phases = ["discovery", "selection", "dialogue", "logging", "archive"]
        for phase in required_phases:
            # Check for phase heading or substate reference
            assert phase in content.lower(), f"Skill must define phase: {phase}"

    def test_skill_has_archive_protocol(self):
        """Skill must have Mandatory Archive Protocol section."""
        content = SKILL_FILE.read_text()

        assert "archive protocol" in content.lower(), \
            "Skill must have 'Archive Protocol' section"
        assert "sbs_archive_state" in content, \
            "Skill must reference sbs_archive_state MCP tool"
        assert "global_state" in content, \
            "Skill must reference global_state"

    def test_skill_has_recovery_semantics(self):
        """Skill must have recovery semantics section."""
        content = SKILL_FILE.read_text()

        assert "recovery" in content.lower(), \
            "Skill must have recovery section"
        assert "compaction" in content.lower(), \
            "Skill must mention compaction survival"

    def test_skill_has_four_pillars(self):
        """Skill must document four pillars framework."""
        content = SKILL_FILE.read_text()

        pillars = [
            "user effectiveness",
            "claude execution",
            "alignment patterns",
            "system engineering"
        ]
        for pillar in pillars:
            assert pillar.lower() in content.lower(), \
                f"Skill must document pillar: {pillar}"

    def test_skill_has_tool_inventory(self):
        """Skill must have tool inventory section (consolidated from agent)."""
        content = SKILL_FILE.read_text()

        assert "tool inventory" in content.lower(), \
            "Skill must have 'Tool Inventory' section"

        # Should reference key MCP tools
        expected_tools = ["sbs_archive_state", "sbs_search_entries", "sbs_issue_create"]
        for tool in expected_tools:
            assert tool in content, f"Skill must reference tool: {tool}"

    def test_skill_has_anti_patterns(self):
        """Skill must document anti-patterns (consolidated from agent)."""
        content = SKILL_FILE.read_text()

        assert "anti-pattern" in content.lower(), \
            "Skill must have anti-patterns section"

    def test_skill_has_analysis_workflow(self):
        """Skill must have analysis workflow section."""
        content = SKILL_FILE.read_text()

        assert "analysis workflow" in content.lower(), \
            "Skill must have 'Analysis Workflow' section"

        # Should have the 4 steps
        expected_steps = ["gather data", "pattern detection", "generate findings", "prioritize"]
        for step in expected_steps:
            assert step.lower() in content.lower(), \
                f"Skill must document workflow step: {step}"

    def test_skill_has_finding_template(self):
        """Skill must have finding template."""
        content = SKILL_FILE.read_text()

        assert "finding template" in content.lower(), \
            "Skill must have 'Finding Template' section"

        # Template should have key fields
        expected_fields = ["pillar", "evidence", "frequency", "impact", "recommendation"]
        for field in expected_fields:
            assert field.lower() in content.lower(), \
                f"Finding template must have field: {field}"


# =============================================================================
# V5: Archive Entry with self-improve Tag
# =============================================================================


@pytest.mark.dev
class TestArchiveEntryWithSelfImproveTag:
    """V5: Archive entries with self-improve tag work correctly."""

    def test_create_entry_with_self_improve_tag(self, temp_archive_dir: Path):
        """Can create archive entry with self-improve tag."""
        entry = ArchiveEntry(
            entry_id="test_self_improve",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            tags=["self-improve"],
            trigger="skill",
            global_state={"skill": "self-improve", "substate": "discovery"},
        )

        index = ArchiveIndex()
        index.add_entry(entry)

        # Tag should be indexed
        assert "self-improve" in index.by_tag
        assert "test_self_improve" in index.by_tag["self-improve"]

    def test_self_improve_global_state_valid(self, temp_archive_dir: Path):
        """self-improve skill state is valid global_state."""
        valid_substates = ["discovery", "selection", "dialogue", "logging", "archive"]

        for substate in valid_substates:
            entry = ArchiveEntry(
                entry_id=f"test_{substate}",
                created_at=datetime.now(timezone.utc).isoformat(),
                project="TestProject",
                global_state={"skill": "self-improve", "substate": substate},
                state_transition="phase_start",
                trigger="skill",
            )

            assert entry.global_state["skill"] == "self-improve"
            assert entry.global_state["substate"] == substate

    def test_self_improve_entry_roundtrip(self, temp_archive_dir: Path):
        """self-improve entry survives save/load cycle."""
        entry = ArchiveEntry(
            entry_id="roundtrip_test",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            tags=["self-improve"],
            trigger="skill",
            global_state={"skill": "self-improve", "substate": "selection"},
            state_transition="phase_start",
            issue_refs=[42, 43],
        )

        index = ArchiveIndex()
        index.add_entry(entry)
        index.global_state = entry.global_state

        index_path = temp_archive_dir / "archive_index.json"
        index.save(index_path)

        loaded = ArchiveIndex.load(index_path)
        loaded_entry = loaded.entries.get("roundtrip_test")

        assert loaded_entry is not None
        assert loaded_entry.tags == ["self-improve"]
        assert loaded_entry.global_state == {"skill": "self-improve", "substate": "selection"}
        assert loaded_entry.issue_refs == [42, 43]
        assert loaded.global_state == {"skill": "self-improve", "substate": "selection"}


# =============================================================================
# V7: Recovery from Each Phase
# =============================================================================


@pytest.mark.dev
class TestRecoveryFromEachPhase:
    """V7: Recovery from each phase works correctly."""

    def test_recovery_from_discovery(self, temp_archive_dir: Path):
        """Can detect and recover from discovery phase."""
        index = ArchiveIndex()
        index.global_state = {"skill": "self-improve", "substate": "discovery"}

        entry = ArchiveEntry(
            entry_id="discovery_entry",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            global_state={"skill": "self-improve", "substate": "discovery"},
            state_transition="phase_start",
            trigger="skill",
        )
        index.add_entry(entry)

        index_path = temp_archive_dir / "archive_index.json"
        index.save(index_path)

        # Simulate recovery
        loaded = ArchiveIndex.load(index_path)
        assert loaded.global_state is not None
        assert loaded.global_state["skill"] == "self-improve"
        assert loaded.global_state["substate"] == "discovery"

    def test_recovery_from_selection(self, temp_archive_dir: Path):
        """Can detect and recover from selection phase."""
        index = ArchiveIndex()
        index.global_state = {"skill": "self-improve", "substate": "selection"}

        index_path = temp_archive_dir / "archive_index.json"
        index.save(index_path)

        loaded = ArchiveIndex.load(index_path)
        assert loaded.global_state["substate"] == "selection"

    def test_recovery_from_dialogue(self, temp_archive_dir: Path):
        """Can detect and recover from dialogue phase."""
        index = ArchiveIndex()
        index.global_state = {"skill": "self-improve", "substate": "dialogue"}

        index_path = temp_archive_dir / "archive_index.json"
        index.save(index_path)

        loaded = ArchiveIndex.load(index_path)
        assert loaded.global_state["substate"] == "dialogue"

    def test_recovery_from_logging(self, temp_archive_dir: Path):
        """Can detect and recover from logging phase."""
        index = ArchiveIndex()
        index.global_state = {"skill": "self-improve", "substate": "logging"}

        index_path = temp_archive_dir / "archive_index.json"
        index.save(index_path)

        loaded = ArchiveIndex.load(index_path)
        assert loaded.global_state["substate"] == "logging"

    def test_recovery_from_archive(self, temp_archive_dir: Path):
        """Can detect and recover from archive phase."""
        index = ArchiveIndex()
        index.global_state = {"skill": "self-improve", "substate": "archive"}

        index_path = temp_archive_dir / "archive_index.json"
        index.save(index_path)

        loaded = ArchiveIndex.load(index_path)
        assert loaded.global_state["substate"] == "archive"

    def test_phase_end_clears_state(self, temp_archive_dir: Path):
        """phase_end transition clears global_state."""
        index = ArchiveIndex()
        index.global_state = {"skill": "self-improve", "substate": "archive"}

        # Create phase_end entry
        entry = ArchiveEntry(
            entry_id="end_entry",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            state_transition="phase_end",
            trigger="skill",
            issue_refs=[42, 43, 44],
        )
        index.add_entry(entry)

        # Simulate state clearing (as upload.py does)
        if entry.state_transition == "phase_end":
            index.global_state = None

        index_path = temp_archive_dir / "archive_index.json"
        index.save(index_path)

        loaded = ArchiveIndex.load(index_path)
        assert loaded.global_state is None

    def test_state_conflict_detection(self, temp_archive_dir: Path):
        """Can detect state conflict with another skill."""
        index = ArchiveIndex()
        # Another skill owns the state
        index.global_state = {"skill": "task", "substate": "execution"}

        index_path = temp_archive_dir / "archive_index.json"
        index.save(index_path)

        loaded = ArchiveIndex.load(index_path)

        # self-improve should detect conflict
        assert loaded.global_state is not None
        assert loaded.global_state["skill"] != "self-improve"
        assert loaded.global_state["skill"] == "task"

    def test_null_state_means_idle(self, temp_archive_dir: Path):
        """null global_state means system is idle."""
        index = ArchiveIndex()
        index.global_state = None

        index_path = temp_archive_dir / "archive_index.json"
        index.save(index_path)

        loaded = ArchiveIndex.load(index_path)
        assert loaded.global_state is None


# =============================================================================
# V3: sbs_analysis_summary Returns Structured Data
# =============================================================================


@pytest.mark.dev
class TestAnalysisSummaryReturnsStructuredData:
    """V3: sbs_analysis_summary returns valid structured data."""

    def test_returns_total_entries(self, mock_archive_dir: Path):
        """sbs_analysis_summary returns total_entries field."""
        # Import using helper to avoid __init__.py MCP dependencies
        module = _get_self_improve_module()
        result = module.sbs_analysis_summary_impl()

        assert hasattr(result, "total_entries")
        assert isinstance(result.total_entries, int)
        assert result.total_entries >= 0

    def test_returns_entries_by_trigger(self, mock_archive_dir: Path):
        """sbs_analysis_summary returns entries_by_trigger dict."""
        module = _get_self_improve_module()
        result = module.sbs_analysis_summary_impl()

        assert hasattr(result, "entries_by_trigger")
        assert isinstance(result.entries_by_trigger, dict)

    def test_returns_most_common_tags(self, mock_archive_dir: Path):
        """sbs_analysis_summary returns most_common_tags list."""
        module = _get_self_improve_module()
        result = module.sbs_analysis_summary_impl()

        assert hasattr(result, "most_common_tags")
        assert isinstance(result.most_common_tags, list)

    def test_returns_date_range(self, mock_archive_dir: Path):
        """sbs_analysis_summary returns date_range string."""
        module = _get_self_improve_module()
        result = module.sbs_analysis_summary_impl()

        assert hasattr(result, "date_range")
        assert isinstance(result.date_range, str)

    def test_returns_projects_summary(self, mock_archive_dir: Path):
        """sbs_analysis_summary returns projects_summary dict."""
        module = _get_self_improve_module()
        result = module.sbs_analysis_summary_impl()

        assert hasattr(result, "projects_summary")
        assert isinstance(result.projects_summary, dict)

    def test_returns_findings_list(self, mock_archive_dir: Path):
        """sbs_analysis_summary returns findings as list."""
        module = _get_self_improve_module()
        result = module.sbs_analysis_summary_impl()

        assert hasattr(result, "findings")
        assert isinstance(result.findings, list)

    def test_with_populated_archive(self, mock_archive_dir: Path, monkeypatch: pytest.MonkeyPatch):
        """sbs_analysis_summary works with populated archive."""
        # Patch ARCHIVE_DIR in sbs_lsp_mcp.sbs_utils too
        sbs_utils_module = sys.modules.get("sbs_lsp_mcp.sbs_utils")
        if sbs_utils_module:
            monkeypatch.setattr(sbs_utils_module, "ARCHIVE_DIR", mock_archive_dir)

        module = _get_self_improve_module()

        # Create some entries
        index = ArchiveIndex()
        for i in range(3):
            entry = ArchiveEntry(
                entry_id=f"2024010{i}120000",
                created_at=datetime.now(timezone.utc).isoformat(),
                project="TestProject",
                trigger="build" if i < 2 else "manual",
                tags=["test", f"tag{i}"],
            )
            index.add_entry(entry)

        index_path = mock_archive_dir / "archive_index.json"
        index.save(index_path)

        result = module.sbs_analysis_summary_impl()

        assert result.total_entries == 3
        assert "build" in result.entries_by_trigger
        assert result.entries_by_trigger["build"] == 2
        assert "test" in result.most_common_tags


# =============================================================================
# V4: sbs_entries_since_self_improve Returns Entry Count
# =============================================================================


@pytest.mark.dev
class TestEntriesSinceReturnsCount:
    """V4: sbs_entries_since_self_improve returns entry count."""

    def test_returns_entries_since(self, mock_archive_dir: Path):
        """sbs_entries_since_self_improve returns entries_since list."""
        module = _get_self_improve_module()
        result = module.sbs_entries_since_self_improve_impl()

        assert hasattr(result, "entries_since")
        assert isinstance(result.entries_since, list)

    def test_returns_count_by_trigger(self, mock_archive_dir: Path):
        """sbs_entries_since_self_improve returns count_by_trigger dict."""
        module = _get_self_improve_module()
        result = module.sbs_entries_since_self_improve_impl()

        assert hasattr(result, "count_by_trigger")
        assert isinstance(result.count_by_trigger, dict)

    def test_returns_count(self, mock_archive_dir: Path):
        """sbs_entries_since_self_improve returns count integer."""
        module = _get_self_improve_module()
        result = module.sbs_entries_since_self_improve_impl()

        assert hasattr(result, "count")
        assert isinstance(result.count, int)
        assert result.count >= 0

    def test_returns_last_self_improve_fields(self, mock_archive_dir: Path):
        """sbs_entries_since_self_improve returns last_self_improve fields."""
        module = _get_self_improve_module()
        result = module.sbs_entries_since_self_improve_impl()

        assert hasattr(result, "last_self_improve_entry")
        assert hasattr(result, "last_self_improve_timestamp")
        # Can be None if no self-improve entry exists
        assert result.last_self_improve_entry is None or isinstance(
            result.last_self_improve_entry, str
        )

    def test_finds_entries_after_self_improve(self, mock_archive_dir: Path, monkeypatch: pytest.MonkeyPatch):
        """sbs_entries_since_self_improve finds entries after last self-improve."""
        # Patch ARCHIVE_DIR in sbs_lsp_mcp.sbs_utils too
        sbs_utils_module = sys.modules.get("sbs_lsp_mcp.sbs_utils")
        if sbs_utils_module:
            monkeypatch.setattr(sbs_utils_module, "ARCHIVE_DIR", mock_archive_dir)

        module = _get_self_improve_module()

        index = ArchiveIndex()

        # Create a self-improve entry
        self_improve_entry = ArchiveEntry(
            entry_id="20240101120000",
            created_at=datetime.now(timezone.utc).isoformat(),
            project="TestProject",
            trigger="skill",
            global_state={"skill": "self-improve", "substate": "archive"},
        )
        index.add_entry(self_improve_entry)

        # Create entries after self-improve
        for i in range(1, 4):
            entry = ArchiveEntry(
                entry_id=f"2024010{i + 1}120000",
                created_at=datetime.now(timezone.utc).isoformat(),
                project="TestProject",
                trigger="build",
            )
            index.add_entry(entry)

        index_path = mock_archive_dir / "archive_index.json"
        index.save(index_path)

        result = module.sbs_entries_since_self_improve_impl()

        assert result.last_self_improve_entry == "20240101120000"
        assert result.count == 3
        assert len(result.entries_since) == 3
        assert "build" in result.count_by_trigger
        assert result.count_by_trigger["build"] == 3

    def test_all_entries_when_no_self_improve(self, mock_archive_dir: Path, monkeypatch: pytest.MonkeyPatch):
        """Returns all entries when no self-improve entry exists."""
        # Patch ARCHIVE_DIR in sbs_lsp_mcp.sbs_utils too
        sbs_utils_module = sys.modules.get("sbs_lsp_mcp.sbs_utils")
        if sbs_utils_module:
            monkeypatch.setattr(sbs_utils_module, "ARCHIVE_DIR", mock_archive_dir)

        module = _get_self_improve_module()

        index = ArchiveIndex()

        # Create entries without any self-improve
        for i in range(3):
            entry = ArchiveEntry(
                entry_id=f"2024010{i}120000",
                created_at=datetime.now(timezone.utc).isoformat(),
                project="TestProject",
                trigger="build",
            )
            index.add_entry(entry)

        index_path = mock_archive_dir / "archive_index.json"
        index.save(index_path)

        result = module.sbs_entries_since_self_improve_impl()

        assert result.last_self_improve_entry is None
        assert result.count == 3


# =============================================================================
# New Analysis Functions (Issues #22-#26)
# =============================================================================


@pytest.mark.dev
class TestNewAnalysisFunctions:
    """Tests for new self-improve analysis MCP tools."""

    def test_successful_sessions_returns_structured_data(self, mock_archive_dir: Path):
        """sbs_successful_sessions_impl returns SuccessPatterns."""
        module = _get_self_improve_module()
        result = module.sbs_successful_sessions_impl()
        assert hasattr(result, "patterns")
        assert hasattr(result, "total_sessions_analyzed")
        assert isinstance(result.patterns, list)

    def test_comparative_analysis_returns_structured_data(self, mock_archive_dir: Path):
        """sbs_comparative_analysis_impl returns ComparativeAnalysis."""
        module = _get_self_improve_module()
        result = module.sbs_comparative_analysis_impl()
        assert hasattr(result, "approved_count")
        assert hasattr(result, "rejected_count")
        assert hasattr(result, "features")

    def test_system_health_returns_structured_data(self, mock_archive_dir: Path):
        """sbs_system_health_impl returns SystemHealthReport."""
        module = _get_self_improve_module()
        result = module.sbs_system_health_impl()
        assert hasattr(result, "build_metrics")
        assert hasattr(result, "findings")
        assert hasattr(result, "overall_health")

    def test_user_patterns_returns_structured_data(self, mock_archive_dir: Path):
        """sbs_user_patterns_impl returns UserPatternAnalysis."""
        module = _get_self_improve_module()
        result = module.sbs_user_patterns_impl()
        assert hasattr(result, "total_sessions_analyzed")
        assert hasattr(result, "effective_patterns")
        assert hasattr(result, "findings")


# =============================================================================
# Self-Improve MCP Tools (Issue #65)
# =============================================================================


@pytest.mark.dev
class TestSelfImproveMCPTools:
    """Tests for the 5 new self-improve MCP tools."""

    # --- Structural tests (one per tool) ---

    def test_skill_stats_returns_structured_data(self, mock_archive_dir: Path):
        """sbs_skill_stats_impl returns SkillStatsResult."""
        module = _get_self_improve_module()
        result = module.sbs_skill_stats_impl()
        assert hasattr(result, "skills")
        assert hasattr(result, "total_sessions")
        assert hasattr(result, "findings")
        assert hasattr(result, "summary")
        assert isinstance(result.skills, dict)
        assert isinstance(result.total_sessions, int)

    def test_phase_transition_health_returns_structured_data(self, mock_archive_dir: Path):
        """sbs_phase_transition_health_impl returns PhaseTransitionHealthResult."""
        module = _get_self_improve_module()
        result = module.sbs_phase_transition_health_impl()
        assert hasattr(result, "reports")
        assert hasattr(result, "findings")
        assert hasattr(result, "summary")
        assert isinstance(result.reports, list)

    def test_interruption_analysis_returns_structured_data(self, mock_archive_dir: Path):
        """sbs_interruption_analysis_impl returns InterruptionAnalysisResult."""
        module = _get_self_improve_module()
        result = module.sbs_interruption_analysis_impl()
        assert hasattr(result, "events")
        assert hasattr(result, "total_sessions_analyzed")
        assert hasattr(result, "sessions_with_interruptions")
        assert hasattr(result, "findings")
        assert isinstance(result.events, list)

    def test_gate_failures_returns_structured_data(self, mock_archive_dir: Path):
        """sbs_gate_failures_impl returns GateFailureReport."""
        module = _get_self_improve_module()
        result = module.sbs_gate_failures_impl()
        assert hasattr(result, "total_gate_checks")
        assert hasattr(result, "total_failures")
        assert hasattr(result, "failure_rate")
        assert hasattr(result, "failures")
        assert hasattr(result, "findings")

    def test_tag_effectiveness_returns_structured_data(self, mock_archive_dir: Path):
        """sbs_tag_effectiveness_impl returns TagEffectivenessResult."""
        module = _get_self_improve_module()
        result = module.sbs_tag_effectiveness_impl()
        assert hasattr(result, "tags")
        assert hasattr(result, "noisy_tags")
        assert hasattr(result, "signal_tags")
        assert hasattr(result, "findings")
        assert isinstance(result.tags, list)

    # --- Populated archive tests ---

    def test_skill_stats_counts_completions(self, mock_archive_dir: Path, monkeypatch: pytest.MonkeyPatch):
        """Skill stats correctly count invocations and completions."""
        sbs_utils_module = sys.modules.get("sbs_lsp_mcp.sbs_utils")
        if sbs_utils_module:
            monkeypatch.setattr(sbs_utils_module, "ARCHIVE_DIR", mock_archive_dir)

        module = _get_self_improve_module()

        index = ArchiveIndex()
        # Session 1: complete task (phase_start alignment -> phase_start execution -> phase_end)
        index.add_entry(ArchiveEntry(
            entry_id="20240101100000",
            created_at="2024-01-01T10:00:00+00:00",
            project="TestProject",
            trigger="skill",
            global_state={"skill": "task", "substate": "alignment"},
            state_transition="phase_start",
        ))
        index.add_entry(ArchiveEntry(
            entry_id="20240101110000",
            created_at="2024-01-01T11:00:00+00:00",
            project="TestProject",
            trigger="skill",
            global_state={"skill": "task", "substate": "execution"},
        ))
        index.add_entry(ArchiveEntry(
            entry_id="20240101120000",
            created_at="2024-01-01T12:00:00+00:00",
            project="TestProject",
            trigger="skill",
            global_state={"skill": "task", "substate": "finalization"},
            state_transition="phase_end",
        ))
        # Session 2: incomplete task (phase_start only)
        index.add_entry(ArchiveEntry(
            entry_id="20240102100000",
            created_at="2024-01-02T10:00:00+00:00",
            project="TestProject",
            trigger="skill",
            global_state={"skill": "task", "substate": "alignment"},
            state_transition="phase_start",
        ))
        index.add_entry(ArchiveEntry(
            entry_id="20240102110000",
            created_at="2024-01-02T11:00:00+00:00",
            project="TestProject",
            trigger="skill",
            global_state={"skill": "task", "substate": "planning"},
        ))

        index_path = mock_archive_dir / "archive_index.json"
        index.save(index_path)

        result = module.sbs_skill_stats_impl()
        assert "task" in result.skills
        task_stats = result.skills["task"]
        assert task_stats.invocation_count == 2
        assert task_stats.completion_count == 1

    def test_phase_transition_detects_backward(self, mock_archive_dir: Path, monkeypatch: pytest.MonkeyPatch):
        """Phase transition health detects backward jumps."""
        sbs_utils_module = sys.modules.get("sbs_lsp_mcp.sbs_utils")
        if sbs_utils_module:
            monkeypatch.setattr(sbs_utils_module, "ARCHIVE_DIR", mock_archive_dir)

        module = _get_self_improve_module()

        index = ArchiveIndex()
        # Session with backward jump: alignment -> execution -> alignment
        index.add_entry(ArchiveEntry(
            entry_id="20240101100000",
            created_at="2024-01-01T10:00:00+00:00",
            project="TestProject",
            trigger="skill",
            global_state={"skill": "task", "substate": "alignment"},
            state_transition="phase_start",
        ))
        index.add_entry(ArchiveEntry(
            entry_id="20240101110000",
            created_at="2024-01-01T11:00:00+00:00",
            project="TestProject",
            trigger="skill",
            global_state={"skill": "task", "substate": "execution"},
        ))
        index.add_entry(ArchiveEntry(
            entry_id="20240101120000",
            created_at="2024-01-01T12:00:00+00:00",
            project="TestProject",
            trigger="skill",
            global_state={"skill": "task", "substate": "alignment"},
        ))

        index_path = mock_archive_dir / "archive_index.json"
        index.save(index_path)

        result = module.sbs_phase_transition_health_impl()
        assert len(result.reports) > 0
        task_report = [r for r in result.reports if r.skill == "task"]
        assert len(task_report) == 1
        assert task_report[0].backward_transitions >= 1

    def test_interruption_detects_retry(self, mock_archive_dir: Path, monkeypatch: pytest.MonkeyPatch):
        """Interruption analysis detects retry patterns (>2 entries in same substate)."""
        sbs_utils_module = sys.modules.get("sbs_lsp_mcp.sbs_utils")
        if sbs_utils_module:
            monkeypatch.setattr(sbs_utils_module, "ARCHIVE_DIR", mock_archive_dir)

        module = _get_self_improve_module()

        index = ArchiveIndex()
        # Session with 3+ entries in same substate
        for i in range(4):
            index.add_entry(ArchiveEntry(
                entry_id=f"2024010110{i:04d}",
                created_at=f"2024-01-01T10:{i:02d}:00+00:00",
                project="TestProject",
                trigger="skill",
                global_state={"skill": "task", "substate": "execution"},
                state_transition="phase_start" if i == 0 else None,
            ))

        index_path = mock_archive_dir / "archive_index.json"
        index.save(index_path)

        result = module.sbs_interruption_analysis_impl()
        retry_events = [e for e in result.events if e.event_type == "retry"]
        assert len(retry_events) >= 1

    def test_gate_failures_detects_failure(self, mock_archive_dir: Path, monkeypatch: pytest.MonkeyPatch):
        """Gate failures analysis detects entries with gate_validation.passed == False."""
        sbs_utils_module = sys.modules.get("sbs_lsp_mcp.sbs_utils")
        if sbs_utils_module:
            monkeypatch.setattr(sbs_utils_module, "ARCHIVE_DIR", mock_archive_dir)

        module = _get_self_improve_module()

        index = ArchiveIndex()
        index.add_entry(ArchiveEntry(
            entry_id="20240101100000",
            created_at="2024-01-01T10:00:00+00:00",
            project="TestProject",
            trigger="skill",
            global_state={"skill": "task", "substate": "execution"},
            state_transition="phase_start",
            gate_validation={"passed": False, "findings": ["T5 failed"]},
        ))
        # A passing entry for comparison
        index.add_entry(ArchiveEntry(
            entry_id="20240101110000",
            created_at="2024-01-01T11:00:00+00:00",
            project="TestProject",
            trigger="skill",
            global_state={"skill": "task", "substate": "execution"},
            gate_validation={"passed": True, "findings": []},
        ))

        index_path = mock_archive_dir / "archive_index.json"
        index.save(index_path)

        result = module.sbs_gate_failures_impl()
        assert result.total_gate_checks == 2
        assert result.total_failures == 1
        assert len(result.failures) == 1
        assert "T5 failed" in result.failures[0].gate_findings

    def test_tag_effectiveness_classifies_noise(self, mock_archive_dir: Path, monkeypatch: pytest.MonkeyPatch):
        """Tag effectiveness classifies high-frequency tags as noise."""
        sbs_utils_module = sys.modules.get("sbs_lsp_mcp.sbs_utils")
        if sbs_utils_module:
            monkeypatch.setattr(sbs_utils_module, "ARCHIVE_DIR", mock_archive_dir)

        module = _get_self_improve_module()

        index = ArchiveIndex()
        # Create 10 entries, one tag appears on 9+
        for i in range(10):
            auto_tags = ["ubiquitous_tag"]
            if i < 2:
                auto_tags.append("rare_tag")
            index.add_entry(ArchiveEntry(
                entry_id=f"2024010{i}100000",
                created_at=f"2024-01-0{i + 1}T10:00:00+00:00" if i < 9 else "2024-01-10T10:00:00+00:00",
                project="TestProject",
                trigger="skill",
                auto_tags=auto_tags,
            ))

        index_path = mock_archive_dir / "archive_index.json"
        index.save(index_path)

        result = module.sbs_tag_effectiveness_impl()
        assert "ubiquitous_tag" in result.noisy_tags

    def test_as_findings_populates_findings(self, mock_archive_dir: Path, monkeypatch: pytest.MonkeyPatch):
        """as_findings=True populates the findings field on populated data."""
        sbs_utils_module = sys.modules.get("sbs_lsp_mcp.sbs_utils")
        if sbs_utils_module:
            monkeypatch.setattr(sbs_utils_module, "ARCHIVE_DIR", mock_archive_dir)

        module = _get_self_improve_module()

        index = ArchiveIndex()
        # Create 3 separate incomplete task sessions to trigger low completion rate finding.
        # Each session is separated by a different-skill entry (which closes the previous
        # task session). Null-state entries do NOT break sessions in the fixed algorithm.
        for i in range(3):
            # Start a task session
            index.add_entry(ArchiveEntry(
                entry_id=f"2024010{i}100000",
                created_at=f"2024-01-0{i + 1}T10:00:00+00:00",
                project="TestProject",
                trigger="skill",
                global_state={"skill": "task", "substate": "alignment"},
                state_transition="phase_start",
            ))
            # Different-skill entry forces session boundary
            index.add_entry(ArchiveEntry(
                entry_id=f"2024010{i}110000",
                created_at=f"2024-01-0{i + 1}T11:00:00+00:00",
                project="TestProject",
                trigger="skill",
                global_state={"skill": "log", "substate": "logging"},
                state_transition="phase_start",
            ))

        index_path = mock_archive_dir / "archive_index.json"
        index.save(index_path)

        result = module.sbs_skill_stats_impl(as_findings=True)
        # With 3 invocations and 0 completions, completion_rate = 0 < 0.5
        # and invocation_count >= 2, so a finding should be generated
        assert len(result.findings) >= 1
        assert result.findings[0].pillar == "claude_execution"
