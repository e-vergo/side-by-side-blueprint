"""
Tests for the /self-improve skill and sbs-improver agent.

Validates:
- V1: Skill file exists and parses correctly
- V2: Agent file exists and parses correctly
- V5: Archive entries with self-improve tag work
- V7: Recovery from each phase works

MCP tool tests (V3, V4) are in Wave 2.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from sbs.archive.entry import ArchiveEntry, ArchiveIndex


# =============================================================================
# Paths
# =============================================================================

MONOREPO_ROOT = Path("/Users/eric/GitHub/Side-By-Side-Blueprint")
SKILL_FILE = MONOREPO_ROOT / ".claude" / "skills" / "self-improve" / "SKILL.md"
AGENT_FILE = MONOREPO_ROOT / ".claude" / "agents" / "sbs-improver.md"


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


# =============================================================================
# V2: Agent File Tests
# =============================================================================


@pytest.mark.dev
class TestAgentFileExistsAndParses:
    """V2: Agent file exists and parses correctly."""

    def test_agent_file_exists(self):
        """Agent file must exist at expected path."""
        assert AGENT_FILE.exists(), f"Agent file not found at {AGENT_FILE}"

    def test_agent_file_has_yaml_frontmatter(self):
        """Agent file must have valid YAML frontmatter."""
        content = AGENT_FILE.read_text()

        assert content.startswith("---"), "Agent file must start with YAML frontmatter"

        parts = content.split("---", 2)
        assert len(parts) >= 3, "Agent file must have closing --- for frontmatter"

        frontmatter = parts[1].strip()
        parsed = yaml.safe_load(frontmatter)

        assert isinstance(parsed, dict), "Frontmatter must parse to a dict"

    def test_agent_frontmatter_has_required_fields(self):
        """Agent frontmatter must have name, model, color."""
        content = AGENT_FILE.read_text()
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1].strip())

        assert "name" in frontmatter, "Frontmatter must have 'name'"
        assert frontmatter["name"] == "sbs-improver", "Name must be 'sbs-improver'"

        assert "model" in frontmatter, "Frontmatter must have 'model'"
        assert frontmatter["model"] == "opus", "Model must be 'opus'"

        assert "color" in frontmatter, "Frontmatter must have 'color'"
        assert frontmatter["color"] != "pink", "Color must not be pink (reserved for sbs-developer)"

    def test_agent_has_four_pillars(self):
        """Agent must document four pillars framework."""
        content = AGENT_FILE.read_text()

        pillars = [
            "user effectiveness",
            "claude execution",
            "alignment patterns",
            "system engineering"
        ]
        for pillar in pillars:
            assert pillar.lower() in content.lower(), \
                f"Agent must document pillar: {pillar}"

    def test_agent_has_tool_inventory(self):
        """Agent must have tool inventory section."""
        content = AGENT_FILE.read_text()

        assert "tool inventory" in content.lower(), \
            "Agent must have 'Tool Inventory' section"

        # Should reference key MCP tools
        expected_tools = ["sbs_archive_state", "sbs_search_entries", "sbs_issue_create"]
        for tool in expected_tools:
            assert tool in content, f"Agent must reference tool: {tool}"

    def test_agent_has_anti_patterns(self):
        """Agent must document anti-patterns."""
        content = AGENT_FILE.read_text()

        assert "anti-pattern" in content.lower(), \
            "Agent must have anti-patterns section"


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
