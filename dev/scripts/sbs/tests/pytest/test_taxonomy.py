"""
Tests for the unified taxonomy system.

Validates that taxonomy.yaml (v3.0) loads correctly, entries are well-formed,
context filtering works, and the Python API is backward-compatible.
Also validates archive-specific concerns (scope field, tagger integration).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from sbs.labels import (
    TAXONOMY_PATH,
    _entry_matches_context,
    _reset_taxonomy_cache,
    get_all_labels,
    get_dimension_for_label,
    get_label_color,
    get_label_info,
    load_taxonomy,
    validate_labels,
)
from sbs.archive.tagger import (
    build_entry_context,
    build_session_context,
    build_tagging_context,
    load_agent_state_taxonomy,
    _reset_taxonomy_cache as _reset_tagger_cache,
    VALID_SCOPES,
    _ENTRY_FIELDS,
    _SESSION_FIELDS,
)
from sbs.archive.entry import ArchiveEntry

# All tests in this module are evergreen (production tests, never skip)
pytestmark = pytest.mark.evergreen


# Expected dimensions from both sources
ISSUE_DIMENSIONS = {
    "origin", "type", "area_sbs", "area_devtools", "area_lean",
    "loop", "impact", "scope", "pillar", "project", "friction",
}

ARCHIVE_DIMENSIONS = {
    "phase", "transition", "skill", "trigger", "session",
    "outcome", "signal", "scope", "repo", "epoch",
    "linkage", "token", "thinking", "tool", "quality", "model",
    "improvement",
}

ALL_DIMENSIONS = ISSUE_DIMENSIONS | ARCHIVE_DIMENSIONS


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def _clear_caches():
    """Ensure taxonomy caches are cleared between tests."""
    _reset_taxonomy_cache()
    _reset_tagger_cache()
    yield
    _reset_taxonomy_cache()
    _reset_tagger_cache()


@pytest.fixture()
def raw_taxonomy() -> dict:
    """Load the raw taxonomy YAML."""
    with open(TAXONOMY_PATH) as f:
        return yaml.safe_load(f)


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
# 1. Loading
# =============================================================================


class TestTaxonomyLoading:
    """Tests that taxonomy.yaml loads and has expected structure."""

    def test_taxonomy_loads(self) -> None:
        """YAML loads without error and has required top-level keys."""
        taxonomy = load_taxonomy()
        assert "version" in taxonomy
        assert taxonomy["version"] == "3.0"
        assert "dimensions" in taxonomy
        assert isinstance(taxonomy["dimensions"], dict)

    def test_taxonomy_has_all_dimensions(self, raw_taxonomy: dict) -> None:
        """Taxonomy defines the complete set of dimensions from both sources."""
        actual = set(raw_taxonomy["dimensions"].keys())
        assert actual == ALL_DIMENSIONS, (
            f"Missing: {ALL_DIMENSIONS - actual}, Extra: {actual - ALL_DIMENSIONS}"
        )

    def test_taxonomy_has_standalone(self) -> None:
        """Taxonomy defines standalone entries."""
        taxonomy = load_taxonomy()
        standalone = taxonomy.get("standalone", [])
        assert len(standalone) >= 1
        names = [e["name"] for e in standalone]
        assert "ai-authored" in names


# =============================================================================
# 2. Entry Uniqueness
# =============================================================================


class TestEntryUniqueness:
    """Tests that all entry names are unique across dimensions."""

    def test_all_entries_unique(self) -> None:
        """No duplicate entry names across all dimensions and standalone."""
        all_labels = get_all_labels()
        seen: set[str] = set()
        duplicates: list[str] = []
        for label in all_labels:
            if label in seen:
                duplicates.append(label)
            seen.add(label)
        assert duplicates == [], f"Duplicate entries found: {duplicates}"


# =============================================================================
# 3. Naming Convention
# =============================================================================


class TestEntryNaming:
    """Tests that entry names follow the colon-delimited convention."""

    # Entries that are intentionally single-segment (no colons)
    SINGLE_SEGMENT_EXCEPTIONS = {"behavior", "investigation", "ai-authored"}

    def test_entry_names_colon_delimited(self) -> None:
        """All multi-segment entries use colons as delimiters."""
        all_labels = get_all_labels()
        violations: list[str] = []
        for label in all_labels:
            if label in self.SINGLE_SEGMENT_EXCEPTIONS:
                continue
            if ":" not in label:
                violations.append(label)
        assert violations == [], (
            f"Entries without colons (not in exceptions): {violations}"
        )

    def test_no_spaces_in_entry_names(self) -> None:
        """Entry names must not contain spaces."""
        all_labels = get_all_labels()
        with_spaces = [l for l in all_labels if " " in l]
        assert with_spaces == [], f"Entries with spaces: {with_spaces}"


# =============================================================================
# 4. Colors
# =============================================================================

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class TestColors:
    """Tests that colors are valid hex codes."""

    def test_colors_valid_hex(self) -> None:
        """All defined colors are valid 6-digit hex codes."""
        taxonomy = load_taxonomy()
        invalid: list[tuple[str, str]] = []

        # Dimension-level colors
        for dim_name, dim_data in taxonomy.get("dimensions", {}).items():
            dim_color = dim_data.get("color")
            if dim_color and not HEX_COLOR_RE.match(dim_color):
                invalid.append((f"dimension:{dim_name}", dim_color))

            # Entry-level colors
            for entry in dim_data.get("entries", []):
                entry_color = entry.get("color")
                if entry_color and not HEX_COLOR_RE.match(entry_color):
                    invalid.append((entry["name"], entry_color))

        # Standalone colors
        for entry in taxonomy.get("standalone", []):
            entry_color = entry.get("color")
            if entry_color and not HEX_COLOR_RE.match(entry_color):
                invalid.append((entry["name"], entry_color))

        assert invalid == [], f"Invalid hex colors: {invalid}"

    def test_every_issue_label_has_resolvable_color(self) -> None:
        """Every issue-context entry resolves to a color (own or dimension default)."""
        issue_labels = get_all_labels(context="issues")
        missing: list[str] = []
        for label in issue_labels:
            color = get_label_color(label)
            if not color:
                missing.append(label)
        assert missing == [], f"Issue labels with no resolvable color: {missing}"


# =============================================================================
# 5. Context Filtering
# =============================================================================


class TestContextFiltering:
    """Tests that context-based filtering works correctly."""

    def test_all_labels_returns_everything(self) -> None:
        """get_all_labels() with no args returns all entries."""
        all_labels = get_all_labels()
        assert len(all_labels) >= 200, f"Expected 200+ entries, got {len(all_labels)}"

    def test_issues_context_filters_correctly(self) -> None:
        """Issues context returns only issue-scoped entries."""
        issue_labels = get_all_labels(context="issues")
        # Issue-only entries like origin:user should be present
        assert "origin:user" in issue_labels
        # Archive-only entries like phase:execution should not
        assert "phase:execution" not in issue_labels

    def test_archive_context_filters_correctly(self) -> None:
        """Archive context returns only archive-scoped entries."""
        archive_labels = get_all_labels(context="archive")
        # Archive-only entries like phase:execution should be present
        assert "phase:execution" in archive_labels
        # Issue-only entries like origin:user should not
        assert "origin:user" not in archive_labels

    def test_both_context_entries_appear_in_issues_and_archive(self) -> None:
        """Entries with contexts=[both] appear in both issue and archive queries."""
        issue_labels = set(get_all_labels(context="issues"))
        archive_labels = set(get_all_labels(context="archive"))
        # scope:cross-repo has contexts=[both]
        assert "scope:cross-repo" in issue_labels
        assert "scope:cross-repo" in archive_labels
        assert "scope:single-repo" in issue_labels
        assert "scope:single-repo" in archive_labels

    def test_no_naming_collisions_within_contexts(self) -> None:
        """No duplicate names exist within a single context."""
        for ctx in ("issues", "archive"):
            labels = get_all_labels(context=ctx)
            seen: set[str] = set()
            dupes: list[str] = []
            for label in labels:
                if label in seen:
                    dupes.append(label)
                seen.add(label)
            assert dupes == [], f"Duplicates in {ctx} context: {dupes}"

    def test_issue_count_matches_original(self) -> None:
        """Issue-context entry count matches the original labels taxonomy."""
        issue_labels = get_all_labels(context="issues")
        # Original had 107 labels (105 in dimensions + 2 standalone)
        assert len(issue_labels) == 107, (
            f"Expected 107 issue labels, got {len(issue_labels)}"
        )

    def test_archive_count_matches_original(self) -> None:
        """Archive-context entry count matches the original agent-state taxonomy."""
        archive_labels = get_all_labels(context="archive")
        # Original had 138 tags (all from dimensions, no standalone)
        assert len(archive_labels) == 138, (
            f"Expected 138 archive tags, got {len(archive_labels)}"
        )


# =============================================================================
# 6. Scope Field (archive entries)
# =============================================================================


class TestScopeField:
    """Tests that archive-context entries have valid scope fields."""

    def test_archive_entries_have_scope(self, raw_taxonomy: dict) -> None:
        """Every archive-context entry defines a scope field."""
        missing: list[str] = []
        for dim_data in raw_taxonomy["dimensions"].values():
            for entry in dim_data.get("entries", []):
                contexts = entry.get("contexts", [])
                if "archive" in contexts or "both" in contexts:
                    if "scope" not in entry:
                        missing.append(entry["name"])
        assert missing == [], f"Archive entries missing scope: {missing}"

    def test_scope_values_valid(self, raw_taxonomy: dict) -> None:
        """Every archive entry's scope is one of: entry, session, both."""
        invalid: list[tuple[str, str]] = []
        for dim_data in raw_taxonomy["dimensions"].values():
            for entry in dim_data.get("entries", []):
                contexts = entry.get("contexts", [])
                if "archive" in contexts or "both" in contexts:
                    scope = entry.get("scope")
                    if scope not in VALID_SCOPES:
                        invalid.append((entry["name"], str(scope)))
        assert invalid == [], f"Archive entries with invalid scope: {invalid}"


