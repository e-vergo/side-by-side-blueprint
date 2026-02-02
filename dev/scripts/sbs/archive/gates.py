"""Gate validation for archive state transitions.

Gates are defined in plan files and validated before allowing
transition from execution to finalization in the /task skill.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class GateDefinition:
    """Gate requirements parsed from a plan file."""
    tests: Optional[str] = None  # "all_pass" or threshold like ">=0.9"
    quality: dict[str, str] = field(default_factory=dict)  # {"T5": ">=0.8", "T6": ">=0.9"}
    regression: Optional[str] = None  # ">= 0"


@dataclass
class GateResult:
    """Result of gate evaluation."""
    passed: bool
    findings: list[str] = field(default_factory=list)


def parse_gates_from_plan(plan_content: str) -> Optional[GateDefinition]:
    """Extract gates section from plan markdown.

    Looks for a ```yaml block under ## Gates or gates: key.
    Returns None if no gates section found.
    """
    # Look for gates: YAML block in plan
    # Pattern: ```yaml followed by gates: section
    yaml_block_pattern = r'```yaml\s*\n(.*?)```'
    matches = re.findall(yaml_block_pattern, plan_content, re.DOTALL)

    for match in matches:
        try:
            # Preprocess: quote unquoted >= values to handle YAML edge case
            # This allows plan authors to write "T1: >= 1.0" without quotes
            preprocessed = re.sub(
                r':\s*(>=\s*[\d.]+)',  # Match ": >= 1.0" patterns
                r': "\1"',  # Quote them
                match
            )
            data = yaml.safe_load(preprocessed)
            if data and 'gates' in data:
                gates_data = data['gates']
                return GateDefinition(
                    tests=gates_data.get('tests'),
                    quality=gates_data.get('quality', {}),
                    regression=gates_data.get('regression'),
                )
        except yaml.YAMLError:
            continue

    return None


def find_active_plan() -> Optional[Path]:
    """Find the most recently modified plan file in ~/.claude/plans/."""
    plans_dir = Path.home() / ".claude" / "plans"
    if not plans_dir.exists():
        return None

    plan_files = list(plans_dir.glob("*.md"))
    if not plan_files:
        return None

    # Return most recently modified
    return max(plan_files, key=lambda p: p.stat().st_mtime)


def evaluate_test_gate(gate: GateDefinition) -> GateResult:
    """Run tests and check against gate threshold.

    Returns GateResult with pass/fail and findings.
    """
    if gate.tests is None:
        return GateResult(passed=True, findings=["No test gate defined"])

    # Run pytest via subprocess - use homebrew pytest directly
    scripts_dir = Path(__file__).parent.parent.parent
    pytest_path = "/opt/homebrew/bin/pytest"
    if not Path(pytest_path).exists():
        pytest_path = "pytest"  # Fall back to PATH

    result = subprocess.run(
        [pytest_path, "sbs/tests/pytest", "-q", "--tb=no"],
        cwd=scripts_dir,
        capture_output=True,
        text=True,
        timeout=300,
    )

    # Parse output for pass/fail counts
    output = result.stdout + result.stderr

    # Look for "X passed" pattern
    passed_match = re.search(r'(\d+) passed', output)
    failed_match = re.search(r'(\d+) failed', output)

    passed_count = int(passed_match.group(1)) if passed_match else 0
    failed_count = int(failed_match.group(1)) if failed_match else 0
    total = passed_count + failed_count

    if gate.tests == "all_pass":
        if failed_count > 0:
            return GateResult(
                passed=False,
                findings=[f"Test gate failed: {failed_count} tests failed (required: all_pass)"]
            )
        return GateResult(passed=True, findings=[f"Test gate passed: {passed_count} tests passed"])

    # Handle threshold like ">=0.9"
    if gate.tests.startswith(">="):
        threshold = float(gate.tests[2:])
        if total > 0:
            ratio = passed_count / total
            if ratio < threshold:
                return GateResult(
                    passed=False,
                    findings=[f"Test gate failed: {ratio:.1%} passed (required: {threshold:.0%})"]
                )
        return GateResult(passed=True, findings=[f"Test gate passed: {passed_count}/{total} tests"])

    return GateResult(passed=True, findings=["Unknown test gate format, allowing"])


