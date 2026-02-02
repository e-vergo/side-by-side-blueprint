"""
Main CLI for the sbs tool.

Provides a unified interface for all Side-by-Side Blueprint development commands.
"""

from __future__ import annotations

import argparse
import sys

from sbs.core.utils import log


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
        prog="sbs",
        description="Side-by-Side Blueprint development CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  capture      Capture screenshots of generated site
  compare      Compare latest screenshots to previous capture
  history      List capture history for a project
  inspect      Show build state, artifact locations, manifest contents
  validate     Run validation checks on generated site
  compliance   Visual compliance validation loop
  validate-all Run compliance + quality score evaluation
  status       Show git status across all repos
  diff         Show changes across all repos
  sync         Ensure all repos are synced (commit + push)
  versions     Show dependency versions across repos
  archive      Archive management commands
  oracle       Oracle management commands

Examples:
  sbs capture                    # Capture screenshots from localhost:8000
  sbs compare                    # Compare latest to most recent archive
  sbs compliance                 # Run visual compliance check
  sbs validate-all               # Run compliance + quality scores
  sbs status                     # Show git status for all repos
  sbs inspect                    # Show build artifacts and manifest
  sbs sync -m "Fix bug"          # Commit and push all changes
  sbs oracle compile             # Compile Oracle from sources
  sbs readme-check               # Check which READMEs may need updating
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

    # --- capture ---
    capture_parser = subparsers.add_parser(
        "capture",
        help="Capture screenshots of generated site",
        description="Capture screenshots from a running blueprint site for visual diff testing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sbs capture                           # Capture from localhost:8000
  sbs capture --url http://example.com  # Capture from custom URL
  sbs capture --pages dashboard,chapter # Capture specific pages
  sbs capture --viewport 1280x720       # Custom viewport size
        """,
    )
    capture_parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL to capture from (default: http://localhost:8000)",
    )
    capture_parser.add_argument(
        "--project",
        help="Project name (default: detect from runway.json)",
    )
    capture_parser.add_argument(
        "--pages",
        help="Comma-separated list of pages to capture (default: all)",
    )
    capture_parser.add_argument(
        "--viewport",
        default="1920x1080",
        help="Viewport size as WxH (default: 1920x1080)",
    )
    capture_parser.add_argument(
        "--interactive",
        action="store_true",
        help="Include interactive state capture (clicks, hovers, modals)",
    )
    capture_parser.add_argument(
        "--rediscover",
        action="store_true",
        help="Rediscover interactive elements (ignore saved manifests)",
    )

    # --- compare ---
    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare latest screenshots to previous capture",
        description="Compare latest screenshots against a baseline to detect visual changes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sbs compare                          # Compare to most recent archive
  sbs compare --baseline 2024-01-15    # Compare to specific archive
        """,
    )
    compare_parser.add_argument(
        "--project",
        help="Project name (default: detect from runway.json)",
    )
    compare_parser.add_argument(
        "--baseline",
        help="Archive name to compare against (default: most recent)",
    )

    # --- history ---
    history_parser = subparsers.add_parser(
        "history",
        help="List capture history for a project",
        description="Show all archived captures for a project.",
    )
    history_parser.add_argument(
        "--project",
        help="Project name (default: detect from runway.json)",
    )

    # --- inspect ---
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Show build state, artifact locations, manifest contents",
        description="Inspect the current build state including artifacts, manifest, and site.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sbs inspect            # Show build state summary
  sbs inspect --verbose  # Include detailed file listings
        """,
    )
    inspect_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed information",
    )

    # --- validate ---
    validate_parser = subparsers.add_parser(
        "validate",
        help="Run validation checks on generated site",
        description="Check the generated site for missing files, broken links, etc.",
    )

    # --- compliance ---
    compliance_parser = subparsers.add_parser(
        "compliance",
        help="Visual compliance validation loop",
        description="Run visual compliance checks using AI vision analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sbs compliance                    # Check compliance with smart reset
  sbs compliance --full             # Force full re-validation
  sbs compliance --page dashboard   # Validate specific page
  sbs compliance --interactive      # Include interactive state capture
        """,
    )
    compliance_parser.add_argument(
        "--project",
        help="Project name (default: detect from runway.json)",
    )
    compliance_parser.add_argument(
        "--full",
        action="store_true",
        help="Force full re-validation (ignore ledger)",
    )
    compliance_parser.add_argument(
        "--page",
        help="Validate specific page only",
    )
    compliance_parser.add_argument(
        "--interactive",
        action="store_true",
        help="Include interactive state capture and validation",
    )
    compliance_parser.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="Maximum validation iterations (default: 10)",
    )

    # --- status ---
    status_parser = subparsers.add_parser(
        "status",
        help="Show git status across all repos",
        description="Show git status for all repos in the SBS workspace.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sbs status            # Show status summary
  sbs status --verbose  # Include file-level changes
        """,
    )
    status_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show file-level changes",
    )

    # --- diff ---
    diff_parser = subparsers.add_parser(
        "diff",
        help="Show changes across all repos",
        description="Show git diff for all repos with uncommitted changes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sbs diff         # Show diff summary (--stat)
  sbs diff --full  # Show full diff output
        """,
    )
    diff_parser.add_argument(
        "--full",
        action="store_true",
        help="Show full diff output instead of --stat",
    )

    # --- sync ---
    sync_parser = subparsers.add_parser(
        "sync",
        help="Ensure all repos are synced (commit + push)",
        description="Commit and push all uncommitted changes across repos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sbs sync                     # Commit with default message
  sbs sync -m "Fix bug"        # Commit with custom message
  sbs sync --dry-run           # Show what would be done
        """,
    )
    sync_parser.add_argument(
        "-m", "--message",
        help="Commit message (default: 'Auto-commit from sbs sync')",
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    sync_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output",
    )

    # --- versions ---
    versions_parser = subparsers.add_parser(
        "versions",
        help="Show dependency versions across repos",
        description="Check dependency versions across all repos and highlight mismatches.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sbs versions          # Show version summary
  sbs versions --table  # Show full version table
        """,
    )
    versions_parser.add_argument(
        "--table",
        action="store_true",
        help="Show full version table",
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
  sbs archive list                        # List all entries
  sbs archive list --project SBSTest      # List entries for project
  sbs archive tag 1738340279 release v1   # Add tags to entry
  sbs archive note 1738340279 "Baseline"  # Add note to entry
  sbs archive show 1738340279             # Show entry details
  sbs archive charts                      # Generate charts
  sbs archive sync                        # Sync to iCloud
  sbs archive retroactive --dry-run       # Preview migration
  sbs archive upload --dry-run            # Preview upload
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
  sbs archive retroactive            # Run migration
  sbs archive retroactive --dry-run  # Preview without making changes
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
  sbs archive upload                    # Full upload
  sbs archive upload --dry-run          # Preview without making changes
  sbs archive upload --project SBSTest  # Associate with specific project
  sbs archive upload --trigger build    # Mark as build-triggered
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
        choices=["phase_start", "phase_end"],
        help="State transition type (phase_start or phase_end)",
    )

    # --- oracle (command group) ---
    oracle_parser = subparsers.add_parser(
        "oracle",
        help="Oracle management commands",
        description="Compile and manage the SBS Oracle agent documentation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Subcommands:
  compile      Compile Oracle from sources

Examples:
  sbs oracle compile                         # Compile to default location
  sbs oracle compile --dry-run               # Print output without writing
  sbs oracle compile --output custom.md      # Write to custom path
        """,
    )
    oracle_subparsers = oracle_parser.add_subparsers(
        dest="oracle_command",
        title="oracle commands",
        metavar="<subcommand>",
    )

    # --- oracle compile ---
    oracle_compile_parser = oracle_subparsers.add_parser(
        "compile",
        help="Compile Oracle from sources",
        description="Compile the SBS Oracle agent documentation from source files.",
    )
    oracle_compile_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output without writing",
    )
    oracle_compile_parser.add_argument(
        "--output",
        help="Output path (default: .claude/agents/sbs-oracle.md)",
    )

    # --- readme-check ---
    readme_check_parser = subparsers.add_parser(
        "readme-check",
        help="Check which READMEs may need updating",
        description="Check git state across all repos and report which READMEs may need updating.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Checks all 11 repos (main + 10 submodules) for uncommitted changes or
unpushed commits. Repos with changes may have READMEs that need updating.

Examples:
  sbs readme-check         # Human-readable report
  sbs readme-check --json  # JSON output for scripts
        """,
    )
    readme_check_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # --- validate-all ---
    validate_all_parser = subparsers.add_parser(
        "validate-all",
        help="Run compliance + quality score evaluation",
        description="Unified validation: runs compliance check and reports quality score status.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Combines compliance validation with quality score tracking:
1. Runs compliance check (or reports current status)
2. Checks quality scores for staleness
3. Reports which metrics need re-evaluation
4. Shows combined validation status

Examples:
  sbs validate-all                     # Check all validation status
  sbs validate-all --project SBSTest   # Check for specific project
        """,
    )
    validate_all_parser.add_argument(
        "--project",
        help="Project name (default: detect from runway.json)",
    )

    return parser


# =============================================================================
# Command Handlers
# =============================================================================


def cmd_oracle(args: argparse.Namespace) -> int:
    """Handle oracle commands."""
    from pathlib import Path
    from sbs.oracle import OracleCompiler

    if not args.oracle_command:
        log.error("No oracle subcommand specified. Use 'sbs oracle compile'.")
        return 1

    if args.oracle_command == "compile":
        # Find repo root: cli.py is at dev/scripts/sbs/cli.py (4 levels up)
        repo_root = Path(__file__).resolve().parent.parent.parent.parent

        compiler = OracleCompiler(repo_root)
        content = compiler.compile()

        if args.dry_run:
            print(content)
            log.info("\n--- Dry run complete ---")
            log.info(f"  Size: {len(content):,} bytes")
        else:
            # Determine output path
            if args.output:
                output_path = Path(args.output)
                if not output_path.is_absolute():
                    output_path = repo_root / output_path
            else:
                output_path = repo_root / ".claude" / "agents" / "sbs-oracle.md"

            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write output
            output_path.write_text(content, encoding="utf-8")

            log.success(f"Compiled Oracle to: {output_path}")
            log.info(f"  Size: {len(content):,} bytes")

        return 0

    log.error(f"Unknown oracle command: {args.oracle_command}")
    return 1


def cmd_readme_check(args: argparse.Namespace) -> int:
    """Handle readme-check command."""
    from pathlib import Path
    from sbs.readme import check_all_repos, format_report, format_json

    # Find repo root: cli.py is at dev/scripts/sbs/cli.py (4 levels up)
    repo_root = Path(__file__).resolve().parent.parent.parent.parent

    statuses = check_all_repos(repo_root)

    if args.json:
        print(format_json(statuses))
    else:
        print(format_report(statuses))

    return 0


def cmd_validate_all(args: argparse.Namespace) -> int:
    """Handle validate-all command: compliance + quality scores."""
    from pathlib import Path
    from sbs.core.utils import detect_project

    # Detect project
    if args.project:
        project_name = args.project
    else:
        project_name, _ = detect_project()

    log.header(f"Unified Validation: {project_name}")

    # 1. Check compliance status
    log.info("Checking compliance status...")
    try:
        from sbs.tests.compliance.ledger_ops import load_ledger as load_compliance_ledger, is_fully_compliant
        compliance_ledger = load_compliance_ledger()

        if compliance_ledger.project == project_name:
            compliant = is_fully_compliant(compliance_ledger)
            summary = compliance_ledger.summary
            log.info(f"Compliance: {summary.compliance_percent:.1f}% ({summary.passed}/{summary.total_checks} passed)")
            if not compliant:
                log.warning(f"  {summary.failed} pages need attention")
        else:
            log.info(f"No compliance data for {project_name}")
            compliant = False
    except Exception as e:
        log.warning(f"Could not load compliance ledger: {e}")
        compliant = False

    print()

    # 2. Check quality scores
    log.info("Checking quality scores...")
    try:
        from sbs.tests.scoring import (
            load_ledger as load_quality_ledger,
            get_stale_metrics,
            get_pending_metrics,
            compute_metrics_to_evaluate,
        )

        quality_ledger = load_quality_ledger(project_name)
        stale = get_stale_metrics(quality_ledger)
        pending = get_pending_metrics(quality_ledger)

        log.info(f"Overall quality score: {quality_ledger.overall_score:.2f}%")

        if stale:
            log.warning(f"Stale metrics ({len(stale)}): {', '.join(stale)}")

        if pending:
            log.warning(f"Pending metrics ({len(pending)}): {', '.join(pending)}")

        # Show individual scores
        print()
        log.info("Quality Metrics:")
        weights = {
            "t1-cli-execution": ("CLI Execution", 10),
            "t2-ledger-population": ("Ledger Population", 10),
            "t3-dashboard-clarity": ("Dashboard Clarity", 10),
            "t4-toggle-discoverability": ("Toggle Discoverability", 10),
            "t5-color-match": ("Status Color Match", 15),
            "t6-css-coverage": ("CSS Variable Coverage", 15),
            "t7-jarring": ("Jarring-Free Check", 15),
            "t8-professional": ("Professional Score", 15),
        }

        for metric_id in sorted(weights.keys()):
            name, weight = weights[metric_id]
            score = quality_ledger.scores.get(metric_id)
            if score:
                status = "STALE" if score.stale else ("PASS" if score.passed else "FAIL")
                print(f"  {metric_id}: {score.value:.1f} ({status}) - {name}")
            else:
                print(f"  {metric_id}: - (pending) - {name}")

    except Exception as e:
        log.warning(f"Could not load quality ledger: {e}")
        pending = []
        stale = []

    print()

    # 3. Summary
    log.header("Validation Summary")

    all_valid = compliant and not pending and not stale

    if all_valid:
        log.success("All validations passing")
        return 0
    else:
        if not compliant:
            log.warning("Compliance: needs attention")
        else:
            log.success("Compliance: passing")

        if pending:
            log.warning(f"Quality: {len(pending)} metrics need evaluation")
        elif stale:
            log.warning(f"Quality: {len(stale)} metrics are stale")
        else:
            log.success("Quality: all metrics current")

        return 1


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
        if args.command == "capture":
            from sbs.tests.compliance.capture import cmd_capture
            return cmd_capture(args)

        elif args.command == "compare":
            from sbs.tests.compliance.compare import cmd_compare
            return cmd_compare(args)

        elif args.command == "history":
            from sbs.tests.compliance.compare import cmd_history
            return cmd_history(args)

        elif args.command == "inspect":
            from sbs.build.inspect import cmd_inspect
            return cmd_inspect(args)

        elif args.command == "validate":
            from sbs.build.inspect import cmd_validate
            return cmd_validate(args)

        elif args.command == "compliance":
            from sbs.tests.compliance.validate import cmd_compliance
            return cmd_compliance(args)

        elif args.command == "status":
            from sbs.core.git_ops import cmd_status
            return cmd_status(args)

        elif args.command == "diff":
            from sbs.core.git_ops import cmd_diff
            return cmd_diff(args)

        elif args.command == "sync":
            from sbs.core.git_ops import cmd_sync
            return cmd_sync(args)

        elif args.command == "versions":
            from sbs.build.versions import cmd_versions
            return cmd_versions(args)

        elif args.command == "archive":
            from sbs.archive import cmd_archive
            return cmd_archive(args)

        elif args.command == "oracle":
            return cmd_oracle(args)

        elif args.command == "readme-check":
            return cmd_readme_check(args)

        elif args.command == "validate-all":
            return cmd_validate_all(args)

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
