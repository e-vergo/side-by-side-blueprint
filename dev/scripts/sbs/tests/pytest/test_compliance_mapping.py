"""
Tests for compliance mapping module.

Tests repo-to-page mapping and repo-to-validator mapping.
"""

from __future__ import annotations

import pytest

from sbs.tests.compliance.mapping import (
    REPO_PAGE_MAPPING,
    REPO_VALIDATOR_MAPPING,
    ALL_PAGES,
    get_affected_pages,
    get_validators_for_changes,
    detect_changed_repos,
    validate_mapping,
)


# =============================================================================
# Validator Mapping Tests
# =============================================================================


@pytest.mark.evergreen
class TestValidatorMapping:
    """Tests for change-based validator selection."""

    def test_dress_changes_trigger_visual_validators(self):
        """Dress repo changes should trigger T3, T5, T6."""
        validators = get_validators_for_changes(["Dress"])
        assert "T3" in validators
        assert "T5" in validators
        assert "T6" in validators

    def test_css_changes_trigger_color_validators(self):
        """dress-blueprint-action changes should trigger T5, T6, T7, T8."""
        validators = get_validators_for_changes(["dress-blueprint-action"])
        assert "T5" in validators
        assert "T6" in validators
        assert "T7" in validators
        assert "T8" in validators

    def test_runway_changes_trigger_all_visual(self):
        """Runway repo changes should trigger T3-T8."""
        validators = get_validators_for_changes(["Runway"])
        assert "T3" in validators
        assert "T4" in validators
        assert "T5" in validators
        assert "T6" in validators
        assert "T7" in validators
        assert "T8" in validators

    def test_lean_architect_triggers_status(self):
        """LeanArchitect changes should trigger T5 (status colors)."""
        validators = get_validators_for_changes(["LeanArchitect"])
        assert "T5" in validators
        assert len(validators) == 1

    def test_multiple_repos_union_validators(self):
        """Multiple repo changes should union their validators."""
        validators = get_validators_for_changes(["Dress", "LeanArchitect"])
        # Dress: T3, T5, T6 + LeanArchitect: T5 = T3, T5, T6
        assert "T3" in validators
        assert "T5" in validators
        assert "T6" in validators

    def test_unknown_repo_returns_empty(self):
        """Unknown repo should return empty list."""
        validators = get_validators_for_changes(["unknown-repo"])
        assert validators == []

    def test_empty_input_returns_empty(self):
        """Empty repo list should return empty validators."""
        validators = get_validators_for_changes([])
        assert validators == []

    def test_test_project_triggers_all(self):
        """Test project changes should trigger all validators T1-T8."""
        validators = get_validators_for_changes(["SBS-Test"])
        assert validators == ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"]

    def test_validators_sorted_numerically(self):
        """Validators should be sorted T1, T2, ..., T8."""
        validators = get_validators_for_changes(["SBS-Test"])
        expected_order = ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"]
        assert validators == expected_order

    def test_highlighting_repos_trigger_polish(self):
        """Highlighting repos should trigger T7, T8 (polish)."""
        for repo in ["subverso", "verso"]:
            validators = get_validators_for_changes([repo])
            assert "T7" in validators
            assert "T8" in validators


# =============================================================================
# Page Mapping Tests
# =============================================================================


@pytest.mark.evergreen
class TestPageMapping:
    """Tests for repo-to-page mapping."""

    def test_runway_affects_all_pages(self):
        """Runway changes should affect all pages."""
        pages = get_affected_pages(["Runway"])
        assert pages == ALL_PAGES

    def test_dress_affects_graph_and_chapter(self):
        """Dress changes should affect dep_graph and chapter."""
        pages = get_affected_pages(["Dress"])
        assert "dep_graph" in pages
        assert "chapter" in pages

    def test_verso_affects_verso_pages(self):
        """Verso changes should affect paper_verso and blueprint_verso."""
        pages = get_affected_pages(["verso"])
        assert "paper_verso" in pages
        assert "blueprint_verso" in pages

    def test_mapping_valid(self):
        """Mapping validation should pass."""
        assert validate_mapping() is True


# =============================================================================
# Change Detection Tests
# =============================================================================


@pytest.mark.evergreen
class TestChangeDetection:
    """Tests for repo change detection."""

    def test_detect_new_commit(self):
        """Detect changed repo when commit differs."""
        current = {"Dress": "abc123", "Runway": "def456"}
        previous = {"Dress": "abc123", "Runway": "old456"}

        changed = detect_changed_repos(current, previous)
        assert "Runway" in changed
        assert "Dress" not in changed

    def test_detect_new_repo(self):
        """Detect new repo not in previous commits."""
        current = {"Dress": "abc123", "NewRepo": "new123"}
        previous = {"Dress": "abc123"}

        changed = detect_changed_repos(current, previous)
        assert "NewRepo" in changed

    def test_no_changes(self):
        """No changes when all commits match."""
        current = {"Dress": "abc123", "Runway": "def456"}
        previous = {"Dress": "abc123", "Runway": "def456"}

        changed = detect_changed_repos(current, previous)
        assert changed == []


# =============================================================================
# Mapping Consistency Tests
# =============================================================================


@pytest.mark.evergreen
class TestMappingConsistency:
    """Tests for mapping consistency."""

    def test_all_validator_ids_valid(self):
        """All validator IDs should be T1-T8."""
        valid_ids = {f"T{i}" for i in range(1, 9)}

        for repo, validators in REPO_VALIDATOR_MAPPING.items():
            for v in validators:
                assert v in valid_ids, f"Invalid validator {v} for repo {repo}"

    def test_repo_validator_mapping_has_entries(self):
        """REPO_VALIDATOR_MAPPING should have entries."""
        assert len(REPO_VALIDATOR_MAPPING) > 0

    def test_key_repos_have_mappings(self):
        """Key repos should have validator mappings."""
        key_repos = ["Dress", "Runway", "LeanArchitect", "dress-blueprint-action"]
        for repo in key_repos:
            assert repo in REPO_VALIDATOR_MAPPING, f"Missing mapping for {repo}"