# =============================================================================
# 7. Validation API (backward compatibility)
# =============================================================================


class TestValidation:
    """Tests for the validate_labels() function."""

    def test_validate_labels_known(self) -> None:
        """Known labels are returned in the valid list."""
        valid, invalid = validate_labels(["bug:visual", "origin:agent", "ai-authored"])
        assert valid == ["bug:visual", "origin:agent", "ai-authored"]
        assert invalid == []

    def test_validate_labels_unknown(self) -> None:
        """Unknown labels are detected and returned in the invalid list."""
        valid, invalid = validate_labels(["bug:visual", "totally-fake", "nope:nope"])
        assert valid == ["bug:visual"]
        assert invalid == ["totally-fake", "nope:nope"]

    def test_validate_labels_empty(self) -> None:
        """Empty input produces empty output."""
        valid, invalid = validate_labels([])
        assert valid == []
        assert invalid == []

    def test_validate_labels_includes_archive_tags(self) -> None:
        """Archive-only tags are also valid in the full taxonomy."""
        valid, invalid = validate_labels(["phase:execution", "skill:task"])
        assert valid == ["phase:execution", "skill:task"]
        assert invalid == []


# =============================================================================
# 8. Dimension Lookup
# =============================================================================


class TestDimensionLookup:
    """Tests for get_dimension_for_label()."""

    def test_get_dimension_issue_labels(self) -> None:
        """Correct dimension returned for issue-context labels."""
        assert get_dimension_for_label("origin:user") == "origin"
        assert get_dimension_for_label("bug:visual") == "type"
        assert get_dimension_for_label("area:sbs:graph") == "area_sbs"
        assert get_dimension_for_label("area:devtools:cli") == "area_devtools"
        assert get_dimension_for_label("area:lean:dress") == "area_lean"
        assert get_dimension_for_label("loop:work") == "loop"
        assert get_dimension_for_label("impact:visual") == "impact"
        assert get_dimension_for_label("scope:single-repo") == "scope"
        assert get_dimension_for_label("pillar:user-effectiveness") == "pillar"
        assert get_dimension_for_label("project:sbs-test") == "project"
        assert get_dimension_for_label("friction:context-loss") == "friction"

    def test_get_dimension_archive_tags(self) -> None:
        """Correct dimension returned for archive-context tags."""
        assert get_dimension_for_label("phase:execution") == "phase"
        assert get_dimension_for_label("transition:handoff") == "transition"
        assert get_dimension_for_label("skill:task") == "skill"
        assert get_dimension_for_label("trigger:build") == "trigger"
        assert get_dimension_for_label("session:long") == "session"
        assert get_dimension_for_label("outcome:gate-pass") == "outcome"
        assert get_dimension_for_label("signal:retry-loop") == "signal"
        assert get_dimension_for_label("repo:dress") == "repo"
        assert get_dimension_for_label("epoch:opening") == "epoch"
        assert get_dimension_for_label("linkage:has-issue") == "linkage"
        assert get_dimension_for_label("token:efficient") == "token"
        assert get_dimension_for_label("thinking:heavy") == "thinking"
        assert get_dimension_for_label("tool:bash-dominant") == "tool"
        assert get_dimension_for_label("quality:high") == "quality"
        assert get_dimension_for_label("model:opus") == "model"
        assert get_dimension_for_label("improvement:process") == "improvement"

    def test_get_dimension_standalone(self) -> None:
        """Standalone labels return 'standalone'."""
        assert get_dimension_for_label("ai-authored") == "standalone"

    def test_get_dimension_unknown(self) -> None:
        """Unknown labels return None."""
        assert get_dimension_for_label("nonexistent:label") is None


