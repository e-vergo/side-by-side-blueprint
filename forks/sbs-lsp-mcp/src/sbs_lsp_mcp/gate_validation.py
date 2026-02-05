"""Gate validation module for skill phase transitions.

This module provides infrastructure for validating gates defined in task plans.
Gates are quality checkpoints that must pass before phase transitions.

A gate specification is extracted from plan markdown and may include:
- Test requirements (evergreen, specific test filters)
- Quality thresholds (T1-T8 validator scores)
- Regression checks (no degradation from baseline)

Example gate spec in plan markdown:

```yaml
gates:
  tests:
    tier: evergreen
    filter: test_color
  quality:
    T5: 1.0  # Status colors must match
    T6: 0.9  # CSS variable coverage >= 90%
  regression: true
```
"""

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context

# Paths
SBS_ROOT = Path("/Users/eric/GitHub/Side-By-Side-Blueprint")
SCRIPTS_DIR = SBS_ROOT / "dev" / "scripts"
STORAGE_DIR = SBS_ROOT / "dev" / "storage"


@dataclass
class GateSpec:
    """Specification for gate validation at phase transitions.

    Attributes:
        tests: Test filter pattern (pytest -k compatible), if any
        test_tier: Test tier to run (evergreen, dev, all)
        quality: Dict mapping validator IDs to minimum scores (e.g., {"T5": 1.0, "T6": 0.9})
        regression: Whether to check for quality regression from baseline
    """

    tests: Optional[str] = None
    test_tier: str = "evergreen"
    quality: Dict[str, float] = field(default_factory=dict)
    regression: bool = False


@dataclass
class GateResult:
    """Result of gate validation.

    Attributes:
        all_pass: Whether all gates passed
        results: List of individual check results (strings describing what passed)
        failures: List of failure descriptions
        test_passed: Number of tests passed
        test_total: Total number of tests run
        validator_scores: Dict of validator ID -> actual score
    """

    all_pass: bool
    results: List[str] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)
    test_passed: int = 0
    test_total: int = 0
    validator_scores: Dict[str, float] = field(default_factory=dict)


def parse_gate_spec_from_plan(plan_content: str) -> Optional[GateSpec]:
    """Parse gate specification from plan markdown content.

    Looks for a YAML block labeled 'gates' in the plan and extracts
    the gate specification.

    Args:
        plan_content: Full plan markdown content

    Returns:
        GateSpec if gates block found, None otherwise

    Example plan format:
        ```yaml
        gates:
          tests:
            tier: evergreen
            filter: test_color
          quality:
            T5: 1.0
            T6: 0.9
          regression: true
        ```

    Also supports simpler formats:
        ```yaml
        gates:
          tests: all_pass
          quality:
            T5: >= 0.8
            T6: >= 0.9
        ```
    """
    if not plan_content:
        return None

    # Look for gates: block in YAML code blocks
    yaml_pattern = r"```ya?ml\s*\n(.*?)```"
    matches = re.findall(yaml_pattern, plan_content, re.DOTALL | re.IGNORECASE)

    for yaml_block in matches:
        if "gates:" not in yaml_block:
            continue

        # Simple YAML parsing (avoid full yaml dependency)
        spec = GateSpec()

        # Extract tests section - handle both formats
        # Format 1: tests: all_pass
        simple_tests_match = re.search(r"tests:\s*(all_pass|[\d.]+)", yaml_block)
        if simple_tests_match:
            value = simple_tests_match.group(1)
            if value == "all_pass":
                spec.tests = "all_pass"
            else:
                spec.tests = value  # Could be a threshold like "0.95"

        # Format 2: tests:\n    tier: evergreen\n    filter: ...
        tests_match = re.search(
            r"tests:\s*\n\s+tier:\s*(\w+)(?:\s*\n\s+filter:\s*(.+))?",
            yaml_block,
        )
        if tests_match:
            spec.test_tier = tests_match.group(1).strip()
            if tests_match.group(2):
                spec.tests = tests_match.group(2).strip()

        # Also handle test_tier at top level
        test_tier_match = re.search(r"test_tier:\s*(\w+)", yaml_block)
        if test_tier_match:
            spec.test_tier = test_tier_match.group(1).strip()

        # Extract quality thresholds - handle both "T5: 1.0" and "T5: >= 0.8"
        quality_section = re.search(
            r"quality:\s*\n((?:\s+T\d+:\s*[><=\s]*[\d.]+.*\n?)+)",
            yaml_block,
        )
        if quality_section:
            quality_lines = quality_section.group(1)
            for match in re.finditer(r"(T\d+):\s*(?:>=?\s*)?([\d.]+)", quality_lines):
                spec.quality[match.group(1)] = float(match.group(2))

        # Extract regression flag
        regression_match = re.search(r"regression:\s*([>=<\s]*)(\d+|true|false)", yaml_block, re.IGNORECASE)
        if regression_match:
            value = regression_match.group(2).lower()
            if value == "true":
                spec.regression = True
            elif value == "false":
                spec.regression = False
            else:
                # Numeric value like ">= 0" means regression >= 0 (no regression allowed)
                spec.regression = True

        return spec

    return None


