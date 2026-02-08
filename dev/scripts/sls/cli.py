"""
Main CLI for the sls tool.

Provides a unified interface for all Strange Loop Station orchestration commands.
"""

from __future__ import annotations

import argparse
import sys

from sbs_core.utils import log


# =============================================================================
# Version
# =============================================================================

__version__ = "0.1.0"


# =============================================================================
# Argument Parsing
# =============================================================================


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with all subcommands."""

    # Main parser
    parser = argparse.ArgumentParser(
        prog="sls",
        description="Strange Loop Station orchestration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  archive      Archive management commands
  labels       Label taxonomy management
  readme-check Check which READMEs may need updating
  test-catalog List all testable components (MCP tools, tests, CLI commands)
  watch        Watch for changes and incrementally regenerate site
  dev          Dev server with HTTP serving and live reload
  clean        Remove build artifacts and caches

Examples:
  sls archive list                        # List all entries
  sls archive upload --dry-run            # Preview upload
  sls labels list                         # Show label taxonomy tree
  sls labels sync --dry-run               # Preview GitHub label sync
  sls readme-check                        # Check which READMEs may need updating
  sls test-catalog                        # List testable components
  sls watch --project SBSTest             # Watch for changes and regenerate
  sls dev --project SBSTest               # Dev server with live reload
  sls clean --project SBSTest             # Clean build artifacts for SBSTest
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    # Subparsers
    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        metavar="<command>",
    )

    # --- archive (command group) ---
    archive_parser = subparsers.add_parser(
        "archive",
        help="Archive management commands",
        description="Manage archive entries, tags, notes, and sync to iCloud.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Subcommands:
  tag          Add tags to an archive entry
  note         Add or update note on an archive entry
  list         List archive entries
  show         Show details of an archive entry
  charts       Generate all charts from unified ledger
  sync         Sync archive to iCloud
  retroactive  Migrate historical archives to entry system
  upload       Extract Claude data and upload to archive

Examples:
  sls archive list                        # List all entries
  sls archive list --project SBSTest      # List entries for project
  sls archive tag 1738340279 release v1   # Add tags to entry
  sls archive note 1738340279 "Baseline"  # Add note to entry
  sls archive show 1738340279             # Show entry details
  sls archive charts                      # Generate charts
  sls archive sync                        # Sync to iCloud
  sls archive retroactive --dry-run       # Preview migration
  sls archive upload --dry-run            # Preview upload
        """,
    )
    archive_subparsers = archive_parser.add_subparsers(
        dest="archive_command",
        title="archive commands",
        metavar="<subcommand>",
    )

    # --- archive tag ---
    archive_tag_parser = archive_subparsers.add_parser(
        "tag",
        help="Add tags to an archive entry",
        description="Add one or more tags to an existing archive entry.",
    )
    archive_tag_parser.add_argument(
        "entry_id",
        help="Archive entry ID (Unix timestamp)",
    )
    archive_tag_parser.add_argument(
        "tags",
        nargs="+",
        help="Tags to add",
    )

    # --- archive note ---
    archive_note_parser = archive_subparsers.add_parser(
        "note",
        help="Add or update note on an archive entry",
        description="Set the note field on an existing archive entry.",
    )
    archive_note_parser.add_argument(
        "entry_id",
        help="Archive entry ID (Unix timestamp)",
    )
    archive_note_parser.add_argument(
        "note_text",
        help="Note text to set",
    )

    # --- archive list ---
    archive_list_parser = archive_subparsers.add_parser(
        "list",
        help="List archive entries",
        description="List archive entries with optional filtering.",
    )
    archive_list_parser.add_argument(
        "--project", "-p",
        help="Filter by project name",
    )
    archive_list_parser.add_argument(
        "--tag", "-t",
        help="Filter by tag",
    )

    # --- archive show ---
    archive_show_parser = archive_subparsers.add_parser(
        "show",
        help="Show details of an archive entry",
        description="Display detailed information about an archive entry.",
    )
    archive_show_parser.add_argument(
        "entry_id",
        help="Archive entry ID (Unix timestamp)",
    )

    # --- archive charts ---
    archive_subparsers.add_parser(
        "charts",
        help="Generate all charts from unified ledger",
        description="Generate LOC trends, timing breakdown, and activity heatmap charts.",
    )

    # --- archive sync ---
    archive_subparsers.add_parser(
        "sync",
        help="Sync archive to iCloud",
        description="Sync archive index, charts, and unsynced entries to iCloud.",
    )

    # --- archive retroactive ---
    archive_retroactive_parser = archive_subparsers.add_parser(
        "retroactive",
        help="Migrate historical archives to entry system",
        description="Scan existing archive directories and create ArchiveEntry records.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scans archive/{project}/archive/{timestamp}/ directories and creates
ArchiveEntry records with best-effort metadata linkage from unified_ledger.

Examples:
  sls archive retroactive            # Run migration
  sls archive retroactive --dry-run  # Preview without making changes
        """,
    )
    archive_retroactive_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )

    # --- archive upload ---
    archive_upload_parser = archive_subparsers.add_parser(
        "upload",
        help="Extract Claude data and upload to archive",
        description="Extract Claude Code session data, create archive entry, run auto-tagging, sync to iCloud, and ensure porcelain git state.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Extracts all SBS-related data from ~/.claude and creates an archive entry:
1. Parses session JSONL files and extracts tool calls
2. Copies plan files
3. Runs auto-tagging rules and hooks
4. Syncs to iCloud
5. Commits and pushes all repos (porcelain guarantee)

Examples:
  sls archive upload                    # Full upload
  sls archive upload --dry-run          # Preview without making changes
  sls archive upload --project SBSTest  # Associate with specific project
  sls archive upload --trigger build    # Mark as build-triggered
  sls archive upload --validate         # Upload with validator run
        """,
    )
    archive_upload_parser.add_argument(
        "--project",
        help="Associate with specific project",
    )
    archive_upload_parser.add_argument(
        "--trigger",
        default="manual",
        choices=["build", "manual", "skill"],
        help="Upload trigger type (default: manual)",
    )
    archive_upload_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    archive_upload_parser.add_argument(
        "--global-state",
        help='JSON object for orchestration state, e.g. \'{"skill": "task", "substate": "execution"}\'',
    )
    archive_upload_parser.add_argument(
        "--state-transition",
        choices=["phase_start", "phase_end", "handoff"],
        help="State transition type (phase_start, phase_end, or handoff)",
    )
    archive_upload_parser.add_argument(
        "--handoff-to",
        help='JSON object for incoming skill state during handoff, e.g. \'{"skill": "update-and-archive", "substate": "readme-wave"}\'',
    )
    archive_upload_parser.add_argument(
        "--issue-refs",
        type=str,
        help="Comma-separated list of GitHub issue numbers to link (e.g., '42,57')",
    )
    archive_upload_parser.add_argument(
        "--pr-number",
        type=str,
        help="Comma-separated list of PR numbers to link (e.g., '42,57')",
    )
    archive_upload_parser.add_argument(
        "--validate",
        action="store_true",
        help="Run validators and attach quality scores to the archive entry",
    )

    # --- labels (command group) ---
    labels_parser = subparsers.add_parser(
        "labels",
        help="Label taxonomy management",
        description="Manage GitHub issue label taxonomy.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Subcommands:
  list         Show taxonomy tree grouped by dimension
  sync         Sync labels to GitHub
  validate     Validate label names against taxonomy

Examples:
  sls labels list                        # Show taxonomy tree
  sls labels sync --dry-run              # Preview GitHub label sync
  sls labels sync --repo owner/repo      # Sync to specific repo
  sls labels validate bug:visual origin:agent  # Validate label names
        """,
    )
    labels_subparsers = labels_parser.add_subparsers(
        dest="labels_command",
        title="labels commands",
        metavar="<subcommand>",
    )

    # --- labels list ---
    labels_subparsers.add_parser(
        "list",
        help="Show taxonomy tree grouped by dimension",
        description="Render the label taxonomy as a tree with label counts.",
    )

    # --- labels sync ---
    labels_sync_parser = labels_subparsers.add_parser(
        "sync",
        help="Sync labels to GitHub",
        description="Create or update GitHub labels to match taxonomy.yaml.",
    )
    labels_sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be done without making changes",
    )
    labels_sync_parser.add_argument(
        "--repo",
        default="e-vergo/Side-By-Side-Blueprint",
        help="Target repository (default: e-vergo/Side-By-Side-Blueprint)",
    )

    # --- labels validate ---
    labels_validate_parser = labels_subparsers.add_parser(
        "validate",
        help="Validate label names against taxonomy",
        description="Check if label names are defined in the taxonomy.",
    )
    labels_validate_parser.add_argument(
        "label_names",
        nargs="+",
        help="Label names to validate",
    )

    # --- readme-check ---
    readme_check_parser = subparsers.add_parser(
        "readme-check",
        help="Check which READMEs may need updating",
        description="Check git state across all repos and report which READMEs may need updating.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Checks all repos for uncommitted changes or unpushed commits.
Repos with changes may have READMEs that need updating.

Examples:
  sls readme-check         # Human-readable report
  sls readme-check --json  # JSON output for scripts
        """,
    )
    readme_check_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # --- test-catalog ---
    test_catalog_parser = subparsers.add_parser(
        "test-catalog",
        help="List all testable components",
        description="List all MCP tools, pytest tests, and CLI commands.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Lists all testable components in the SLS toolchain:
- MCP Tools
- Pytest tests with tier markers (evergreen, dev, temporary)
- CLI commands

Examples:
  sls test-catalog                  # Human-readable output
  sls test-catalog --json           # JSON output for scripts
  sls test-catalog --tier evergreen # Filter tests by tier
        """,
    )
    test_catalog_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    test_catalog_parser.add_argument(
        "--tier",
        choices=["evergreen", "dev", "temporary"],
        help="Filter pytest tests by tier",
    )

    # --- watch ---
    watch_parser = subparsers.add_parser(
        "watch",
        help="Watch for changes and incrementally regenerate site",
        description="Monitor files for changes and trigger minimal regeneration.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Change types and actions:
  CSS/JS assets       -> Copy to _site (instant)
  Dressed artifacts   -> Regenerate affected pages
  Runway templates    -> Full page regeneration
  Graph topology      -> Re-layout graph + regen pages
  Status-only change  -> Recolor graph nodes
  runway.json         -> Full rebuild

Examples:
  sls watch --project SBSTest          # Watch with default port
  sls watch --project GCR --port 9000  # Custom port
        """,
    )
    watch_parser.add_argument(
        "--project",
        required=True,
        help="Project name (SBSTest, GCR, PNT) or path to project directory",
    )
    watch_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for dev server (default: 8000)",
    )

    # --- dev ---
    dev_parser = subparsers.add_parser(
        "dev",
        help="Dev server with HTTP serving, file watching, and WebSocket live reload",
        description="Combined dev server: serves the site, watches for changes, and pushes live reloads to connected browsers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
HTTP server injects a small script into HTML responses that connects
to a WebSocket server. When file changes trigger regeneration, all
connected browsers are notified to reload.

  CSS-only changes  -> Hot-swap stylesheets (no full reload)
  Everything else   -> Full page reload

Examples:
  sls dev --project SBSTest          # Default port 8000, WS on 8001
  sls dev --project GCR --port 9000  # HTTP on 9000, WS on 9001
        """,
    )
    dev_parser.add_argument(
        "--project",
        required=True,
        help="Project name (SBSTest, GCR, PNT) or path to project directory",
    )
    dev_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP server (default: 8000). WebSocket uses port+1.",
    )

    # --- clean ---
    clean_parser = subparsers.add_parser(
        "clean",
        help="Remove build artifacts and caches",
        description="Remove .lake/build, lakefile.olean, and cached hashes for repos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sls clean --project SBSTest --check   # Show what would be cleaned
  sls clean --project SBSTest           # Clean SBSTest + toolchain deps
  sls clean --all --force               # Clean everything
  sls clean --all --full --force        # Clean everything including .lake/packages
        """,
    )
    clean_parser.add_argument(
        "--project",
        choices=["SBSTest", "GCR", "PNT"],
        help="Clean specific project and its toolchain dependencies",
    )
    clean_parser.add_argument(
        "--all",
        action="store_true",
        help="Clean all toolchain repos and all projects",
    )
    clean_parser.add_argument(
        "--full",
        action="store_true",
        help="Also remove .lake/packages/ (requires re-download)",
    )
    clean_parser.add_argument(
        "--check",
        action="store_true",
        help="Dry run: show what would be cleaned without deleting",
    )
    clean_parser.add_argument(
        "--force",
        action="store_true",
        help="Required when using --all to confirm deletion",
    )

    return parser


