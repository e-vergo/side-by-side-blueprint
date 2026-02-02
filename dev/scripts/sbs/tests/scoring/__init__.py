"""
Quality score persistence and repo-change invalidation.

Provides the T1-T8 quality score ledger with intelligent reset
based on which repos have changed.
"""

from .ledger import (
    MetricScore,
    ScoreSnapshot,
    QualityScoreLedger,
    load_ledger,
    save_ledger,
    get_ledger_path,
    get_status_md_path,
    update_score,
    add_snapshot,
    get_stale_metrics,
    get_pending_metrics,
)

from .reset import (
    REPO_SCORE_MAPPING,
    ALL_METRICS,
    get_repo_commits,
    detect_changed_repos,
    get_affected_metrics,
    invalidate_stale_scores,
    compute_metrics_to_evaluate,
    update_ledger_commits,
    validate_mapping,
    print_dependency_graph,
    print_metric_dependencies,
    print_repo_status,
)

__all__ = [
    # Data structures
    "MetricScore",
    "ScoreSnapshot",
    "QualityScoreLedger",
    # Ledger operations
    "load_ledger",
    "save_ledger",
    "get_ledger_path",
    "get_status_md_path",
    "update_score",
    "add_snapshot",
    "get_stale_metrics",
    "get_pending_metrics",
    # Reset/invalidation
    "REPO_SCORE_MAPPING",
    "ALL_METRICS",
    "get_repo_commits",
    "detect_changed_repos",
    "get_affected_metrics",
    "invalidate_stale_scores",
    "compute_metrics_to_evaluate",
    "update_ledger_commits",
    "validate_mapping",
    # Debug utilities
    "print_dependency_graph",
    "print_metric_dependencies",
    "print_repo_status",
]
