"""SBS-specific tool implementations.

This module contains SBS-specific MCP tools for:
- Oracle querying (sbs_oracle_query)
- Archive state inspection (sbs_archive_state, sbs_epoch_summary)
- Context generation (sbs_context)
- Testing tools (sbs_run_tests, sbs_validate_project)
- Build tools (sbs_build_project, sbs_serve_project)
- Investigation tools (sbs_last_screenshot, sbs_visual_history, sbs_search_entries)
"""

import json
import os
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Annotated, List, Optional

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .sbs_models import (
    AnalysisFinding,
    AnalysisSummary,
    ArchiveEntrySummary,
    ArchiveStateResult,
    ContextResult,
    EpochSummaryResult,
    GitHubIssue,
    GitHubPullRequest,
    HistoryEntry,
    IssueCloseResult,
    IssueCreateResult,
    IssueGetResult,
    IssueListResult,
    OracleConcept,
    OracleMatch,
    OracleQueryResult,
    PRCreateResult,
    PRGetResult,
    PRListResult,
    PRMergeResult,
    SBSBuildResult,
    SBSValidationResult,
    ScreenshotResult,
    SearchResult,
    SelfImproveEntries,
    SelfImproveEntrySummary,
    ServeResult,
    SkillEndResult,
    SkillStartResult,
    SkillStatusResult,
    SkillTransitionResult,
    TestFailure,
    TestResult,
    ValidatorScore,
    VisualChange,
    VisualHistoryResult,
)
from .sbs_utils import (
    ARCHIVE_DIR,
    SBS_ROOT,
    aggregate_visual_changes,
    collect_projects,
    collect_tags,
    compute_hash,
    count_builds,
    format_time_range,
    generate_context_block,
    get_archived_screenshot,
    get_entry_timestamp,
    get_epoch_entries,
    get_screenshot_path,
    load_archive_index,
    load_oracle_content,
    parse_oracle_sections,
    search_oracle,
    summarize_entry,
)


