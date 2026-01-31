"""
sbs - Side-by-Side Blueprint development CLI.

A unified command-line tool for build diagnostics, cross-repo operations,
and screenshot management.

Usage:
    python -m sbs <command> [options]

Commands:
    capture     Capture screenshots of generated site
    compare     Compare latest screenshots to previous capture
    history     List capture history for a project
    inspect     Show build state, artifact locations, manifest contents
    validate    Run validation checks on generated site
    status      Show git status across all repos
    diff        Show changes across all repos
    sync        Ensure all repos are synced (commit + push)
    versions    Show dependency versions across repos
"""

from .cli import __version__, main

__all__ = ["__version__", "main"]