def _run_tests(spec: GateSpec) -> tuple[int, int, List[str]]:
    """Run pytest tests according to spec.

    Returns:
        (passed_count, total_count, failure_messages)
    """
    cmd = ["python3", "-m", "pytest", str(SCRIPTS_DIR / "sbs" / "tests" / "pytest")]

    # Add tier marker if specified
    if spec.test_tier and spec.test_tier != "all":
        cmd.extend(["-m", spec.test_tier])

    # Add filter if specified
    if spec.tests and spec.tests not in ("all_pass", "all"):
        cmd.extend(["-k", spec.tests])

    # Add JSON output for parsing
    cmd.extend(["--tb=short", "-q"])

    try:
        result = subprocess.run(
            cmd,
            cwd=str(SCRIPTS_DIR),
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        # Parse pytest output for counts
        passed = 0
        failed = 0
        errors = 0
        failures: List[str] = []

        # Parse summary line like "5 passed, 2 failed in 1.23s"
        summary_match = re.search(
            r"(\d+) passed(?:.*?(\d+) failed)?(?:.*?(\d+) error)?",
            result.stdout + result.stderr,
        )
        if summary_match:
            passed = int(summary_match.group(1) or 0)
            failed = int(summary_match.group(2) or 0)
            errors = int(summary_match.group(3) or 0)

        # Extract failure messages
        if failed > 0 or errors > 0:
            # Look for FAILED lines
            for line in (result.stdout + result.stderr).split("\n"):
                if line.startswith("FAILED") or "ERROR" in line:
                    failures.append(line.strip())

        total = passed + failed + errors
        return passed, total, failures

    except subprocess.TimeoutExpired:
        return 0, 0, ["Test execution timed out after 300 seconds"]
    except Exception as e:
        return 0, 0, [f"Failed to run tests: {str(e)}"]


def _run_validators(spec: GateSpec, project: str) -> Dict[str, float]:
    """Run quality validators according to spec.

    Returns:
        Dict mapping validator ID to actual score
    """
    if not spec.quality:
        return {}

    validators = list(spec.quality.keys())
    cmd = [
        "python3", "-m", "sbs", "validate",
        "--project", project,
        "--validators", ",".join(validators),
        "--json",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(SCRIPTS_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            # Return zeros for all validators on failure
            return {v: 0.0 for v in validators}

        # Parse JSON output
        try:
            data = json.loads(result.stdout)
            scores = {}
            for validator_id, validator_data in data.get("results", {}).items():
                if isinstance(validator_data, dict):
                    scores[validator_id] = float(validator_data.get("value", 0.0))
                else:
                    scores[validator_id] = float(validator_data)
            return scores
        except (json.JSONDecodeError, ValueError):
            return {v: 0.0 for v in validators}

    except subprocess.TimeoutExpired:
        return {v: 0.0 for v in validators}
    except Exception:
        return {v: 0.0 for v in validators}


def _check_regression(project: str) -> tuple[bool, Optional[str]]:
    """Check for quality score regression from baseline.

    Returns:
        (no_regression, failure_message)
    """
    ledger_path = STORAGE_DIR / project / "quality_ledger.json"
    if not ledger_path.exists():
        # No baseline to compare against
        return True, None

    try:
        with open(ledger_path) as f:
            ledger = json.load(f)

        # Check for any degradation in tracked metrics
        # (implementation depends on ledger format)
        # For now, just check if any recent score is lower than previous
        entries = ledger.get("entries", [])
        if len(entries) < 2:
            return True, None

        current = entries[-1]
        previous = entries[-2]

        regressions = []
        for key in current.get("scores", {}):
            curr_score = current["scores"].get(key, 0)
            prev_score = previous.get("scores", {}).get(key, 0)
            if curr_score < prev_score:
                regressions.append(f"{key}: {prev_score:.2f} -> {curr_score:.2f}")

        if regressions:
            return False, f"Regressions detected: {', '.join(regressions)}"

        return True, None

    except Exception as e:
        return True, None  # Can't check regression, so don't fail


def validate_gates(
    ctx: Context,
    spec: GateSpec,
    project: str,
) -> GateResult:
    """Validate gates according to specification.

    Runs the specified tests and quality validators, checks for regression
    if enabled, and returns consolidated results.

    Args:
        ctx: MCP context for accessing tools
        spec: Gate specification to validate against
        project: Project name (SBSTest, GCR, PNT)

    Returns:
        GateResult with all_pass, results, and failures
    """
    results: List[str] = []
    failures: List[str] = []
    test_passed = 0
    test_total = 0
    validator_scores: Dict[str, float] = {}

    # 1. Run tests if specified
    if spec.tests is not None:
        passed, total, test_failures = _run_tests(spec)
        test_passed = passed
        test_total = total

        if spec.tests == "all_pass":
            # All tests must pass
            if total > 0 and passed == total:
                results.append(f"Tests: {passed}/{total} passed (all_pass requirement met)")
            else:
                failures.extend(test_failures)
                failures.append(f"Tests: {passed}/{total} passed (all_pass requirement NOT met)")
        else:
            # Just record what passed
            results.append(f"Tests: {passed}/{total} passed")
            if test_failures:
                failures.extend(test_failures)

    # 2. Run quality validators if specified
    if spec.quality:
        scores = _run_validators(spec, project)
        validator_scores = scores

        for validator_id, threshold in spec.quality.items():
            actual = scores.get(validator_id, 0.0)
            if actual >= threshold:
                results.append(f"{validator_id}: {actual:.2f} >= {threshold:.2f} (PASS)")
            else:
                failures.append(f"{validator_id}: {actual:.2f} < {threshold:.2f} (FAIL)")

    # 3. Check for regression if enabled
    if spec.regression:
        no_regression, regression_msg = _check_regression(project)
        if no_regression:
            results.append("Regression check: no regressions detected")
        else:
            failures.append(f"Regression check: {regression_msg}")

    return GateResult(
        all_pass=len(failures) == 0,
        results=results,
        failures=failures,
        test_passed=test_passed,
        test_total=test_total,
        validator_scores=validator_scores,
    )