# =============================================================================
# Command Handlers
# =============================================================================


def cmd_labels(args: argparse.Namespace) -> int:
    """Handle labels commands."""
    if not args.labels_command:
        log.error("No labels subcommand specified. Use 'sls labels list', 'sync', or 'validate'.")
        return 1

    if args.labels_command == "list":
        from sls.labels.sync import render_taxonomy_tree
        print(render_taxonomy_tree())
        return 0

    elif args.labels_command == "sync":
        from sls.labels.sync import sync_labels
        sync_labels(repo=args.repo, dry_run=args.dry_run)
        return 0

    elif args.labels_command == "validate":
        from sls.labels import validate_labels
        valid, invalid = validate_labels(args.label_names)
        if valid:
            for name in valid:
                log.success(f"  {name}")
        if invalid:
            for name in invalid:
                log.error(f"  {name} (unknown)")
            return 1
        return 0

    log.error(f"Unknown labels command: {args.labels_command}")
    return 1


def cmd_readme_check(args: argparse.Namespace) -> int:
    """Handle readme-check command."""
    from pathlib import Path
    from sls.readme import check_all_repos, format_report, format_json

    # Find repo root: cli.py is at dev/scripts/sls/cli.py (4 levels up)
    repo_root = Path(__file__).resolve().parent.parent.parent.parent

    statuses = check_all_repos(repo_root)

    if args.json:
        print(format_json(statuses))
    else:
        print(format_report(statuses))

    return 0


