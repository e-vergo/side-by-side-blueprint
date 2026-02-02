"""SBS-specific utility functions for archive and oracle integration.

This module provides integration with the SBS Python modules for:
- Loading and querying the archive index
- Loading and parsing the oracle markdown
- Computing file hashes for visual comparison
- Epoch and entry summarization utilities
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional


def _find_sbs_root() -> Path:
    """Find the SBS monorepo root.

    Resolution order:
    1. SBS_ROOT environment variable
    2. Walk up from this file's location (expected: forks/sbs-lsp-mcp/src/sbs_lsp_mcp/)
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
    # This file is at: SBS_ROOT/forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_utils.py
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
from sbs.archive.entry import ArchiveEntry, ArchiveIndex
from sbs.core.utils import ARCHIVE_DIR as _ARCHIVE_DIR

if TYPE_CHECKING:
    pass

# Re-export for convenience
SBS_ROOT = _SBS_ROOT
ARCHIVE_DIR = _ARCHIVE_DIR  # Re-export from sbs.core.utils
ZULIP_ARCHIVE_DIR = ARCHIVE_DIR / "zulip"


# =============================================================================
# Archive Loading
# =============================================================================


def load_archive_index() -> ArchiveIndex:
    """Load the archive index from disk.

    Returns:
        The loaded ArchiveIndex, or an empty index if file doesn't exist.
    """
    return ArchiveIndex.load(ARCHIVE_DIR / "archive_index.json")


def get_archive_dir() -> Path:
    """Get the archive directory path."""
    return ARCHIVE_DIR


# =============================================================================
# Oracle Loading and Parsing
# =============================================================================


def load_oracle_content() -> str:
    """Load the compiled oracle markdown content.

    Returns:
        The oracle markdown content, or empty string if not found.
    """
    oracle_path = SBS_ROOT / ".claude" / "agents" / "sbs-oracle.md"
    if oracle_path.exists():
        return oracle_path.read_text()
    return ""


def parse_oracle_sections(content: str) -> Dict[str, Any]:
    """Parse oracle markdown into searchable sections.

    Args:
        content: The raw oracle markdown content.

    Returns:
        Dictionary with:
        - file_map: {path: {section: str, notes: str}} mapping files to their sections
        - concept_index: [{name: str, location: str, notes: str, section: str}] list of concepts
        - sections: {section_name: content} mapping section names to content
        - raw_content: The original content
    """
    sections: Dict[str, Any] = {
        "file_map": {},
        "concept_index": [],
        "sections": {},
        "raw_content": content,
    }

    current_section: Optional[str] = None
    current_content: List[str] = []
    in_table = False

    for line in content.split("\n"):
        # Track section headers
        if line.startswith("## "):
            # Save previous section
            if current_section:
                sections["sections"][current_section] = "\n".join(current_content)

            current_section = line[3:].strip()
            current_content = []
            in_table = False
            continue

        if current_section:
            current_content.append(line)

        # Parse markdown table rows (format: | col1 | col2 | col3 |)
        if line.startswith("|") and current_section:
            # Skip header separator rows (|---|---|---|)
            if "---" in line:
                in_table = True
                continue

            # Skip header rows (first row after section start)
            if not in_table and "Concept" in line or "Primary Location" in line:
                in_table = True
                continue

            # Parse data rows
            parts = [p.strip() for p in line.split("|")]
            # Remove empty first/last elements from leading/trailing |
            parts = [p for p in parts if p]

            if len(parts) >= 2:
                concept_name = parts[0].strip("`").strip()
                location = parts[1].strip("`").strip() if len(parts) > 1 else ""
                notes = parts[2].strip() if len(parts) > 2 else ""

                # Check if location looks like a file path
                if "/" in location or location.endswith(".lean") or location.endswith(".py") or location.endswith(".md"):
                    sections["file_map"][location] = {
                        "section": current_section,
                        "concept": concept_name,
                        "notes": notes,
                    }

                # Also add to concept index
                sections["concept_index"].append({
                    "name": concept_name,
                    "location": location,
                    "notes": notes,
                    "section": current_section,
                })

        # Also extract file paths and concepts from list items (fallback)
        elif line.startswith("- ") and current_section:
            item = line[2:].strip()
            # Check if it looks like a file path
            if "/" in item or item.endswith(".lean") or item.endswith(".py"):
                # Extract just the path part (before any description)
                path = item.split(" - ")[0].strip().strip("`")
                sections["file_map"][path] = {"section": current_section}
            else:
                # Treat as a concept
                sections["concept_index"].append(
                    {"name": item, "section": current_section}
                )

    # Save final section
    if current_section:
        sections["sections"][current_section] = "\n".join(current_content)

    return sections


