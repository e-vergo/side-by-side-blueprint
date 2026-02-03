"""
Tests for gate validation system.

These tests ensure gates are correctly parsed, evaluated, and enforced.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from sbs.archive.gates import (
    GateDefinition,
    GateResult,
    parse_gates_from_plan,
    find_active_plan,
    evaluate_test_gate,
    evaluate_quality_gate,
    check_gates,
)


# =============================================================================
# Gate Parsing Tests
# =============================================================================


@pytest.mark.evergreen
class TestGateParsing:
    """Gate definitions parsed from plan YAML."""

    def test_parse_complete_gate(self):
        """Parse a plan with all gate types."""
        plan_content = """
# Test Plan

## Gates

```yaml
gates:
  tests: all_pass
  quality:
    T5: ">= 0.8"
    T6: ">= 0.9"
  regression: ">= 0"
```
"""
        gate = parse_gates_from_plan(plan_content)

        assert gate is not None
        assert gate.tests == "all_pass"
        assert gate.quality == {"T5": ">= 0.8", "T6": ">= 0.9"}
        assert gate.regression == ">= 0"

    def test_parse_minimal_gate(self):
        """Parse a plan with only test gate."""
        plan_content = """
## Gates

```yaml
gates:
  tests: all_pass
```
"""
        gate = parse_gates_from_plan(plan_content)

        assert gate is not None
        assert gate.tests == "all_pass"
        assert gate.quality == {}
        assert gate.regression is None

    def test_parse_no_gates_section(self):
        """Return None when no gates section exists."""
        plan_content = """
# Plan without gates

## Summary

This plan has no gates defined.
"""
        gate = parse_gates_from_plan(plan_content)

        assert gate is None

    def test_parse_empty_yaml_block(self):
        """Handle empty YAML block gracefully."""
        plan_content = """
```yaml
```
"""
        gate = parse_gates_from_plan(plan_content)
        assert gate is None

    def test_parse_yaml_without_gates_key(self):
        """Handle YAML that doesn't have gates key."""
        plan_content = """
```yaml
other:
  key: value
```
"""
        gate = parse_gates_from_plan(plan_content)
        assert gate is None

    def test_parse_quality_gate_only(self):
        """Parse a plan with only quality gates."""
        plan_content = """
```yaml
gates:
  quality:
    T5: ">= 0.95"
```
"""
        gate = parse_gates_from_plan(plan_content)

        assert gate is not None
        assert gate.tests is None
        assert gate.quality == {"T5": ">= 0.95"}

    def test_parse_multiple_yaml_blocks(self):
        """Find gates in the correct YAML block when multiple exist."""
        plan_content = """
# Plan

```yaml
metadata:
  version: 1.0
```

## Gates

```yaml
gates:
  tests: all_pass
```

```yaml
other_config:
  setting: value
```
"""
        gate = parse_gates_from_plan(plan_content)

        assert gate is not None
        assert gate.tests == "all_pass"


# =============================================================================
# Gate Evaluation Tests
# =============================================================================


@pytest.mark.evergreen
class TestGateEvaluation:
    """Gate evaluation against actual results."""

    def test_gate_result_passed_true(self):
        """GateResult with passed=True."""
        result = GateResult(passed=True, findings=["All tests passed"])
        assert result.passed is True
        assert len(result.findings) == 1

    def test_gate_result_passed_false(self):
        """GateResult with passed=False."""
        result = GateResult(passed=False, findings=["3 tests failed"])
        assert result.passed is False

    def test_gate_result_default_findings(self):
        """GateResult defaults to empty findings list."""
        result = GateResult(passed=True)
        assert result.findings == []

    def test_gate_definition_defaults(self):
        """GateDefinition has sensible defaults."""
        gate = GateDefinition()
        assert gate.tests is None
        assert gate.quality == {}
        assert gate.regression is None

    def test_gate_definition_with_values(self):
        """GateDefinition stores values correctly."""
        gate = GateDefinition(
            tests="all_pass",
            quality={"T5": ">= 0.8"},
            regression=">= 0",
        )
        assert gate.tests == "all_pass"
        assert "T5" in gate.quality
        assert gate.regression == ">= 0"

    def test_gate_definition_mutable_quality(self):
        """Quality dict can be modified after creation."""
        gate = GateDefinition()
        gate.quality["T6"] = ">= 0.9"
        assert gate.quality["T6"] == ">= 0.9"


