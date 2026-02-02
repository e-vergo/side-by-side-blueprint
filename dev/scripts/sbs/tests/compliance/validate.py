"""
Visual compliance validation orchestration.

Provides validation result structures and agent prompt generation.
Actual validation is performed by Claude agents using AI vision analysis.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sbs.tests.compliance.criteria import (
    format_criteria_for_prompt,
    get_all_criteria_ids,
    get_interactive_elements,
    GLOBAL_CRITERIA,
    PAGE_CRITERIA,
)
from sbs.tests.compliance.ledger_ops import (
    ComplianceLedger,
    load_ledger,
    save_ledger,
    update_page_result,
    update_interaction_result,
    get_pages_needing_validation,
    get_failed_pages,
    is_fully_compliant,
    initialize_ledger,
    mark_pages_for_revalidation,
    start_run,
    record_screenshots,
    record_validation_agent,
    record_iteration,
    finalize_run,
)
from sbs.tests.compliance.mapping import (
    compute_pages_to_validate,
    update_ledger_commits,
    ALL_PAGES,
)
from sbs.core.utils import (
    ARCHIVE_DIR,
    IMAGES_DIR,  # Legacy alias
    get_sbs_root,
    detect_project,
    log,
)


# =============================================================================
# Validation Result
# =============================================================================


@dataclass
class ValidationResult:
    """Result of validating a single page or interaction."""

    page: str
    interaction: Optional[str] = None
    passed: bool = False
    findings: list[str] = field(default_factory=list)
    confidence: float = 0.0
    criteria_checked: list[str] = field(default_factory=list)
    raw_response: str = ""


def parse_validation_response(response: str, page: str, interaction: Optional[str] = None) -> ValidationResult:
    """Parse agent's validation response into structured result.

    Expects JSON format:
    {
        "page": "dashboard",
        "pass": true,
        "findings": ["issue1", "issue2"],
        "confidence": 0.95
    }
    """
    result = ValidationResult(page=page, interaction=interaction, raw_response=response)

    try:
        # Try to extract JSON from response
        json_start = response.find("{")
        json_end = response.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            data = json.loads(json_str)

            result.passed = data.get("pass", False)
            result.findings = data.get("findings", [])
            result.confidence = data.get("confidence", 0.0)
            result.criteria_checked = data.get("criteria_checked", [])

    except json.JSONDecodeError:
        # If JSON parsing fails, try to extract pass/fail from text
        response_lower = response.lower()
        if "pass" in response_lower and "fail" not in response_lower:
            result.passed = True
        elif "fail" in response_lower:
            result.passed = False
            # Try to extract findings from text
            result.findings = ["Unable to parse structured response - manual review needed"]

    return result


# =============================================================================
# Agent Prompt Generation
# =============================================================================


def generate_page_validation_prompt(
    page: str,
    screenshot_path: Path,
    project: str,
) -> str:
    """Generate prompt for validating a page screenshot.

    This prompt is designed to be used with Claude's vision capabilities.
    """
    criteria_text = format_criteria_for_prompt(page)

    prompt = f"""# Visual Compliance Validation: {page}

You are validating a screenshot from the {project} Side-by-Side Blueprint site.

**Screenshot:** {screenshot_path}

Please analyze this screenshot against the following compliance criteria:

{criteria_text}

## Instructions

1. Read the screenshot image at the path above
2. Check each criterion carefully
3. Note any violations or concerns
4. Provide your assessment

## Response Format

Return a JSON object:

```json
{{
    "page": "{page}",
    "pass": true/false,
    "findings": ["issue 1", "issue 2"],
    "confidence": 0.0-1.0,
    "criteria_checked": ["criterion_id_1", "criterion_id_2"]
}}
```

- `pass`: true if ALL required criteria are met
- `findings`: list of any issues found (empty if pass)
- `confidence`: your confidence in the assessment (0.0-1.0)
- `criteria_checked`: list of criterion IDs you verified

