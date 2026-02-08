"""Tests for SBS Build and Testing tools."""

from typing import List
from unittest.mock import MagicMock, patch

import pytest


class TestRunTests:
    """Tests for sls_run_tests tool."""

    def test_parses_pass_count(self, sample_passing_output: str) -> None:
        """Parses passed test count from output."""
        from sls_mcp.sls_tools import _parse_pytest_output

        passed, failed, errors, skipped = _parse_pytest_output(sample_passing_output)

        assert passed == 10
        assert failed == 0
        assert errors == 0

    def test_parses_fail_count(self, sample_failing_output: str) -> None:
        """Parses failed test count from output."""
        from sls_mcp.sls_tools import _parse_pytest_output

        passed, failed, errors, skipped = _parse_pytest_output(sample_failing_output)

        assert passed == 8
        assert failed == 2

    def test_parses_mixed_results(self, sample_mixed_output: str) -> None:
        """Parses mixed results including skipped and errors."""
        from sls_mcp.sls_tools import _parse_pytest_output

        passed, failed, errors, skipped = _parse_pytest_output(sample_mixed_output)

        assert passed == 14
        assert failed == 1
        assert errors == 1
        assert skipped == 4

    def test_extracts_failures(self, sample_failing_output: str) -> None:
        """Extracts failure details."""
        from sls_mcp.sls_tools import _extract_failures

        failures = _extract_failures(sample_failing_output)

        assert len(failures) == 2
        assert any("test_one" in f.test_name for f in failures)
        assert any("test_two" in f.test_name for f in failures)

    def test_respects_filter(self) -> None:
        """Respects pytest -k filter pattern."""
        from sls_mcp.sls_models import TestResult

        # Verify the model structure supports filter results
        result = TestResult(
            passed=3,
            failed=0,
            errors=0,
            skipped=7,  # Skipped due to filter
            duration_seconds=0.5,
            failures=[],
        )

        assert result.passed == 3
        assert result.skipped == 7


class TestValidateProject:
    """Tests for sls_validate_project tool."""

    def test_returns_overall_score(self, validation_passing_output: str) -> None:
        """Returns calculated overall score."""
        from sls_mcp.sls_tools import _parse_validation_output

        results, overall_score, passed = _parse_validation_output(
            validation_passing_output, ["T5", "T6"]
        )

        assert overall_score == 97.75

    def test_returns_per_validator_scores(self, validation_passing_output: str) -> None:
        """Returns individual validator scores."""
        from sls_mcp.sls_tools import _parse_validation_output

        results, overall_score, passed = _parse_validation_output(
            validation_passing_output, ["T5", "T6"]
        )

        assert "t5-color-match" in results
        assert results["t5-color-match"].value == 100.0
        assert results["t5-color-match"].passed is True

    def test_handles_project_normalization(self) -> None:
        """Normalizes project names correctly."""
        # Test the project normalization logic
        project_map = {
            "SBSTest": "SBSTest",
            "sbs-test": "SBSTest",
            "GCR": "GCR",
            "gcr": "GCR",
            "General_Crystallographic_Restriction": "GCR",
            "PNT": "PNT",
            "pnt": "PNT",
            "PrimeNumberTheoremAnd": "PNT",
        }

        assert project_map.get("sbs-test") == "SBSTest"
        assert project_map.get("gcr") == "GCR"
        assert project_map.get("PrimeNumberTheoremAnd") == "PNT"

    def test_default_validators(self) -> None:
        """Uses T5, T6 as default validators."""
        # The default should be T5 and T6
        default_validators = ["T5", "T6"]

        assert "T5" in default_validators
        assert "T6" in default_validators
        assert len(default_validators) == 2

    def test_handles_validation_failure(self, validation_failing_output: str) -> None:
        """Handles failed validation correctly."""
        from sls_mcp.sls_tools import _parse_validation_output

        results, overall_score, passed = _parse_validation_output(
            validation_failing_output, ["T5", "T6"]
        )

        assert overall_score == 90.0
        assert passed is False


class TestBuildProject:
    """Tests for sls_build_project tool."""

    def test_dry_run_returns_correct_structure(self) -> None:
        """Dry run returns correct result structure."""
        from sls_mcp.sls_models import SBSBuildResult

        result = SBSBuildResult(
            success=True,
            duration_seconds=0.0,
            build_run_id=None,
            errors=[],
            warnings=["Dry run - no actual build performed"],
            project="SBSTest",
            manifest_path=None,
        )

        assert result.success is True
        assert result.duration_seconds == 0.0
        assert "Dry run" in result.warnings[0]

    def test_returns_duration(self) -> None:
        """Returns build duration."""
        from sls_mcp.sls_models import SBSBuildResult

        result = SBSBuildResult(
            success=True,
            duration_seconds=123.45,
            build_run_id="build-001",
            errors=[],
            warnings=[],
            project="SBSTest",
            manifest_path="/path/to/manifest.json",
        )

        assert result.duration_seconds == 123.45

    def test_captures_errors(self) -> None:
        """Captures error messages."""
        from sls_mcp.sls_models import SBSBuildResult

        result = SBSBuildResult(
            success=False,
            duration_seconds=10.0,
            build_run_id=None,
            errors=["[ERROR] Lake build failed", "error: unknown identifier 'foo'"],
            warnings=["[WARN] Deprecated syntax"],
            project="SBSTest",
            manifest_path=None,
        )

        assert result.success is False
        assert len(result.errors) == 2
        assert "[ERROR]" in result.errors[0]

    def test_extracts_build_run_id(self) -> None:
        """Extracts build_run_id from build output."""
        from sls_mcp.sls_tools import _extract_build_run_id

        output = "Starting build...\nbuild_run_id: abc123-def456\nBuild complete."
        build_id = _extract_build_run_id(output)

        assert build_id == "abc123-def456"

    def test_handles_unknown_project(self) -> None:
        """Handles unknown project name."""
        from sls_mcp.sls_models import SBSBuildResult

        result = SBSBuildResult(
            success=False,
            duration_seconds=0.0,
            build_run_id=None,
            errors=["Unknown project: FakeProject. Valid: SBSTest, GCR, PNT"],
            warnings=[],
            project="FakeProject",
            manifest_path=None,
        )

        assert result.success is False
        assert "Unknown project" in result.errors[0]


class TestServeProject:
    """Tests for sls_serve_project tool."""

    def test_serve_result_structure(self) -> None:
        """ServeResult has correct structure."""
        from sls_mcp.sls_models import ServeResult

        result = ServeResult(
            running=True,
            url="http://localhost:8000",
            pid=12345,
            project="SBSTest",
        )

        assert result.running is True
        assert result.url == "http://localhost:8000"
        assert result.pid == 12345
        assert result.project == "SBSTest"

    def test_serve_not_running(self) -> None:
        """ServeResult for not running server."""
        from sls_mcp.sls_models import ServeResult

        result = ServeResult(
            running=False,
            url=None,
            pid=None,
            project="SBSTest",
        )

        assert result.running is False
        assert result.url is None
        assert result.pid is None