def search_oracle(
    sections: Dict[str, Any], query: str, max_results: int = 10
) -> List[Dict[str, Any]]:
    """Search the parsed oracle for matches.

    Args:
        sections: Parsed oracle sections from parse_oracle_sections().
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        List of matches with file, context, and relevance score.
    """
    query_lower = query.lower()
    query_words = query_lower.split()
    results: List[Dict[str, Any]] = []
    seen_files: set = set()  # Deduplicate file results

    # Search in file map (direct path match)
    for path, info in sections["file_map"].items():
        if query_lower in path.lower():
            if path not in seen_files:
                seen_files.add(path)
                concept = info.get("concept", "")
                notes = info.get("notes", "")
                context = f"Found in section: {info['section']}"
                if concept:
                    context = f"{concept} -> {context}"
                if notes:
                    context += f" ({notes})"
                results.append(
                    {
                        "file": path,
                        "lines": None,
                        "context": context,
                        "relevance": 1.0 if query_lower == path.lower() else 0.7,
                    }
                )

    # Search in concepts (table rows from oracle)
    for concept in sections["concept_index"]:
        name = concept.get("name", "").lower()
        location = concept.get("location", "")
        notes = concept.get("notes", "").lower()
        section = concept.get("section", "")

        # Check if query matches concept name, notes, or location
        relevance = 0.0
        if query_lower in name:
            relevance = 0.9 if query_lower == name else 0.8
        elif any(word in name for word in query_words):
            relevance = 0.7
        elif query_lower in notes:
            relevance = 0.6
        elif any(word in notes for word in query_words):
            relevance = 0.5

        if relevance > 0:
            # If location is a file path, add as file match
            if location and ("/" in location or location.endswith((".lean", ".py", ".md"))):
                if location not in seen_files:
                    seen_files.add(location)
                    results.append(
                        {
                            "file": location,
                            "lines": None,
                            "context": f"Concept '{concept.get('name', '')}' in {section}" + (f" ({notes})" if notes else ""),
                            "relevance": relevance,
                        }
                    )
            else:
                # Add as concept match
                results.append(
                    {
                        "file": "",
                        "lines": None,
                        "context": f"Concept '{concept.get('name', '')}' at '{location}' in section: {section}",
                        "relevance": relevance,
                    }
                )

    # Search in section content (fallback for things not in tables)
    for section_name, section_content in sections.get("sections", {}).items():
        if query_lower in section_content.lower():
            # Find the line with the match
            for i, line in enumerate(section_content.split("\n")):
                if query_lower in line.lower():
                    # Skip table rows (already handled above)
                    if line.strip().startswith("|"):
                        continue
                    results.append(
                        {
                            "file": "",
                            "lines": None,
                            "context": f"In section '{section_name}': {line[:100]}...",
                            "relevance": 0.4,
                        }
                    )
                    break

    # Sort by relevance and limit
    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results[:max_results]


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


# =============================================================================
# Entry/Epoch Utilities
# =============================================================================


def get_entry_timestamp(index: ArchiveIndex, entry_id: Optional[str]) -> Optional[str]:
    """Get ISO timestamp for an entry ID.

    Args:
        index: The archive index.
        entry_id: Entry ID to look up.

    Returns:
        ISO timestamp string, or None if entry not found.
    """
    if not entry_id or entry_id not in index.entries:
        return None
    return index.entries[entry_id].created_at


