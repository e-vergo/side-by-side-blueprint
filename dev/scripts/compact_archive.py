#!/usr/bin/env python3
"""
One-time migration: extract claude_data from archive_index.json into per-entry sidecar files.

Reads the archive index, writes each entry's claude_data to:
    dev/storage/archive_data/<entry_id>.json

Then removes claude_data from the index and re-saves it.

Usage:
    python3 compact_archive.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Bootstrap: add scripts dir to path so we can import sbs modules
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from sbs.core.utils import ARCHIVE_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description="Compact archive_index.json by extracting claude_data to sidecars")
    parser.add_argument("--dry-run", action="store_true", help="Print stats without writing")
    args = parser.parse_args()

    index_path = ARCHIVE_DIR / "archive_index.json"
    sidecar_dir = ARCHIVE_DIR / "archive_data"

    if not index_path.exists():
        print(f"ERROR: Archive index not found at {index_path}")
        return 1

    # Measure before size
    before_size = index_path.stat().st_size
    print(f"Before: {index_path} is {before_size / 1_000_000:.1f} MB")

    # Load raw JSON (not via ArchiveIndex, to preserve all data exactly)
    with open(index_path) as f:
        data = json.load(f)

    entries = data.get("entries", {})
    total = len(entries)
    extracted = 0
    skipped = 0
    sidecar_bytes = 0

    if not args.dry_run:
        sidecar_dir.mkdir(parents=True, exist_ok=True)

    for entry_id, entry_data in entries.items():
        claude_data = entry_data.get("claude_data")
        if claude_data is None:
            skipped += 1
            continue

        sidecar_path = sidecar_dir / f"{entry_id}.json"

        if args.dry_run:
            sidecar_content = json.dumps(claude_data, indent=2)
            sidecar_bytes += len(sidecar_content.encode())
        else:
            sidecar_content = json.dumps(claude_data, indent=2)
            sidecar_bytes += len(sidecar_content.encode())
            with open(sidecar_path, "w") as f:
                f.write(sidecar_content)

        # Remove claude_data from the index entry
        entry_data.pop("claude_data", None)
        extracted += 1

    print(f"\nEntries total:     {total}")
    print(f"  with claude_data:  {extracted}")
    print(f"  without:           {skipped}")
    print(f"Sidecar data:      {sidecar_bytes / 1_000_000:.1f} MB across {extracted} files")

    if args.dry_run:
        # Estimate compacted size
        compacted = json.dumps(data, indent=2).encode()
        print(f"\nEstimated after:   {len(compacted) / 1_000_000:.1f} MB")
        print("\n[DRY RUN] No files written.")
        return 0

    # Write compacted index
    with open(index_path, "w") as f:
        json.dump(data, f, indent=2)

    after_size = index_path.stat().st_size
    print(f"\nAfter:  {index_path} is {after_size / 1_000_000:.1f} MB")
    print(f"Saved:  {(before_size - after_size) / 1_000_000:.1f} MB ({100 * (1 - after_size / before_size):.1f}% reduction)")
    print(f"Sidecars written to: {sidecar_dir}/")

    return 0


if __name__ == "__main__":
    sys.exit(main())
