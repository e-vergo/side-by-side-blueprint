"""
Main archive upload command.

Provides a single `sbs archive upload` command that:
1. Extracts ~/.claude data
2. Creates ArchiveEntry with ClaudeDataSnapshot
3. Runs tagging engine (rules + hooks)
4. Saves to archive_index.json
5. Syncs to iCloud
6. Commits and pushes all repos (porcelain guarantee)
"""

from __future__ import annotations

import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from sbs.archive.entry import ArchiveEntry, ArchiveIndex
from sbs.archive.extractor import extract_claude_data
from sbs.archive.gates import check_gates, GateResult
from sbs.archive.session_data import ClaudeDataSnapshot, SessionData
from sbs.archive.tagger import TaggingEngine, build_tagging_context
from sbs.archive.icloud_sync import full_sync
from sbs.core.utils import log, ARCHIVE_DIR, SBS_ROOT

# Repo paths relative to monorepo root
REPO_PATHS = {
    "verso": "forks/verso",
    "subverso": "forks/subverso",
    "LeanArchitect": "forks/LeanArchitect",
    "Dress": "toolchain/Dress",
    "Runway": "toolchain/Runway",
    "SBS-Test": "toolchain/SBS-Test",
    "dress-blueprint-action": "toolchain/dress-blueprint-action",
    "GCR": "showcase/General_Crystallographic_Restriction",
    "PNT": "showcase/PrimeNumberTheoremAnd",
    "storage": "dev/storage",
}


def get_monorepo_root() -> Path:
    """Get the Side-By-Side-Blueprint monorepo root.

    Uses the auto-detected SBS_ROOT from utils.py.
    """
    return SBS_ROOT


def get_repo_commit(repo_path: Path) -> Optional[str]:
    """Get current commit SHA for a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def repo_is_dirty(repo_path: Path) -> bool:
    """Check if repo has uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return bool(result.stdout.strip())
    except Exception:
        return True


