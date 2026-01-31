"""
Git metrics validator for tracking commits, diffs, and repo state across SBS workspace.

This validator collects git metrics from all repos in the SBS workspace and validates
that they are clean (no uncommitted changes). The SBS build system requires all repos
to be committed before building to ensure reproducible builds.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Optional

from .base import BaseValidator, ValidationContext, ValidatorResult
from .registry import register_validator


# SBS toolchain repos (relative to workspace root)
TOOLCHAIN_REPOS = [
    "subverso",
    "verso",
    "LeanArchitect",
    "Dress",
    "Runway",
    "dress-blueprint-action",
]


def _run_git(repo_path: Path, args: list[str]) -> Optional[str]:
    """Run a git command and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (OSError, subprocess.SubprocessError):
        return None


def _get_commit(repo_path: Path) -> str:
    """Get current commit hash (short)."""
    result = _run_git(repo_path, ["rev-parse", "--short", "HEAD"])
    return result if result else "unknown"


def _get_branch(repo_path: Path) -> str:
    """Get current branch name."""
    result = _run_git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"])
    return result if result else "unknown"


def _is_clean(repo_path: Path) -> bool:
    """Check if repo has no uncommitted changes."""
    result = _run_git(repo_path, ["status", "--porcelain"])
    return result == "" if result is not None else True


def _get_files_changed(repo_path: Path) -> list[str]:
    """Get list of changed files (modified, added, deleted)."""
    result = _run_git(repo_path, ["status", "--porcelain"])
    if not result:
        return []

    files = []
    for line in result.split("\n"):
        if line.strip():
            # Format: "XY filename" where XY is the status
            files.append(line.strip())
    return files


def _get_diff_stats(repo_path: Path) -> tuple[int, int]:
    """Get lines added and deleted from uncommitted changes.

    Returns (lines_added, lines_deleted).
    """
    # Get stats for staged changes
    staged = _run_git(repo_path, ["diff", "--cached", "--numstat"])
    # Get stats for unstaged changes
    unstaged = _run_git(repo_path, ["diff", "--numstat"])

    lines_added = 0
    lines_deleted = 0

    for output in [staged, unstaged]:
        if output:
            for line in output.split("\n"):
                parts = line.split("\t")
                if len(parts) >= 2:
                    # Format: "added\tdeleted\tfilename"
                    # Binary files show "-" for added/deleted
                    try:
                        if parts[0] != "-":
                            lines_added += int(parts[0])
                        if parts[1] != "-":
                            lines_deleted += int(parts[1])
                    except ValueError:
                        continue

    return lines_added, lines_deleted


def _collect_repo_metrics(repo_path: Path) -> dict[str, Any]:
    """Collect all metrics for a single repo."""
    files_changed = _get_files_changed(repo_path)
    lines_added, lines_deleted = _get_diff_stats(repo_path)

    return {
        "commit": _get_commit(repo_path),
        "branch": _get_branch(repo_path),
        "clean": _is_clean(repo_path),
        "files_changed": len(files_changed),
        "files_list": files_changed,
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
    }


def _infer_workspace_root(project_root: Path) -> Path:
    """Infer the SBS workspace root from a project root.

    The workspace root is the parent directory containing all repos.
    For SBS-Test, GCR, PNT: workspace is parent of project_root
    For standalone projects: workspace might be the project itself
    """
    # Check if parent contains expected toolchain repos
    parent = project_root.parent
    for repo in TOOLCHAIN_REPOS[:3]:  # Check first few
        if (parent / repo).exists():
            return parent

    # Fallback to project root
    return project_root


@register_validator
class GitMetricsValidator(BaseValidator):
    """Validates git state and collects metrics across SBS workspace repos.

    This validator ensures all repos are clean (no uncommitted changes) before
    builds, which is required for reproducible builds and proper compliance ledger
    tracking.

    Expected context.extra keys:
        repos: list[Path] - Optional list of repo paths to check.
            If not provided, infers from project_root.

    Recorded metrics:
        repos: dict[str, dict] - Per-repo metrics (commit, branch, clean, etc.)
        total_files_changed: int - Total files changed across all repos
        total_lines_added: int - Total lines added across all repos
        total_lines_deleted: int - Total lines deleted across all repos
        dirty_repos: list[str] - Names of repos with uncommitted changes
    """

    def __init__(self) -> None:
        super().__init__("git-metrics", "git")

    def validate(self, context: ValidationContext) -> ValidatorResult:
        """Collect git metrics and validate repos are clean.

        Args:
            context: Validation context with project_root and optional
                repos list in extra dict.

        Returns:
            ValidatorResult that passes if all repos are clean, fails if
            any repo has uncommitted changes.
        """
        # Determine which repos to check
        repo_paths: list[tuple[str, Path]] = []

        if "repos" in context.extra:
            # Use explicitly provided repo paths
            for path in context.extra["repos"]:
                path = Path(path)
                if path.exists():
                    repo_paths.append((path.name, path))
        else:
            # Infer repos from workspace structure
            workspace_root = _infer_workspace_root(context.project_root)

            # Add toolchain repos
            for repo_name in TOOLCHAIN_REPOS:
                repo_path = workspace_root / repo_name
                if repo_path.exists() and (repo_path / ".git").exists():
                    repo_paths.append((repo_name, repo_path))

            # Add the project repo itself
            if (context.project_root / ".git").exists():
                repo_paths.append((context.project_root.name, context.project_root))

        # Collect metrics for each repo
        repos_metrics: dict[str, dict[str, Any]] = {}
        dirty_repos: list[str] = []
        total_files_changed = 0
        total_lines_added = 0
        total_lines_deleted = 0

        for repo_name, repo_path in repo_paths:
            metrics = _collect_repo_metrics(repo_path)
            repos_metrics[repo_name] = metrics

            if not metrics["clean"]:
                dirty_repos.append(repo_name)

            total_files_changed += metrics["files_changed"]
            total_lines_added += metrics["lines_added"]
            total_lines_deleted += metrics["lines_deleted"]

        # Build findings
        findings: list[str] = []

        if dirty_repos:
            findings.append(
                f"{len(dirty_repos)} repo(s) have uncommitted changes: {', '.join(dirty_repos)}"
            )
            for repo_name in dirty_repos:
                metrics = repos_metrics[repo_name]
                findings.append(
                    f"  {repo_name}: {metrics['files_changed']} file(s), "
                    f"+{metrics['lines_added']}/-{metrics['lines_deleted']} lines"
                )
        else:
            findings.append(f"All {len(repos_metrics)} repos are clean")

        # Build metrics dict
        # Remove files_list from repos_metrics to keep metrics compact
        compact_repos = {
            name: {k: v for k, v in m.items() if k != "files_list"}
            for name, m in repos_metrics.items()
        }

        metrics = {
            "repos": compact_repos,
            "total_files_changed": total_files_changed,
            "total_lines_added": total_lines_added,
            "total_lines_deleted": total_lines_deleted,
            "dirty_repos": dirty_repos,
            "repos_checked": len(repos_metrics),
        }

        # Validation passes only if all repos are clean
        passed = len(dirty_repos) == 0

        return self._make_result(
            passed=passed,
            findings=findings,
            metrics=metrics,
            confidence=1.0,  # Git state is deterministic
            details={
                "workspace_root": str(_infer_workspace_root(context.project_root)),
                "repos_with_changes": {
                    name: repos_metrics[name]["files_list"]
                    for name in dirty_repos
                },
            },
        )
