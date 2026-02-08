"""SBS-specific utility functions for file paths and hashing.

This module provides:
- SBS monorepo root resolution and path constants
- File hash computation for visual comparison
- Screenshot path utilities
- Zulip screenshot path utilities
- Sidecar claude data loading
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import Optional


def _find_sbs_root() -> Path:
    """Find the SBS monorepo root.

    Resolution order:
    1. SBS_ROOT environment variable
    2. Walk up from this file's location (expected: forks/sls-mcp/src/sls_mcp/)
    3. Walk up from current working directory

    Returns:
        Path to SBS monorepo root.

    Raises:
        RuntimeError: If SBS root cannot be found.
    """
    # 1. Check environment variable
    env_root = os.environ.get("SBS_ROOT")
    if env_root:
        path = Path(env_root).resolve()
        if (path / "dev" / "scripts" / "sbs").is_dir():
            return path

    # 2. Walk up from this file's location
    # This file is at: SLS_ROOT/forks/sls-mcp/src/sls_mcp/sls_utils.py
    current = Path(__file__).resolve()
    for _ in range(10):  # Max 10 levels up
        if (current / "dev" / "scripts" / "sbs").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent

    # 3. Walk up from CWD
    current = Path.cwd().resolve()
    for _ in range(10):
        if (current / "dev" / "scripts" / "sbs").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent

    raise RuntimeError(
        "Cannot find SBS monorepo root. Set SBS_ROOT environment variable or "
        "run from within the Side-By-Side-Blueprint repository."
    )


# Find SBS root and add scripts to path
_SBS_ROOT = _find_sbs_root()
_SBS_SCRIPTS = _SBS_ROOT / "dev" / "scripts"
if str(_SBS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SBS_SCRIPTS))

# Now we can import SBS modules
from sbs.core.utils import ARCHIVE_DIR as _ARCHIVE_DIR

# Re-export for convenience
SBS_ROOT = _SBS_ROOT
ARCHIVE_DIR = _ARCHIVE_DIR  # Re-export from sbs.core.utils
ZULIP_ARCHIVE_DIR = ARCHIVE_DIR / "zulip"


# =============================================================================
# Archive Data Directory
# =============================================================================


def get_archive_dir() -> Path:
    """Get the archive directory path."""
    return ARCHIVE_DIR


ARCHIVE_DATA_DIR = ARCHIVE_DIR / "archive_data"


# =============================================================================
# Sidecar Claude Data Loading
# =============================================================================


def load_entry_claude_data(entry_id: str) -> Optional[dict]:
    """Load claude_data from a sidecar file for the given entry.

    Sidecar files live at ``ARCHIVE_DIR/archive_data/<entry_id>.json``.

    Args:
        entry_id: The archive entry ID (unix timestamp string).

    Returns:
        The claude_data dict, or None if the sidecar file doesn't exist.
    """
    import json as _json

    path = ARCHIVE_DATA_DIR / f"{entry_id}.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return _json.load(f)
    except Exception:
        return None


# =============================================================================
# Filename Utilities
# =============================================================================


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as filename.

    Replaces non-alphanumeric characters with underscores, truncates to 100 chars.
    """
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:100]


# =============================================================================
# Zulip Screenshot Utilities
# =============================================================================


def get_zulip_screenshot_path(stream: str, topic: str, latest: bool = True) -> Path:
    """Get path for a Zulip thread screenshot.

    Args:
        stream: Zulip stream name
        topic: Zulip topic name
        latest: If True, return path in latest/; otherwise archive/

    Returns:
        Path to screenshot file
    """
    safe_name = sanitize_filename(f"thread_{stream}_{topic}")
    if latest:
        return ZULIP_ARCHIVE_DIR / "latest" / f"{safe_name}.png"
    return ZULIP_ARCHIVE_DIR / "archive" / f"{safe_name}.png"


# =============================================================================
# Screenshot Utilities
# =============================================================================


def get_screenshot_path(project: str, page: str) -> Path:
    """Get path to latest screenshot for a page.

    Args:
        project: Project name (e.g., 'SBSTest').
        page: Page name (e.g., 'dashboard', 'dep_graph').

    Returns:
        Path to the screenshot file (may not exist).
    """
    return ARCHIVE_DIR / project / "latest" / f"{page}.png"


def get_archived_screenshot(project: str, entry_id: str, page: str) -> Path:
    """Get path to an archived screenshot.

    Args:
        project: Project name.
        entry_id: Archive entry ID (unix timestamp).
        page: Page name.

    Returns:
        Path to the archived screenshot (may not exist).
    """
    return ARCHIVE_DIR / project / entry_id / f"{page}.png"


def compute_hash(path: Path) -> Optional[str]:
    """Compute SHA256 hash prefix of a file.

    Args:
        path: Path to file.

    Returns:
        First 16 characters of SHA256 hash, or None if file doesn't exist.
    """
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
