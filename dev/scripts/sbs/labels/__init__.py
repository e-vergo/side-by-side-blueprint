"""
Label taxonomy loader for the SBS project.

Loads the taxonomy definition from dev/storage/labels/taxonomy.yaml and
provides utilities for validation, lookup, and enumeration.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

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


def _taxonomy_path() -> Path:
    """Return the absolute path to taxonomy.yaml."""
    return _find_repo_root() / "dev" / "storage" / "labels" / "taxonomy.yaml"


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


# =============================================================================
# Label Enumeration
# =============================================================================


def get_all_labels() -> list[str]:
    """Return a flat list of all label names across all dimensions and standalone."""
    taxonomy = load_taxonomy()
    labels: list[str] = []

    # Dimension labels
    dimensions = taxonomy.get("dimensions", {})
    for dim_data in dimensions.values():
        for label in dim_data.get("labels", []):
            labels.append(label["name"])

    # Standalone labels
    for label in taxonomy.get("standalone", []):
        labels.append(label["name"])

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
        for label in dim_data.get("labels", []):
            if label["name"] == label_name:
                return dim_name

    # Check standalone
    for label in taxonomy.get("standalone", []):
        if label["name"] == label_name:
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
        for label in dim_data.get("labels", []):
            if label["name"] == label_name:
                return label.get("color", dim_color)

    # Check standalone
    for label in taxonomy.get("standalone", []):
        if label["name"] == label_name:
            return label.get("color")

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
        for label in dim_data.get("labels", []):
            if label["name"] == label_name:
                return {
                    "name": label["name"],
                    "description": label.get("description", ""),
                    "color": label.get("color", dim_color),
                    "dimension": dim_name,
                }

    for label in taxonomy.get("standalone", []):
        if label["name"] == label_name:
            return {
                "name": label["name"],
                "description": label.get("description", ""),
                "color": label.get("color"),
                "dimension": "standalone",
            }

    return None
