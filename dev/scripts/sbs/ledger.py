"""
Compliance ledger management.

This module is a backward compatibility shim. The actual implementation
has been moved to sbs.tests.compliance.ledger_ops.

For new code, import directly from:
- sbs.core.ledger for core data structures (BuildMetrics, UnifiedLedger, etc.)
- sbs.tests.compliance.ledger_ops for compliance-specific operations
"""

from __future__ import annotations

# Re-export everything from both modules for backward compatibility

# Core types from sbs.core.ledger
from sbs.core.ledger import (
    InteractionResult,
    PageResult,
    LedgerSummary,
    RunStatistics,
    HistoricalStats,
    BuildMetrics,
    UnifiedLedger,
    get_or_create_unified_ledger,
    _serialize_run_stats,
    _deserialize_run_stats,
    _deserialize_historical_stats,
)

# Compliance-specific types and operations from sbs.tests.compliance.ledger_ops
from sbs.tests.compliance.ledger_ops import (
    ComplianceLedger,
    # Paths
    get_archive_root,
    get_images_dir,
    get_project_dir,
    get_ledger_path,
    get_status_md_path,
    get_lifetime_stats_path,
    get_manifests_dir,
    get_unified_ledger_path,
    # Read/Write
    load_ledger,
    save_ledger,
    save_lifetime_stats,
    load_lifetime_stats,
    # Update operations
    update_page_result,
    update_interaction_result,
    # Reset operations
    mark_pages_for_revalidation,
    reset_all,
    get_pages_needing_validation,
    get_failed_pages,
    is_fully_compliant,
    # Initialization
    initialize_ledger,
    # Statistics tracking
    start_run,
    record_iteration,
    record_screenshots,
    record_validation_agent,
    record_criteria_stats,
    finalize_run,
    get_run_summary,
)

__all__ = [
    # Core types
    "InteractionResult",
    "PageResult",
    "LedgerSummary",
    "RunStatistics",
    "HistoricalStats",
    "BuildMetrics",
    "UnifiedLedger",
    "get_or_create_unified_ledger",
    # Compliance types
    "ComplianceLedger",
    # Paths
    "get_archive_root",
    "get_images_dir",
    "get_project_dir",
    "get_ledger_path",
    "get_status_md_path",
    "get_lifetime_stats_path",
    "get_manifests_dir",
    "get_unified_ledger_path",
    # Read/Write
    "load_ledger",
    "save_ledger",
    "save_lifetime_stats",
    "load_lifetime_stats",
    # Update operations
    "update_page_result",
    "update_interaction_result",
    # Reset operations
    "mark_pages_for_revalidation",
    "reset_all",
    "get_pages_needing_validation",
    "get_failed_pages",
    "is_fully_compliant",
    # Initialization
    "initialize_ledger",
    # Statistics tracking
    "start_run",
    "record_iteration",
    "record_screenshots",
    "record_validation_agent",
    "record_criteria_stats",
    "finalize_run",
    "get_run_summary",
]
