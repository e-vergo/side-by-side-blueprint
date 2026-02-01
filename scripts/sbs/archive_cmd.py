"""
Archive management command implementations.
"""

from __future__ import annotations

import argparse
from typing import Optional

from .archive import ArchiveEntry, ArchiveIndex, full_sync, generate_all_charts
from .utils import ARCHIVE_DIR, log


def cmd_archive(args: argparse.Namespace) -> int:
    """Dispatch to archive subcommands."""
    if not hasattr(args, "archive_command") or args.archive_command is None:
        log.error("No archive subcommand specified. Use 'sbs archive --help' for usage.")
        return 1

    if args.archive_command == "tag":
        return cmd_archive_tag(args)
    elif args.archive_command == "note":
        return cmd_archive_note(args)
    elif args.archive_command == "list":
        return cmd_archive_list(args)
    elif args.archive_command == "show":
        return cmd_archive_show(args)
    elif args.archive_command == "charts":
        return cmd_archive_charts(args)
    elif args.archive_command == "sync":
        return cmd_archive_sync(args)
    elif args.archive_command == "retroactive":
        return cmd_archive_retroactive(args)
    else:
        log.error(f"Unknown archive subcommand: {args.archive_command}")
        return 1


def cmd_archive_tag(args: argparse.Namespace) -> int:
    """Add tags to an archive entry."""
    index_path = ARCHIVE_DIR / "archive_index.json"
    if not index_path.exists():
        log.error("No archive index found")
        return 1

    index = ArchiveIndex.load(index_path)
    entry_id = args.entry_id

    if entry_id not in index.entries:
        log.error(f"Entry {entry_id} not found")
        return 1

    entry = index.entries[entry_id]
    tags_added = []

    for tag in args.tags:
        if tag not in entry.tags:
            entry.tags.append(tag)
            tags_added.append(tag)
            # Update by_tag index
            if tag not in index.by_tag:
                index.by_tag[tag] = []
            if entry_id not in index.by_tag[tag]:
                index.by_tag[tag].append(entry_id)

    if tags_added:
        index.save(index_path)
        log.success(f"Added tags {tags_added} to entry {entry_id}")
    else:
        log.info(f"Tags already present on entry {entry_id}")

    return 0


def cmd_archive_note(args: argparse.Namespace) -> int:
    """Add or update note on an archive entry."""
    index_path = ARCHIVE_DIR / "archive_index.json"
    if not index_path.exists():
        log.error("No archive index found")
        return 1

    index = ArchiveIndex.load(index_path)
    entry_id = args.entry_id

    if entry_id not in index.entries:
        log.error(f"Entry {entry_id} not found")
        return 1

    index.entries[entry_id].notes = args.note_text
    index.save(index_path)
    log.success(f"Updated note for entry {entry_id}")

    return 0


def cmd_archive_list(args: argparse.Namespace) -> int:
    """List archive entries."""
    index_path = ARCHIVE_DIR / "archive_index.json"
    if not index_path.exists():
        log.info("No archive index found")
        return 0

    index = ArchiveIndex.load(index_path)

    # Determine which entries to show
    tag: Optional[str] = getattr(args, "tag", None)
    project: Optional[str] = getattr(args, "project", None)

    if tag:
        entry_ids = index.by_tag.get(tag, [])
    elif project:
        entry_ids = index.by_project.get(project, [])
    else:
        entry_ids = list(index.entries.keys())

    if not entry_ids:
        log.info("No entries found")
        return 0

    # Sort by entry_id (timestamp) descending
    entry_ids = sorted(entry_ids, reverse=True)

    log.header("Archive Entries")
    for eid in entry_ids:
        entry = index.entries.get(eid)
        if entry:
            tags_str = f" [{', '.join(entry.tags)}]" if entry.tags else ""
            sync_icon = " [synced]" if entry.synced_to_icloud else ""
            log.info(f"{entry.entry_id} | {entry.project} | {entry.created_at[:19]}{tags_str}{sync_icon}")

    return 0


def cmd_archive_show(args: argparse.Namespace) -> int:
    """Show details of an archive entry."""
    index_path = ARCHIVE_DIR / "archive_index.json"
    if not index_path.exists():
        log.error("No archive index found")
        return 1

    index = ArchiveIndex.load(index_path)
    entry_id = args.entry_id

    if entry_id not in index.entries:
        log.error(f"Entry {entry_id} not found")
        return 1

    entry = index.entries[entry_id]

    log.header(f"Archive Entry: {entry.entry_id}")
    log.info(f"Created:     {entry.created_at}")
    log.info(f"Project:     {entry.project}")
    log.info(f"Build Run:   {entry.build_run_id or 'N/A'}")
    log.info(f"Tags:        {', '.join(entry.tags) if entry.tags else 'None'}")
    log.info(f"Notes:       {entry.notes or 'None'}")
    log.info(f"Screenshots: {len(entry.screenshots)}")
    log.info(f"Synced:      {'Yes' if entry.synced_to_icloud else 'No'}")

    if entry.repo_commits:
        log.info("Commits:")
        for repo, commit in entry.repo_commits.items():
            log.info(f"  {repo}: {commit[:8]}")

    return 0


def cmd_archive_charts(args: argparse.Namespace) -> int:
    """Generate all charts from unified ledger."""
    result = generate_all_charts(ARCHIVE_DIR)

    if result["generated"]:
        log.header("Generated Charts")
        for path in result["generated"]:
            log.success(path)

    if result["failed"]:
        log.header("Failed")
        for f in result["failed"]:
            log.error(f)

    if result["skipped"]:
        log.warning(f"Skipped: {result['skipped']}")

    return 0 if not result["failed"] else 1


def cmd_archive_sync(args: argparse.Namespace) -> int:
    """Sync archive to iCloud."""
    index_path = ARCHIVE_DIR / "archive_index.json"
    if index_path.exists():
        index = ArchiveIndex.load(index_path)
    else:
        index = ArchiveIndex()

    result = full_sync(ARCHIVE_DIR, index)

    if result["success"]:
        log.success("Archive synced to iCloud")
        log.info(f"Synced: {len(result['synced'])} items")
        for item in result["synced"]:
            log.dim(f"  {item}")
    else:
        log.error("Sync partially failed")
        for err in result["errors"]:
            log.error(f"  {err}")

    # Save index with updated sync status
    if index_path.exists() or index.entries:
        index.save(index_path)

    return 0 if result["success"] else 1


def cmd_archive_retroactive(args: argparse.Namespace) -> int:
    """Run retroactive migration of historical archives."""
    from .archive import retroactive_migration

    dry_run = getattr(args, "dry_run", False)

    log.header("Retroactive Migration")
    log.info("Scanning historical captures...")

    result = retroactive_migration(ARCHIVE_DIR, dry_run=dry_run)

    log.info(f"Entries created: {result['entries_created']}")
    log.info(f"Entries skipped: {result['entries_skipped']}")

    if result["errors"]:
        log.header("Errors")
        for err in result["errors"]:
            log.error(err)

    if dry_run and result["entries"]:
        log.header("Dry Run - Entries That Would Be Created")
        for entry in result["entries"]:
            tags_str = f" [{', '.join(entry.tags)}]" if entry.tags else ""
            log.info(f"  {entry.entry_id} | {entry.project} | {entry.created_at[:19]}{tags_str}")

    if result["entries_created"] > 0 and not dry_run:
        log.success(f"Migration complete. Created {result['entries_created']} entries.")
    elif dry_run:
        log.info("Dry run complete. No changes made.")
    else:
        log.info("No new entries to create.")

    return 0 if not result["errors"] else 1