Be thorough but pragmatic. Minor styling differences are acceptable.
Focus on functional correctness and layout compliance.
"""

    return prompt


def generate_interaction_validation_prompt(
    page: str,
    interaction: str,
    screenshot_path: Path,
    baseline_path: Optional[Path],
    project: str,
) -> str:
    """Generate prompt for validating an interactive state screenshot."""

    prompt = f"""# Interactive State Validation: {page} / {interaction}

You are validating an interactive state screenshot from the {project} Side-by-Side Blueprint site.

**Screenshot:** {screenshot_path}
**Baseline (before interaction):** {baseline_path or "Not available"}

## Interaction Context

This screenshot was captured after triggering: `{interaction}`

## Criteria

Check that:
1. The interaction produced a visible change (if expected)
2. The UI remains functional and properly laid out
3. No visual glitches or broken elements
4. Theme/state changes are complete (no partial transitions)

## Response Format

```json
{{
    "page": "{page}",
    "interaction": "{interaction}",
    "pass": true/false,
    "findings": ["issue 1", "issue 2"],
    "confidence": 0.0-1.0
}}
```
"""

    return prompt


def generate_final_review_prompt(
    screenshot_paths: list[Path],
    project: str,
) -> str:
    """Generate prompt for final comprehensive review."""

    screenshots_list = "\n".join(f"- {p}" for p in screenshot_paths)

    prompt = f"""# Final Compliance Review: {project}

All pages have passed individual validation. Please perform a comprehensive
final review to confirm 100% visual compliance.

## Screenshots to Review

{screenshots_list}

## Global Criteria

All pages must satisfy:
"""

    for c in GLOBAL_CRITERIA:
        prompt += f"\n- {c.description}"

    prompt += """

## Instructions

1. Read each screenshot
2. Verify global criteria on all pages
3. Check for cross-page consistency (sidebar, theme, layout)
4. Note any concerns

## Response Format

```json
{
    "overall_pass": true/false,
    "pages_reviewed": ["page1", "page2"],
    "findings": ["concern 1", "concern 2"],
    "confidence": 0.0-1.0,
    "recommendation": "approve" or "needs_attention"
}
```

