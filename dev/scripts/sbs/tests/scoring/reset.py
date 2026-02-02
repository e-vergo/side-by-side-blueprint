"""
Intelligent score invalidation based on repo changes.

Determines which quality metrics need re-evaluation when repos change.
Mirrors the pattern from compliance/mapping.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from sbs.core.utils import (
    get_sbs_root,
    get_git_commit,
    get_repos,
    log,
)

from .ledger import QualityScoreLedger


# =============================================================================
# Repo-to-Score Mapping
# =============================================================================

# Maps repo names to the quality metrics they affect
REPO_SCORE_MAPPING: dict[str, list[str]] = {
    # Color definitions in Svg.lean (source of truth for status colors)
    "Dress": ["t5-color-match"],

    # CSS/JS assets affect visual tests
    "dress-blueprint-action": [
        "t5-color-match",      # CSS variables for colors
        "t6-css-coverage",     # CSS variable coverage
        "t7-jarring",          # Visual jarring check
        "t8-professional",     # Professional polish
    ],

    # Dashboard templates and site generation
    "Runway": [
        "t3-dashboard-clarity",      # Dashboard layout
        "t4-toggle-discoverability", # Toggle visibility
    ],

    # Highlighting affects code display
    "subverso": [
        "t7-jarring",         # Code highlighting can cause jarring
        "t8-professional",    # Code appearance
    ],

    # Page structure and Verso documents
    "verso": [
        "t3-dashboard-clarity",      # Page structure
        "t4-toggle-discoverability", # Verso-based toggles
    ],

    # LeanArchitect affects status definitions
    "LeanArchitect": ["t5-color-match"],

    # Test project doesn't affect scores directly
    "SBS-Test": [],

    # Showcase projects don't affect tooling scores
    "General_Crystallographic_Restriction": [],
    "PrimeNumberTheoremAnd": [],
}

# All known quality metrics
ALL_METRICS = [
    "t1-cli-execution",
    "t2-ledger-population",
    "t3-dashboard-clarity",
    "t4-toggle-discoverability",
    "t5-color-match",
    "t6-css-coverage",
    "t7-jarring",
    "t8-professional",
]


# =============================================================================
# Commit Tracking
# =============================================================================


def get_repo_commits(project_root: Optional[Path] = None) -> dict[str, str]:
    """Get current commit hashes for all repos.

    Returns dict of repo_name -> commit_hash.
    """
    commits = {}
    sbs_root = get_sbs_root()

    for name, path in get_repos():
        commits[name] = get_git_commit(path, short=True)

    # Add the project itself if specified
    if project_root:
        project_name = project_root.name
        commits[project_name] = get_git_commit(project_root, short=True)

    return commits


def detect_changed_repos(
    current_commits: dict[str, str],
    previous_commits: dict[str, str],
) -> list[str]:
    """Detect which repos have changed since last run.

    Returns list of repo names that have new commits.
    """
    changed = []

    for repo_name, current_commit in current_commits.items():
        previous_commit = previous_commits.get(repo_name)

        if previous_commit is None:
            # New repo, treat as changed
            changed.append(repo_name)
        elif current_commit != previous_commit:
            changed.append(repo_name)

    return changed


def get_affected_metrics(changed_repos: list[str]) -> list[str]:
    """Determine which metrics are affected by repo changes.

    Returns list of metric IDs that need re-evaluation.
    """
    affected = set()

    for repo in changed_repos:
        metrics = REPO_SCORE_MAPPING.get(repo, [])
        affected.update(metrics)

    return list(affected)


# =============================================================================
# Invalidation
# =============================================================================


def invalidate_stale_scores(ledger: QualityScoreLedger) -> list[str]:
    """Mark scores as stale based on repo changes.

    Compares current repo commits against commits stored in the ledger.
    Marks affected metrics as stale.

    Args:
        ledger: The quality score ledger to update

    Returns:
        List of metric IDs that were marked stale
    """
    # Get current commits
    current_commits = get_repo_commits()

    # Get previous commits from ledger
    previous_commits = ledger.repo_commits

    if not previous_commits:
        log.info("No previous commits in ledger, all metrics need evaluation")
        # Mark all existing scores as stale
        stale_metrics = list(ledger.scores.keys())
        for metric_id in stale_metrics:
            ledger.scores[metric_id].stale = True
        # Update ledger commits
        ledger.repo_commits = current_commits
        return stale_metrics

    # Detect changes
    changed_repos = detect_changed_repos(current_commits, previous_commits)

    if not changed_repos:
        log.info("No repo changes detected")
        return []

    log.info(f"Changed repos: {', '.join(changed_repos)}")

    # Get affected metrics
    affected = get_affected_metrics(changed_repos)
    log.info(f"Affected metrics: {', '.join(affected) if affected else 'none'}")

    # Mark affected scores as stale
    stale_metrics = []
    for metric_id in affected:
        if metric_id in ledger.scores:
            ledger.scores[metric_id].stale = True
            stale_metrics.append(metric_id)

    # Update ledger commits
    ledger.repo_commits = current_commits

    return stale_metrics


def compute_metrics_to_evaluate(
    ledger: QualityScoreLedger,
    force_full: bool = False,
) -> tuple[list[str], dict[str, str]]:
    """Compute which metrics need evaluation based on repo changes.

    Args:
        ledger: Current quality score ledger
        force_full: If True, evaluate all metrics regardless of changes

    Returns:
        (metrics_to_evaluate, current_commits)
    """
    # Get current repo commits
    current_commits = get_repo_commits()

    if force_full:
        log.info("Full evaluation requested")
        return ALL_METRICS, current_commits

    # Invalidate stale scores
    stale_from_changes = invalidate_stale_scores(ledger)

    # Get metrics needing evaluation
    # Include: never evaluated, stale, or failed
    metrics_to_eval = []

    for metric_id in ALL_METRICS:
        score = ledger.scores.get(metric_id)

        if score is None:
            # Never evaluated
            metrics_to_eval.append(metric_id)
        elif score.stale:
            # Marked stale due to repo changes
            metrics_to_eval.append(metric_id)
        elif not score.passed:
            # Previously failed, should retry
            metrics_to_eval.append(metric_id)

    if metrics_to_eval:
        log.info(f"Metrics to evaluate: {', '.join(metrics_to_eval)}")
    else:
        log.info("All metrics up to date")

    return metrics_to_eval, current_commits


def update_ledger_commits(ledger: QualityScoreLedger, commits: dict[str, str]) -> None:
    """Update the repo commits stored in the ledger."""
    ledger.repo_commits = commits


# =============================================================================
# Validation
# =============================================================================


def validate_mapping() -> bool:
    """Validate that the repo-score mapping is consistent.

    Returns True if valid, False otherwise.
    """
    # Check that all mapped metrics exist
    all_mapped_metrics = set()
    for metrics in REPO_SCORE_MAPPING.values():
        all_mapped_metrics.update(metrics)

    unknown_metrics = all_mapped_metrics - set(ALL_METRICS)
    if unknown_metrics:
        log.error(f"Unknown metrics in mapping: {unknown_metrics}")
        return False

    return True


# =============================================================================
# Debug Utilities
# =============================================================================


def print_dependency_graph() -> None:
    """Print the repo -> metric dependency graph for debugging."""
    print("\nRepo -> Metric Dependency Graph:")
    print("=" * 50)

    for repo, metrics in sorted(REPO_SCORE_MAPPING.items()):
        if metrics:
            print(f"  {repo:<30} -> {', '.join(metrics)}")
        else:
            print(f"  {repo:<30} -> (no direct impact)")

    print()


def print_metric_dependencies() -> None:
    """Print the metric -> repo dependency graph for debugging."""
    print("\nMetric -> Repo Dependencies:")
    print("=" * 50)

    # Invert the mapping
    metric_to_repos: dict[str, list[str]] = {m: [] for m in ALL_METRICS}

    for repo, metrics in REPO_SCORE_MAPPING.items():
        for metric in metrics:
            if metric in metric_to_repos:
                metric_to_repos[metric].append(repo)

    for metric_id in ALL_METRICS:
        repos = metric_to_repos[metric_id]
        if repos:
            print(f"  {metric_id:<30} <- {', '.join(repos)}")
        else:
            print(f"  {metric_id:<30} <- (infrastructure only)")

    print()


def print_repo_status() -> None:
    """Print current repo commit status."""
    commits = get_repo_commits()

    print("\nCurrent Repo Commits:")
    print("=" * 50)

    for repo, commit in sorted(commits.items()):
        print(f"  {repo:<30} {commit}")

    print()
