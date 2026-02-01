"""
Visual compliance testing package.

Provides screenshot capture, comparison, validation criteria, and compliance loop.
"""

from __future__ import annotations

# Criteria and page definitions
from sbs.tests.compliance.criteria import (
    Criterion,
    PageCriteria,
    PAGE_CRITERIA,
    GLOBAL_CRITERIA,
    SIDEBAR_CRITERIA,
    STATUS_COLORS,
    get_criteria_for_page,
    get_sidebar_criteria,
    get_interactive_elements,
    format_criteria_for_prompt,
    get_all_criteria_ids,
    get_status_color,
    get_all_status_colors,
)

# Design criteria
from sbs.tests.compliance.criteria_design import (
    DesignCriterion,
    JARRING_CHECK_CRITERIA,
    get_jarring_criteria,
    get_jarring_criteria_ids,
    format_jarring_criteria_for_prompt,
)

# Capture commands
from sbs.tests.compliance.capture import (
    cmd_capture,
    run_capture,
    run_interactive_capture,
    capture_page,
    find_chapter_page,
    archive_previous_captures,
    get_archive_history,
)

# Compare commands
from sbs.tests.compliance.compare import (
    cmd_compare,
    cmd_history,
    compare_captures,
    compare_images,
    ComparisonResult,
)

# Validation
from sbs.tests.compliance.validate import (
    cmd_compliance,
    ValidationResult,
    ComplianceConfig,
    run_compliance_check,
    apply_validation_result,
    check_compliance_status,
    get_validation_summary,
    generate_page_validation_prompt,
    generate_interaction_validation_prompt,
    generate_final_review_prompt,
    parse_validation_response,
    get_screenshot_path,
    get_all_screenshot_paths,
)

# Ledger operations
from sbs.tests.compliance.ledger_ops import (
    ComplianceLedger,
    load_ledger,
    save_ledger,
    update_page_result,
    update_interaction_result,
    mark_pages_for_revalidation,
    reset_all,
    get_pages_needing_validation,
    get_failed_pages,
    is_fully_compliant,
    initialize_ledger,
    start_run,
    record_iteration,
    record_screenshots,
    record_validation_agent,
    record_criteria_stats,
    finalize_run,
    get_run_summary,
    get_archive_root,
    get_project_dir,
    get_ledger_path,
    get_status_md_path,
)

# Mapping
from sbs.tests.compliance.mapping import (
    REPO_PAGE_MAPPING,
    ALL_PAGES,
    get_repo_commits,
    detect_changed_repos,
    get_affected_pages,
    compute_pages_to_validate,
    update_ledger_commits,
)

__all__ = [
    # Criteria
    "Criterion",
    "PageCriteria",
    "PAGE_CRITERIA",
    "GLOBAL_CRITERIA",
    "SIDEBAR_CRITERIA",
    "STATUS_COLORS",
    "get_criteria_for_page",
    "get_sidebar_criteria",
    "get_interactive_elements",
    "format_criteria_for_prompt",
    "get_all_criteria_ids",
    "get_status_color",
    "get_all_status_colors",
    # Design criteria
    "DesignCriterion",
    "JARRING_CHECK_CRITERIA",
    "get_jarring_criteria",
    "get_jarring_criteria_ids",
    "format_jarring_criteria_for_prompt",
    # Capture
    "cmd_capture",
    "run_capture",
    "run_interactive_capture",
    "capture_page",
    "find_chapter_page",
    "archive_previous_captures",
    "get_archive_history",
    # Compare
    "cmd_compare",
    "cmd_history",
    "compare_captures",
    "compare_images",
    "ComparisonResult",
    # Validate
    "cmd_compliance",
    "ValidationResult",
    "ComplianceConfig",
    "run_compliance_check",
    "apply_validation_result",
    "check_compliance_status",
    "get_validation_summary",
    "generate_page_validation_prompt",
    "generate_interaction_validation_prompt",
    "generate_final_review_prompt",
    "parse_validation_response",
    "get_screenshot_path",
    "get_all_screenshot_paths",
    # Ledger
    "ComplianceLedger",
    "load_ledger",
    "save_ledger",
    "update_page_result",
    "update_interaction_result",
    "mark_pages_for_revalidation",
    "reset_all",
    "get_pages_needing_validation",
    "get_failed_pages",
    "is_fully_compliant",
    "initialize_ledger",
    "start_run",
    "record_iteration",
    "record_screenshots",
    "record_validation_agent",
    "record_criteria_stats",
    "finalize_run",
    "get_run_summary",
    "get_archive_root",
    "get_project_dir",
    "get_ledger_path",
    "get_status_md_path",
    # Mapping
    "REPO_PAGE_MAPPING",
    "ALL_PAGES",
    "get_repo_commits",
    "detect_changed_repos",
    "get_affected_pages",
    "compute_pages_to_validate",
    "update_ledger_commits",
]