This is the final gate before declaring 100% compliance.
Be thorough but practical.
"""

    return prompt


# =============================================================================
# Compliance Loop
# =============================================================================


@dataclass
class ComplianceConfig:
    """Configuration for compliance validation."""

    project_root: Path
    project_name: str
    force_full: bool = False
    include_interactive: bool = True
    max_iterations: int = 10
    specific_page: Optional[str] = None


def get_screenshot_path(project: str, page: str, interaction: Optional[str] = None) -> Path:
    """Get path to a screenshot file."""
    project_dir = IMAGES_DIR / project / "latest"

    if interaction:
        return project_dir / f"{page}_{interaction}.png"
    return project_dir / f"{page}.png"


def get_all_screenshot_paths(project: str) -> list[Path]:
    """Get paths to all captured screenshots."""
    project_dir = IMAGES_DIR / project / "latest"

    if not project_dir.exists():
        return []

    return list(project_dir.glob("*.png"))


def run_compliance_check(config: ComplianceConfig) -> ComplianceLedger:
    """Run a single iteration of compliance validation.

    This function:
    1. Loads/initializes the ledger
    2. Determines which pages need validation
    3. Returns the ledger with pages marked for validation

    Actual validation is performed by the orchestrating agent
    using the prompts generated by this module.
    """
    log.header("Visual Compliance Check")

    # Load or initialize ledger
    ledger = load_ledger()

    if not ledger.pages or ledger.project != config.project_name:
        log.info(f"Initializing ledger for {config.project_name}")
        ledger = initialize_ledger(
            config.project_name,
            ALL_PAGES,
            config.project_root,
        )

    # Determine pages to validate
    pages_to_validate, current_commits = compute_pages_to_validate(
        ledger,
        config.project_root,
        config.force_full,
    )

    # Start run statistics tracking
    project_commit = current_commits.get(config.project_name, "unknown")
    start_run(ledger, config.project_name, project_commit)

    # Record screenshot counts
    all_screenshots = get_all_screenshot_paths(config.project_name)
    interactive_count = sum(1 for p in all_screenshots if "_" in p.stem and p.stem != "dep_graph")
    static_count = len(all_screenshots) - interactive_count
    record_screenshots(ledger, static_count, interactive_count)

    # Filter to specific page if requested
    if config.specific_page:
        if config.specific_page in pages_to_validate:
            pages_to_validate = [config.specific_page]
        else:
            log.warning(f"Page {config.specific_page} not in validation set")
            pages_to_validate = [config.specific_page]

    # Update ledger with current commits
    update_ledger_commits(ledger, current_commits)

    # Mark pages for validation
    if pages_to_validate:
        mark_pages_for_revalidation(ledger, pages_to_validate)
        log.info(f"Pages to validate: {', '.join(pages_to_validate)}")
    else:
        log.info("No pages need validation")

    # Save ledger
    save_ledger(ledger)

    return ledger


def apply_validation_result(result: ValidationResult) -> None:
    """Apply a validation result to the ledger."""
    ledger = load_ledger()

    status = "pass" if result.passed else "fail"
    screenshot = get_screenshot_path(
        ledger.project,
        result.page,
        result.interaction,
    )

    if result.interaction:
        update_interaction_result(
            ledger,
            result.page,
            result.interaction,
            status,
            result.findings,
            str(screenshot.name) if screenshot.exists() else None,
            result.confidence,
        )
    else:
        update_page_result(
            ledger,
            result.page,
            status,
            result.findings,
            str(screenshot.name) if screenshot.exists() else None,
            result.confidence,
        )

    save_ledger(ledger)


def check_compliance_status() -> tuple[bool, ComplianceLedger]:
    """Check current compliance status.

    Returns (is_fully_compliant, ledger).
    """
    ledger = load_ledger()
    return is_fully_compliant(ledger), ledger


def get_validation_summary(ledger: ComplianceLedger) -> str:
    """Generate a summary of validation status."""
    s = ledger.summary

    lines = [
        f"## Compliance Summary: {s.compliance_percent:.1f}%",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Checks | {s.total_checks} |",
        f"| Passed | {s.passed} |",
        f"| Failed | {s.failed} |",
        f"| Pending | {s.pending} |",
        f"| Skipped | {s.skipped} |",
        "",
    ]

    if s.failed > 0:
        failed_pages = get_failed_pages(ledger)
        lines.append("### Failed Pages")
        lines.append("")
        for page in failed_pages:
            result = ledger.pages[page]
            lines.append(f"- **{page}**")
            for finding in result.findings:
                lines.append(f"  - {finding}")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# CLI Entry Point
# =============================================================================


def cmd_compliance(args) -> int:
    """Main entry point for the compliance command."""
    try:
        # Detect project
        if args.project:
            project_name = args.project
            project_root = Path.cwd()
        else:
            project_name, project_root = detect_project()

        config = ComplianceConfig(
            project_root=project_root,
            project_name=project_name,
            force_full=args.full,
            include_interactive=args.interactive,
            max_iterations=args.max_iterations,
            specific_page=args.page,
        )

        # Run compliance check
        ledger = run_compliance_check(config)

        # Print status
        print()
        print(get_validation_summary(ledger))

        # Print prompts for pages needing validation
        pages = get_pages_needing_validation(ledger)

        if pages:
            # Record that validation agents will be spawned for these pages
            record_validation_agent(ledger, len(pages))

            print("## Pages Requiring Validation")
            print()
            print("Use AI vision analysis to validate these pages:")
            print()

            for page in pages:
                screenshot = get_screenshot_path(project_name, page)
                print(f"### {page}")
                print(f"Screenshot: {screenshot}")
                print()
                print("Criteria:")
                print(format_criteria_for_prompt(page))
                print()
                print("-" * 50)
                print()

        # Finalize run statistics before checking compliance
        finalize_run(ledger)
        save_ledger(ledger)

        # Check if fully compliant
        if is_fully_compliant(ledger):
            log.success("100% compliance achieved!")
            return 0
        else:
            return 1

    except KeyboardInterrupt:
        log.warning("Compliance check interrupted")
        return 130
    except Exception as e:
        log.error(str(e))
        return 1