def evaluate_quality_gate(gate: GateDefinition, project: str = "SBSTest") -> GateResult:
    """Run validators and check quality scores.

    Returns GateResult with pass/fail and findings.
    """
    if not gate.quality:
        return GateResult(passed=True, findings=["No quality gate defined"])

    # Run validators via subprocess - use homebrew python for sbs module
    scripts_dir = Path(__file__).parent.parent.parent
    python_path = "/opt/homebrew/bin/python3"
    if not Path(python_path).exists():
        python_path = "python3"  # Fall back to PATH

    result = subprocess.run(
        [python_path, "-m", "sbs", "validate-all", "--project", project],
        cwd=scripts_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )

    findings = []
    all_passed = True

    # Try to load quality ledger directly for more reliable score checking
    try:
        from sbs.tests.scoring import load_ledger as load_quality_ledger

        ledger = load_quality_ledger(project)

        for validator, threshold_str in gate.quality.items():
            # Normalize validator name (T5 -> t5-color-match, etc.)
            validator_lower = validator.lower()
            metric_id = None

            # Map short names to full metric IDs
            metric_map = {
                "t1": "t1-cli-execution",
                "t2": "t2-ledger-population",
                "t3": "t3-dashboard-clarity",
                "t4": "t4-toggle-discoverability",
                "t5": "t5-color-match",
                "t6": "t6-css-coverage",
                "t7": "t7-jarring",
                "t8": "t8-professional",
            }

            if validator_lower in metric_map:
                metric_id = metric_map[validator_lower]
            elif validator_lower.startswith("t") and "-" in validator_lower:
                metric_id = validator_lower

            if metric_id is None:
                findings.append(f"Unknown validator: {validator}")
                continue

            threshold = float(threshold_str.replace(">=", "").strip())
            score_data = ledger.scores.get(metric_id)

            if score_data is None:
                findings.append(f"Quality gate {validator} skipped: no score available")
                continue

            score = score_data.value

            if score < threshold:
                all_passed = False
                findings.append(f"Quality gate {validator} failed: {score:.2f} < {threshold}")
            else:
                findings.append(f"Quality gate {validator} passed: {score:.2f} >= {threshold}")

    except Exception as e:
        findings.append(f"Could not evaluate quality gates: {e}")
        # Don't fail on load errors - allow transition with warning

    return GateResult(passed=all_passed, findings=findings)


def check_gates(project: str = "SBSTest", force: bool = False) -> GateResult:
    """Run all gate checks for the active plan.

    Args:
        project: Project name for quality validation
        force: If True, return passed=True regardless of actual results

    Returns:
        Combined GateResult from all checks
    """
    if force:
        return GateResult(passed=True, findings=["Gates bypassed with --force flag"])

    # Find and parse active plan
    plan_path = find_active_plan()
    if not plan_path:
        return GateResult(passed=True, findings=["No active plan found, skipping gates"])

    plan_content = plan_path.read_text()
    gate = parse_gates_from_plan(plan_content)

    if gate is None:
        return GateResult(passed=True, findings=["No gates defined in plan, skipping validation"])

    # Collect all results
    all_findings = [f"Checking gates from: {plan_path.name}"]
    all_passed = True

    # Test gate
    test_result = evaluate_test_gate(gate)
    all_findings.extend(test_result.findings)
    if not test_result.passed:
        all_passed = False

    # Quality gate
    quality_result = evaluate_quality_gate(gate, project)
    all_findings.extend(quality_result.findings)
    if not quality_result.passed:
        all_passed = False

    return GateResult(passed=all_passed, findings=all_findings)
