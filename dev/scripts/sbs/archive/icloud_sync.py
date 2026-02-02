"""Non-blocking iCloud sync for SBS archive data.

Syncs the entire local archive to iCloud for backup.
Never fails a build on sync errors - all operations log warnings and return False on failure.

Local archive: dev/storage/ (referred to as ARCHIVE_DIR)
iCloud backup: ~/Library/Mobile Documents/com~apple~CloudDocs/SBS_archive/
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .entry import ArchiveEntry, ArchiveIndex

logger = logging.getLogger(__name__)

ICLOUD_BASE = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/SBS_archive"

# Files to sync from archive root
ARCHIVE_FILES = [
    "archive_index.json",
    "unified_ledger.json",
    "compliance_ledger.json",
    "baselines.json",
    "migrations.json",
]

# Directories to sync from archive root
ARCHIVE_DIRS = [
    "charts",
    "claude_data",
    "tagging",
]

# Known project directories (screenshots)
PROJECT_DIRS = ["SBSTest", "GCR", "PNT"]


def get_icloud_path() -> Path:
    """Return the iCloud SBS_archive directory."""
    return ICLOUD_BASE


def ensure_icloud_structure() -> bool:
    """
    Create iCloud directory structure if it doesn't exist.
    Returns True if successful, False if iCloud is not available.
    """
    try:
        # Check if iCloud directory exists (parent must exist for iCloud to be available)
        icloud_parent = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs"
        if not icloud_parent.exists():
            logger.warning("iCloud Drive not available at %s", icloud_parent)
            return False

        # Create the base directory
        ICLOUD_BASE.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        for subdir in ["entries", "charts", "claude_data", "tagging"]:
            (ICLOUD_BASE / subdir).mkdir(exist_ok=True)

        return True

    except OSError as e:
        logger.warning("Failed to create iCloud structure: %s", e)
        return False


def sync_file(local_path: Path, dest_path: Path) -> bool:
    """Sync a single file to iCloud."""
    try:
        if not local_path.exists():
            return True  # Not an error if file doesn't exist locally

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dest_path)
        logger.debug("Synced file: %s", local_path.name)
        return True

    except Exception as e:
        logger.warning("Failed to sync file %s: %s", local_path, e)
        return False


def sync_directory(local_dir: Path, dest_dir: Path, incremental: bool = False) -> bool:
    """
    Sync an entire directory to iCloud.

    Args:
        local_dir: Source directory
        dest_dir: Destination directory in iCloud
        incremental: If True, only copy new items (for archive/ directories)
    """
    try:
        if not local_dir.exists():
            return True  # Not an error if directory doesn't exist locally

        dest_dir.mkdir(parents=True, exist_ok=True)

        if incremental:
            # Only copy items that don't exist in destination
            for item in local_dir.iterdir():
                dest_item = dest_dir / item.name
                if not dest_item.exists():
                    if item.is_dir():
                        shutil.copytree(item, dest_item)
                    else:
                        shutil.copy2(item, dest_item)
        else:
            # Full sync - replace destination contents
            for item in local_dir.iterdir():
                dest_item = dest_dir / item.name
                if item.is_dir():
                    if dest_item.exists():
                        shutil.rmtree(dest_item)
                    shutil.copytree(item, dest_item)
                else:
                    shutil.copy2(item, dest_item)

        logger.debug("Synced directory: %s", local_dir.name)
        return True

    except Exception as e:
        logger.warning("Failed to sync directory %s: %s", local_dir, e)
        return False


def sync_entry(entry: ArchiveEntry, local_archive: Path) -> bool:
    """
    Sync a single archive entry to iCloud.

    Creates entries/{entry_id}/ with:
    - metadata.json: Full entry data
    - screenshots/: Any screenshots for this entry
    """
    try:
        if not ensure_icloud_structure():
            entry.sync_error = "iCloud not available"
            return False

        entry_dir = ICLOUD_BASE / "entries" / entry.entry_id
        entry_dir.mkdir(parents=True, exist_ok=True)

        # Write metadata.json
        metadata_path = entry_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(entry.to_dict(), f, indent=2)

        # Copy screenshots if they exist
        screenshots_dir = entry_dir / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)

        project = entry.project or "SBSMonorepo"
        for screenshot in entry.screenshots:
            # Try latest/ first (most common case)
            local_screenshot = local_archive / project / "latest" / screenshot
            if not local_screenshot.exists():
                # Try archive/{entry_id}/ as fallback (for historical entries)
                local_screenshot = local_archive / project / "archive" / entry.entry_id / screenshot
            if local_screenshot.exists():
                dest = screenshots_dir / Path(screenshot).name
                shutil.copy2(local_screenshot, dest)

        # Mark as synced
        entry.synced_to_icloud = True
        entry.sync_timestamp = datetime.now().isoformat()
        entry.sync_error = None

        logger.debug("Synced entry %s to iCloud", entry.entry_id)
        return True

    except Exception as e:
        error_msg = f"Failed to sync entry {entry.entry_id}: {e}"
        logger.warning(error_msg)
        entry.sync_error = str(e)
        entry.synced_to_icloud = False
        return False


def sync_index(index: ArchiveIndex) -> bool:
    """Sync archive_index.json to iCloud."""
    try:
        if not ensure_icloud_structure():
            return False

        dest = ICLOUD_BASE / "archive_index.json"
        with open(dest, "w") as f:
            json.dump(index.to_dict(), f, indent=2)

        logger.info("Synced archive_index.json to iCloud")
        return True

    except Exception as e:
        logger.warning("Failed to sync index: %s", e)
        return False


def sync_project_screenshots(project: str, local_archive: Path) -> bool:
    """Sync a project's screenshots (latest/ and archive/) to iCloud."""
    try:
        if not ensure_icloud_structure():
            return False

        local_project_dir = local_archive / project
        if not local_project_dir.exists():
            logger.debug("Local project directory not found: %s", local_project_dir)
            return True  # Not an error

        dest_project_dir = ICLOUD_BASE / project
        dest_project_dir.mkdir(exist_ok=True)

        # Sync latest/ (full replacement)
        local_latest = local_project_dir / "latest"
        if local_latest.exists():
            dest_latest = dest_project_dir / "latest"
            if dest_latest.exists():
                shutil.rmtree(dest_latest)
            shutil.copytree(local_latest, dest_latest)

        # Sync archive/ (incremental - only new snapshots)
        local_archive_dir = local_project_dir / "archive"
        if local_archive_dir.exists():
            sync_directory(local_archive_dir, dest_project_dir / "archive", incremental=True)

        logger.debug("Synced project %s screenshots to iCloud", project)
        return True

    except Exception as e:
        logger.warning("Failed to sync project %s screenshots: %s", project, e)
        return False