def get_epoch_entries(
    index: ArchiveIndex, epoch_entry_id: Optional[str] = None
) -> List[ArchiveEntry]:
    """Get all entries in an epoch.

    An epoch is the period between skill-triggered entries.

    Args:
        index: The archive index.
        epoch_entry_id: Entry ID that closes the epoch. If None, returns
            entries in the current (open) epoch.

    Returns:
        List of entries in the epoch, sorted by entry ID.
    """
    sorted_ids = sorted(index.entries.keys())

    if epoch_entry_id is None:
        # Current epoch: entries since last_epoch_entry
        start_id = index.last_epoch_entry or "0"
        return [
            index.entries[eid]
            for eid in sorted_ids
            if eid > start_id
        ]
    else:
        # Find the previous epoch boundary (skill-triggered entry before this one)
        try:
            epoch_idx = sorted_ids.index(epoch_entry_id)
        except ValueError:
            return []

        # Find previous skill-triggered entry
        start_id = "0"
        for i in range(epoch_idx - 1, -1, -1):
            entry = index.entries[sorted_ids[i]]
            if entry.trigger == "skill":
                start_id = sorted_ids[i]
                break

        return [
            index.entries[eid]
            for eid in sorted_ids
            if eid > start_id and eid <= epoch_entry_id
        ]


def aggregate_visual_changes(entries: List[ArchiveEntry]) -> List[Dict[str, Any]]:
    """Aggregate visual changes across entries.

    Args:
        entries: List of archive entries.

    Returns:
        List of visual change records with entry_id, screenshots, timestamp.
    """
    changes: List[Dict[str, Any]] = []
    for entry in entries:
        if entry.screenshots:
            changes.append(
                {
                    "entry_id": entry.entry_id,
                    "screenshots": entry.screenshots,
                    "timestamp": entry.created_at,
                }
            )
    return changes


def collect_tags(entries: List[ArchiveEntry]) -> List[str]:
    """Collect all unique tags from entries.

    Args:
        entries: List of archive entries.

    Returns:
        Sorted list of unique tags (manual + auto).
    """
    tags = set()
    for entry in entries:
        tags.update(entry.tags)
        tags.update(entry.auto_tags)
    return sorted(tags)


def collect_projects(entries: List[ArchiveEntry]) -> List[str]:
    """Collect all unique projects from entries.

    Args:
        entries: List of archive entries.

    Returns:
        Sorted list of unique project names.
    """
    return sorted(set(entry.project for entry in entries))


def count_builds(entries: List[ArchiveEntry]) -> int:
    """Count build-triggered entries.

    Args:
        entries: List of archive entries.

    Returns:
        Number of entries with trigger == 'build'.
    """
    return sum(1 for entry in entries if entry.trigger == "build")


def summarize_entry(entry: ArchiveEntry) -> Dict[str, Any]:
    """Create a summary dict from an archive entry.

    Args:
        entry: The archive entry to summarize.

    Returns:
        Dictionary with key fields suitable for search results.
    """
    return {
        "entry_id": entry.entry_id,
        "created_at": entry.created_at,
        "project": entry.project,
        "trigger": entry.trigger,
        "tags": entry.tags + entry.auto_tags,
        "has_screenshots": len(entry.screenshots) > 0,
        "notes_preview": entry.notes[:100] if entry.notes else "",
        "build_run_id": entry.build_run_id,
    }


def format_time_range(entries: List[ArchiveEntry]) -> Optional[str]:
    """Format the time range covered by entries.

    Args:
        entries: List of archive entries.

    Returns:
        Human-readable time range (e.g., '2h 30m'), or None if < 2 entries.
    """
    if len(entries) < 2:
        return None

    try:
        # Parse ISO timestamps
        first = datetime.fromisoformat(entries[0].created_at.replace("Z", "+00:00"))
        last = datetime.fromisoformat(entries[-1].created_at.replace("Z", "+00:00"))
        delta = last - first

        total_seconds = int(delta.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except (ValueError, IndexError):
        return None


# =============================================================================
# Context Generation
# =============================================================================


def generate_context_block(
    entries: List[ArchiveEntry], max_entries: int = 10
) -> str:
    """Generate a context block summarizing recent entries.

    Args:
        entries: List of entries to summarize (most recent first).
        max_entries: Maximum entries to include.

    Returns:
        Formatted markdown context block.
    """
    if not entries:
        return "No archive entries found."

    recent = entries[:max_entries]
    lines = ["## Recent Archive Activity", ""]

    for entry in recent:
        tags_str = ", ".join(entry.tags + entry.auto_tags) or "none"
        lines.append(f"- **{entry.entry_id}** ({entry.trigger}): {entry.project}")
        if entry.notes:
            lines.append(f"  Notes: {entry.notes[:80]}...")
        lines.append(f"  Tags: {tags_str}")
        lines.append("")

    return "\n".join(lines)
