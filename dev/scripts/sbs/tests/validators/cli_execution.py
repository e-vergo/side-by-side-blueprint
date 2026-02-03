"""
CLI execution validator (T1).

Runs the evergreen pytest suite and reports pass/fail.
Binary validator: 100.0 if all tests pass, 0.0 otherwise.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from .base import BaseValidator, ValidationContext, ValidatorResult
from .registry import register_validator


def _parse_pytest_summary(output: str) -> tuple[int, int]:
    """Parse pytest output for pass/fail counts.

    Looks for summary lines like:
    - "5 passed"
    - "2 failed, 3 passed"
    - "1 failed, 4 passed, 1 warning"
    - "no tests ran"

    Args:
        output: Combined stdout/stderr from pytest.

    Returns:
        Tuple of (passed_count, failed_count).
    """
    passed = 0
    failed = 0

    # Match "N passed" anywhere in output
    passed_match = re.search(r"(\d+)\s+passed", output)
    if passed_match:
        passed = int(passed_match.group(1))

    # Match "N failed" anywhere in output
    failed_match = re.search(r"(\d+)\s+failed", output)
    if failed_match:
        failed = int(failed_match.group(1))

    return passed, failed


@register_validator
class CLIExecutionValidator(BaseValidator):
    """Validates that the evergreen pytest suite passes.

    This is a deterministic binary validator (T1 in the test suite).
    It runs `pytest sbs/tests/pytest -m evergreen -q --tb=no` and
    reports whether all tests pass.

    Metrics returned:
        tests_passed: int - Number of tests that passed
        tests_failed: int - Number of tests that failed
        tests_total: int - Total tests run
    """

    def __init__(self) -> None:
        super().__init__("cli-execution", "code")

    def validate(self, context: ValidationContext) -> ValidatorResult:
        """Run evergreen pytest suite and report results.

        Args:
            context: Validation context (project info used for logging only).

        Returns:
            ValidatorResult with pass/fail and test count metrics.
        """
        # dev/scripts directory is where pytest should run from
        scripts_dir = Path(__file__).resolve().parent.parent.parent

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m", "pytest",
                    "sbs/tests/pytest",
                    "-m", "evergreen",
                    "-q",
                    "--tb=no",
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=scripts_dir,
            )
        except subprocess.TimeoutExpired:
            return self._make_fail(
                findings=["Pytest timed out after 120 seconds"],
                metrics={"tests_passed": 0, "tests_failed": 0, "tests_total": 0},
                confidence=1.0,
            )
        except FileNotFoundError as e:
            return self._make_fail(
                findings=[f"Failed to run pytest: {e}"],
                metrics={"tests_passed": 0, "tests_failed": 0, "tests_total": 0},
                confidence=1.0,
            )

        # Combine stdout and stderr for parsing
        combined_output = f"{result.stdout}\n{result.stderr}"

        passed, failed = _parse_pytest_summary(combined_output)
        total = passed + failed

        # Build findings
        findings: list[str] = []
        all_passed = failed == 0 and passed > 0

        if all_passed:
            findings.append(f"All {passed} evergreen tests passed")
        elif passed == 0 and failed == 0:
            findings.append("No evergreen tests found or ran")
            all_passed = False
        else:
            findings.append(f"{failed} test(s) failed out of {total}")
            # Include last few lines of output for failure context
            output_lines = combined_output.strip().splitlines()
            # Grab up to 5 lines before the summary for failure hints
            for line in output_lines[-10:]:
                line = line.strip()
                if line and "passed" not in line and "failed" not in line:
                    findings.append(f"  {line}")

        return self._make_result(
            passed=all_passed,
            findings=findings,
            metrics={
                "tests_passed": passed,
                "tests_failed": failed,
                "tests_total": total,
            },
            confidence=1.0,
        )