def full_sync(local_archive: Path, index: ArchiveIndex) -> dict:
    """
    Full sync of entire archive to iCloud.

    Syncs:
    - All JSON files (ledgers, baselines, migrations)
    - archive_index.json (from index object)
    - charts/ directory
    - claude_data/ directory (sessions, plans, tool_calls)
    - tagging/ directory (rules, hooks)
    - Project screenshots (SBSTest, GCR, PNT)
    - Individual entry metadata

    Returns dict with:
    {
        "success": bool,
        "synced": ["archive_index.json", "claude_data/", ...],
        "failed": ["charts/", ...],
        "errors": ["iCloud not available", ...]
    }
    """
    result = {
        "success": True,
        "synced": [],
        "failed": [],
        "errors": [],
    }

    # Check iCloud availability first
    if not ensure_icloud_structure():
        result["success"] = False
        result["errors"].append("iCloud not available")
        return result

    # Sync archive index (from object, not file)
    if sync_index(index):
        result["synced"].append("archive_index.json")
    else:
        result["failed"].append("archive_index.json")
        result["success"] = False

    # Sync individual JSON files
    for filename in ARCHIVE_FILES:
        if filename == "archive_index.json":
            continue  # Already synced above
        local_path = local_archive / filename
        dest_path = ICLOUD_BASE / filename
        if local_path.exists():
            if sync_file(local_path, dest_path):
                result["synced"].append(filename)
            else:
                result["failed"].append(filename)
                result["success"] = False

    # Sync directories (charts, claude_data, tagging)
    for dirname in ARCHIVE_DIRS:
        local_dir = local_archive / dirname
        dest_dir = ICLOUD_BASE / dirname
        if local_dir.exists():
            if sync_directory(local_dir, dest_dir):
                result["synced"].append(f"{dirname}/")
            else:
                result["failed"].append(f"{dirname}/")
                result["success"] = False

    # Sync all entries (only unsynced ones)
    for entry_id, entry in index.entries.items():
        if not entry.synced_to_icloud:
            if sync_entry(entry, local_archive):
                result["synced"].append(f"entries/{entry_id}/")
            else:
                result["failed"].append(f"entries/{entry_id}/")
                if entry.sync_error:
                    result["errors"].append(f"Entry {entry_id}: {entry.sync_error}")
                result["success"] = False

    # Sync project screenshots
    # Include both known projects and any found in index
    projects_to_sync = set(PROJECT_DIRS)
    projects_to_sync.update(index.by_project.keys())

    for project in projects_to_sync:
        if sync_project_screenshots(project, local_archive):
            result["synced"].append(f"{project}/")
        else:
            result["failed"].append(f"{project}/")
            result["success"] = False

    logger.info("Full sync complete: %d synced, %d failed",
                len(result["synced"]), len(result["failed"]))
    return result


# Legacy function aliases for backwards compatibility
def sync_ledger(local_ledger_path: Path) -> bool:
    """Sync unified_ledger.json to iCloud."""
    return sync_file(local_ledger_path, ICLOUD_BASE / local_ledger_path.name)


def sync_charts(local_charts_dir: Path) -> bool:
    """Sync charts directory to iCloud."""
    return sync_directory(local_charts_dir, ICLOUD_BASE / "charts")