# =============================================================================
# 9. Label Count Sanity
# =============================================================================


class TestLabelCount:
    """Sanity check on total label count."""

    def test_total_count(self) -> None:
        """Total entry count is between 230 and 260 (sanity check)."""
        all_labels = get_all_labels()
        count = len(all_labels)
        assert 230 <= count <= 260, (
            f"Expected 230-260 entries, got {count}. "
            f"Taxonomy may have drifted significantly."
        )


# =============================================================================
# 10. No empty descriptions
# =============================================================================


class TestDescriptions:
    """All entries and dimensions have non-empty descriptions."""

    def test_no_empty_entry_descriptions(self, raw_taxonomy: dict) -> None:
        """Every entry has a non-empty description string."""
        empty: list[str] = []
        for dim_data in raw_taxonomy["dimensions"].values():
            for entry in dim_data.get("entries", []):
                if not entry.get("description", "").strip():
                    empty.append(entry["name"])
        assert empty == [], f"Entries with empty descriptions: {empty}"

    def test_no_empty_dimension_descriptions(self, raw_taxonomy: dict) -> None:
        """Every dimension has a non-empty description."""
        empty: list[str] = []
        for dim_name, dim_data in raw_taxonomy["dimensions"].items():
            if not dim_data.get("description", "").strip():
                empty.append(dim_name)
        assert empty == [], f"Dimensions with empty descriptions: {empty}"


