"""
Main CLI for the sbs tool.

Provides a unified interface for all Side-by-Side Blueprint development commands.
"""

from __future__ import annotations

import argparse
import sys

from .utils import log


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
  capture     Capture screenshots of generated site
  compare     Compare latest screenshots to previous capture
  history     List capture history for a project
  inspect     Show build state, artifact locations, manifest contents
  validate    Run validation checks on generated site
  compliance  Visual compliance validation loop
  status      Show git status across all repos
  diff        Show changes across all repos
  sync        Ensure all repos are synced (commit + push)
  versions    Show dependency versions across repos

Examples:
  sbs capture                    # Capture screenshots from localhost:8000
  sbs compare                    # Compare latest to most recent archive
  sbs compliance                 # Run visual compliance check
  sbs status                     # Show git status for all repos
  sbs inspect                    # Show build artifacts and manifest
  sbs sync -m "Fix bug"          # Commit and push all changes
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

    return parser


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
            from .capture import cmd_capture
            return cmd_capture(args)

        elif args.command == "compare":
            from .compare import cmd_compare
            return cmd_compare(args)

        elif args.command == "history":
            from .compare import cmd_history
            return cmd_history(args)

        elif args.command == "inspect":
            from .inspect_cmd import cmd_inspect
            return cmd_inspect(args)

        elif args.command == "validate":
            from .inspect_cmd import cmd_validate
            return cmd_validate(args)

        elif args.command == "compliance":
            from .validate import cmd_compliance
            return cmd_compliance(args)

        elif args.command == "status":
            from .git_ops import cmd_status
            return cmd_status(args)

        elif args.command == "diff":
            from .git_ops import cmd_diff
            return cmd_diff(args)

        elif args.command == "sync":
            from .git_ops import cmd_sync
            return cmd_sync(args)

        elif args.command == "versions":
            from .versions import cmd_versions
            return cmd_versions(args)

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
