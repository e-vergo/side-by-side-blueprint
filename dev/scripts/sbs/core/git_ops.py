"""
Git operations for Side-by-Side Blueprint.

Status, diff, and sync operations across all repos.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from sbs.core.utils import (
    get_repos,
    get_sbs_root,
    get_git_branch,
    git_has_changes,
    git_status_short,
    git_diff_stat,
    log,
)


# =============================================================================
# Git Status
# =============================================================================


def get_repo_status(repo_path: Path) -> dict:
    """Get comprehensive status for a repo.

    Returns dict with: branch, has_changes, status_short, ahead_behind
    """
    status = {
        "path": repo_path,
        "branch": get_git_branch(repo_path),
        "has_changes": git_has_changes(repo_path),
        "status_short": git_status_short(repo_path) if git_has_changes(repo_path) else "",
    }

    # Check ahead/behind
    try:
        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) == 2:
                ahead, behind = int(parts[0]), int(parts[1])
                status["ahead"] = ahead
                status["behind"] = behind
    except Exception:
        pass

    return status


# =============================================================================
# Git Sync
# =============================================================================


def sync_repo(repo_path: Path, message: str = "Auto-commit from sbs sync") -> dict:
    """Commit and push changes for a repo.

    Returns dict with: success, committed, pushed, error
    """
    result = {
        "path": repo_path,
        "success": True,
        "committed": False,
        "pushed": False,
        "error": None,
    }

    if not git_has_changes(repo_path):
        return result

    try:
        # Stage all changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Commit
        commit_message = f"{message}\n\nCo-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        result["committed"] = True

        # Push
        subprocess.run(
            ["git", "push"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        result["pushed"] = True

    except subprocess.CalledProcessError as e:
        result["success"] = False
        result["error"] = e.stderr if e.stderr else str(e)

    return result


# =============================================================================
# CLI Entry Points
# =============================================================================


def cmd_status(args) -> int:
    """Main entry point for the status command."""
    log.header("Git Status Across All Repos")

    try:
        repos = get_repos()
        sbs_root = get_sbs_root()

        # Add monorepo
        repos.insert(0, ("Side-By-Side-Blueprint", sbs_root))

        has_changes = False

        for name, path in repos:
            status = get_repo_status(path)

            # Build status line
            parts = []

            if status["has_changes"]:
                has_changes = True
                parts.append("[MODIFIED]")

            if status.get("ahead", 0) > 0:
                parts.append(f"+{status['ahead']}")
            if status.get("behind", 0) > 0:
                parts.append(f"-{status['behind']}")

            branch = status["branch"]
            if branch != "main":
                branch = f"({branch})"
            else:
                branch = ""

            status_str = " ".join(parts)

            if status["has_changes"]:
                log.warning(f"{name:<40} {branch} {status_str}")
                if args.verbose and status["status_short"]:
                    for line in status["status_short"].split("\n"):
                        log.dim(f"    {line}")
            else:
                if status_str:
                    log.info(f"{name:<40} {branch} {status_str}")
                else:
                    log.success(f"{name:<40} {branch} clean")

        print()
        if has_changes:
            log.warning("Some repos have uncommitted changes")
            log.info("Run 'sbs sync' to commit and push all changes")
        else:
            log.success("All repos are clean")

        return 0

    except KeyboardInterrupt:
        log.warning("Interrupted")
        return 130
    except Exception as e:
        log.error(str(e))
        return 1


def cmd_diff(args) -> int:
    """Main entry point for the diff command."""
    log.header("Git Diff Across All Repos")

    try:
        repos = get_repos()
        sbs_root = get_sbs_root()

        # Add monorepo
        repos.insert(0, ("Side-By-Side-Blueprint", sbs_root))

        has_changes = False

        for name, path in repos:
            if not git_has_changes(path):
                continue

            has_changes = True
            log.header(name)

            if args.full:
                # Full diff
                result = subprocess.run(
                    ["git", "diff"],
                    cwd=path,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.stdout:
                    print(result.stdout)
            else:
                # Stat only
                diff_stat = git_diff_stat(path)
                if diff_stat:
                    for line in diff_stat.split("\n"):
                        log.info(line)

        if not has_changes:
            log.success("No changes in any repo")

        return 0

    except KeyboardInterrupt:
        log.warning("Interrupted")
        return 130
    except Exception as e:
        log.error(str(e))
        return 1


def cmd_sync(args) -> int:
    """Main entry point for the sync command."""
    log.header("Sync All Repos to GitHub")

    try:
        repos = get_repos()
        sbs_root = get_sbs_root()

        # Add monorepo
        repos.insert(0, ("Side-By-Side-Blueprint", sbs_root))

        message = args.message if args.message else "Auto-commit from sbs sync"

        synced = 0
        failed = 0

        for name, path in repos:
            if not git_has_changes(path):
                if args.verbose:
                    log.dim(f"{name}: no changes")
                continue

            log.info(f"Syncing {name}...")

            if args.dry_run:
                log.dim(f"  Would commit and push changes")
                synced += 1
                continue

            result = sync_repo(path, message)

            if result["success"]:
                if result["committed"]:
                    log.success(f"{name}: committed and pushed")
                    synced += 1
            else:
                log.error(f"{name}: {result['error']}")
                failed += 1

        print()
        if synced > 0:
            log.success(f"Synced {synced} repo(s)")
        if failed > 0:
            log.error(f"Failed to sync {failed} repo(s)")
        if synced == 0 and failed == 0:
            log.info("All repos already in sync")

        return 1 if failed > 0 else 0

    except KeyboardInterrupt:
        log.warning("Interrupted")
        return 130
    except Exception as e:
        log.error(str(e))
        return 1