# =============================================================================
# 11. Archive taxonomy loader (tagger integration)
# =============================================================================


class TestTaggerLoader:
    """Tests for load_agent_state_taxonomy() from tagger module."""

    def test_loader_returns_flat_dict(self) -> None:
        """Loader returns a flat dict keyed by tag name."""
        flat = load_agent_state_taxonomy()
        assert isinstance(flat, dict)
        assert len(flat) > 0
        assert "phase:execution" in flat
        assert flat["phase:execution"]["dimension"] == "phase"

    def test_loader_caches(self) -> None:
        """Second call returns the same object (cached)."""
        first = load_agent_state_taxonomy()
        second = load_agent_state_taxonomy()
        assert first is second

    def test_loader_has_description_dimension_scope(self) -> None:
        """Every entry in the flat taxonomy has description, dimension, and scope."""
        flat = load_agent_state_taxonomy()
        for tag_name, info in flat.items():
            assert "description" in info, f"{tag_name} missing description"
            assert "dimension" in info, f"{tag_name} missing dimension"
            assert "scope" in info, f"{tag_name} missing scope"
            assert info["scope"] in VALID_SCOPES, (
                f"{tag_name} has invalid scope: {info['scope']}"
            )

    def test_loader_excludes_issue_only_entries(self) -> None:
        """Loader does not include issue-only entries."""
        flat = load_agent_state_taxonomy()
        # origin:user is issues-only, should not appear
        assert "origin:user" not in flat
        assert "bug:visual" not in flat

    def test_loader_includes_both_context_entries(self) -> None:
        """Loader includes entries with contexts=[both]."""
        flat = load_agent_state_taxonomy()
        assert "scope:cross-repo" in flat
        assert "scope:single-repo" in flat


