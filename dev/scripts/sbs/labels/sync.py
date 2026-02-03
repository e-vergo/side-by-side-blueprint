"""
GitHub label sync: reconcile taxonomy.yaml with actual GitHub labels.

Reads the taxonomy, compares against existing labels via `gh label list`,
and creates/updates labels to match. Supports --dry-run and --repo flags.
"""

from __future__ import annotations

import json
import subprocess
import time
from typing import Any

from sbs.core.utils import log
from sbs.labels import get_all_labels, get_label_info, load_taxonomy


# =============================================================================
# GitHub Label Operations
# =============================================================================

DEFAULT_REPO = "e-vergo/Side-By-Side-Blueprint"
API_DELAY_SECONDS = 0.5


def _normalize_color(color: str) -> str:
    """Normalize a hex color to lowercase without '#' prefix."""
    return color.lstrip("#").lower()


def _fetch_existing_labels(repo: str) -> dict[str, dict[str, str]]:
    """Fetch all existing labels from GitHub.

    Returns dict mapping label name -> {"color": "hex", "description": "..."}.
    """
    result = subprocess.run(
        [
            "gh", "label", "list",
            "--repo", repo,
            "--json", "name,color,description",
            "--limit", "200",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    labels_json = json.loads(result.stdout)
    return {
        label["name"]: {
            "color": _normalize_color(label.get("color", "")),
            "description": label.get("description", ""),
        }
        for label in labels_json
    }


def _create_label(
    name: str,
    color: str,
    description: str,
    repo: str,
    dry_run: bool,
) -> None:
    """Create a new GitHub label."""
    hex_color = _normalize_color(color)
    if dry_run:
        log.info(f"  [DRY RUN] Would create: {name} (#{hex_color})")
        return

    subprocess.run(
        [
            "gh", "label", "create", name,
            "--repo", repo,
            "--color", hex_color,
            "--description", description,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    time.sleep(API_DELAY_SECONDS)


def _update_label(
    name: str,
    color: str,
    description: str,
    repo: str,
    dry_run: bool,
) -> None:
    """Update an existing GitHub label."""
    hex_color = _normalize_color(color)
    if dry_run:
        log.info(f"  [DRY RUN] Would update: {name} (#{hex_color})")
        return

    subprocess.run(
        [
            "gh", "label", "edit", name,
            "--repo", repo,
            "--color", hex_color,
            "--description", description,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    time.sleep(API_DELAY_SECONDS)


# =============================================================================
# Sync Logic
# =============================================================================


def sync_labels(
    repo: str = DEFAULT_REPO,
    dry_run: bool = False,
) -> dict[str, int]:
    """Sync taxonomy labels to GitHub.

    Returns summary dict with counts: {"created": N, "updated": N, "skipped": N}.
    """
    log.header(f"Syncing labels to {repo}")

    if dry_run:
        log.info("[DRY RUN MODE]")
        log.info("")

    # Fetch existing labels
    log.info("Fetching existing labels from GitHub...")
    existing = _fetch_existing_labels(repo)
    log.info(f"Found {len(existing)} existing labels")
    log.info("")

    # Build target label list from taxonomy
    all_label_names = get_all_labels()
    summary = {"created": 0, "updated": 0, "skipped": 0}

    for label_name in all_label_names:
        info = get_label_info(label_name)
        if info is None:
            continue

        color = info.get("color") or ""
        description = info.get("description") or ""

        if not color:
            log.warning(f"  Skipping {label_name}: no color defined")
            summary["skipped"] += 1
            continue

        normalized_target_color = _normalize_color(color)

        if label_name in existing:
            existing_entry = existing[label_name]
            existing_color = existing_entry["color"]
            existing_desc = existing_entry["description"]

            if (
                existing_color == normalized_target_color
                and existing_desc == description
            ):
                summary["skipped"] += 1
            else:
                reasons = []
                if existing_color != normalized_target_color:
                    reasons.append(f"color: #{existing_color} -> #{normalized_target_color}")
                if existing_desc != description:
                    reasons.append("description changed")
                log.info(f"  Updating: {label_name} ({', '.join(reasons)})")
                _update_label(label_name, color, description, repo, dry_run)
                summary["updated"] += 1
        else:
            log.info(f"  Creating: {label_name} (#{normalized_target_color})")
            _create_label(label_name, color, description, repo, dry_run)
            summary["created"] += 1

    # Report
    log.info("")
    log.header("Sync Summary")
    log.info(f"  Created: {summary['created']}")
    log.info(f"  Updated: {summary['updated']}")
    log.info(f"  Skipped: {summary['skipped']} (already correct)")
    log.info(f"  Total:   {sum(summary.values())}")

    return summary


# =============================================================================
# Tree Renderer
# =============================================================================


def render_taxonomy_tree() -> str:
    """Render the taxonomy as a formatted tree string grouped by dimension."""
    taxonomy = load_taxonomy()
    lines: list[str] = []
    total = 0

    dimensions = taxonomy.get("dimensions", {})
    for dim_name, dim_data in dimensions.items():
        labels = dim_data.get("labels", [])
        dim_desc = dim_data.get("description", "")
        dim_color = dim_data.get("color", "")
        lines.append(f"{dim_name} ({dim_desc})")

        for i, label in enumerate(labels):
            is_last = i == len(labels) - 1
            prefix = "  +-- " if is_last else "  |-- "
            color = label.get("color", dim_color)
            lines.append(f"{prefix}{label['name']}  [{color}]")
            total += 1

        lines.append("")

    # Standalone
    standalone = taxonomy.get("standalone", [])
    if standalone:
        lines.append("standalone")
        for i, label in enumerate(standalone):
            is_last = i == len(standalone) - 1
            prefix = "  +-- " if is_last else "  |-- "
            color = label.get("color", "")
            lines.append(f"{prefix}{label['name']}  [{color}]")
            total += 1
        lines.append("")

    lines.append(f"Total: {total} labels across {len(dimensions)} dimensions + standalone")
    return "\n".join(lines)