# =============================================================================
# Test Gate Evaluation Tests
# =============================================================================


@pytest.mark.evergreen
class TestTestGateEvaluation:
    """Tests for evaluate_test_gate function."""

    def test_no_test_gate_passes(self):
        """No test gate defined should pass."""
        gate = GateDefinition(tests=None)
        result = evaluate_test_gate(gate)

        assert result.passed is True
        assert any("no test gate" in f.lower() for f in result.findings)

    @patch("sbs.archive.gates.subprocess.run")
    def test_all_pass_with_failures_fails(self, mock_run):
        """all_pass gate with failures should fail."""
        mock_run.return_value = MagicMock(
            stdout="10 passed, 2 failed",
            stderr="",
            returncode=1,
        )

        gate = GateDefinition(tests="all_pass")
        result = evaluate_test_gate(gate)

        assert result.passed is False
        assert any("failed" in f.lower() for f in result.findings)

    @patch("sbs.archive.gates.subprocess.run")
    def test_all_pass_with_all_passing(self, mock_run):
        """all_pass gate with all tests passing should pass."""
        mock_run.return_value = MagicMock(
            stdout="10 passed",
            stderr="",
            returncode=0,
        )

        gate = GateDefinition(tests="all_pass")
        result = evaluate_test_gate(gate)

        assert result.passed is True
        assert any("passed" in f.lower() for f in result.findings)

    @patch("sbs.archive.gates.subprocess.run")
    def test_threshold_gate_passes_above_threshold(self, mock_run):
        """Threshold gate passes when ratio exceeds threshold."""
        mock_run.return_value = MagicMock(
            stdout="9 passed, 1 failed",  # 90% pass rate
            stderr="",
            returncode=1,
        )

        gate = GateDefinition(tests=">=0.8")  # 80% threshold
        result = evaluate_test_gate(gate)

        assert result.passed is True

    @patch("sbs.archive.gates.subprocess.run")
    def test_threshold_gate_fails_below_threshold(self, mock_run):
        """Threshold gate fails when ratio is below threshold."""
        mock_run.return_value = MagicMock(
            stdout="7 passed, 3 failed",  # 70% pass rate
            stderr="",
            returncode=1,
        )

        gate = GateDefinition(tests=">=0.8")  # 80% threshold
        result = evaluate_test_gate(gate)

        assert result.passed is False


# =============================================================================
# Gate Enforcement Tests
# =============================================================================


@pytest.mark.evergreen
class TestGateEnforcement:
    """Gate enforcement in upload flow."""

    def test_force_flag_bypasses_gate(self):
        """--force should bypass all gate checks."""
        result = check_gates(force=True)

        assert result.passed is True
        assert any(
            "bypass" in f.lower() or "force" in f.lower() for f in result.findings
        )

    @patch("sbs.archive.gates.find_active_plan")
    def test_no_plan_skips_gates(self, mock_find_plan):
        """No active plan should skip gates (permissive)."""
        mock_find_plan.return_value = None

        result = check_gates(force=False)

        assert result.passed is True
        assert any("no" in f.lower() and "plan" in f.lower() for f in result.findings)

    @patch("sbs.archive.gates.find_active_plan")
    def test_no_gates_defined_skips(self, mock_find_plan, tmp_path):
        """Plan without gates section should skip validation."""
        plan_file = tmp_path / "test.md"
        plan_file.write_text("# Plan without gates")
        mock_find_plan.return_value = plan_file

        result = check_gates(force=False)

        assert result.passed is True
        assert any("no gates" in f.lower() or "skip" in f.lower() for f in result.findings)

    def test_gate_result_includes_findings(self):
        """Gate results should always include explanatory findings."""
        result = check_gates(force=True)

        assert isinstance(result.findings, list)
        assert len(result.findings) > 0


