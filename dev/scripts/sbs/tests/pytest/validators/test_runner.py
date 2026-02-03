"""
Tests for the validator runner module.

Tests cover:
- Mapping table completeness and consistency
- Project resolution logic
- Running validators with mocked registry
- Heuristic skipping behavior
- Heuristic metric constants
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbs.tests.validators.runner import (
    HEURISTIC_METRICS,
    METRIC_TO_VALIDATOR,
    VALIDATOR_TO_METRIC,
    RunnerResult,
    resolve_project,
    run_validators,
)
from sbs.tests.validators.base import ValidationContext, ValidatorResult


# =============================================================================
# Mapping Table Tests
# =============================================================================


@pytest.mark.evergreen
class TestMappingTables:
    """Verify mapping tables between validators and metric IDs."""

    def test_mapping_completeness(self) -> None:
        """VALIDATOR_TO_METRIC has exactly 8 entries covering t1-t8."""
        assert len(VALIDATOR_TO_METRIC) == 8
        metric_ids = set(VALIDATOR_TO_METRIC.values())
        expected = {
            "t1-cli-execution",
            "t2-ledger-population",
            "t3-dashboard-clarity",
            "t4-toggle-discoverability",
            "t5-color-match",
            "t6-css-coverage",
            "t7-jarring",
            "t8-professional",
        }
        assert metric_ids == expected

    def test_reverse_mapping_consistency(self) -> None:
        """METRIC_TO_VALIDATOR is the exact inverse of VALIDATOR_TO_METRIC."""
        expected_reverse = {v: k for k, v in VALIDATOR_TO_METRIC.items()}
        assert METRIC_TO_VALIDATOR == expected_reverse


# =============================================================================
# Project Resolution Tests
# =============================================================================


@pytest.mark.evergreen
class TestResolveProject:
    """Verify project name to path resolution."""

    def test_resolve_project_explicit(self) -> None:
        """Resolving 'SBSTest' returns correct name and path."""
        name, path = resolve_project("SBSTest")
        assert name == "SBSTest"
        assert path.name == "SBS-Test"
        assert "toolchain" in str(path)

    def test_resolve_project_none_defaults(self) -> None:
        """Resolving None defaults to SBSTest."""
        name, path = resolve_project(None)
        assert name == "SBSTest"
        assert path.name == "SBS-Test"


# =============================================================================
# Runner Execution Tests
# =============================================================================


@pytest.mark.evergreen
class TestRunValidators:
    """Verify runner orchestration logic."""

    def test_run_validators_with_mocked_registry(self) -> None:
        """Runner executes a single mocked validator and returns its result."""
        # Create a fake validator
        fake_validator = MagicMock()
        fake_validator.name = "status-color-match"
        fake_validator.category = "visual"
        fake_validator.validate.return_value = ValidatorResult(
            validator="status-color-match",
            passed=True,
            findings=["All colors match"],
            metrics={"colors_matched": 6},
            confidence=1.0,
        )

        # Create a fake registry that returns our validator
        fake_registry = MagicMock()
        fake_registry.get.return_value = fake_validator

        with (
            patch("sbs.tests.validators.runner.discover_validators"),
            patch("sbs.tests.validators.runner.registry", fake_registry),
            patch("sbs.tests.validators.runner.load_ledger"),
            patch("sbs.tests.validators.runner.save_ledger"),
            patch("sbs.tests.validators.runner.update_score"),
            patch("sbs.tests.validators.runner.add_snapshot"),
        ):
            result = run_validators(
                "SBSTest",
                metric_ids=["t5-color-match"],
                update_ledger=False,
            )

        assert "t5-color-match" in result.results
        assert result.results["t5-color-match"].passed is True

    def test_skip_heuristic(self) -> None:
        """Heuristic metrics are skipped when skip_heuristic=True."""
        with (
            patch("sbs.tests.validators.runner.discover_validators"),
            patch("sbs.tests.validators.runner.registry") as mock_reg,
            patch("sbs.tests.validators.runner.load_ledger"),
            patch("sbs.tests.validators.runner.save_ledger"),
            patch("sbs.tests.validators.runner.update_score"),
            patch("sbs.tests.validators.runner.add_snapshot"),
        ):
            # Make registry return None for any get() call so non-heuristic
            # validators are skipped (not found), isolating the heuristic skip logic
            mock_reg.get.return_value = None

            result = run_validators(
                "SBSTest",
                skip_heuristic=True,
                update_ledger=False,
            )

        # All 4 heuristic metrics should be in skipped
        for metric_id in HEURISTIC_METRICS:
            assert metric_id in result.skipped


# =============================================================================
# Constants Tests
# =============================================================================


@pytest.mark.evergreen
class TestHeuristicConstants:
    """Verify heuristic metric constants."""

    def test_heuristic_metrics_constant(self) -> None:
        """HEURISTIC_METRICS contains exactly t3, t4, t7, t8."""
        expected = {
            "t3-dashboard-clarity",
            "t4-toggle-discoverability",
            "t7-jarring",
            "t8-professional",
        }
        assert HEURISTIC_METRICS == expected
