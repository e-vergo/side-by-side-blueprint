"""
sbs.core - Foundation layer for the sbs CLI.

Exports core utilities, data structures, and git operations.
"""

# Utils
from sbs.core.utils import (
    # Logging
    log,
    Logger,
    # Constants
    SBS_ROOT,
    ARCHIVE_DIR,
    IMAGES_DIR,
    CACHE_DIR,
    REPO_PATHS,
    REPO_NAMES,
    # Path utilities
    get_sbs_root,
    get_project_root,
    detect_project,
    get_repos,
    get_repo_path,
    # Git utilities
    get_git_commit,
    get_git_branch,
    git_has_changes,
    git_status_short,
    git_diff_stat,
    # Lakefile parsing
    parse_lakefile,
    get_lean_toolchain,
    # Runtime utilities
    run_cmd,
)

# Git operations
from sbs.core.git_ops import (
    get_repo_status,
    sync_repo,
    cmd_status,
    cmd_diff,
    cmd_sync,
)

# Ledger data structures
from sbs.core.ledger import (
    BuildMetrics,
    UnifiedLedger,
    get_or_create_unified_ledger,
    # Also export shared types needed by sbs.ledger
    InteractionResult,
    PageResult,
    LedgerSummary,
    RunStatistics,
    HistoricalStats,
)

__all__ = [
    # Logging
    "log",
    "Logger",
    # Constants
    "SBS_ROOT",
    "ARCHIVE_DIR",
    "IMAGES_DIR",
    "CACHE_DIR",
    "REPO_PATHS",
    "REPO_NAMES",
    # Path utilities
    "get_sbs_root",
    "get_project_root",
    "detect_project",
    "get_repos",
    "get_repo_path",
    # Git utilities
    "get_git_commit",
    "get_git_branch",
    "git_has_changes",
    "git_status_short",
    "git_diff_stat",
    # Lakefile parsing
    "parse_lakefile",
    "get_lean_toolchain",
    # Runtime utilities
    "run_cmd",
    # Git operations
    "get_repo_status",
    "sync_repo",
    "cmd_status",
    "cmd_diff",
    "cmd_sync",
    # Ledger types
    "BuildMetrics",
    "UnifiedLedger",
    "get_or_create_unified_ledger",
    "InteractionResult",
    "PageResult",
    "LedgerSummary",
    "RunStatistics",
    "HistoricalStats",
]
