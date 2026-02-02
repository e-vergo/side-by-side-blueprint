"""Branch management utilities for PR workflow.

Provides functions for creating, managing, and cleaning up feature branches
used in the PR-based development workflow.
"""

import re
import subprocess
from typing import Optional

from sbs.core.utils import log


def slugify(text: str, max_length: int = 40) -> str:
    """Convert text to a valid git branch slug.

    - Lowercase
    - Replace spaces and special chars with hyphens
    - Remove consecutive hyphens
    - Truncate to max_length
    """
    # Lowercase and replace non-alphanumeric with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower())
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Truncate
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip('-')
    return slug


def create_feature_branch(
    slug: str,
    issue_number: Optional[int] = None,
    base: str = "main",
) -> Optional[str]:
    """Create and checkout a feature branch.

    Args:
        slug: Short description for branch name
        issue_number: Optional GitHub issue number to include
        base: Base branch to create from (default: main)

    Returns:
        Branch name if successful, None if failed

    Branch naming:
        - With issue: task/<issue>-<slug>
        - Without issue: task/<slug>
    """
    # Build branch name
    slug = slugify(slug)
    if issue_number:
        branch = f"task/{issue_number}-{slug}"
    else:
        branch = f"task/{slug}"

    try:
        # Ensure we're on the base branch and up to date
        subprocess.run(
            ["git", "checkout", base],
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            ["git", "pull", "--ff-only"],
            capture_output=True,
            text=True,
        )

        # Create and checkout new branch
        result = subprocess.run(
            ["git", "checkout", "-b", branch],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            log.error(f"Failed to create branch: {result.stderr}")
            return None

        log.success(f"Created branch: {branch}")
        return branch

    except subprocess.CalledProcessError as e:
        log.error(f"Git error: {e.stderr}")
        return None
    except Exception as e:
        log.error(f"Error creating branch: {e}")
        return None


def get_current_branch() -> Optional[str]:
    """Get the name of the current branch.

    Returns:
        Branch name, or None if not in a git repo or detached HEAD
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        return branch if branch else None
    except Exception:
        return None


def is_on_feature_branch() -> bool:
    """Check if we're on a feature branch (not main/master).

    Feature branches are identified by the task/ prefix.
    """
    branch = get_current_branch()
    if not branch:
        return False
    return branch.startswith("task/")


def is_on_main() -> bool:
    """Check if we're on the main branch."""
    branch = get_current_branch()
    return branch in ("main", "master")


def push_branch(branch: Optional[str] = None, set_upstream: bool = True) -> bool:
    """Push branch to origin.

    Args:
        branch: Branch to push (default: current branch)
        set_upstream: Whether to set upstream tracking

    Returns:
        True if successful
    """
    if branch is None:
        branch = get_current_branch()

    if not branch:
        log.error("No branch to push")
        return False

    try:
        cmd = ["git", "push"]
        if set_upstream:
            cmd.extend(["-u", "origin", branch])
        else:
            cmd.extend(["origin", branch])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            log.error(f"Failed to push: {result.stderr}")
            return False

        log.success(f"Pushed branch: {branch}")
        return True

    except Exception as e:
        log.error(f"Error pushing branch: {e}")
        return False


def delete_branch(branch: str, remote: bool = True) -> bool:
    """Delete a branch locally and optionally remotely.

    Args:
        branch: Branch name to delete
        remote: Whether to also delete from origin

    Returns:
        True if successful
    """
    current = get_current_branch()
    if current == branch:
        # Switch to main first
        subprocess.run(["git", "checkout", "main"], capture_output=True)

    success = True

    # Delete locally
    try:
        result = subprocess.run(
            ["git", "branch", "-D", branch],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            log.warning(f"Failed to delete local branch: {result.stderr}")
            success = False
        else:
            log.dim(f"Deleted local branch: {branch}")
    except Exception as e:
        log.warning(f"Error deleting local branch: {e}")
        success = False

    # Delete remotely
    if remote:
        try:
            result = subprocess.run(
                ["git", "push", "origin", "--delete", branch],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                # Branch might not exist on remote - that's OK
                if "remote ref does not exist" not in result.stderr:
                    log.warning(f"Failed to delete remote branch: {result.stderr}")
            else:
                log.dim(f"Deleted remote branch: {branch}")
        except Exception as e:
            log.warning(f"Error deleting remote branch: {e}")

    return success


def checkout_branch(branch: str) -> bool:
    """Checkout an existing branch.

    Args:
        branch: Branch name to checkout

    Returns:
        True if successful
    """
    try:
        result = subprocess.run(
            ["git", "checkout", branch],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            log.error(f"Failed to checkout: {result.stderr}")
            return False
        return True
    except Exception as e:
        log.error(f"Error checking out branch: {e}")
        return False
