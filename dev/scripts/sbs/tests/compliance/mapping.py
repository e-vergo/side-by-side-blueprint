"""
Repo-to-page dependency mapping.

Determines which pages need revalidation when repos change.
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


# =============================================================================
# Dependency Graph
# =============================================================================

# Maps repo names to the pages they affect
REPO_PAGE_MAPPING: dict[str, list[str]] = {
    # Core highlighting - affects all pages with Lean code
    "subverso": ["ALL"],

    # Status/attributes - affects graph and chapter pages
    "LeanArchitect": ["dep_graph", "chapter"],

    # Artifact generation, graph layout - affects graph and chapters
    "Dress": ["dep_graph", "chapter"],

    # Templates, site structure - affects all pages
    "Runway": ["ALL"],

    # Verso documents
    "verso": ["paper_verso", "blueprint_verso"],

    # CSS/JS assets - affects all pages
    "dress-blueprint-action": ["ALL"],

    # Test project itself
    "SBS-Test": ["ALL"],
}

# All known pages
ALL_PAGES = [
    "dashboard",
    "dep_graph",
    "paper_tex",
    "pdf_tex",
    "paper_verso",
    "pdf_verso",
    "blueprint_verso",
    "chapter",
]


# =============================================================================
# Change Detection
# =============================================================================


def get_repo_commits(project_root: Optional[Path] = None) -> dict[str, str]:
    """Get current commit hashes for all repos.

    Returns dict of repo_name -> commit_hash.
    """
    commits = {}
    sbs_root = get_sbs_root()

    for name, path in get_repos():
        commits[name] = get_git_commit(path, short=True)

    # Add the project itself
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


def get_affected_pages(changed_repos: list[str]) -> list[str]:
    """Determine which pages are affected by repo changes.

    Returns list of page names that need revalidation.
    """
    affected = set()

    for repo in changed_repos:
        pages = REPO_PAGE_MAPPING.get(repo, [])

        if "ALL" in pages:
            # This repo affects all pages
            return ALL_PAGES

        affected.update(pages)

    return list(affected)


# =============================================================================
# Smart Reset
# =============================================================================


def compute_pages_to_validate(
    ledger,  # ComplianceLedger - avoid circular import
    project_root: Path,
    force_full: bool = False,
) -> tuple[list[str], dict[str, str]]:
    """Compute which pages need validation based on repo changes.

    Args:
        ledger: Current compliance ledger
        project_root: Path to project root
        force_full: If True, validate all pages regardless of changes

    Returns:
        (pages_to_validate, current_commits)
    """
    # Get current repo commits
    current_commits = get_repo_commits(project_root)

    if force_full:
        log.info("Full validation requested")
        return ALL_PAGES, current_commits

    # Get previous commits from ledger
    previous_commits = ledger.repo_commits

    if not previous_commits:
        log.info("No previous commits in ledger, validating all pages")
        return ALL_PAGES, current_commits

    # Detect changes
    changed_repos = detect_changed_repos(current_commits, previous_commits)

    if not changed_repos:
        log.info("No repo changes detected")
        # Still need to check pages that were pending or failed
        pending = [
            name for name, result in ledger.pages.items()
            if result.status in ("pending", "fail") or result.needs_revalidation
        ]
        return pending if pending else [], current_commits

    log.info(f"Changed repos: {', '.join(changed_repos)}")

    # Get affected pages
    affected = get_affected_pages(changed_repos)
    log.info(f"Affected pages: {', '.join(affected)}")

    return affected, current_commits


def update_ledger_commits(ledger, commits: dict[str, str]) -> None:
    """Update the repo commits stored in the ledger."""
    ledger.repo_commits = commits


# =============================================================================
# Validation
# =============================================================================


def validate_mapping() -> bool:
    """Validate that the repo-page mapping is consistent.

    Returns True if valid, False otherwise.
    """
    # Check that all mapped pages exist
    all_mapped_pages = set()
    for pages in REPO_PAGE_MAPPING.values():
        if "ALL" not in pages:
            all_mapped_pages.update(pages)

    unknown_pages = all_mapped_pages - set(ALL_PAGES)
    if unknown_pages:
        log.error(f"Unknown pages in mapping: {unknown_pages}")
        return False

    return True


# =============================================================================
# Debug Utilities
# =============================================================================


def print_dependency_graph() -> None:
    """Print the dependency graph for debugging."""
    print("\nRepo -> Page Dependency Graph:")
    print("=" * 50)

    for repo, pages in sorted(REPO_PAGE_MAPPING.items()):
        if "ALL" in pages:
            print(f"  {repo:<25} -> ALL pages")
        else:
            print(f"  {repo:<25} -> {', '.join(pages)}")

    print()


def print_repo_status(project_root: Optional[Path] = None) -> None:
    """Print current repo commit status."""
    commits = get_repo_commits(project_root)

    print("\nCurrent Repo Commits:")
    print("=" * 50)

    for repo, commit in sorted(commits.items()):
        print(f"  {repo:<25} {commit}")

    print()
