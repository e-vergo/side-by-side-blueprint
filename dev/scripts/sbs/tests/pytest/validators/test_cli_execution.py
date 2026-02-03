"""
Tests for the T1 CLI Execution validator.

Tests cover:
- Validator properties (name, category)
- Parsing pytest output for pass/fail counts
- Handling subprocess timeout
- Handling zero tests found
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbs.tests.validators.cli_execution import CLIExecutionValidator
from sbs.tests.validators.base import ValidationContext

from .base_test import ValidatorPropertiesTestMixin


# =============================================================================
# Validator Properties
# =============================================================================


@pytest.mark.evergreen
class TestCLIExecutionProperties(ValidatorPropertiesTestMixin):
    """Verify T1 validator name and category."""

    validator_name = "cli-execution"
    validator_category = "code"

    @pytest.fixture
    def validator(self) -> CLIExecutionValidator:
        return CLIExecutionValidator()


# =============================================================================
# Validation Behavior
# =============================================================================


@pytest.mark.evergreen
class TestCLIExecutionValidation:
    """Tests for CLI execution validation logic."""

    @pytest.fixture
    def validator(self) -> CLIExecutionValidator:
        return CLIExecutionValidator()

    @pytest.fixture
    def context(self) -> ValidationContext:
        return ValidationContext(
            project="test",
            project_root=Path("/tmp"),
            commit="abc123",
        )

    def test_validate_all_pass(
        self, validator: CLIExecutionValidator, context: ValidationContext
    ) -> None:
        """All tests passing yields a passing result with correct metrics."""
        mock_result = MagicMock()
        mock_result.stdout = "10 passed in 2.5s\n"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = validator.validate(context)

        assert result.passed is True
        assert result.metrics["tests_passed"] == 10
        assert result.metrics["tests_failed"] == 0
        assert result.metrics["tests_total"] == 10

    def test_validate_with_failures(
        self, validator: CLIExecutionValidator, context: ValidationContext
    ) -> None:
        """Failures in pytest output yield a failing result."""
        mock_result = MagicMock()
        mock_result.stdout = "2 failed, 8 passed in 3.0s\n"
        mock_result.stderr = ""
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            result = validator.validate(context)

        assert result.passed is False
        assert result.metrics["tests_passed"] == 8
        assert result.metrics["tests_failed"] == 2
        assert result.metrics["tests_total"] == 10

    def test_validate_timeout(
        self, validator: CLIExecutionValidator, context: ValidationContext
    ) -> None:
        """Subprocess timeout yields a failing result mentioning timeout."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="pytest", timeout=120),
        ):
            result = validator.validate(context)

        assert result.passed is False
        assert any("timed out" in f.lower() for f in result.findings)
        assert result.metrics["tests_passed"] == 0
        assert result.metrics["tests_failed"] == 0

    def test_validate_no_tests_found(
        self, validator: CLIExecutionValidator, context: ValidationContext
    ) -> None:
        """No tests found yields a failing result."""
        mock_result = MagicMock()
        mock_result.stdout = "no tests ran\n"
        mock_result.stderr = ""
        mock_result.returncode = 5

        with patch("subprocess.run", return_value=mock_result):
            result = validator.validate(context)

        assert result.passed is False
        assert result.metrics["tests_passed"] == 0
        assert result.metrics["tests_failed"] == 0
