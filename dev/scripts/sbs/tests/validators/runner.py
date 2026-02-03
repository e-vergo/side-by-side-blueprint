"""
Validator runner: central orchestration for running validators and updating ledger.

Maps between validator names (registry keys) and metric IDs (ledger keys),
runs validators with proper context, and persists results to the quality
score ledger.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from sbs.core.utils import get_sbs_root, get_git_commit, log
from sbs.tests.scoring import load_ledger, save_ledger, update_score, add_snapshot
from sbs.tests.scoring.reset import get_repo_commits
from sbs.tests.validators.base import ValidationContext, ValidatorResult
from sbs.tests.validators.registry import registry, discover_validators


# =============================================================================
# Mapping Tables
# =============================================================================

# Validator name (registry key) -> metric ID (ledger key)
VALIDATOR_TO_METRIC: dict[str, str] = {
    "cli-execution": "t1-cli-execution",
    "ledger-health": "t2-ledger-population",
    "dashboard-clarity": "t3-dashboard-clarity",
    "toggle-discoverability": "t4-toggle-discoverability",
    "status-color-match": "t5-color-match",
    "css-variable-coverage": "t6-css-coverage",
    "jarring-check": "t7-jarring",
    "professional-score": "t8-professional",
}

# Reverse: metric ID -> validator name
METRIC_TO_VALIDATOR: dict[str, str] = {v: k for k, v in VALIDATOR_TO_METRIC.items()}

# Heuristic metrics that require screenshots and AI vision analysis
HEURISTIC_METRICS: set[str] = {
    "t3-dashboard-clarity",
    "t4-toggle-discoverability",
    "t7-jarring",
    "t8-professional",
}

# Known project paths relative to monorepo root
_PROJECT_PATHS: dict[str, str] = {
    "SBSTest": "toolchain/SBS-Test",
    "GCR": "showcase/General_Crystallographic_Restriction",
    "PNT": "showcase/PrimeNumberTheoremAnd",
}


# =============================================================================
# Result Type
# =============================================================================


@dataclass
class RunnerResult:
    """Aggregated result from running a set of validators."""

    results: dict[str, ValidatorResult] = field(default_factory=dict)
    """Metric ID -> ValidatorResult for each validator that ran."""

    overall_passed: bool = True
    """True if all validators that ran passed."""

    ledger_updated: bool = False
    """Whether the quality score ledger was updated."""

    skipped: list[str] = field(default_factory=list)
    """Metric IDs that were skipped (heuristic, missing screenshots, etc.)."""

    errors: list[str] = field(default_factory=list)
    """Error messages from validators that raised exceptions."""


# =============================================================================
# Project Resolution
# =============================================================================


def resolve_project(project: Optional[str] = None) -> tuple[str, Path]:
    """Resolve a project name to (name, root_path).

    Args:
        project: Project name (SBSTest, GCR, PNT). Defaults to SBSTest.

    Returns:
        Tuple of (project_name, project_root_path).

    Raises:
        FileNotFoundError: If the resolved project directory doesn't exist.
    """
    if project is None:
        project = "SBSTest"

    sbs_root = get_sbs_root()
    rel_path = _PROJECT_PATHS.get(project)

    if rel_path is None:
        raise ValueError(
            f"Unknown project '{project}'. "
            f"Known projects: {', '.join(sorted(_PROJECT_PATHS.keys()))}"
        )

    project_root = sbs_root / rel_path
    if not project_root.exists():
        raise FileNotFoundError(f"Project directory not found: {project_root}")

    return project, project_root


# =============================================================================
# Context Building
# =============================================================================


def build_validation_context(
    project: str,
    project_root: Path,
) -> ValidationContext:
    """Build a ValidationContext for the given project.

    Populates commit hashes, screenshot directory, site directory,
    and other fields needed by validators.

    Args:
        project: Project name.
        project_root: Absolute path to the project directory.

    Returns:
        Fully populated ValidationContext.
    """
    sbs_root = get_sbs_root()

    # Git commit for the project
    commit = get_git_commit(project_root, short=True)

    # Repo commits for all toolchain repos
    repo_commits = get_repo_commits(project_root)

    # Screenshots directory
    screenshots_dir = sbs_root / "dev" / "storage" / project / "screenshots" / "latest"
    if not screenshots_dir.exists():
        screenshots_dir = None

    # Site directory
    site_dir = project_root / ".lake" / "build" / "runway"
    if not site_dir.exists():
        site_dir = None

    # Manifest path
    manifest_path = None
    if site_dir is not None:
        candidate = site_dir / "manifest.json"
        if candidate.exists():
            manifest_path = candidate

    return ValidationContext(
        project=project,
        project_root=project_root,
        commit=commit,
        screenshots_dir=screenshots_dir,
        site_dir=site_dir,
        manifest_path=manifest_path,
        repo_commits=repo_commits,
    )


# =============================================================================
# Score Extraction
# =============================================================================


def _extract_score_value(metric_id: str, result: ValidatorResult) -> float:
    """Extract a 0-100 score value from a ValidatorResult.

    Different validators report metrics differently:
    - T1 (cli-execution): binary pass/fail -> 100.0 or 0.0
    - T2 (ledger-health): population_rate as 0.0-1.0 -> multiply by 100
    - T5 (status-color-match): binary pass/fail -> 100.0 or 0.0
    - T6 (css-variable-coverage): coverage as 0.0-1.0 -> multiply by 100
    - Heuristic validators: binary pass/fail -> 100.0 or 0.0

    Args:
        metric_id: The metric identifier.
        result: The validator result.

    Returns:
        Score value in 0-100 range.
    """
    if metric_id == "t2-ledger-population":
        rate = result.metrics.get("population_rate", 0.0)
        return round(float(rate) * 100, 2)

    if metric_id == "t6-css-coverage":
        coverage = result.metrics.get("coverage", 0.0)
        return round(float(coverage) * 100, 2)

    # Default: binary scoring
    return 100.0 if result.passed else 0.0


# =============================================================================
# Runner
# =============================================================================


def run_validators(
    project: Optional[str] = None,
    project_root: Optional[Path] = None,
    metric_ids: Optional[list[str]] = None,
    update_ledger: bool = True,
    skip_heuristic: bool = False,
) -> RunnerResult:
    """Run validators and optionally update the quality score ledger.

    This is the main entry point for running validators programmatically.

    Args:
        project: Project name (SBSTest, GCR, PNT). Defaults to SBSTest.
        project_root: Override project root path. If None, resolved from project name.
        metric_ids: Specific metric IDs to run. If None, runs all.
        update_ledger: Whether to persist results to the quality score ledger.
        skip_heuristic: If True, skip heuristic validators (T3, T4, T7, T8).

    Returns:
        RunnerResult with per-metric results, overall status, and any errors.
    """
    runner_result = RunnerResult()

    # Discover all validators
    try:
        discover_validators()
    except Exception:
        pass  # Idempotent; duplicates raise ValueError which is fine

    # Resolve project
    if project_root is not None and project is None:
        # Infer project name from path
        project = project_root.name
    resolved_project, resolved_root = resolve_project(project)
    if project_root is not None:
        resolved_root = project_root

    # Build context
    context = build_validation_context(resolved_project, resolved_root)

    # Determine which validators to run
    if metric_ids is None:
        target_metrics = list(METRIC_TO_VALIDATOR.keys())
    else:
        target_metrics = list(metric_ids)

    # Check if screenshots are available for heuristic validators
    has_screenshots = (
        context.screenshots_dir is not None
        and context.screenshots_dir.exists()
        and any(context.screenshots_dir.glob("*.png"))
    )

    # Run each validator
    for metric_id in target_metrics:
        # Look up validator name
        validator_name = METRIC_TO_VALIDATOR.get(metric_id)
        if validator_name is None:
            runner_result.errors.append(
                f"No validator mapped for metric '{metric_id}'"
            )
            continue

        # Skip heuristic validators if requested
        if skip_heuristic and metric_id in HEURISTIC_METRICS:
            runner_result.skipped.append(metric_id)
            log.dim(f"Skipped {metric_id} (heuristic, --skip-heuristic)")
            continue

        # Skip heuristic validators if no screenshots available
        if metric_id in HEURISTIC_METRICS and not has_screenshots:
            runner_result.skipped.append(metric_id)
            log.dim(f"Skipped {metric_id} (no screenshots available)")
            continue

        # Get validator from registry
        validator = registry.get(validator_name)
        if validator is None:
            runner_result.skipped.append(metric_id)
            log.warning(f"Validator '{validator_name}' not found in registry, skipping {metric_id}")
            continue

        # Run the validator
        try:
            result = validator.validate(context)
            runner_result.results[metric_id] = result

            if not result.passed:
                runner_result.overall_passed = False

            status = "PASS" if result.passed else "FAIL"
            log.info(f"{metric_id}: {status}")

        except Exception as e:
            error_msg = f"{metric_id}: validator '{validator_name}' raised {type(e).__name__}: {e}"
            runner_result.errors.append(error_msg)
            runner_result.overall_passed = False
            log.error(error_msg)
            log.dim(traceback.format_exc())

    # Update ledger if requested
    if update_ledger and runner_result.results:
        try:
            ledger = load_ledger(resolved_project)
            repo_commits = context.repo_commits

            for metric_id, result in runner_result.results.items():
                value = _extract_score_value(metric_id, result)
                update_score(
                    ledger,
                    metric_id=metric_id,
                    value=value,
                    passed=result.passed,
                    findings=result.findings,
                    repo_commits=repo_commits,
                )

            add_snapshot(ledger)
            save_ledger(ledger, resolved_project)
            runner_result.ledger_updated = True
            log.success(f"Ledger updated for {resolved_project}")

        except Exception as e:
            error_msg = f"Failed to update ledger: {e}"
            runner_result.errors.append(error_msg)
            log.error(error_msg)

    return runner_result