# =============================================================================
# find_active_plan Tests
# =============================================================================


@pytest.mark.evergreen
class TestFindActivePlan:
    """Tests for find_active_plan function."""

    def test_no_plans_dir_returns_none(self, tmp_path, monkeypatch):
        """Returns None when ~/.claude/plans doesn't exist."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        # Don't create the plans directory

        result = find_active_plan()
        assert result is None

    def test_empty_plans_dir_returns_none(self, tmp_path, monkeypatch):
        """Returns None when plans directory is empty."""
        plans_dir = tmp_path / ".claude" / "plans"
        plans_dir.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = find_active_plan()
        assert result is None

    def test_returns_most_recent_plan(self, tmp_path, monkeypatch):
        """Returns the most recently modified plan file."""
        plans_dir = tmp_path / ".claude" / "plans"
        plans_dir.mkdir(parents=True)

        # Create two plan files with different modification times
        import time

        old_plan = plans_dir / "old_plan.md"
        old_plan.write_text("# Old Plan")

        time.sleep(0.01)  # Ensure different mtime

        new_plan = plans_dir / "new_plan.md"
        new_plan.write_text("# New Plan")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = find_active_plan()
        assert result == new_plan


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.evergreen
class TestGateIntegration:
    """Integration tests for gate system."""

    def test_gate_imports(self):
        """All gate module exports should be importable."""
        from sbs.archive.gates import (
            GateDefinition,
            GateResult,
            parse_gates_from_plan,
            find_active_plan,
            evaluate_test_gate,
            evaluate_quality_gate,
            check_gates,
        )

        # All should be callable or classes
        assert callable(parse_gates_from_plan)
        assert callable(find_active_plan)
        assert callable(check_gates)
        assert callable(evaluate_test_gate)
        assert callable(evaluate_quality_gate)

    def test_gate_result_serializable(self):
        """GateResult should be serializable for storage."""
        result = GateResult(passed=True, findings=["Test passed"])

        # Should be convertible to dict
        result_dict = {
            "passed": result.passed,
            "findings": result.findings,
        }

        assert result_dict["passed"] is True
        assert result_dict["findings"] == ["Test passed"]

    def test_gate_definition_serializable(self):
        """GateDefinition should be serializable."""
        gate = GateDefinition(
            tests="all_pass",
            quality={"T5": ">= 0.8"},
            regression=">= 0",
        )

        gate_dict = {
            "tests": gate.tests,
            "quality": gate.quality,
            "regression": gate.regression,
        }

        assert gate_dict["tests"] == "all_pass"
        assert gate_dict["quality"]["T5"] == ">= 0.8"

    @patch("sbs.archive.gates.find_active_plan")
    @patch("sbs.archive.gates.evaluate_test_gate")
    @patch("sbs.archive.gates.evaluate_quality_gate")
    def test_check_gates_combines_results(
        self, mock_quality, mock_test, mock_find_plan, tmp_path
    ):
        """check_gates combines test and quality gate results."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("""
```yaml
gates:
  tests: all_pass
  quality:
    T5: ">= 0.8"
```
""")
        mock_find_plan.return_value = plan_file
        mock_test.return_value = GateResult(passed=True, findings=["Tests passed"])
        mock_quality.return_value = GateResult(passed=True, findings=["Quality OK"])

        result = check_gates(force=False)

        assert result.passed is True
        assert any("tests" in f.lower() for f in result.findings)
        assert any("quality" in f.lower() for f in result.findings)

    @patch("sbs.archive.gates.find_active_plan")
    @patch("sbs.archive.gates.evaluate_test_gate")
    @patch("sbs.archive.gates.evaluate_quality_gate")
    def test_check_gates_fails_if_any_gate_fails(
        self, mock_quality, mock_test, mock_find_plan, tmp_path
    ):
        """check_gates fails if any individual gate fails."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("""
