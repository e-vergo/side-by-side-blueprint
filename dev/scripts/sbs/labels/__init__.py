"""
Label taxonomy loader for the SBS project.

Loads the unified taxonomy definition from dev/storage/taxonomy.yaml and
provides utilities for validation, lookup, and enumeration. Supports
context filtering (issues, archive, both) for the unified taxonomy.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml


# =============================================================================
# Repo Root Detection
# =============================================================================


def _find_repo_root() -> Path:
    """Find the repository root by walking up from this file looking for CLAUDE.md."""
    current = Path(__file__).resolve().parent
    for _ in range(10):  # safety bound
        if (current / "CLAUDE.md").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find repo root (no CLAUDE.md found in ancestors)")


TAXONOMY_PATH = _find_repo_root() / "dev" / "storage" / "taxonomy.yaml"


def _taxonomy_path() -> Path:
    """Return the absolute path to taxonomy.yaml."""
    return TAXONOMY_PATH


# =============================================================================
# Taxonomy Loading (cached)
# =============================================================================


@lru_cache(maxsize=1)
def load_taxonomy() -> dict[str, Any]:
    """Load and return the parsed taxonomy dictionary.

    Result is cached for the lifetime of the process.
    """
    path = _taxonomy_path()
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _reset_taxonomy_cache() -> None:
    """Reset the taxonomy cache (for testing)."""
    load_taxonomy.cache_clear()


# =============================================================================
# Context Matching Helpers
# =============================================================================


def _entry_matches_context(entry: dict, context: Optional[str]) -> bool:
    """Check if an entry matches the given context filter.

    Args:
        entry: A taxonomy entry dict with a ``contexts`` field.
        context: One of ``"issues"``, ``"archive"``, or ``None`` (match all).

    Returns:
        True if the entry should be included for the given context.
    """
    if context is None:
        return True
    contexts = entry.get("contexts", [])
    return context in contexts or "both" in contexts


# =============================================================================
# Label Enumeration
# =============================================================================


def get_all_labels(context: Optional[str] = None) -> list[str]:
    """Return a flat list of all entry names across all dimensions and standalone.

    Args:
        context: Optional filter -- ``"issues"`` for GH labels, ``"archive"``
                 for auto-tags, or ``None`` for all entries.

    Returns:
        List of entry name strings.
    """
    taxonomy = load_taxonomy()
    labels: list[str] = []

    # Dimension entries
    dimensions = taxonomy.get("dimensions", {})
    for dim_data in dimensions.values():
        for entry in dim_data.get("entries", []):
            if _entry_matches_context(entry, context):
                labels.append(entry["name"])

    # Standalone entries
    for entry in taxonomy.get("standalone", []):
        if _entry_matches_context(entry, context):
            labels.append(entry["name"])

    return labels


# =============================================================================
# Dimension Lookup
# =============================================================================


def get_dimension_for_label(label_name: str) -> str | None:
    """Return the dimension name for a given label, or None if not found.

    Standalone labels return 'standalone'.
    """
    taxonomy = load_taxonomy()

    # Check dimensions
    dimensions = taxonomy.get("dimensions", {})
    for dim_name, dim_data in dimensions.items():
        for entry in dim_data.get("entries", []):
            if entry["name"] == label_name:
                return dim_name

    # Check standalone
    for entry in taxonomy.get("standalone", []):
        if entry["name"] == label_name:
            return "standalone"

    return None


# =============================================================================
# Validation
# =============================================================================


def validate_labels(labels: list[str]) -> tuple[list[str], list[str]]:
    """Validate a list of label names against the taxonomy.

    Returns:
        Tuple of (valid_labels, invalid_labels).
    """
    all_known = set(get_all_labels())
    valid = [l for l in labels if l in all_known]
    invalid = [l for l in labels if l not in all_known]
    return valid, invalid


# =============================================================================
# Color Lookup
# =============================================================================


def get_label_color(label_name: str) -> str | None:
    """Return the hex color for a label.

    Uses the label-specific color if defined, otherwise falls back to the
    dimension default color. Returns None if label not found.
    """
    taxonomy = load_taxonomy()

    # Check dimensions
    dimensions = taxonomy.get("dimensions", {})
    for dim_data in dimensions.values():
        dim_color = dim_data.get("color")
        for entry in dim_data.get("entries", []):
            if entry["name"] == label_name:
                return entry.get("color", dim_color)

    # Check standalone
    for entry in taxonomy.get("standalone", []):
        if entry["name"] == label_name:
            return entry.get("color")

    return None


# =============================================================================
# Label Detail Lookup
# =============================================================================


def get_label_info(label_name: str) -> dict[str, Any] | None:
    """Return full info dict for a label (name, description, color, dimension).

    Returns None if the label is not found.
    """
    taxonomy = load_taxonomy()

    dimensions = taxonomy.get("dimensions", {})
    for dim_name, dim_data in dimensions.items():
        dim_color = dim_data.get("color")
        for entry in dim_data.get("entries", []):
            if entry["name"] == label_name:
                return {
                    "name": entry["name"],
                    "description": entry.get("description", ""),
                    "color": entry.get("color", dim_color),
                    "dimension": dim_name,
                    "contexts": entry.get("contexts", []),
                }

    for entry in taxonomy.get("standalone", []):
        if entry["name"] == label_name:
            return {
                "name": entry["name"],
                "description": entry.get("description", ""),
                "color": entry.get("color"),
                "dimension": "standalone",
                "contexts": entry.get("contexts", []),
            }

    return None
