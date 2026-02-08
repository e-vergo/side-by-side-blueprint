"""
Retroactive migration of historical archive data to entry system.

Scans existing archive/{project}/archive/{timestamp}/ directories
and creates ArchiveEntry records with best-effort metadata linkage.
"""

from pathlib import Path
from typing import Optional
import json
import logging
from datetime import datetime

from .entry import ArchiveEntry, ArchiveIndex

log = logging.getLogger(__name__)


def scan_historical_captures(archive_root: Path) -> list[dict]:
    """
    Scan for historical capture directories.

    Looks for: archive/{project}/archive/{timestamp}/

    Returns list of dicts with:
    {
        "project": str,
        "timestamp": str,
        "path": Path,
        "capture_json": dict or None,
        "screenshots": list[str],
    }
    """
    captures = []

    for project_dir in archive_root.iterdir():
        if not project_dir.is_dir():
            continue

        # Skip non-project directories
        if project_dir.name in ("charts", "chat_summaries", "manifests", "entries"):
            continue

        project = project_dir.name
        archive_dir = project_dir / "archive"

        if not archive_dir.exists():
            continue

        for ts_dir in archive_dir.iterdir():
            if not ts_dir.is_dir():
                continue

            timestamp = ts_dir.name
            capture = {
                "project": project,
                "timestamp": timestamp,
                "path": ts_dir,
                "capture_json": None,
                "screenshots": [],
            }

            # Try to load capture.json
            capture_json_path = ts_dir / "capture.json"
            if capture_json_path.exists():
                try:
                    with open(capture_json_path) as f:
                        capture["capture_json"] = json.load(f)
                except Exception as e:
                    log.warning(f"Could not load {capture_json_path}: {e}")

            # List screenshots
            capture["screenshots"] = [p.name for p in ts_dir.glob("*.png")]

            captures.append(capture)

    return sorted(captures, key=lambda c: c["timestamp"])


def parse_archive_timestamp(timestamp: str) -> Optional[datetime]:
    """
    Parse various timestamp formats from archive directories.

    Supports:
    - "2026-01-31_10-21-19" (current format)
    - "20250130_143022" (legacy format)

    Returns datetime or None if parsing fails.
    """
    # Try current format: 2026-01-31_10-21-19
    try:
        return datetime.strptime(timestamp, "%Y-%m-%d_%H-%M-%S")
    except ValueError:
        pass

    # Try legacy format: 20250130_143022
    try:
        return datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
    except ValueError:
        pass

    return None


def find_matching_build(timestamp: str, ledger_path: Path) -> Optional[dict]:
    """
    Find a build in unified_ledger.json that matches the timestamp.

    Uses fuzzy matching (within 1 hour window).

    Returns the build dict or None.
    """
    if not ledger_path.exists():
        return None

    try:
        with open(ledger_path) as f:
            ledger = json.load(f)

        # Collect all builds from both current_build and build_history
        builds = []
        if ledger.get("current_build"):
            builds.append(ledger["current_build"])
        builds.extend(ledger.get("build_history", []))

        # Parse target timestamp
        target_dt = parse_archive_timestamp(timestamp)
        if target_dt is None:
            return None

        # Find closest build within 1 hour
        best_match = None
        best_delta = float("inf")

        for build in builds:
            build_ts = build.get("started_at", "")
            try:
                # Handle ISO format with optional timezone
                build_dt = datetime.fromisoformat(build_ts.replace("Z", "+00:00"))
                # Remove timezone for comparison if present
                if build_dt.tzinfo is not None:
                    build_dt = build_dt.replace(tzinfo=None)
                delta = abs((build_dt - target_dt).total_seconds())
                if delta < 3600 and delta < best_delta:  # Within 1 hour
                    best_match = build
                    best_delta = delta
            except (ValueError, TypeError):
                continue

        return best_match

    except Exception as e:
        log.warning(f"Error searching ledger: {e}")
        return None