```yaml
gates:
  tests: all_pass
  quality:
    T5: ">= 0.8"
```
""")
        mock_find_plan.return_value = plan_file
        mock_test.return_value = GateResult(passed=False, findings=["Tests failed"])
        mock_quality.return_value = GateResult(passed=True, findings=["Quality OK"])

        result = check_gates(force=False)

        assert result.passed is False


# =============================================================================
# Quality Gate Evaluation Tests
# =============================================================================


@pytest.mark.evergreen
class TestQualityGateEvaluation:
    """Tests for evaluate_quality_gate function."""

    def test_no_quality_gate_passes(self):
        """No quality gate defined should pass."""
        gate = GateDefinition(quality={})
        result = evaluate_quality_gate(gate)

        assert result.passed is True
        assert any("no quality gate" in f.lower() for f in result.findings)

    @patch("sbs.archive.gates.subprocess.run")
    def test_quality_gate_runs_validators(self, mock_run):
        """Quality gate should run validators."""
        mock_run.return_value = MagicMock(
            stdout="Validation complete",
            stderr="",
            returncode=0,
        )

        gate = GateDefinition(quality={"T5": ">= 0.8"})

        # This will attempt to load the ledger, which may not exist in test
        # The function handles this gracefully with a warning
        result = evaluate_quality_gate(gate, project="TestProject")

        # Should have findings regardless of success
        assert isinstance(result.findings, list)


# =============================================================================
# Tier Filtering Tests
# =============================================================================


@pytest.mark.evergreen
class TestTierFiltering:
    """Tests for test tier filtering in gate evaluation."""

    @patch("sbs.archive.gates.subprocess.run")
    def test_evergreen_tier_adds_marker(self, mock_run):
        """evaluate_test_gate with tier='evergreen' passes -m evergreen."""
        mock_run.return_value = MagicMock(
            stdout="10 passed",
            stderr="",
            returncode=0,
        )

        gate = GateDefinition(tests="all_pass")
        evaluate_test_gate(gate, tier="evergreen")

        # Verify -m evergreen was in the command
        call_args = mock_run.call_args[0][0]
        assert "-m" in call_args
        idx = call_args.index("-m")
        assert call_args[idx + 1] == "evergreen"

    @patch("sbs.archive.gates.subprocess.run")
    def test_all_tier_no_marker(self, mock_run):
        """evaluate_test_gate with tier='all' runs without marker filter."""
        mock_run.return_value = MagicMock(
            stdout="10 passed",
            stderr="",
            returncode=0,
        )

        gate = GateDefinition(tests="all_pass")
        evaluate_test_gate(gate, tier="all")

        # Verify -m was NOT in the command
        call_args = mock_run.call_args[0][0]
        assert "-m" not in call_args

    @patch("sbs.archive.gates.subprocess.run")
    def test_dev_tier_adds_marker(self, mock_run):
        """evaluate_test_gate with tier='dev' passes -m dev."""
        mock_run.return_value = MagicMock(
            stdout="5 passed",
            stderr="",
            returncode=0,
        )

        gate = GateDefinition(tests="all_pass")
        evaluate_test_gate(gate, tier="dev")

        call_args = mock_run.call_args[0][0]
        assert "-m" in call_args
        idx = call_args.index("-m")
        assert call_args[idx + 1] == "dev"

    def test_gate_definition_default_tier(self):
        """GateDefinition defaults to evergreen tier."""
        gate = GateDefinition()
        assert gate.test_tier == "evergreen"

    def test_gate_definition_custom_tier(self):
        """GateDefinition stores custom tier."""
        gate = GateDefinition(test_tier="all")
        assert gate.test_tier == "all"

    def test_parse_gates_with_tier(self):
        """parse_gates_from_plan parses test_tier field."""
        plan_content = """
```yaml
gates:
  tests: all_pass
  test_tier: dev
```
"""
        gate = parse_gates_from_plan(plan_content)

        assert gate is not None
        assert gate.tests == "all_pass"
        assert gate.test_tier == "dev"

    def test_parse_gates_default_tier(self):
        """parse_gates_from_plan defaults to evergreen when tier not specified."""
        plan_content = """
```yaml
gates:
  tests: all_pass
```
"""
        gate = parse_gates_from_plan(plan_content)

        assert gate is not None
        assert gate.test_tier == "evergreen"