# =============================================================================
# 12. Tag prefix matches dimension (archive tags)
# =============================================================================


class TestTagPrefixMatchesDimension:
    """Archive tag prefixes match their dimension key."""

    def test_tag_prefix_matches_dimension(self, raw_taxonomy: dict) -> None:
        """Tag prefix (before first colon) matches its dimension key for archive entries."""
        mismatched: list[tuple[str, str]] = []
        for dim_name, dim_data in raw_taxonomy["dimensions"].items():
            for entry in dim_data.get("entries", []):
                contexts = entry.get("contexts", [])
                if "archive" not in contexts and "both" not in contexts:
                    continue
                name = entry["name"]
                prefix = name.split(":")[0]
                if prefix != dim_name:
                    mismatched.append((name, dim_name))
        assert mismatched == [], f"Tag prefix != dimension: {mismatched}"


# =============================================================================
# 13. Context builder tests (from agent_state_taxonomy tests)
# =============================================================================


class TestContextStateMachine:
    """build_tagging_context() includes state machine fields."""

    def test_skill_field(self, minimal_entry: ArchiveEntry) -> None:
        ctx = build_tagging_context(minimal_entry)
        assert ctx["skill"] == "task"

    def test_substate_field(self, minimal_entry: ArchiveEntry) -> None:
        ctx = build_tagging_context(minimal_entry)
        assert ctx["substate"] == "execution"

    def test_state_transition_field(self, minimal_entry: ArchiveEntry) -> None:
        ctx = build_tagging_context(minimal_entry)
        assert ctx["state_transition"] == "phase_start"

    def test_has_epoch_summary(self, minimal_entry: ArchiveEntry) -> None:
        ctx = build_tagging_context(minimal_entry)
        assert ctx["has_epoch_summary"] is True

    def test_gate_passed(self, minimal_entry: ArchiveEntry) -> None:
        ctx = build_tagging_context(minimal_entry)
        assert ctx["gate_passed"] is True

    def test_null_global_state(self) -> None:
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
        ctx = build_tagging_context(minimal_entry)
        assert ctx["quality_overall"] == 0.85
        assert ctx["quality_delta"] == 0.02


