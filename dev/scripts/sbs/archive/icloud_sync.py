"""Non-blocking iCloud sync for SBS archive data.

Never fails a build on sync errors - all operations log warnings and return False on failure.
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

        # Create the directory structure
        dirs_to_create = [
            ICLOUD_BASE,
            ICLOUD_BASE / "charts",
            ICLOUD_BASE / "chat_summaries",
            ICLOUD_BASE / "entries",
        ]

        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)

        return True

    except OSError as e:
        logger.warning("Failed to create iCloud structure: %s", e)
        return False


def sync_entry(entry: ArchiveEntry, local_base: Path) -> bool:
    """
    Sync a single archive entry to iCloud.

    Steps:
    1. Create entry dir: SBS_archive/entries/{entry_id}/
    2. Write metadata.json with entry.to_dict()
    3. Copy screenshots from local to iCloud
    4. Mark entry.synced_to_icloud = True

    On error: log warning, set entry.sync_error, return False.
    Never raises exceptions - this must not fail builds.
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

        for screenshot in entry.screenshots:
            local_screenshot = local_base / screenshot
            if local_screenshot.exists():
                dest = screenshots_dir / Path(screenshot).name
                shutil.copy2(local_screenshot, dest)

        # Mark as synced
        entry.synced_to_icloud = True
        entry.sync_timestamp = datetime.now().isoformat()
        entry.sync_error = None

        logger.info("Synced entry %s to iCloud", entry.entry_id)
        return True

    except Exception as e:
        error_msg = f"Failed to sync entry {entry.entry_id}: {e}"
        logger.warning(error_msg)
        entry.sync_error = str(e)
        entry.synced_to_icloud = False
        return False


def sync_ledger(local_ledger_path: Path) -> bool:
    """Sync unified_ledger.json to iCloud."""
    try:
        if not ensure_icloud_structure():
            return False

        if not local_ledger_path.exists():
            logger.warning("Local ledger not found: %s", local_ledger_path)
            return False

        dest = ICLOUD_BASE / "unified_ledger.json"
        shutil.copy2(local_ledger_path, dest)

        logger.info("Synced unified_ledger.json to iCloud")
        return True

    except Exception as e:
        logger.warning("Failed to sync ledger: %s", e)
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


def sync_charts(local_charts_dir: Path) -> bool:
    """Sync all charts from archive/charts/ to iCloud."""
    try:
        if not ensure_icloud_structure():
            return False

        if not local_charts_dir.exists():
            logger.warning("Local charts directory not found: %s", local_charts_dir)
            return False

        dest_dir = ICLOUD_BASE / "charts"
        dest_dir.mkdir(exist_ok=True)

        # Copy all chart files
        for chart_file in local_charts_dir.iterdir():
            if chart_file.is_file():
                shutil.copy2(chart_file, dest_dir / chart_file.name)

        logger.info("Synced charts to iCloud")
        return True

    except Exception as e:
        logger.warning("Failed to sync charts: %s", e)
        return False


def sync_project_screenshots(project: str, local_base: Path) -> bool:
    """Sync a project's screenshots (latest/ and archive/) to iCloud."""
    try:
        if not ensure_icloud_structure():
            return False

        local_project_dir = local_base / project
        if not local_project_dir.exists():
            logger.warning("Local project directory not found: %s", local_project_dir)
            return False

        dest_project_dir = ICLOUD_BASE / project
        dest_project_dir.mkdir(exist_ok=True)

        # Sync latest/
        local_latest = local_project_dir / "latest"
        if local_latest.exists():
            dest_latest = dest_project_dir / "latest"
            if dest_latest.exists():
                shutil.rmtree(dest_latest)
            shutil.copytree(local_latest, dest_latest)

        # Sync archive/
        local_archive = local_project_dir / "archive"
        if local_archive.exists():
            dest_archive = dest_project_dir / "archive"
            dest_archive.mkdir(exist_ok=True)

            # Only copy new archive entries (by timestamp directory name)
            for archive_entry in local_archive.iterdir():
                if archive_entry.is_dir():
                    dest_entry = dest_archive / archive_entry.name
                    if not dest_entry.exists():
                        shutil.copytree(archive_entry, dest_entry)

        logger.info("Synced project %s screenshots to iCloud", project)
        return True

    except Exception as e:
        logger.warning("Failed to sync project %s screenshots: %s", project, e)
        return False


def full_sync(local_base: Path, index: ArchiveIndex) -> dict:
    """
    Full sync of all archive data to iCloud.

    Returns dict with:
    {
        "success": bool,
        "synced": ["unified_ledger.json", "archive_index.json", ...],
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

    # Sync unified ledger
    ledger_path = local_base / "stats" / "unified_ledger.json"
    if ledger_path.exists():
        if sync_ledger(ledger_path):
            result["synced"].append("unified_ledger.json")
        else:
            result["failed"].append("unified_ledger.json")
            result["success"] = False

    # Sync archive index
    if sync_index(index):
        result["synced"].append("archive_index.json")
    else:
        result["failed"].append("archive_index.json")
        result["success"] = False

    # Sync charts
    charts_dir = local_base / "archive" / "charts"
    if charts_dir.exists():
        if sync_charts(charts_dir):
            result["synced"].append("charts/")
        else:
            result["failed"].append("charts/")
            result["success"] = False

    # Sync all entries
    for entry_id, entry in index.entries.items():
        if not entry.synced_to_icloud:
            if sync_entry(entry, local_base):
                result["synced"].append(f"entries/{entry_id}/")
            else:
                result["failed"].append(f"entries/{entry_id}/")
                if entry.sync_error:
                    result["errors"].append(f"Entry {entry_id}: {entry.sync_error}")
                result["success"] = False

    # Sync project screenshots
    for project in index.by_project.keys():
        images_dir = local_base.parent / "images"
        if images_dir.exists():
            if sync_project_screenshots(project, images_dir):
                result["synced"].append(f"{project}/")
            else:
                result["failed"].append(f"{project}/")
                result["success"] = False

    return result