def cmd_test_catalog(args: argparse.Namespace) -> int:
    """Handle test-catalog command."""
    from datetime import datetime
    from pathlib import Path
    from sls.test_catalog import build_catalog, format_catalog, format_catalog_json

    # Find scripts dir: cli.py is at dev/scripts/sls/cli.py (2 levels up to dev/scripts)
    scripts_dir = Path(__file__).resolve().parent.parent
    # Find repo root: cli.py is at dev/scripts/sls/cli.py (4 levels up)
    repo_root = Path(__file__).resolve().parent.parent.parent.parent

    tier_filter = getattr(args, "tier", None)
    catalog = build_catalog(scripts_dir, tier_filter)

    if args.json:
        output = format_catalog_json(catalog)
        print(output)
    else:
        output = format_catalog(catalog)
        print(output)

        # Write to fixed file location (only for human-readable output)
        catalog_path = repo_root / "dev" / "storage" / "TEST_CATALOG.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        md_content = f"""# SLS Test Catalog

> Auto-generated on {timestamp}
> Run `sls test-catalog` to regenerate

```
{output}
```
"""
        catalog_path.write_text(md_content, encoding="utf-8")
        log.info(f"Written to: {catalog_path}")

    return 0


# =============================================================================
# Command Dispatch
# =============================================================================


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Handle --no-color
    if args.no_color:
        log.set_color(False)

    # No command specified
    if not args.command:
        parser.print_help()
        return 0

    # Dispatch to command handler
    try:
        if args.command == "archive":
            from sls.archive import cmd_archive
            return cmd_archive(args)

        elif args.command == "labels":
            return cmd_labels(args)

        elif args.command == "readme-check":
            return cmd_readme_check(args)

        elif args.command == "test-catalog":
            return cmd_test_catalog(args)

        elif args.command == "watch":
            from sls.commands.watch import cmd_watch
            return cmd_watch(args)

        elif args.command == "dev":
            from sls.commands.dev import cmd_dev
            return cmd_dev(args)

        elif args.command == "clean":
            from sls.commands.clean import cmd_clean
            return cmd_clean(args)

        else:
            log.error(f"Unknown command: {args.command}")
            return 1

    except KeyboardInterrupt:
        log.warning("\nInterrupted")
        return 130
    except Exception as e:
        log.error(str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
