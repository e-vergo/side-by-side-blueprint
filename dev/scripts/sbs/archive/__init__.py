"""Archive module for SBS project snapshots."""

from .entry import ArchiveEntry, ArchiveIndex
from .session_data import SessionData, ToolCall, ClaudeDataSnapshot
from .extractor import extract_claude_data
from .tagger import TaggingEngine, build_tagging_context
from .upload import (
    archive_upload,
    ensure_porcelain,
    collect_repo_commits,
)
from .icloud_sync import (
    full_sync,
    get_icloud_path,
    sync_entry,
    sync_index,
    sync_ledger,
)
from .visualizations import (
    generate_loc_chart,
    generate_timing_chart,
    generate_activity_heatmap,
    generate_all_charts,
)
from .chat_archive import (
    archive_chat_sessions,
    list_recent_sessions,
    parse_jsonl_session,
    generate_session_summary,
    copy_active_plans,
)
from .retroactive import (
    retroactive_migration,
    scan_historical_captures,
)

__all__ = [
    # Entry types
    "ArchiveEntry",
    "ArchiveIndex",
    # Session data types
    "SessionData",
    "ToolCall",
    "ClaudeDataSnapshot",
    # Extraction
    "extract_claude_data",
    # Tagging
    "TaggingEngine",
    "build_tagging_context",
    # Upload
    "archive_upload",
    "ensure_porcelain",
    "collect_repo_commits",
    # iCloud sync
    "full_sync",
    "get_icloud_path",
    "sync_entry",
    "sync_index",
    "sync_ledger",
    # Visualizations
    "generate_loc_chart",
    "generate_timing_chart",
    "generate_activity_heatmap",
    "generate_all_charts",
    # Chat archive
    "archive_chat_sessions",
    "list_recent_sessions",
    "parse_jsonl_session",
    "generate_session_summary",
    "copy_active_plans",
    # Retroactive
    "retroactive_migration",
    "scan_historical_captures",
]