def register_sbs_tools(mcp: FastMCP) -> None:
    """Register all SBS-specific tools with the MCP server.

    Args:
        mcp: The FastMCP server instance to register tools on.
    """

    @mcp.tool(
        "sbs_oracle_query",
        annotations=ToolAnnotations(
            title="SBS Oracle Query",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def sbs_oracle_query(
        ctx: Context,
        query: Annotated[str, Field(description="Natural language query to search oracle")],
        max_results: Annotated[int, Field(description="Maximum results to return", ge=1)] = 10,
    ) -> OracleQueryResult:
        """Query the SBS Oracle for file locations and concept information.

        Searches the compiled oracle (sbs-oracle.md) for matching files and concepts.
        Use for finding where things are in the codebase or understanding project structure.

        Examples:
        - "graph layout" -> finds Dress/Graph/Layout.lean
        - "status color" -> finds color model documentation
        - "archive entry" -> finds entry.py and related files
        """
        # Load and parse oracle content
        content = load_oracle_content()
        if not content:
            return OracleQueryResult(
                matches=[],
                concepts=[],
                raw_section=None,
            )

        sections = parse_oracle_sections(content)

        # Search for matches
        raw_matches = search_oracle(sections, query, max_results)

        # Convert to model objects
        matches: List[OracleMatch] = []
        concepts: List[OracleConcept] = []

        for match in raw_matches:
            if match["file"]:
                matches.append(
                    OracleMatch(
                        file=match["file"],
                        lines=match.get("lines"),
                        context=match["context"],
                        relevance=match["relevance"],
                    )
                )
            else:
                # Extract concept name from context if possible
                context_str = match["context"]
                if "Concept '" in context_str:
                    # Parse: "Concept 'name' in section: Section Name"
                    start = context_str.find("'") + 1
                    end = context_str.find("'", start)
                    if start > 0 and end > start:
                        name = context_str[start:end]
                        section = context_str.split("in section: ")[-1] if "in section: " in context_str else ""
                        concepts.append(OracleConcept(name=name, section=section))

        # Check for exact section match
        raw_section = None
        query_lower = query.lower()
        for section_name, section_content in sections.get("sections", {}).items():
            if query_lower in section_name.lower():
                raw_section = f"## {section_name}\n{section_content}"
                break

        return OracleQueryResult(
            matches=matches,
            concepts=concepts,
            raw_section=raw_section,
        )

    @mcp.tool(
        "sbs_archive_state",
        annotations=ToolAnnotations(
            title="SBS Archive State",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def sbs_archive_state(ctx: Context) -> ArchiveStateResult:
        """Get current orchestration state from the archive.

        Returns the global state machine status, last epoch entry, and count of entries
        in the current epoch. Use to understand what skill/substate is active and how
        much work has accumulated since last /update-and-archive.

        The global_state field shows:
        - null: System is idle (between tasks)
        - {skill: "task", substate: "alignment"}: In /task skill, alignment phase
        - {skill: "update-and-archive", substate: "execution"}: In /update-and-archive
        """
        index = load_archive_index()

        # Get entries in current epoch
        current_epoch_entries = get_epoch_entries(index, epoch_entry_id=None)

        # Get all unique projects
        all_projects = sorted(index.by_project.keys())

        # Get last epoch timestamp
        last_epoch_timestamp = get_entry_timestamp(index, index.last_epoch_entry)

        return ArchiveStateResult(
            global_state=index.global_state,
            last_epoch_entry=index.last_epoch_entry,
            last_epoch_timestamp=last_epoch_timestamp,
            entries_in_current_epoch=len(current_epoch_entries),
            total_entries=len(index.entries),
            projects=all_projects,
        )

    @mcp.tool(
        "sbs_epoch_summary",
        annotations=ToolAnnotations(
            title="SBS Epoch Summary",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def sbs_epoch_summary(
        ctx: Context,
        epoch_entry_id: Annotated[
            Optional[str],
            Field(description="Entry ID that closed the epoch (omit for current)"),
        ] = None,
    ) -> EpochSummaryResult:
        """Get aggregate statistics for an epoch.

        An epoch is the set of entries between two /update-and-archive invocations.
        Returns counts, visual changes, tags used, and other summary data.

        Use this to understand:
        - How much work happened in a period
        - What visual changes occurred
        - Which projects were touched
        - What tags were applied
        """
        index = load_archive_index()

        # Get entries for the specified epoch
        entries = get_epoch_entries(index, epoch_entry_id)

        if not entries:
            # Return empty summary
            return EpochSummaryResult(
                epoch_id=epoch_entry_id or "current",
                started_at="",
                ended_at="",
                entries=0,
                builds=0,
                visual_changes=[],
                tags_used=[],
                projects_touched=[],
            )

        # Sort entries by ID (chronological order)
        sorted_entries = sorted(entries, key=lambda e: e.entry_id)

        # Compute aggregates
        visual_changes_raw = aggregate_visual_changes(sorted_entries)
        visual_changes = [
            VisualChange(
                entry_id=vc["entry_id"],
                screenshots=vc["screenshots"],
                timestamp=vc["timestamp"],
            )
            for vc in visual_changes_raw
        ]

        tags_used = collect_tags(sorted_entries)
        projects_touched = collect_projects(sorted_entries)
        builds = count_builds(sorted_entries)

        # Get time bounds
        started_at = sorted_entries[0].created_at if sorted_entries else ""
        ended_at = sorted_entries[-1].created_at if sorted_entries else ""

        return EpochSummaryResult(
            epoch_id=epoch_entry_id or "current",
            started_at=started_at,
            ended_at=ended_at,
            entries=len(sorted_entries),
            builds=builds,
            visual_changes=visual_changes,
            tags_used=tags_used,
            projects_touched=projects_touched,
        )

    @mcp.tool(
        "sbs_context",
        annotations=ToolAnnotations(
            title="SBS Context Block",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def sbs_context(
        ctx: Context,
        include: Annotated[
            Optional[List[str]],
            Field(description="Sections to include: state, epoch, quality, recent"),
        ] = None,
        max_entries: Annotated[
            int,
            Field(description="Max recent entries to include", ge=1),
        ] = 10,
    ) -> ContextResult:
        """Build a formatted context block for agent injection.

        Generates a markdown-formatted context block containing selected information
        from the archive. Use this to inject context into agent prompts.

        Available sections:
        - state: Current global state and active skill/substate
        - epoch: Summary of current epoch
        - quality: Latest quality scores (if available)
        - recent: Recent entries summary

        Default includes all sections if none specified.
        """
        if include is None:
            include = ["state", "epoch", "quality", "recent"]

        index = load_archive_index()
        lines: List[str] = []
        entry_count = 0

        # State section
        if "state" in include:
            lines.append("## Orchestration State")
            lines.append("")
            if index.global_state:
                skill = index.global_state.get("skill", "unknown")
                substate = index.global_state.get("substate", "unknown")
                lines.append(f"- **Active Skill:** {skill}")
                lines.append(f"- **Substate:** {substate}")
            else:
                lines.append("- **Status:** Idle (no active skill)")

            if index.last_epoch_entry:
                lines.append(f"- **Last Epoch:** {index.last_epoch_entry}")
                timestamp = get_entry_timestamp(index, index.last_epoch_entry)
                if timestamp:
                    lines.append(f"- **Last Epoch Time:** {timestamp}")
            lines.append("")

        # Epoch section
        if "epoch" in include:
            current_entries = get_epoch_entries(index, epoch_entry_id=None)
            sorted_entries = sorted(current_entries, key=lambda e: e.entry_id)

            lines.append("## Current Epoch")
            lines.append("")
            lines.append(f"- **Entries:** {len(sorted_entries)}")
            lines.append(f"- **Builds:** {count_builds(sorted_entries)}")

            time_range = format_time_range(sorted_entries)
            if time_range:
                lines.append(f"- **Duration:** {time_range}")

            projects = collect_projects(sorted_entries)
            if projects:
                lines.append(f"- **Projects:** {', '.join(projects)}")

            tags = collect_tags(sorted_entries)
            if tags:
                lines.append(f"- **Tags:** {', '.join(tags[:10])}")
                if len(tags) > 10:
                    lines.append(f"  *(+{len(tags) - 10} more)*")
            lines.append("")

            entry_count += len(sorted_entries)

        # Quality section
        if "quality" in include:
            # Find most recent entry with quality scores
            sorted_all = sorted(index.entries.values(), key=lambda e: e.entry_id, reverse=True)
            quality_entry = None
            for entry in sorted_all:
                if entry.quality_scores:
                    quality_entry = entry
                    break

            lines.append("## Quality Scores")
            lines.append("")
            if quality_entry and quality_entry.quality_scores:
                overall = quality_entry.quality_scores.get("overall", "N/A")
                lines.append(f"- **Overall:** {overall}")
                lines.append(f"- **From Entry:** {quality_entry.entry_id}")

                scores = quality_entry.quality_scores.get("scores", {})
                if scores:
                    lines.append("- **Breakdown:**")
                    for metric_id, score_data in sorted(scores.items()):
                        if isinstance(score_data, dict):
                            value = score_data.get("value", "?")
                            passed = score_data.get("passed", False)
                            status = "PASS" if passed else "FAIL"
                            lines.append(f"  - {metric_id}: {value} ({status})")
                        else:
                            lines.append(f"  - {metric_id}: {score_data}")
            else:
                lines.append("- No quality scores recorded yet")
            lines.append("")

        # Recent entries section
        if "recent" in include:
            sorted_all = sorted(index.entries.values(), key=lambda e: e.entry_id, reverse=True)
            recent = sorted_all[:max_entries]

            lines.append("## Recent Activity")
            lines.append("")
            if recent:
                context_block = generate_context_block(recent, max_entries)
                # Skip the header since we already have one
                context_lines = context_block.split("\n")
                for line in context_lines:
                    if not line.startswith("## "):
                        lines.append(line)
            else:
                lines.append("No recent entries.")
            lines.append("")

            entry_count += len(recent)

        # Calculate time range for the response
        if entry_count > 0:
            sorted_all = sorted(index.entries.values(), key=lambda e: e.entry_id, reverse=True)
            time_range = format_time_range(sorted_all[:entry_count])
        else:
            time_range = None

        return ContextResult(
            context_block="\n".join(lines),
            entry_count=entry_count,
            time_range=time_range,
        )

    # =========================================================================
    # Testing Tools
    # =========================================================================

    @mcp.tool(
        "sbs_run_tests",
        annotations=ToolAnnotations(
            title="SBS Run Tests",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def sbs_run_tests(
        ctx: Context,
        path: Annotated[
            Optional[str],
            Field(description="Test path relative to dev/scripts (default: sbs/tests/pytest)"),
        ] = None,
        filter: Annotated[
            Optional[str],
            Field(description="Pytest -k filter pattern"),
        ] = None,
        tier: Annotated[
            Optional[str],
            Field(description="Test tier to run: evergreen, dev, temporary, or all (default: all)"),
        ] = None,
        verbose: Annotated[
            bool,
            Field(description="Show verbose output"),
        ] = False,
    ) -> TestResult:
        """Run pytest suite and return structured results.

        Runs tests in the SBS dev/scripts directory. Returns pass/fail counts
        and details about any failures.

        Examples:
        - Run all tests: sbs_run_tests()
        - Run specific tests: sbs_run_tests(filter="test_color")
        - Run tests in a specific path: sbs_run_tests(path="sbs/tests/pytest/validators")
        - Run only evergreen tests: sbs_run_tests(tier="evergreen")
        """
        scripts_dir = SBS_ROOT / "dev" / "scripts"
        test_path = path or "sbs/tests/pytest"

        # Build pytest command
        cmd = ["python", "-m", "pytest", test_path]

        if filter:
            cmd.extend(["-k", filter])

        # Add tier marker filter if specified
        if tier and tier != "all":
            cmd.extend(["-m", tier])

        if verbose:
            cmd.append("-v")

        # Try to use json-report plugin for structured output
        cmd.extend(["--tb=short", "-q"])

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=scripts_dir,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            duration = time.time() - start_time

            # Parse output to extract counts
            output = result.stdout + result.stderr
            passed, failed, errors, skipped = _parse_pytest_output(output)
            failures = _extract_failures(output)

            return TestResult(
                passed=passed,
                failed=failed,
                errors=errors,
                skipped=skipped,
                duration_seconds=round(duration, 2),
                failures=failures,
            )

        except subprocess.TimeoutExpired:
            return TestResult(
                passed=0,
                failed=0,
                errors=1,
                skipped=0,
                duration_seconds=300.0,
                failures=[
                    TestFailure(
                        test_name="TIMEOUT",
                        message="Test execution timed out after 5 minutes",
                        file=None,
                        line=None,
                    )
                ],
            )
        except Exception as e:
            return TestResult(
                passed=0,
                failed=0,
                errors=1,
                skipped=0,
                duration_seconds=time.time() - start_time,
                failures=[
                    TestFailure(
                        test_name="ERROR",
                        message=str(e),
                        file=None,
                        line=None,
                    )
                ],
            )

    @mcp.tool(
        "sbs_validate_project",
        annotations=ToolAnnotations(
            title="SBS Validate Project",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def sbs_validate_project(
        ctx: Context,
        project: Annotated[
            str,
            Field(description="Project name: SBSTest, GCR, or PNT"),
        ],
        validators: Annotated[
            Optional[List[str]],
            Field(description="Validators to run (T1-T8), default: T5,T6"),
        ] = None,
    ) -> SBSValidationResult:
        """Run T1-T8 validators on a project.

        Validators check various quality dimensions:
        - T1: CLI Execution (10%)
        - T2: Ledger Population (10%)
        - T5: Status Color Match (15%)
        - T6: CSS Variable Coverage (15%)
        - T3: Dashboard Clarity (10%) [heuristic]
        - T4: Toggle Discoverability (10%) [heuristic]
        - T7: Jarring-Free Check (15%) [heuristic]
        - T8: Professional Score (15%) [heuristic]

        Default runs T5 and T6 (deterministic tests).
        """
        scripts_dir = SBS_ROOT / "dev" / "scripts"

        # Normalize project name
        project_map = {
            "SBSTest": "SBSTest",
            "sbs-test": "SBSTest",
            "GCR": "GCR",
            "gcr": "GCR",
            "General_Crystallographic_Restriction": "GCR",
            "PNT": "PNT",
            "pnt": "PNT",
            "PrimeNumberTheoremAnd": "PNT",
        }
        normalized_project = project_map.get(project, project)

        # Default validators
        if validators is None:
            validators = ["T5", "T6"]

        # Normalize validator names (accept T5, t5, t5-color-match, etc.)
        validator_ids = []
        for v in validators:
            v_upper = v.upper()
            if v_upper.startswith("T") and v_upper[1:].isdigit():
                validator_ids.append(v_upper)
            elif v.startswith("t") and "-" in v:
                # Extract T number from t5-color-match format
                num = v.split("-")[0][1:]
                validator_ids.append(f"T{num}")
            else:
                validator_ids.append(v_upper)

        # Run validation via sbs validate-all command
        # This is the simplest approach - use the existing CLI
        cmd = ["python", "-m", "sbs", "validate-all", "--project", normalized_project]

        try:
            result = subprocess.run(
                cmd,
                cwd=scripts_dir,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
            )

            # Parse output to extract scores
            output = result.stdout + result.stderr
            results, overall_score, passed = _parse_validation_output(output, validator_ids)

            return SBSValidationResult(
                overall_score=overall_score,
                passed=passed,
                results=results,
                timestamp=datetime.now().isoformat(),
            )

        except subprocess.TimeoutExpired:
            return SBSValidationResult(
                overall_score=0.0,
                passed=False,
                results={
                    "error": ValidatorScore(
                        value=0.0,
                        passed=False,
                        stale=False,
                        findings=["Validation timed out after 2 minutes"],
                    )
                },
                timestamp=datetime.now().isoformat(),
            )
        except Exception as e:
            return SBSValidationResult(
                overall_score=0.0,
                passed=False,
                results={
                    "error": ValidatorScore(
                        value=0.0,
                        passed=False,
                        stale=False,
                        findings=[f"Validation error: {str(e)}"],
                    )
                },
                timestamp=datetime.now().isoformat(),
            )

    # =========================================================================
    # Build Tools
    # =========================================================================

    @mcp.tool(
        "sbs_build_project",
        annotations=ToolAnnotations(
            title="SBS Build Project",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    def sbs_build_project(
        ctx: Context,
        project: Annotated[
            str,
            Field(description="Project name: SBSTest, GCR, or PNT"),
        ],
        dry_run: Annotated[
            bool,
            Field(description="Show what would be done without building"),
        ] = False,
        skip_cache: Annotated[
            bool,
            Field(description="Skip lake cache"),
        ] = False,
    ) -> SBSBuildResult:
        """Trigger build.py for a project.

        Runs the full build pipeline for a showcase project. This includes
        Lake build, artifact generation, and site generation.

        WARNING: Full builds can take several minutes:
        - SBS-Test: ~2 minutes
        - GCR: ~5 minutes
        - PNT: ~20 minutes
        """
        # Map project names to paths
        project_paths = {
            "SBSTest": SBS_ROOT / "toolchain" / "SBS-Test",
            "sbs-test": SBS_ROOT / "toolchain" / "SBS-Test",
            "GCR": SBS_ROOT / "showcase" / "General_Crystallographic_Restriction",
            "gcr": SBS_ROOT / "showcase" / "General_Crystallographic_Restriction",
            "General_Crystallographic_Restriction": SBS_ROOT / "showcase" / "General_Crystallographic_Restriction",
            "PNT": SBS_ROOT / "showcase" / "PrimeNumberTheoremAnd",
            "pnt": SBS_ROOT / "showcase" / "PrimeNumberTheoremAnd",
            "PrimeNumberTheoremAnd": SBS_ROOT / "showcase" / "PrimeNumberTheoremAnd",
        }

        project_path = project_paths.get(project)
        if not project_path:
            return SBSBuildResult(
                success=False,
                duration_seconds=0.0,
                build_run_id=None,
                errors=[f"Unknown project: {project}. Valid: SBSTest, GCR, PNT"],
                warnings=[],
                project=project,
                manifest_path=None,
            )

        if not project_path.exists():
            return SBSBuildResult(
                success=False,
                duration_seconds=0.0,
                build_run_id=None,
                errors=[f"Project path does not exist: {project_path}"],
                warnings=[],
                project=project,
                manifest_path=None,
            )

        # Build command
        scripts_dir = SBS_ROOT / "dev" / "scripts"
        cmd = ["python", str(scripts_dir / "build.py")]

        if dry_run:
            cmd.append("--dry-run")
        if skip_cache:
            cmd.append("--skip-cache")

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minute timeout
            )
            duration = time.time() - start_time

            output = result.stdout + result.stderr
            success = result.returncode == 0

            # Extract build_run_id from output if present
            build_run_id = _extract_build_run_id(output)

            # Extract errors and warnings
            errors = []
            warnings = []
            for line in output.split("\n"):
                if "[ERROR]" in line or "error:" in line.lower():
                    errors.append(line.strip())
                elif "[WARN]" in line or "warning:" in line.lower():
                    warnings.append(line.strip())

            # Check for manifest
            manifest_path = project_path / ".lake" / "build" / "runway" / "manifest.json"
            manifest_str = str(manifest_path) if manifest_path.exists() else None

            return SBSBuildResult(
                success=success,
                duration_seconds=round(duration, 2),
                build_run_id=build_run_id,
                errors=errors[:10],  # Limit to 10
                warnings=warnings[:10],  # Limit to 10
                project=project,
                manifest_path=manifest_str,
            )

        except subprocess.TimeoutExpired:
            return SBSBuildResult(
                success=False,
                duration_seconds=1800.0,
                build_run_id=None,
                errors=["Build timed out after 30 minutes"],
                warnings=[],
                project=project,
                manifest_path=None,
            )
        except Exception as e:
            return SBSBuildResult(
                success=False,
                duration_seconds=time.time() - start_time,
                build_run_id=None,
                errors=[str(e)],
                warnings=[],
                project=project,
                manifest_path=None,
            )

    @mcp.tool(
        "sbs_serve_project",
        annotations=ToolAnnotations(
            title="SBS Serve Project",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    def sbs_serve_project(
        ctx: Context,
        project: Annotated[
            str,
            Field(description="Project name: SBSTest, GCR, or PNT"),
        ],
        action: Annotated[
            str,
            Field(description="Action: start, stop, or status"),
        ],
        port: Annotated[
            int,
            Field(description="Port number"),
        ] = 8000,
    ) -> ServeResult:
        """Start or check status of local dev server.

        Serves the built site from the project's _site directory.
        Actions:
        - start: Start server on specified port
        - stop: Stop running server
        - status: Check if server is running
        """
        # Map project names to site paths
        site_paths = {
            "SBSTest": SBS_ROOT / "toolchain" / "SBS-Test" / "_site",
            "sbs-test": SBS_ROOT / "toolchain" / "SBS-Test" / "_site",
            "GCR": SBS_ROOT / "showcase" / "General_Crystallographic_Restriction" / "_site",
            "gcr": SBS_ROOT / "showcase" / "General_Crystallographic_Restriction" / "_site",
            "General_Crystallographic_Restriction": SBS_ROOT / "showcase" / "General_Crystallographic_Restriction" / "_site",
            "PNT": SBS_ROOT / "showcase" / "PrimeNumberTheoremAnd" / "_site",
            "pnt": SBS_ROOT / "showcase" / "PrimeNumberTheoremAnd" / "_site",
            "PrimeNumberTheoremAnd": SBS_ROOT / "showcase" / "PrimeNumberTheoremAnd" / "_site",
        }

        site_path = site_paths.get(project)
        if not site_path:
            return ServeResult(
                running=False,
                url=None,
                pid=None,
                project=project,
            )

        # Normalize project name for state file
        project_map = {
            "SBSTest": "SBSTest",
            "sbs-test": "SBSTest",
            "GCR": "GCR",
            "gcr": "GCR",
            "General_Crystallographic_Restriction": "GCR",
            "PNT": "PNT",
            "pnt": "PNT",
            "PrimeNumberTheoremAnd": "PNT",
        }
        normalized_project = project_map.get(project, project)

        # State file for tracking servers
        state_dir = Path.home() / ".cache" / "sbs-lsp-mcp"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "servers.json"

        # Load current state
        servers = {}
        if state_file.exists():
            try:
                servers = json.loads(state_file.read_text())
            except Exception:
                servers = {}

        if action == "status":
            # Check if server is running
            server_info = servers.get(normalized_project)
            if server_info:
                pid = server_info.get("pid")
                if pid and _is_process_running(pid):
                    return ServeResult(
                        running=True,
                        url=f"http://localhost:{server_info.get('port', 8000)}",
                        pid=pid,
                        project=normalized_project,
                    )
                else:
                    # Clean up stale entry
                    del servers[normalized_project]
                    state_file.write_text(json.dumps(servers))

            return ServeResult(
                running=False,
                url=None,
                pid=None,
                project=normalized_project,
            )

        elif action == "stop":
            # Stop the server
            server_info = servers.get(normalized_project)
            if server_info:
                pid = server_info.get("pid")
                if pid:
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass  # Already dead

                del servers[normalized_project]
                state_file.write_text(json.dumps(servers))

            return ServeResult(
                running=False,
                url=None,
                pid=None,
                project=normalized_project,
            )

        elif action == "start":
            # Check if already running
            server_info = servers.get(normalized_project)
            if server_info:
                pid = server_info.get("pid")
                if pid and _is_process_running(pid):
                    return ServeResult(
                        running=True,
                        url=f"http://localhost:{server_info.get('port', port)}",
                        pid=pid,
                        project=normalized_project,
                    )

            # Check if site directory exists
            if not site_path.exists():
                return ServeResult(
                    running=False,
                    url=None,
                    pid=None,
                    project=normalized_project,
                )

            # Start server
            try:
                process = subprocess.Popen(
                    ["python", "-m", "http.server", str(port)],
                    cwd=site_path,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )

                # Save state
                servers[normalized_project] = {
                    "pid": process.pid,
                    "port": port,
                    "site_path": str(site_path),
                    "started_at": datetime.now().isoformat(),
                }
                state_file.write_text(json.dumps(servers))

                # Give it a moment to start
                time.sleep(0.5)

                if _is_process_running(process.pid):
                    return ServeResult(
                        running=True,
                        url=f"http://localhost:{port}",
                        pid=process.pid,
                        project=normalized_project,
                    )
                else:
                    return ServeResult(
                        running=False,
                        url=None,
                        pid=None,
                        project=normalized_project,
                    )

            except Exception:
                return ServeResult(
                    running=False,
                    url=None,
                    pid=None,
                    project=normalized_project,
                )

        else:
            # Unknown action
            return ServeResult(
                running=False,
                url=None,
                pid=None,
                project=normalized_project,
            )

    # =========================================================================
    # Investigation Tools
    # =========================================================================

    @mcp.tool(
        "sbs_last_screenshot",
        annotations=ToolAnnotations(
            title="SBS Last Screenshot",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def sbs_last_screenshot(
        ctx: Context,
        project: Annotated[
            str,
            Field(description="Project name (SBSTest, GCR, PNT)"),
        ],
        page: Annotated[
            str,
            Field(description="Page name (dashboard, dep_graph, paper_tex, pdf_tex, chapter, etc.)"),
        ],
    ) -> ScreenshotResult:
        """Get most recent screenshot for a page WITHOUT building.

        Returns the path to the latest captured screenshot for a given project/page
        combination. This allows viewing previous build results without triggering
        a new build.

        Common page names:
        - dashboard: Main project dashboard
        - dep_graph: Dependency graph visualization
        - paper_tex: Paper from TeX source
        - pdf_tex: PDF from TeX source
        - paper_verso: Paper from Verso source
        - blueprint_verso: Blueprint from Verso source
        - chapter: First chapter page
        """
        # Normalize project name
        project_map = {
            "SBSTest": "SBSTest",
            "sbs-test": "SBSTest",
            "GCR": "GCR",
            "gcr": "GCR",
            "General_Crystallographic_Restriction": "GCR",
            "PNT": "PNT",
            "pnt": "PNT",
            "PrimeNumberTheoremAnd": "PNT",
        }
        normalized_project = project_map.get(project, project)

        # Get screenshot path
        screenshot_path = get_screenshot_path(normalized_project, page)

        if not screenshot_path.exists():
            return ScreenshotResult(
                image_path="",
                entry_id="",
                captured_at="",
                hash=None,
                page=page,
                project=normalized_project,
            )

        # Load capture metadata
        capture_json_path = screenshot_path.parent / "capture.json"
        captured_at = ""
        entry_id = ""

        if capture_json_path.exists():
            try:
                capture_data = json.loads(capture_json_path.read_text())
                captured_at = capture_data.get("timestamp", "")
                # Convert timestamp to entry_id format
                if captured_at:
                    # Parse ISO timestamp and convert to entry_id format
                    try:
                        dt = datetime.fromisoformat(captured_at)
                        entry_id = dt.strftime("%Y%m%d%H%M%S")
                    except ValueError:
                        entry_id = ""
            except (json.JSONDecodeError, IOError):
                pass

        # Compute hash for change detection
        file_hash = compute_hash(screenshot_path)

        return ScreenshotResult(
            image_path=str(screenshot_path),
            entry_id=entry_id,
            captured_at=captured_at,
            hash=file_hash,
            page=page,
            project=normalized_project,
        )

    @mcp.tool(
        "sbs_visual_history",
        annotations=ToolAnnotations(
            title="SBS Visual History",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def sbs_visual_history(
        ctx: Context,
        project: Annotated[
            str,
            Field(description="Project name (SBSTest, GCR, PNT)"),
        ],
        page: Annotated[
            str,
            Field(description="Page name (dashboard, dep_graph, paper_tex, etc.)"),
        ],
        limit: Annotated[
            int,
            Field(description="Number of entries to include", ge=1),
        ] = 5,
    ) -> VisualHistoryResult:
        """See how a page looked across recent archive entries.

        Returns a history of screenshots for a page, with hash comparison to
        identify which entries had visual changes. Useful for tracking when
        visual changes occurred.
        """
        # Normalize project name
        project_map = {
            "SBSTest": "SBSTest",
            "sbs-test": "SBSTest",
            "GCR": "GCR",
            "gcr": "GCR",
            "General_Crystallographic_Restriction": "GCR",
            "PNT": "PNT",
            "pnt": "PNT",
            "PrimeNumberTheoremAnd": "PNT",
        }
        normalized_project = project_map.get(project, project)

        # Load archive index
        index = load_archive_index()

        # Get entries for this project, sorted by entry_id descending (most recent first)
        project_entries = index.get_entries_by_project(normalized_project)
        sorted_entries = sorted(project_entries, key=lambda e: e.entry_id, reverse=True)

        # Build history entries
        history: List[HistoryEntry] = []
        total_with_screenshots = 0

        for entry in sorted_entries:
            # Check if this entry has the requested page screenshot
            if page + ".png" in entry.screenshots or page in entry.screenshots:
                total_with_screenshots += 1

                if len(history) < limit:
                    # Convert entry_id to directory format
                    dir_name = _entry_id_to_dir_format(entry.entry_id)
                    screenshot_path = ARCHIVE_DIR / normalized_project / "archive" / dir_name / f"{page}.png"

                    # Compute hash if file exists
                    hash_map = {}
                    if screenshot_path.exists():
                        file_hash = compute_hash(screenshot_path)
                        if file_hash:
                            hash_map[page] = file_hash

                    history.append(
                        HistoryEntry(
                            entry_id=entry.entry_id,
                            timestamp=entry.created_at,
                            screenshots=[f"{page}.png"],
                            hash_map=hash_map,
                            tags=entry.tags + entry.auto_tags,
                        )
                    )

        return VisualHistoryResult(
            project=normalized_project,
            history=history,
            total_count=total_with_screenshots,
        )

    @mcp.tool(
        "sbs_search_entries",
        annotations=ToolAnnotations(
            title="SBS Search Entries",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def sbs_search_entries(
        ctx: Context,
        project: Annotated[
            Optional[str],
            Field(description="Filter by project name (SBSTest, GCR, PNT)"),
        ] = None,
        tags: Annotated[
            Optional[List[str]],
            Field(description="Filter by tags (any match)"),
        ] = None,
        since: Annotated[
            Optional[str],
            Field(description="Entry ID or ISO timestamp to filter from"),
        ] = None,
        trigger: Annotated[
            Optional[str],
            Field(description="Filter by trigger type (build, manual, skill)"),
        ] = None,
        limit: Annotated[
            int,
            Field(description="Maximum entries to return", ge=1),
        ] = 20,
    ) -> SearchResult:
        """Search archive entries by various criteria.

        Flexible search across the archive. All filters are optional and combined
        with AND logic. Returns entries sorted by timestamp descending.

        For tags, matches if ANY tag in the list matches (OR within tags).
        """
        # Normalize project name if provided
        project_map = {
            "SBSTest": "SBSTest",
            "sbs-test": "SBSTest",
            "GCR": "GCR",
            "gcr": "GCR",
            "General_Crystallographic_Restriction": "GCR",
            "PNT": "PNT",
            "pnt": "PNT",
            "PrimeNumberTheoremAnd": "PNT",
        }
        normalized_project = project_map.get(project, project) if project else None

        # Load archive index
        index = load_archive_index()

        # Start with all entries sorted by entry_id descending
        all_entries = sorted(index.entries.values(), key=lambda e: e.entry_id, reverse=True)

        # Apply filters
        filtered_entries = []
        for entry in all_entries:
            # Project filter
            if normalized_project and entry.project != normalized_project:
                continue

            # Tags filter (OR within tags - match if ANY tag matches)
            if tags:
                entry_tags = set(entry.tags + entry.auto_tags)
                if not any(tag in entry_tags for tag in tags):
                    continue

            # Since filter
            if since:
                # Handle both entry_id format and ISO timestamp
                since_id = since
                if "-" in since:
                    # Looks like ISO timestamp, convert to entry_id
                    try:
                        dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                        since_id = dt.strftime("%Y%m%d%H%M%S")
                    except ValueError:
                        # Try parsing as dir format
                        since_id = _dir_format_to_entry_id(since)

                if entry.entry_id <= since_id:
                    continue

            # Trigger filter
            if trigger and entry.trigger != trigger:
                continue

            filtered_entries.append(entry)

        total_count = len(filtered_entries)

        # Limit results
        limited_entries = filtered_entries[:limit]

        # Convert to summaries
        summaries = [
            ArchiveEntrySummary(
                entry_id=entry.entry_id,
                created_at=entry.created_at,
                project=entry.project,
                trigger=entry.trigger,
                tags=entry.tags + entry.auto_tags,
                has_screenshots=len(entry.screenshots) > 0,
                notes_preview=entry.notes[:100] if entry.notes else "",
                build_run_id=entry.build_run_id,
            )
            for entry in limited_entries
        ]

        # Build filters dict for response
        filters_dict = {}
        if normalized_project:
            filters_dict["project"] = normalized_project
        if tags:
            filters_dict["tags"] = tags
        if since:
            filters_dict["since"] = since
        if trigger:
            filters_dict["trigger"] = trigger

        return SearchResult(
            entries=summaries,
            total_count=total_count,
            query=None,
            filters=filters_dict,
        )

    # =========================================================================
    # GitHub Issue Tools
    # =========================================================================

    GITHUB_REPO = "e-vergo/Side-By-Side-Blueprint"

    @mcp.tool(
        "sbs_issue_create",
        annotations=ToolAnnotations(
            title="SBS Issue Create",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    def sbs_issue_create(
        ctx: Context,
        title: Annotated[
            str,
            Field(description="Issue title"),
        ],
        body: Annotated[
            Optional[str],
            Field(description="Issue body/description"),
        ] = None,
        label: Annotated[
            Optional[str],
            Field(description="Issue label: bug, feature, or idea"),
        ] = None,
        area: Annotated[
            Optional[str],
            Field(description="Area label: sbs, devtools, or misc"),
        ] = None,
    ) -> IssueCreateResult:
        """Create a new GitHub issue in the SBS repository.

        Creates an issue in e-vergo/Side-By-Side-Blueprint.

        Examples:
        - sbs_issue_create(title="Bug in graph layout")
        - sbs_issue_create(title="Add dark mode", body="Details here", label="feature")
        - sbs_issue_create(title="Fix Verso export", label="bug", area="sbs")
        """
        # Attribution footer for AI transparency
        attribution = "\n\n---\n🤖 Created with [Claude Code](https://claude.ai/code)"
        full_body = (body or "") + attribution

        cmd = ["gh", "issue", "create", "--repo", GITHUB_REPO, "--title", title]
        cmd.extend(["--body", full_body])

        # Always add ai-authored label, plus optional type and area labels
        labels = ["ai-authored"]
        if label:
            labels.append(label)
        if area:
            labels.append(f"area:{area}")
        cmd.extend(["--label", ",".join(labels)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return IssueCreateResult(
                    success=False,
                    number=None,
                    url=None,
                    error=result.stderr.strip() or "Failed to create issue",
                )

            # Parse URL from output (e.g., "https://github.com/e-vergo/Side-By-Side-Blueprint/issues/123")
            url = result.stdout.strip()
            number = None
            if url and "/issues/" in url:
                try:
                    number = int(url.split("/issues/")[-1])
                except ValueError:
                    pass

            return IssueCreateResult(
                success=True,
                number=number,
                url=url,
                error=None,
            )

        except subprocess.TimeoutExpired:
            return IssueCreateResult(
                success=False,
                number=None,
                url=None,
                error="Command timed out after 30 seconds",
            )
        except Exception as e:
            return IssueCreateResult(
                success=False,
                number=None,
                url=None,
                error=str(e),
            )

    @mcp.tool(
        "sbs_issue_list",
        annotations=ToolAnnotations(
            title="SBS Issue List",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    def sbs_issue_list(
        ctx: Context,
        state: Annotated[
            Optional[str],
            Field(description="Issue state filter: open, closed, or all (default: open)"),
        ] = None,
        label: Annotated[
            Optional[str],
            Field(description="Filter by label"),
        ] = None,
        limit: Annotated[
            int,
            Field(description="Maximum issues to return", ge=1),
        ] = 20,
    ) -> IssueListResult:
        """List GitHub issues from the SBS repository.

        Lists issues from e-vergo/Side-By-Side-Blueprint.

        Examples:
        - sbs_issue_list()  # Open issues
        - sbs_issue_list(state="closed", limit=10)
        - sbs_issue_list(label="bug")
        """
        cmd = [
            "gh", "issue", "list",
            "--repo", GITHUB_REPO,
            "--json", "number,title,state,labels,url,body,createdAt",
            "--limit", str(limit),
        ]

        if state:
            cmd.extend(["--state", state])
        if label:
            cmd.extend(["--label", label])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return IssueListResult(
                    issues=[],
                    total=0,
                )

            # Parse JSON output
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                return IssueListResult(
                    issues=[],
                    total=0,
                )

            issues = []
            for item in data:
                # Extract label names from label objects
                label_names = []
                for lbl in item.get("labels", []):
                    if isinstance(lbl, dict):
                        label_names.append(lbl.get("name", ""))
                    elif isinstance(lbl, str):
                        label_names.append(lbl)

                issues.append(
                    GitHubIssue(
                        number=item.get("number", 0),
                        title=item.get("title", ""),
                        state=item.get("state", ""),
                        labels=label_names,
                        url=item.get("url", ""),
                        body=item.get("body"),
                        created_at=item.get("createdAt"),
                    )
                )

            return IssueListResult(
                issues=issues,
                total=len(issues),
            )

        except subprocess.TimeoutExpired:
            return IssueListResult(
                issues=[],
                total=0,
            )
        except Exception:
            return IssueListResult(
                issues=[],
                total=0,
            )

    @mcp.tool(
        "sbs_issue_get",
        annotations=ToolAnnotations(
            title="SBS Issue Get",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    def sbs_issue_get(
        ctx: Context,
        number: Annotated[
            int,
            Field(description="Issue number to fetch"),
        ],
    ) -> IssueGetResult:
        """Get details of a specific GitHub issue.

        Fetches a single issue from e-vergo/Side-By-Side-Blueprint by number.

        Examples:
        - sbs_issue_get(number=123)
        """
        cmd = [
            "gh", "issue", "view", str(number),
            "--repo", GITHUB_REPO,
            "--json", "number,title,state,labels,url,body,createdAt",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return IssueGetResult(
                    success=False,
                    issue=None,
                    error=result.stderr.strip() or f"Issue #{number} not found",
                )

            # Parse JSON output
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                return IssueGetResult(
                    success=False,
                    issue=None,
                    error="Failed to parse issue data",
                )

            # Extract label names from label objects
            label_names = []
            for lbl in data.get("labels", []):
                if isinstance(lbl, dict):
                    label_names.append(lbl.get("name", ""))
                elif isinstance(lbl, str):
                    label_names.append(lbl)

            issue = GitHubIssue(
                number=data.get("number", 0),
                title=data.get("title", ""),
                state=data.get("state", ""),
                labels=label_names,
                url=data.get("url", ""),
                body=data.get("body"),
                created_at=data.get("createdAt"),
            )

            return IssueGetResult(
                success=True,
                issue=issue,
                error=None,
            )

        except subprocess.TimeoutExpired:
            return IssueGetResult(
                success=False,
                issue=None,
                error="Command timed out after 30 seconds",
            )
        except Exception as e:
            return IssueGetResult(
                success=False,
                issue=None,
                error=str(e),
            )

    @mcp.tool(
        "sbs_issue_close",
        annotations=ToolAnnotations(
            title="SBS Issue Close",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    def sbs_issue_close(
        ctx: Context,
        number: Annotated[
            int,
            Field(description="Issue number to close"),
        ],
        comment: Annotated[
            Optional[str],
            Field(description="Optional comment when closing"),
        ] = None,
    ) -> IssueCloseResult:
        """Close a GitHub issue in the SBS repository.

        Closes an issue in e-vergo/Side-By-Side-Blueprint.

        Examples:
        - sbs_issue_close(number=123)
        - sbs_issue_close(number=123, comment="Fixed in PR #456")
        """
        cmd = ["gh", "issue", "close", str(number), "--repo", GITHUB_REPO]

        if comment:
            cmd.extend(["--comment", comment])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return IssueCloseResult(
                    success=False,
                    error=result.stderr.strip() or f"Failed to close issue #{number}",
                )

            return IssueCloseResult(
                success=True,
                error=None,
            )

        except subprocess.TimeoutExpired:
            return IssueCloseResult(
                success=False,
                error="Command timed out after 30 seconds",
            )
        except Exception as e:
            return IssueCloseResult(
                success=False,
                error=str(e),
            )

    # =========================================================================
    # GitHub Pull Request Tools
    # =========================================================================

    @mcp.tool(
        "sbs_pr_create",
        annotations=ToolAnnotations(
            title="SBS PR Create",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    def sbs_pr_create(
        ctx: Context,
        title: Annotated[
            str,
            Field(description="PR title"),
        ],
        body: Annotated[
            Optional[str],
            Field(description="PR body/description"),
        ] = None,
        base: Annotated[
            str,
            Field(description="Base branch (default: main)"),
        ] = "main",
        draft: Annotated[
            bool,
            Field(description="Create as draft PR"),
        ] = False,
    ) -> PRCreateResult:
        """Create a new GitHub pull request in the SBS repository.

        Creates a PR in e-vergo/Side-By-Side-Blueprint from the current branch.

        Examples:
        - sbs_pr_create(title="Add feature X")
        - sbs_pr_create(title="Fix bug", body="Details here", draft=True)
        """
        # Attribution footer for AI transparency
        attribution = "\n\n---\n🤖 Generated with [Claude Code](https://claude.ai/code)"
        full_body = (body or "") + attribution

        cmd = [
            "gh", "pr", "create",
            "--repo", GITHUB_REPO,
            "--title", title,
            "--body", full_body,
            "--base", base,
            "--label", "ai-authored",
        ]

        if draft:
            cmd.append("--draft")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return PRCreateResult(
                    success=False,
                    number=None,
                    url=None,
                    error=result.stderr.strip() or "Failed to create PR",
                )

            # Parse URL from output (e.g., "https://github.com/e-vergo/Side-By-Side-Blueprint/pull/123")
            url = result.stdout.strip()
            number = None
            if url and "/pull/" in url:
                try:
                    number = int(url.split("/pull/")[-1])
                except ValueError:
                    pass

            return PRCreateResult(
                success=True,
                number=number,
                url=url,
                error=None,
            )

        except subprocess.TimeoutExpired:
            return PRCreateResult(
                success=False,
                number=None,
                url=None,
                error="Command timed out after 30 seconds",
            )
        except Exception as e:
            return PRCreateResult(
                success=False,
                number=None,
                url=None,
                error=str(e),
            )

    @mcp.tool(
        "sbs_pr_list",
        annotations=ToolAnnotations(
            title="SBS PR List",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    def sbs_pr_list(
        ctx: Context,
        state: Annotated[
            Optional[str],
            Field(description="PR state filter: open, closed, merged, or all (default: open)"),
        ] = None,
        label: Annotated[
            Optional[str],
            Field(description="Filter by label"),
        ] = None,
        limit: Annotated[
            int,
            Field(description="Maximum PRs to return", ge=1),
        ] = 20,
    ) -> PRListResult:
        """List GitHub pull requests from the SBS repository.

        Lists PRs from e-vergo/Side-By-Side-Blueprint.

        Examples:
        - sbs_pr_list()  # Open PRs
        - sbs_pr_list(state="closed", limit=10)
        - sbs_pr_list(label="ai-authored")
        """
        cmd = [
            "gh", "pr", "list",
            "--repo", GITHUB_REPO,
            "--json", "number,title,state,labels,url,body,baseRefName,headRefName,isDraft,createdAt",
            "--limit", str(limit),
        ]

        if state:
            cmd.extend(["--state", state])
        if label:
            cmd.extend(["--label", label])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return PRListResult(
                    pull_requests=[],
                    total=0,
                )

            # Parse JSON output
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                return PRListResult(
                    pull_requests=[],
                    total=0,
                )

            pull_requests = []
            for item in data:
                # Extract label names from label objects
                label_names = []
                for lbl in item.get("labels", []):
                    if isinstance(lbl, dict):
                        label_names.append(lbl.get("name", ""))
                    elif isinstance(lbl, str):
                        label_names.append(lbl)

                pull_requests.append(
                    GitHubPullRequest(
                        number=item.get("number", 0),
                        title=item.get("title", ""),
                        state=item.get("state", ""),
                        labels=label_names,
                        url=item.get("url", ""),
                        body=item.get("body"),
                        base_branch=item.get("baseRefName", ""),
                        head_branch=item.get("headRefName", ""),
                        draft=item.get("isDraft", False),
                        mergeable=None,  # Not available in list view
                        created_at=item.get("createdAt"),
                    )
                )

            return PRListResult(
                pull_requests=pull_requests,
                total=len(pull_requests),
            )

        except subprocess.TimeoutExpired:
            return PRListResult(
                pull_requests=[],
                total=0,
            )
        except Exception:
            return PRListResult(
                pull_requests=[],
                total=0,
            )

    @mcp.tool(
        "sbs_pr_get",
        annotations=ToolAnnotations(
            title="SBS PR Get",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    def sbs_pr_get(
        ctx: Context,
        number: Annotated[
            int,
            Field(description="PR number to fetch"),
        ],
    ) -> PRGetResult:
        """Get details of a specific GitHub pull request.

        Fetches a single PR from e-vergo/Side-By-Side-Blueprint by number.

        Examples:
        - sbs_pr_get(number=123)
        """
        cmd = [
            "gh", "pr", "view", str(number),
            "--repo", GITHUB_REPO,
            "--json", "number,title,state,labels,url,body,baseRefName,headRefName,isDraft,mergeable,createdAt",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return PRGetResult(
                    success=False,
                    pull_request=None,
                    error=result.stderr.strip() or f"PR #{number} not found",
                )

            # Parse JSON output
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                return PRGetResult(
                    success=False,
                    pull_request=None,
                    error="Failed to parse PR data",
                )

            # Extract label names from label objects
            label_names = []
            for lbl in data.get("labels", []):
                if isinstance(lbl, dict):
                    label_names.append(lbl.get("name", ""))
                elif isinstance(lbl, str):
                    label_names.append(lbl)

            # Handle mergeable - can be null, "MERGEABLE", "CONFLICTING", etc.
            mergeable_raw = data.get("mergeable")
            mergeable = None
            if mergeable_raw == "MERGEABLE":
                mergeable = True
            elif mergeable_raw == "CONFLICTING":
                mergeable = False
            # Leave as None for UNKNOWN or null

            pull_request = GitHubPullRequest(
                number=data.get("number", 0),
                title=data.get("title", ""),
                state=data.get("state", ""),
                labels=label_names,
                url=data.get("url", ""),
                body=data.get("body"),
                base_branch=data.get("baseRefName", ""),
                head_branch=data.get("headRefName", ""),
                draft=data.get("isDraft", False),
                mergeable=mergeable,
                created_at=data.get("createdAt"),
            )

            return PRGetResult(
                success=True,
                pull_request=pull_request,
                error=None,
            )

        except subprocess.TimeoutExpired:
            return PRGetResult(
                success=False,
                pull_request=None,
                error="Command timed out after 30 seconds",
            )
        except Exception as e:
            return PRGetResult(
                success=False,
                pull_request=None,
                error=str(e),
            )

    @mcp.tool(
        "sbs_pr_merge",
        annotations=ToolAnnotations(
            title="SBS PR Merge",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    def sbs_pr_merge(
        ctx: Context,
        number: Annotated[
            int,
            Field(description="PR number to merge"),
        ],
        strategy: Annotated[
            str,
            Field(description="Merge strategy: squash, rebase, or merge (default: squash)"),
        ] = "squash",
        delete_branch: Annotated[
            bool,
            Field(description="Delete branch after merge"),
        ] = True,
    ) -> PRMergeResult:
        """Merge a GitHub pull request in the SBS repository.

        Merges a PR in e-vergo/Side-By-Side-Blueprint.

        Examples:
        - sbs_pr_merge(number=123)
        - sbs_pr_merge(number=123, strategy="rebase", delete_branch=False)
        """
        cmd = ["gh", "pr", "merge", str(number), "--repo", GITHUB_REPO]

        # Add merge strategy flag
        if strategy == "squash":
            cmd.append("--squash")
        elif strategy == "rebase":
            cmd.append("--rebase")
        elif strategy == "merge":
            cmd.append("--merge")
        else:
            # Default to squash for unknown strategies
            cmd.append("--squash")

        if delete_branch:
            cmd.append("--delete-branch")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return PRMergeResult(
                    success=False,
                    sha=None,
                    error=result.stderr.strip() or f"Failed to merge PR #{number}",
                )

            # Try to extract merge commit SHA from output
            # Output might contain something like "Merged pull request #123"
            # or include the commit SHA
            output = result.stdout.strip()
            sha = None

            # Look for SHA pattern (40 hex characters)
            import re
            sha_match = re.search(r'\b([0-9a-f]{40})\b', output)
            if sha_match:
                sha = sha_match.group(1)

            return PRMergeResult(
                success=True,
                sha=sha,
                error=None,
            )

        except subprocess.TimeoutExpired:
            return PRMergeResult(
                success=False,
                sha=None,
                error="Command timed out after 30 seconds",
            )
        except Exception as e:
            return PRMergeResult(
                success=False,
                sha=None,
                error=str(e),
            )

    # =========================================================================
    # Self-Improve Tools
    # =========================================================================

    @mcp.tool(
        "sbs_analysis_summary",
        annotations=ToolAnnotations(
            title="SBS Analysis Summary",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def sbs_analysis_summary(ctx: Context) -> AnalysisSummary:
        """Get aggregate statistics for archive analysis.

        Returns summary statistics useful for self-improvement:
        - Total entries and date range
        - Entries by trigger type
        - Quality metrics aggregates
        - Most common tags
        - Projects summary
        - Basic improvement findings
        """
        from .sbs_self_improve import sbs_analysis_summary_impl
        return sbs_analysis_summary_impl()

    @mcp.tool(
        "sbs_entries_since_self_improve",
        annotations=ToolAnnotations(
            title="SBS Entries Since Self-Improve",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def sbs_entries_since_self_improve(ctx: Context) -> SelfImproveEntries:
        """Get all entries since the last self-improve invocation.

        Finds the most recent archive entry where global_state.skill == "self-improve"
        and returns all entries created after that point. Useful for determining
        what happened since the last self-improvement cycle.
        """
        from .sbs_self_improve import sbs_entries_since_self_improve_impl
        return sbs_entries_since_self_improve_impl()


# =============================================================================
# Helper Functions
# =============================================================================


def _entry_id_to_dir_format(entry_id: str) -> str:
    """Convert entry_id (20260131102119) to directory format (2026-01-31_10-21-19).

    Args:
        entry_id: Entry ID in format YYYYMMDDHHmmss

    Returns:
        Directory name in format YYYY-MM-DD_HH-mm-ss
    """
    if len(entry_id) != 14:
        return entry_id  # Return as-is if not expected format

    year = entry_id[0:4]
    month = entry_id[4:6]
    day = entry_id[6:8]
    hour = entry_id[8:10]
    minute = entry_id[10:12]
    second = entry_id[12:14]

    return f"{year}-{month}-{day}_{hour}-{minute}-{second}"


def _dir_format_to_entry_id(dir_name: str) -> str:
    """Convert directory format (2026-01-31_10-21-19) to entry_id (20260131102119).

    Args:
        dir_name: Directory name in format YYYY-MM-DD_HH-mm-ss

    Returns:
        Entry ID in format YYYYMMDDHHmmss
    """
    # Remove dashes, underscores
    return dir_name.replace("-", "").replace("_", "")


def _parse_pytest_output(output: str) -> tuple[int, int, int, int]:
    """Parse pytest output to extract pass/fail/error/skip counts.

    Returns: (passed, failed, errors, skipped)
    """
    import re

    passed = 0
    failed = 0
    errors = 0
    skipped = 0

    # Look for summary line like: "5 passed, 2 failed, 1 error, 3 skipped"
    # or "5 passed in 1.23s"
    summary_pattern = r"(\d+)\s+(passed|failed|error|errors|skipped)"

    for match in re.finditer(summary_pattern, output, re.IGNORECASE):
        count = int(match.group(1))
        status = match.group(2).lower()

        if status == "passed":
            passed = count
        elif status == "failed":
            failed = count
        elif status in ("error", "errors"):
            errors = count
        elif status == "skipped":
            skipped = count

    return passed, failed, errors, skipped


def _extract_failures(output: str) -> List[TestFailure]:
    """Extract failure details from pytest output."""
    failures = []
    import re

    # Look for FAILED lines
    failed_pattern = r"FAILED\s+(\S+)::\s*(\S+)"
    for match in re.finditer(failed_pattern, output):
        file_path = match.group(1)
        test_name = match.group(2)
        failures.append(
            TestFailure(
                test_name=test_name,
                message="Test failed",
                file=file_path,
                line=None,
            )
        )

    # Look for error messages (AssertionError, etc.)
    error_pattern = r"(AssertionError|Error|Exception):\s*(.+)"
    for i, match in enumerate(re.finditer(error_pattern, output)):
        if i < len(failures):
            failures[i].message = match.group(2)[:200]  # Limit message length

    return failures[:10]  # Limit to 10 failures


def _parse_validation_output(
    output: str, validator_ids: List[str]
) -> tuple[dict, float, bool]:
    """Parse validation output to extract scores.

    Returns: (results dict, overall_score, passed)
    """
    import re

    results = {}
    overall_score = 0.0
    all_passed = True

    # Look for "Overall quality score: XX.XX%" pattern
    overall_pattern = r"Overall quality score:\s*([\d.]+)%?"
    match = re.search(overall_pattern, output)
    if match:
        overall_score = float(match.group(1))

    # Look for individual metric scores like "t5-color-match: 100.0 (PASS)"
    metric_pattern = r"(t\d+-[\w-]+):\s*([\d.]+)\s*\((\w+)\)"
    for match in re.finditer(metric_pattern, output, re.IGNORECASE):
        metric_id = match.group(1).lower()
        value = float(match.group(2))
        status = match.group(3).upper()
        passed = status == "PASS"

        # Check if this metric was requested
        metric_num = metric_id.split("-")[0].upper()
        if metric_num in validator_ids or metric_id in [v.lower() for v in validator_ids]:
            results[metric_id] = ValidatorScore(
                value=value,
                passed=passed,
                stale=status == "STALE",
                findings=[],
            )
            if not passed:
                all_passed = False

    # If no results found, check for error conditions
    if not results:
        if "compliance: needs attention" in output.lower():
            all_passed = False

    return results, overall_score, all_passed


def _extract_build_run_id(output: str) -> Optional[str]:
    """Extract build_run_id from build output if present."""
    import re

    pattern = r"build_run_id[:\s]+([a-zA-Z0-9_-]+)"
    match = re.search(pattern, output)
    if match:
        return match.group(1)
    return None


def _is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we can't signal it
        return True