def commit_and_push_repo(repo_path: Path, message: str, dry_run: bool = False) -> bool:
    """Commit and push changes in a repo."""
    if dry_run:
        log.dim(f"[dry-run] Would commit and push: {repo_path.name}")
        return True

    try:
        # Check if dirty
        if not repo_is_dirty(repo_path):
            return True

        # Stage all changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=repo_path,
            capture_output=True,
            timeout=30,
        )

        # Commit
        commit_msg = f"{message}\n\nCo-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0 and "nothing to commit" not in result.stdout:
            log.warning(f"Commit failed for {repo_path.name}: {result.stderr}")
            return False

        # Push
        result = subprocess.run(
            ["git", "push"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            log.warning(f"Push failed for {repo_path.name}: {result.stderr}")
            return False

        return True

    except Exception as e:
        log.warning(f"Git operation failed for {repo_path.name}: {e}")
        return False


def ensure_porcelain(dry_run: bool = False) -> tuple[bool, list[str]]:
    """
    Ensure all repos are in porcelain (clean) state.

    Commits and pushes any uncommitted changes.
    Returns (success, list_of_failed_repos).
    """
    root = get_monorepo_root()
    failed = []

    # Process main repo
    if repo_is_dirty(root):
        if not commit_and_push_repo(root, "chore: archive upload", dry_run):
            failed.append("main")

    # Process submodule repos
    for name, rel_path in REPO_PATHS.items():
        repo_path = root / rel_path
        if repo_path.exists() and repo_is_dirty(repo_path):
            if not commit_and_push_repo(repo_path, "chore: archive upload", dry_run):
                failed.append(name)

    return len(failed) == 0, failed


def collect_repo_commits() -> dict[str, str]:
    """Collect current commit SHAs for all repos."""
    root = get_monorepo_root()
    commits = {}

    # Main repo
    main_commit = get_repo_commit(root)
    if main_commit:
        commits["main"] = main_commit

    # Submodule repos
    for name, rel_path in REPO_PATHS.items():
        repo_path = root / rel_path
        if repo_path.exists():
            commit = get_repo_commit(repo_path)
            if commit:
                commits[name] = commit

    return commits


def _load_quality_scores(project: str, index_path: Path) -> tuple[Optional[dict], Optional[dict]]:
    """Load quality scores and compute delta from previous entry.

    Args:
        project: Project name
        index_path: Path to archive index for finding previous entry

    Returns:
        (quality_scores_dict, delta_dict) or (None, None) if unavailable
    """
    try:
        from sbs.tests.scoring import load_ledger as load_quality_ledger

        ledger = load_quality_ledger(project)

        if not ledger.scores:
            return None, None

        # Build quality scores snapshot
        scores_dict = {}
        for metric_id, score in ledger.scores.items():
            scores_dict[metric_id] = {
                "value": score.value,
                "passed": score.passed,
                "stale": score.stale,
            }

        quality_scores = {
            "overall": ledger.overall_score,
            "scores": scores_dict,
            "evaluated_at": ledger.last_evaluated,
        }

        # Compute delta from previous entry
        delta = None
        try:
            index = ArchiveIndex.load(index_path)
            previous = index.get_latest_entry(project)

            if previous and previous.quality_scores:
                prev_overall = previous.quality_scores.get("overall", 0.0)
                delta = {
                    "overall": round(ledger.overall_score - prev_overall, 2),
                    "previous_overall": prev_overall,
                }
        except Exception:
            pass  # Delta is optional

        return quality_scores, delta

    except Exception as e:
        log.warning(f"Could not load quality scores: {e}")
        return None, None


def archive_upload(
    project: Optional[str] = None,
    build_run_id: Optional[str] = None,
    trigger: str = "manual",
    dry_run: bool = False,
    build_success: Optional[bool] = None,
    build_duration_seconds: Optional[float] = None,
    repos_changed: Optional[list[str]] = None,
    # State machine parameters
    global_state: Optional[dict] = None,
    state_transition: Optional[str] = None,
    # Gate validation
    force: bool = False,
) -> dict:
    """
    Main archive upload function.

    1. Extract ~/.claude data
    2. Create ArchiveEntry with ClaudeDataSnapshot
    3. Run tagging engine (rules + hooks)
    4. Save to archive_index.json
    5. Sync to iCloud
    6. Commit and push all repos (porcelain guarantee)

    Args:
        project: Project name (optional)
        build_run_id: Link to unified ledger build (optional)
        trigger: "build", "manual", or "skill"
        dry_run: If True, don't make changes
        build_success: Build success status for tagging
        build_duration_seconds: Build duration for tagging
        repos_changed: List of changed repos for tagging

    Returns:
        Dict with upload results
    """
    log.header("Archive Upload")

    result = {
        "success": False,
        "entry_id": None,
        "sessions_extracted": 0,
        "plans_extracted": 0,
        "tags_applied": [],
        "porcelain": False,
        "synced": False,
        "errors": [],
    }

    try:
        # 1. Extract ~/.claude data
        log.info("Extracting Claude Code data...")
        claude_data_dir = ARCHIVE_DIR / "claude_data"

        if dry_run:
            log.dim("[dry-run] Would extract to: " + str(claude_data_dir))
            snapshot = ClaudeDataSnapshot(
                extraction_timestamp=datetime.now().isoformat()
            )
        else:
            snapshot = extract_claude_data(claude_data_dir)

        result["sessions_extracted"] = len(snapshot.session_ids)
        result["plans_extracted"] = len(snapshot.plan_files)

        # Define index path early (needed for quality score delta computation)
        index_path = ARCHIVE_DIR / "archive_index.json"

        # 2. Create ArchiveEntry
        entry_id = str(int(time.time()))
        entry = ArchiveEntry(
            entry_id=entry_id,
            created_at=datetime.now().isoformat(),
            project=project or "SBSMonorepo",
            build_run_id=build_run_id,
            claude_data=snapshot.to_dict(),
            trigger=trigger,
            global_state=global_state,
            state_transition=state_transition,
        )
        result["entry_id"] = entry_id

        # 2.5 Include quality scores
        log.info("Loading quality scores...")
        quality_scores, quality_delta = _load_quality_scores(project or "SBSMonorepo", index_path)
        entry.quality_scores = quality_scores
        entry.quality_delta = quality_delta
        if quality_scores:
            result["quality_score"] = quality_scores.get("overall", 0.0)

        # 3. Collect repo commits
        log.info("Collecting repo commits...")
        entry.repo_commits = collect_repo_commits()

        # 4. Run tagging engine
        log.info("Running auto-tagging...")
        rules_path = ARCHIVE_DIR / "tagging" / "rules.yaml"
        hooks_dir = ARCHIVE_DIR / "tagging" / "hooks"

        tagger = TaggingEngine(rules_path, hooks_dir)

        # Build context for tagging
        context = build_tagging_context(
            entry,
            build_success=build_success,
            build_duration_seconds=build_duration_seconds,
            repos_changed=repos_changed,
            files_modified=snapshot.files_modified,
        )

        # Load sessions for hooks (if not dry run)
        sessions: list[SessionData] = []
        if not dry_run:
            import json

            sessions_dir = claude_data_dir / "sessions"
            if sessions_dir.exists():
                for f in sessions_dir.glob("*.json"):
                    if f.name != "index.json":
                        try:
                            with open(f) as fp:
                                sessions.append(SessionData.from_dict(json.load(fp)))
                        except Exception:
                            pass

        auto_tags = tagger.evaluate(entry, context, sessions)
        entry.auto_tags = auto_tags
        result["tags_applied"] = auto_tags

        log.info(f"Applied {len(auto_tags)} auto-tags: {auto_tags}")

        # 4.5 Gate validation for /task execution->finalization transition
        gate_result: Optional[GateResult] = None
        if (state_transition == "phase_start" and
            global_state and
            global_state.get("skill") == "task" and
            global_state.get("substate") == "finalization"):

            log.info("Checking gates before finalization...")
            gate_result = check_gates(project=project or "SBSTest", force=force)

            for finding in gate_result.findings:
                log.dim(f"  {finding}")

            if not gate_result.passed:
                log.error("[BLOCKED] Gate validation failed - transition blocked")
                log.warning("Use --force to bypass gate validation")
                return {
                    "success": False,
                    "error": "Gate validation failed",
                    "gate_findings": gate_result.findings,
                    "entry_id": entry_id,
                }
            else:
                log.success("[OK] Gate validation passed")

            # Record gate validation in entry
            entry.gate_validation = {
                "passed": gate_result.passed,
                "findings": gate_result.findings,
            }

        # 5. Save to archive index
        log.info("Saving to archive index...")
        # index_path already defined above

        if dry_run:
            log.dim(f"[dry-run] Would save entry {entry_id} to {index_path}")
        else:
            index = ArchiveIndex.load(index_path)

            # Compute epoch_summary for skill-triggered entries (epoch close)
            if trigger == "skill":
                # Get entries since last epoch close
                last_epoch_id = index.last_epoch_entry
                epoch_entries = []
                for eid, e in index.entries.items():
                    if last_epoch_id is None or eid > last_epoch_id:
                        if eid != entry.entry_id:  # Don't include self
                            epoch_entries.append(e)

                entry.epoch_summary = {
                    "entries_in_epoch": len(epoch_entries),
                    "builds_in_epoch": sum(1 for e in epoch_entries if e.trigger == "build"),
                    "entry_ids": [e.entry_id for e in epoch_entries],
                }

                # Update index to mark this as the new epoch boundary
                index.last_epoch_entry = entry.entry_id

            # Update index global_state if state_transition indicates a change
            if global_state is not None:
                index.global_state = global_state
            elif state_transition == "phase_end" and global_state is None:
                # Clearing state (returning to idle)
                index.global_state = None

            index.add_entry(entry)
            index.save(index_path)

        # 6. Sync to iCloud
        log.info("Syncing to iCloud...")
        if dry_run:
            log.dim("[dry-run] Would sync to iCloud")
            result["synced"] = True
        else:
            try:
                index = ArchiveIndex.load(index_path)
                sync_result = full_sync(ARCHIVE_DIR, index)
                result["synced"] = sync_result.get("success", False)
                if not result["synced"]:
                    result["errors"].extend(sync_result.get("errors", []))
            except Exception as e:
                log.warning(f"iCloud sync failed: {e}")
                result["errors"].append(f"iCloud sync: {e}")

        # 7. Ensure porcelain state
        log.info("Ensuring porcelain git state...")
        porcelain_success, failed_repos = ensure_porcelain(dry_run)
        result["porcelain"] = porcelain_success

        if not porcelain_success:
            result["errors"].append(f"Failed to achieve porcelain: {failed_repos}")
            log.warning(f"Porcelain failed for: {failed_repos}")

        result["success"] = True
        log.success(f"Archive upload complete: entry {entry_id}")

    except Exception as e:
        log.error(f"Archive upload failed: {e}")
        result["errors"].append(str(e))

    return result
