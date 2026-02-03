"""
Tests for the agent-state tag taxonomy and expanded tagging context.

Validates that agent_state_taxonomy.yaml loads correctly, tags are well-formed,
and build_tagging_context() includes state machine, token, and quality fields.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sbs.archive.entry import ArchiveEntry
from sbs.archive.tagger import (
    build_tagging_context,
    load_agent_state_taxonomy,
    _reset_taxonomy_cache,
    _TAXONOMY_PATH,
)

# All tests in this module are evergreen
pytestmark = pytest.mark.evergreen

TAXONOMY_FILE = _TAXONOMY_PATH

EXPECTED_DIMENSIONS = {
    "phase", "transition", "skill", "trigger", "session",
    "outcome", "signal", "scope", "repo", "epoch",
    "linkage", "token", "thinking", "tool", "quality", "model",
}


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def _clear_taxonomy_cache():
    """Ensure taxonomy cache is cleared between tests."""
    _reset_taxonomy_cache()
    yield
    _reset_taxonomy_cache()


@pytest.fixture()
def raw_taxonomy() -> dict:
    """Load the raw taxonomy YAML."""
    with open(TAXONOMY_FILE) as f:
        return yaml.safe_load(f)


@pytest.fixture()
def flat_taxonomy() -> dict[str, dict]:
    """Load taxonomy via the loader function."""
    return load_agent_state_taxonomy()


@pytest.fixture()
def minimal_entry() -> ArchiveEntry:
    """Create a minimal ArchiveEntry for context builder tests."""
    return ArchiveEntry(
        entry_id="1700000000",
        created_at="2025-11-14T00:00:00Z",
        project="SBSTest",
        trigger="skill",
        global_state={"skill": "task", "substate": "execution"},
        state_transition="phase_start",
        epoch_summary={"entries": 5},
        gate_validation={"passed": True, "findings": ["All passed"]},
        quality_scores={"overall": 0.85, "scores": {}},
        quality_delta={"overall": 0.02},
        claude_data={
            "session_ids": ["s1", "s2"],
            "tool_call_count": 42,
            "message_count": 100,
            "plan_files": ["plan.md"],
            "total_input_tokens": 250000,
            "total_output_tokens": 30000,
            "cache_read_tokens": 150000,
            "thinking_block_count": 5,
            "unique_tools_used": ["Read", "Edit", "Bash", "Grep", "Glob"],
            "model_versions_used": ["claude-opus-4-5-20251101"],
        },
    )


# =============================================================================
# 1. Taxonomy YAML loads successfully
# =============================================================================


class TestTaxonomyLoads:
    """Taxonomy YAML loads and has required structure."""

    def test_yaml_loads(self, raw_taxonomy: dict) -> None:
        """YAML file loads without error and has required top-level keys."""
        assert "version" in raw_taxonomy
        assert "name" in raw_taxonomy
        assert raw_taxonomy["name"] == "agent-state"
        assert "dimensions" in raw_taxonomy
        assert isinstance(raw_taxonomy["dimensions"], dict)


# =============================================================================
# 2. All tag names are unique
# =============================================================================


class TestTagUniqueness:
    """All tag names are unique across all dimensions."""

    def test_all_tags_unique(self, raw_taxonomy: dict) -> None:
        """No duplicate tag names across all dimensions."""
        seen: set[str] = set()
        duplicates: list[str] = []
        for dim_data in raw_taxonomy["dimensions"].values():
            for tag_entry in dim_data.get("tags", []):
                name = tag_entry["name"]
                if name in seen:
                    duplicates.append(name)
                seen.add(name)
        assert duplicates == [], f"Duplicate tags found: {duplicates}"


# =============================================================================
# 3. All tag names follow colon-delimited format
# =============================================================================


class TestTagNaming:
    """Tag names follow dimension:value format."""

    def test_colon_delimited(self, raw_taxonomy: dict) -> None:
        """Every tag contains at least one colon (dimension:value)."""
        violations: list[str] = []
        for dim_data in raw_taxonomy["dimensions"].values():
            for tag_entry in dim_data.get("tags", []):
                name = tag_entry["name"]
                if ":" not in name:
                    violations.append(name)
        assert violations == [], f"Tags without colons: {violations}"

    def test_tag_prefix_matches_dimension(self, raw_taxonomy: dict) -> None:
        """Tag prefix (before first colon) matches its dimension key."""
        mismatched: list[tuple[str, str]] = []
        for dim_name, dim_data in raw_taxonomy["dimensions"].items():
            for tag_entry in dim_data.get("tags", []):
                name = tag_entry["name"]
                prefix = name.split(":")[0]
                if prefix != dim_name:
                    mismatched.append((name, dim_name))
        assert mismatched == [], f"Tag prefix != dimension: {mismatched}"

    def test_no_spaces_in_tag_names(self, raw_taxonomy: dict) -> None:
        """Tag names must not contain spaces."""
        with_spaces: list[str] = []
        for dim_data in raw_taxonomy["dimensions"].values():
            for tag_entry in dim_data.get("tags", []):
                if " " in tag_entry["name"]:
                    with_spaces.append(tag_entry["name"])
        assert with_spaces == [], f"Tags with spaces: {with_spaces}"


# =============================================================================
# 4. All 16 dimensions present
# =============================================================================


class TestDimensions:
    """All expected dimensions are defined."""

    def test_all_dimensions_present(self, raw_taxonomy: dict) -> None:
        """Taxonomy defines exactly the expected set of 16 dimensions."""
        actual = set(raw_taxonomy["dimensions"].keys())
        assert actual == EXPECTED_DIMENSIONS, (
            f"Missing: {EXPECTED_DIMENSIONS - actual}, "
            f"Extra: {actual - EXPECTED_DIMENSIONS}"
        )


# =============================================================================
# 5. Tag count in reasonable range
# =============================================================================


class TestTagCount:
    """Sanity check on total tag count."""

    def test_tag_count_range(self, raw_taxonomy: dict) -> None:
        """Total tag count is between 120 and 160 (sanity check)."""
        count = sum(
            len(dim_data.get("tags", []))
            for dim_data in raw_taxonomy["dimensions"].values()
        )
        assert 120 <= count <= 160, (
            f"Expected 120-160 tags, got {count}. "
            f"Taxonomy may have drifted significantly."
        )


# =============================================================================
# 6. Each dimension has at least 3 tags
# =============================================================================


class TestMinimumTags:
    """Each dimension has a minimum number of tags."""

    def test_each_dimension_has_at_least_3(self, raw_taxonomy: dict) -> None:
        """Every dimension defines at least 3 tags."""
        sparse: list[tuple[str, int]] = []
        for dim_name, dim_data in raw_taxonomy["dimensions"].items():
            tag_count = len(dim_data.get("tags", []))
            if tag_count < 3:
                sparse.append((dim_name, tag_count))
        assert sparse == [], f"Dimensions with <3 tags: {sparse}"


# =============================================================================
# 7. No empty descriptions
# =============================================================================


class TestDescriptions:
    """All tags and dimensions have non-empty descriptions."""

    def test_no_empty_tag_descriptions(self, raw_taxonomy: dict) -> None:
        """Every tag has a non-empty description string."""
        empty: list[str] = []
        for dim_data in raw_taxonomy["dimensions"].values():
            for tag_entry in dim_data.get("tags", []):
                if not tag_entry.get("description", "").strip():
                    empty.append(tag_entry["name"])
        assert empty == [], f"Tags with empty descriptions: {empty}"

    def test_no_empty_dimension_descriptions(self, raw_taxonomy: dict) -> None:
        """Every dimension has a non-empty description."""
        empty: list[str] = []
        for dim_name, dim_data in raw_taxonomy["dimensions"].items():
            if not dim_data.get("description", "").strip():
                empty.append(dim_name)
        assert empty == [], f"Dimensions with empty descriptions: {empty}"


# =============================================================================
# 8. Taxonomy loader function works correctly
# =============================================================================


class TestTaxonomyLoader:
    """Tests for load_agent_state_taxonomy()."""

    def test_loader_returns_flat_dict(self, flat_taxonomy: dict[str, dict]) -> None:
        """Loader returns a flat dict keyed by tag name."""
        assert isinstance(flat_taxonomy, dict)
        assert len(flat_taxonomy) > 0
        # Check a known tag
        assert "phase:execution" in flat_taxonomy
        assert flat_taxonomy["phase:execution"]["dimension"] == "phase"

    def test_loader_caches(self) -> None:
        """Second call returns the same object (cached)."""
        first = load_agent_state_taxonomy()
        second = load_agent_state_taxonomy()
        assert first is second

    def test_loader_has_description_and_dimension(self, flat_taxonomy: dict[str, dict]) -> None:
        """Every entry in the flat taxonomy has description and dimension keys."""
        for tag_name, info in flat_taxonomy.items():
            assert "description" in info, f"{tag_name} missing description"
            assert "dimension" in info, f"{tag_name} missing dimension"


# =============================================================================
# 9. Context builder includes state machine fields
# =============================================================================


class TestContextStateMachine:
    """build_tagging_context() includes state machine fields."""

    def test_skill_field(self, minimal_entry: ArchiveEntry) -> None:
        """Context includes skill from global_state."""
        ctx = build_tagging_context(minimal_entry)
        assert ctx["skill"] == "task"

    def test_substate_field(self, minimal_entry: ArchiveEntry) -> None:
        """Context includes substate from global_state."""
        ctx = build_tagging_context(minimal_entry)
        assert ctx["substate"] == "execution"

    def test_state_transition_field(self, minimal_entry: ArchiveEntry) -> None:
        """Context includes state_transition."""
        ctx = build_tagging_context(minimal_entry)
        assert ctx["state_transition"] == "phase_start"

    def test_has_epoch_summary(self, minimal_entry: ArchiveEntry) -> None:
        """Context includes has_epoch_summary boolean."""
        ctx = build_tagging_context(minimal_entry)
        assert ctx["has_epoch_summary"] is True

    def test_gate_passed(self, minimal_entry: ArchiveEntry) -> None:
        """Context includes gate_passed."""
        ctx = build_tagging_context(minimal_entry)
        assert ctx["gate_passed"] is True

    def test_null_global_state(self) -> None:
        """Context handles None global_state gracefully."""
        entry = ArchiveEntry(
            entry_id="1700000001",
            created_at="2025-11-14T00:00:01Z",
            project="SBSTest",
            global_state=None,
            state_transition=None,
            gate_validation=None,
        )
        ctx = build_tagging_context(entry)
        assert ctx["skill"] is None
        assert ctx["substate"] is None
        assert ctx["gate_passed"] is None

    def test_quality_fields(self, minimal_entry: ArchiveEntry) -> None:
        """Context includes quality_overall and quality_delta."""
        ctx = build_tagging_context(minimal_entry)
        assert ctx["quality_overall"] == 0.85
        assert ctx["quality_delta"] == 0.02


# =============================================================================
# 10. Context builder includes token fields
# =============================================================================


class TestContextTokens:
    """build_tagging_context() includes token and model fields."""

    def test_token_counts(self, minimal_entry: ArchiveEntry) -> None:
        """Context includes all token count fields."""
        ctx = build_tagging_context(minimal_entry)
        assert ctx["total_input_tokens"] == 250000
        assert ctx["total_output_tokens"] == 30000
        assert ctx["total_tokens"] == 280000
        assert ctx["cache_read_tokens"] == 150000

    def test_thinking_block_count(self, minimal_entry: ArchiveEntry) -> None:
        """Context includes thinking_block_count."""
        ctx = build_tagging_context(minimal_entry)
        assert ctx["thinking_block_count"] == 5

    def test_unique_tools_count(self, minimal_entry: ArchiveEntry) -> None:
        """Context includes unique_tools_count."""
        ctx = build_tagging_context(minimal_entry)
        assert ctx["unique_tools_count"] == 5

    def test_model_versions(self, minimal_entry: ArchiveEntry) -> None:
        """Context includes model_versions list."""
        ctx = build_tagging_context(minimal_entry)
        assert ctx["model_versions"] == ["claude-opus-4-5-20251101"]

    def test_defaults_without_claude_data(self) -> None:
        """Token fields default to zero when claude_data is absent."""
        entry = ArchiveEntry(
            entry_id="1700000002",
            created_at="2025-11-14T00:00:02Z",
            project="SBSTest",
            claude_data=None,
        )
        ctx = build_tagging_context(entry)
        assert ctx["total_input_tokens"] == 0
        assert ctx["total_output_tokens"] == 0
        assert ctx["total_tokens"] == 0
        assert ctx["cache_read_tokens"] == 0
        assert ctx["thinking_block_count"] == 0
        assert ctx["unique_tools_count"] == 0
        assert ctx["model_versions"] == []
