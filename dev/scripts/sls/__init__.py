"""
sls - Strange Loop Station orchestration CLI.

A unified command-line tool for archive management, cross-repo operations,
label taxonomy, and development tooling.

Usage:
    python -m sls <command> [options]

Commands:
    archive      Archive management commands
    labels       Label taxonomy management
    readme-check Check which READMEs may need updating
    test-catalog List all testable components
    watch        Watch for changes and incrementally regenerate
    dev          Dev server with HTTP serving and live reload
    clean        Remove build artifacts and caches
"""

from .cli import __version__, main

__all__ = ["__version__", "main"]