class TestContextTokens:
    """build_tagging_context() includes token and model fields."""

    def test_token_counts(self, minimal_entry: ArchiveEntry) -> None:
        ctx = build_tagging_context(minimal_entry)
        assert ctx["total_input_tokens"] == 250000
        assert ctx["total_output_tokens"] == 30000
        assert ctx["total_tokens"] == 280000
        assert ctx["cache_read_tokens"] == 150000

    def test_thinking_block_count(self, minimal_entry: ArchiveEntry) -> None:
        ctx = build_tagging_context(minimal_entry)
        assert ctx["thinking_block_count"] == 5

    def test_unique_tools_count(self, minimal_entry: ArchiveEntry) -> None:
        ctx = build_tagging_context(minimal_entry)
        assert ctx["unique_tools_count"] == 5

    def test_model_versions(self, minimal_entry: ArchiveEntry) -> None:
        ctx = build_tagging_context(minimal_entry)
        assert ctx["model_versions"] == ["claude-opus-4-5-20251101"]

    def test_defaults_without_claude_data(self) -> None:
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


class TestSplitContextBuilders:
    """build_entry_context and build_session_context produce correct fields."""

    def test_entry_context_has_no_session_fields(self, minimal_entry: ArchiveEntry) -> None:
        ctx = build_entry_context(minimal_entry)
        for field in _SESSION_FIELDS:
            assert field not in ctx, (
                f"Entry context should not contain session field '{field}'"
            )

    def test_session_context_has_session_fields(self, minimal_entry: ArchiveEntry) -> None:
        ctx = build_session_context(minimal_entry)
        for field in _SESSION_FIELDS:
            assert field in ctx, (
                f"Session context missing expected field '{field}'"
            )

    def test_session_context_has_no_entry_only_fields(self, minimal_entry: ArchiveEntry) -> None:
        ctx = build_session_context(minimal_entry)
        entry_only = {"substate", "state_transition", "gate_passed",
                      "quality_overall", "quality_delta", "issue_refs", "pr_refs"}
        for field in entry_only:
            assert field not in ctx, (
                f"Session context should not contain entry field '{field}'"
            )

    def test_merged_context_has_all_fields(self, minimal_entry: ArchiveEntry) -> None:
        ctx = build_tagging_context(minimal_entry)
        for field in _ENTRY_FIELDS:
            assert field in ctx, f"Merged context missing entry field '{field}'"
        for field in _SESSION_FIELDS:
            assert field in ctx, f"Merged context missing session field '{field}'"


# =============================================================================
# 14. Every entry has a contexts field
# =============================================================================


class TestContextsField:
    """Every entry in the taxonomy has a contexts field."""

    def test_every_entry_has_contexts(self, raw_taxonomy: dict) -> None:
        """Every entry in dimensions defines a contexts field."""
        missing: list[str] = []
        for dim_data in raw_taxonomy["dimensions"].values():
            for entry in dim_data.get("entries", []):
                if "contexts" not in entry:
                    missing.append(entry["name"])
        assert missing == [], f"Entries missing contexts: {missing}"

    def test_every_standalone_has_contexts(self, raw_taxonomy: dict) -> None:
        """Every standalone entry defines a contexts field."""
        missing: list[str] = []
        for entry in raw_taxonomy.get("standalone", []):
            if "contexts" not in entry:
                missing.append(entry["name"])
        assert missing == [], f"Standalone entries missing contexts: {missing}"

    def test_contexts_values_valid(self, raw_taxonomy: dict) -> None:
        """Every contexts list contains only valid values."""
        valid_contexts = {"issues", "archive", "both"}
        invalid: list[tuple[str, list]] = []
        for dim_data in raw_taxonomy["dimensions"].values():
            for entry in dim_data.get("entries", []):
                contexts = entry.get("contexts", [])
                if not all(c in valid_contexts for c in contexts):
                    invalid.append((entry["name"], contexts))
        for entry in raw_taxonomy.get("standalone", []):
            contexts = entry.get("contexts", [])
            if not all(c in valid_contexts for c in contexts):
                invalid.append((entry["name"], contexts))
        assert invalid == [], f"Entries with invalid contexts: {invalid}"