def create_entry_from_capture(capture: dict, build_match: Optional[dict] = None) -> ArchiveEntry:
    """
    Create an ArchiveEntry from a historical capture.

    Uses capture.json metadata if available, otherwise derives from directory.
    """
    # Generate entry_id from timestamp (normalize format)
    ts_dt = parse_archive_timestamp(capture["timestamp"])
    if ts_dt:
        entry_id = ts_dt.strftime("%Y%m%d%H%M%S")
    else:
        # Fallback: strip non-alphanumeric
        entry_id = "".join(c for c in capture["timestamp"] if c.isalnum())

    # Try to get ISO timestamp from capture.json
    capture_json = capture.get("capture_json") or {}
    created_at = capture_json.get("timestamp")

    if not created_at and ts_dt:
        created_at = ts_dt.isoformat()
    elif not created_at:
        created_at = datetime.now().isoformat()

    # Extract build info if available
    build_run_id = None
    repo_commits = {}

    if build_match:
        build_run_id = build_match.get("run_id")
        # Get commits from commits_after (post-build state)
        commits_after = build_match.get("commits_after", {})
        for repo, commit in commits_after.items():
            if commit:
                repo_commits[repo] = commit

    # Also check capture.json for commit info
    if capture_json:
        commit = capture_json.get("commit", capture_json.get("git_commit"))
        if commit:
            # Use project name as key if we have a single commit
            project = capture.get("project", "unknown")
            if project not in repo_commits:
                repo_commits[project] = commit

    return ArchiveEntry(
        entry_id=entry_id,
        created_at=created_at,
        project=capture["project"],
        build_run_id=build_run_id,
        screenshots=capture["screenshots"],
        repo_commits=repo_commits,
        notes="[Retroactive migration]",
        tags=["retroactive"],
    )


def retroactive_migration(archive_root: Path, dry_run: bool = False) -> dict:
    """
    Run retroactive migration of historical archives.

    Steps:
    1. Scan archive/{project}/archive/{timestamp}/ directories
    2. Parse capture.json for metadata
    3. Cross-reference with unified_ledger by timestamp
    4. Create ArchiveEntry with best-effort linkage
    5. Save to index (unless dry_run)

    Does NOT sync to iCloud - user can trigger that separately.

    Returns:
    {
        "entries_created": int,
        "entries_skipped": int,  # Already exist
        "errors": list[str],
        "entries": list[ArchiveEntry],  # If dry_run
    }
    """
    result = {
        "entries_created": 0,
        "entries_skipped": 0,
        "errors": [],
        "entries": [],
    }

    # Load or create index
    index_path = archive_root / "archive_index.json"
    if index_path.exists():
        index = ArchiveIndex.load(index_path)
    else:
        index = ArchiveIndex()

    # Scan historical captures
    captures = scan_historical_captures(archive_root)
    log.info(f"Found {len(captures)} historical captures")

    # Unified ledger path
    ledger_path = archive_root / "unified_ledger.json"

    for capture in captures:
        try:
            # Generate entry_id
            ts_dt = parse_archive_timestamp(capture["timestamp"])
            if ts_dt:
                entry_id = ts_dt.strftime("%Y%m%d%H%M%S")
            else:
                entry_id = "".join(c for c in capture["timestamp"] if c.isalnum())

            # Skip if entry already exists
            if entry_id in index.entries:
                result["entries_skipped"] += 1
                continue

            # Try to find matching build
            build_match = find_matching_build(capture["timestamp"], ledger_path)

            # Create entry
            entry = create_entry_from_capture(capture, build_match)

            if dry_run:
                result["entries"].append(entry)
            else:
                index.add_entry(entry)

            result["entries_created"] += 1

        except Exception as e:
            result["errors"].append(f"{capture['timestamp']}: {e}")

    # Save index
    if not dry_run and result["entries_created"] > 0:
        index.save(index_path)
        log.info(f"Saved {result['entries_created']} new entries to index")

    return result
