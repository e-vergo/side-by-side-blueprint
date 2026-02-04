"""Pydantic models for SBS-specific tool outputs.

This module contains models for SBS MCP tools organized by category:
- Oracle tools: OracleQueryResult
- Archive state tools: ArchiveStateResult, EpochSummaryResult, ContextResult
- Testing tools: TestResult, ValidationResult
- Build tools: BuildResult, ServeResult
- Visual tools: ScreenshotResult, VisualHistoryResult
- Search tools: SearchResult
- GitHub tools: GitHubIssue, GitHubPullRequest, Issue/PR Create/List/Get/Close/Summary/Merge results
- Zulip tools: ZulipMessage, ZulipSearchResult, ZulipThreadResult, ZulipScreenshotResult
- Self-improve tools: AnalysisSummary, SelfImproveEntries
- Skill management tools: SkillStatusResult, SkillStartResult, SkillTransitionResult, SkillEndResult
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Oracle Tools
# =============================================================================


class OracleMatch(BaseModel):
    """A single match from oracle search."""

    file: str = Field(description="File path matching the query")
    lines: Optional[str] = Field(None, description="Line range if applicable (e.g., '10-25')")
    context: str = Field(description="Context description from oracle")
    relevance: float = Field(description="Relevance score 0.0-1.0")


class OracleConcept(BaseModel):
    """A concept from the oracle concept index."""

    name: str = Field(description="Concept name")
    section: str = Field(description="Section where concept is defined")


class OracleQueryResult(BaseModel):
    """Result from querying the SBS oracle."""

    matches: List[OracleMatch] = Field(
        default_factory=list, description="File matches from query"
    )
    concepts: List[OracleConcept] = Field(
        default_factory=list, description="Related concepts found"
    )
    raw_section: Optional[str] = Field(
        None, description="Raw markdown section if exact match found"
    )


# =============================================================================
# Archive State Tools
# =============================================================================


class ArchiveStateResult(BaseModel):
    """Current state of the archive system."""

    global_state: Optional[Dict[str, Any]] = Field(
        None, description="Current orchestration state {skill, substate} or null when idle"
    )
    last_epoch_entry: Optional[str] = Field(
        None, description="Entry ID of last epoch close"
    )
    last_epoch_timestamp: Optional[str] = Field(
        None, description="ISO timestamp of last epoch close"
    )
    entries_in_current_epoch: int = Field(
        description="Number of entries since last epoch close"
    )
    total_entries: int = Field(description="Total number of archive entries")
    projects: List[str] = Field(
        default_factory=list, description="List of projects with archive entries"
    )


class VisualChange(BaseModel):
    """A visual change detected in an entry."""

    entry_id: str = Field(description="Entry ID where change occurred")
    screenshots: List[str] = Field(
        default_factory=list, description="Screenshot filenames"
    )
    timestamp: str = Field(description="ISO timestamp of the change")


class EpochSummaryResult(BaseModel):
    """Summary of an epoch (period between skill-triggered entries)."""

    epoch_id: str = Field(description="Entry ID that closed this epoch")
    started_at: str = Field(description="ISO timestamp when epoch started")
    ended_at: str = Field(description="ISO timestamp when epoch ended")
    entries: int = Field(description="Number of entries in this epoch")
    builds: int = Field(description="Number of build entries in this epoch")
    visual_changes: List[VisualChange] = Field(
        default_factory=list, description="Visual changes detected in this epoch"
    )
    tags_used: List[str] = Field(
        default_factory=list, description="All unique tags used in this epoch"
    )
    projects_touched: List[str] = Field(
        default_factory=list, description="Projects with entries in this epoch"
    )


class ContextResult(BaseModel):
    """Generated context block for AI consumption."""

    context_block: str = Field(
        description="Formatted markdown context block for system prompts"
    )
    entry_count: int = Field(description="Number of entries summarized")
    time_range: Optional[str] = Field(
        None, description="Time range covered (e.g., '2h 30m')"
    )


# =============================================================================
# Testing Tools
# =============================================================================


class TestFailure(BaseModel):
    """A single test failure."""

    test_name: str = Field(description="Name of the failed test")
    message: str = Field(description="Failure message")
    file: Optional[str] = Field(None, description="File where test is defined")
    line: Optional[int] = Field(None, description="Line number of failure")


class TestResult(BaseModel):
    """Result from running test suite."""

    passed: int = Field(description="Number of tests passed")
    failed: int = Field(description="Number of tests failed")
    errors: int = Field(description="Number of tests with errors")
    skipped: int = Field(default=0, description="Number of tests skipped")
    duration_seconds: float = Field(description="Total test duration in seconds")
    failures: List[TestFailure] = Field(
        default_factory=list, description="Details of failed tests"
    )


class ValidatorScore(BaseModel):
    """Score from a single validator."""

    value: float = Field(description="Score value")
    passed: bool = Field(description="Whether this validator passed")
    stale: bool = Field(default=False, description="Whether this result is stale")
    findings: List[str] = Field(
        default_factory=list, description="Findings from validator"
    )


class SBSValidationResult(BaseModel):
    """Result from running SBS validation suite.

    Named SBSValidationResult to avoid conflict with models.ValidationResult.
    """

    overall_score: float = Field(description="Overall quality score 0.0-100.0")
    passed: bool = Field(description="Whether overall validation passed")
    results: Dict[str, ValidatorScore] = Field(
        default_factory=dict, description="Per-validator results keyed by validator name"
    )
    timestamp: str = Field(description="ISO timestamp of validation")


# =============================================================================
# Build Tools
# =============================================================================


class SBSBuildResult(BaseModel):
    """Result from running SBS build.

    Named SBSBuildResult to avoid conflict with models.BuildResult.
    """

    success: bool = Field(description="Whether build succeeded")
    duration_seconds: float = Field(description="Total build duration in seconds")
    build_run_id: Optional[str] = Field(
        None, description="Unique identifier for this build run"
    )
    errors: List[str] = Field(
        default_factory=list, description="Build error messages if any"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Build warning messages"
    )
    project: str = Field(description="Project that was built")
    manifest_path: Optional[str] = Field(
        None, description="Path to generated manifest.json if successful"
    )


class ServeResult(BaseModel):
    """Result from starting/querying the dev server."""

    running: bool = Field(description="Whether server is currently running")
    url: Optional[str] = Field(None, description="Server URL (e.g., 'http://localhost:8000')")
    pid: Optional[int] = Field(None, description="Process ID of server")
    project: Optional[str] = Field(None, description="Project being served")
    error: Optional[str] = Field(None, description="Error message if operation failed")


# =============================================================================
# Visual Tools
# =============================================================================


class ScreenshotResult(BaseModel):
    """Result from capturing a screenshot."""

    image_path: str = Field(description="Absolute path to screenshot file")
    entry_id: str = Field(description="Archive entry ID for this capture")
    captured_at: str = Field(description="ISO timestamp of capture")
    hash: Optional[str] = Field(
        None, description="SHA256 hash prefix (16 chars) for comparison"
    )
    page: str = Field(description="Page type (e.g., 'dashboard', 'dep_graph')")
    project: str = Field(description="Project name")


class HistoryEntry(BaseModel):
    """A single entry in visual history."""

    entry_id: str = Field(description="Archive entry ID")
    timestamp: str = Field(description="ISO timestamp")
    screenshots: List[str] = Field(
        default_factory=list, description="Screenshot filenames in this entry"
    )
    hash_map: Dict[str, str] = Field(
        default_factory=dict, description="Mapping of page -> hash for this entry"
    )
    tags: List[str] = Field(default_factory=list, description="Tags on this entry")


class VisualHistoryResult(BaseModel):
    """Result from querying visual history."""

    project: str = Field(description="Project name")
    history: List[HistoryEntry] = Field(
        default_factory=list, description="History entries, most recent first"
    )
    total_count: int = Field(description="Total number of entries with screenshots")


# =============================================================================
# Search Tools
# =============================================================================


class ArchiveEntrySummary(BaseModel):
    """Summary of an archive entry for search results."""

    entry_id: str = Field(description="Entry ID (unix timestamp)")
    created_at: str = Field(description="ISO timestamp")
    project: str = Field(description="Project name")
    trigger: str = Field(description="What triggered this entry: 'build', 'manual', 'skill'")
    tags: List[str] = Field(default_factory=list, description="All tags (manual + auto)")
    has_screenshots: bool = Field(description="Whether entry has screenshots")
    notes_preview: str = Field(
        default="", description="First 100 chars of notes if any"
    )
    build_run_id: Optional[str] = Field(None, description="Associated build run ID")


class SearchResult(BaseModel):
    """Result from searching archive entries."""

    entries: List[ArchiveEntrySummary] = Field(
        default_factory=list, description="Matching entries"
    )
    total_count: int = Field(description="Total number of matches")
    query: Optional[str] = Field(None, description="The search query used")
    filters: Dict[str, Any] = Field(
        default_factory=dict, description="Filters that were applied"
    )


# =============================================================================
# Manifest/Graph Tools (for completeness)
# =============================================================================


class ManifestNode(BaseModel):
    """A node from the dependency graph manifest."""

    id: str = Field(description="Node ID (e.g., 'thm:main')")
    label: str = Field(description="Display label")
    status: str = Field(
        description="Node status: notReady, ready, sorry, proven, fullyProven, mathlibReady"
    )
    module: str = Field(description="Lean module containing this node")
    title: Optional[str] = Field(None, description="Custom title from @[blueprint]")
    is_key_declaration: bool = Field(
        default=False, description="Whether marked as key declaration"
    )
    message: Optional[str] = Field(None, description="User notes from @[blueprint]")


class NodeDependency(BaseModel):
    """Dependency information for a node."""

    node_id: str = Field(description="Node ID")
    uses: List[str] = Field(
        default_factory=list, description="Node IDs this node depends on"
    )
    used_by: List[str] = Field(
        default_factory=list, description="Node IDs that depend on this node"
    )


class GraphStats(BaseModel):
    """Statistics about the dependency graph."""

    total_nodes: int = Field(description="Total number of nodes")
    total_edges: int = Field(description="Total number of edges")
    status_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of nodes per status (notReady, ready, sorry, proven, fullyProven, mathlibReady)",
    )
    key_declarations: int = Field(description="Number of key declarations")
    is_connected: bool = Field(description="Whether graph is fully connected")
    has_cycles: bool = Field(description="Whether graph has cycles")
    validation_messages: List[str] = Field(
        default_factory=list, description="Validation warnings/errors"
    )


# =============================================================================
# General Browser Tools
# =============================================================================


class BrowserNavigateResult(BaseModel):
    """Result from navigating the browser to a URL."""

    url: str = Field(description="Final URL after navigation")
    title: str = Field(description="Page title")
    status: int = Field(description="HTTP status code")


class BrowserClickResult(BaseModel):
    """Result from clicking an element on the page."""

    selector: str = Field(description="CSS selector clicked")
    clicked: bool = Field(description="Whether element was found and clicked")
    element_text: Optional[str] = Field(None, description="Text content of clicked element")


class BrowserScreenshotResult(BaseModel):
    """Result from capturing a browser screenshot."""

    image_path: str = Field(description="Absolute path to screenshot file")
    url: str = Field(description="URL of the page")
    captured_at: str = Field(description="ISO timestamp of capture")
    hash: Optional[str] = Field(None, description="SHA256 hash prefix for comparison")


class ElementInfo(BaseModel):
    """Information about a single DOM element."""

    tag: str = Field(description="HTML tag name")
    text: str = Field(description="Text content (truncated)")
    attributes: Dict[str, str] = Field(default_factory=dict, description="Key HTML attributes")


class BrowserEvaluateResult(BaseModel):
    """Result from evaluating JavaScript on the page."""

    result: Optional[str] = Field(None, description="JS evaluation result as string")
    type: str = Field(description="Type of the result")


class BrowserElementsResult(BaseModel):
    """Result from querying DOM elements."""

    selector: str = Field(description="CSS selector queried")
    elements: List[ElementInfo] = Field(default_factory=list)
    count: int = Field(description="Total matching elements (may exceed returned)")


# =============================================================================
# Zulip Tools
# =============================================================================


class ZulipMessage(BaseModel):
    """A single Zulip message."""

    id: int = Field(description="Message ID")
    sender: str = Field(description="Sender display name")
    content: str = Field(description="Message content (markdown)")
    timestamp: str = Field(description="ISO timestamp")
    reactions: List[str] = Field(default_factory=list, description="Emoji reactions")


class ZulipSearchResult(BaseModel):
    """Result from searching Zulip messages."""

    messages: List[ZulipMessage] = Field(
        default_factory=list, description="Matching messages"
    )
    total_count: int = Field(description="Total matches found")
    query: str = Field(description="Search query used")
    stream: Optional[str] = Field(None, description="Stream filter if applied")
    topic: Optional[str] = Field(None, description="Topic filter if applied")
    truncated: bool = Field(default=False, description="Whether results were truncated")


class ZulipThreadResult(BaseModel):
    """Result from fetching a Zulip thread."""

    stream: str = Field(description="Stream name")
    topic: str = Field(description="Topic name")
    messages: List[ZulipMessage] = Field(
        default_factory=list, description="Thread messages in chronological order"
    )
    message_count: int = Field(description="Total messages in thread")
    participants: List[str] = Field(
        default_factory=list, description="Unique participants"
    )
    first_message_date: Optional[str] = Field(None, description="Date of first message")
    last_message_date: Optional[str] = Field(
        None, description="Date of most recent message"
    )


class ZulipScreenshotResult(BaseModel):
    """Result from capturing a Zulip screenshot."""

    image_path: str = Field(description="Absolute path to screenshot file")
    url: str = Field(description="URL that was captured")
    captured_at: str = Field(description="ISO timestamp of capture")
    hash: Optional[str] = Field(None, description="SHA256 hash prefix for comparison")
    stream: Optional[str] = Field(None, description="Stream name if thread")
    topic: Optional[str] = Field(None, description="Topic name if thread")
    archived: bool = Field(default=False, description="Whether screenshot was archived")


# =============================================================================
# GitHub Issue Tools
# =============================================================================


class GitHubIssue(BaseModel):
    """A GitHub issue."""

    number: int = Field(description="Issue number")
    title: str = Field(description="Issue title")
    state: str = Field(description="Issue state: open or closed")
    labels: List[str] = Field(default_factory=list, description="Issue labels")
    url: str = Field(description="Issue URL")
    body: Optional[str] = Field(None, description="Issue body/description")
    created_at: Optional[str] = Field(None, description="Creation timestamp")


class IssueCreateResult(BaseModel):
    """Result from creating an issue."""

    success: bool = Field(description="Whether creation succeeded")
    number: Optional[int] = Field(None, description="New issue number")
    url: Optional[str] = Field(None, description="New issue URL")
    error: Optional[str] = Field(None, description="Error message if failed")


class IssueLogResult(BaseModel):
    """Result from autonomous agent issue logging."""

    success: bool = Field(description="Whether creation succeeded")
    number: Optional[int] = Field(None, description="New issue number")
    url: Optional[str] = Field(None, description="New issue URL")
    context_attached: bool = Field(
        description="Whether archive context was successfully attached"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class IssueListResult(BaseModel):
    """Result from listing issues."""

    issues: List[GitHubIssue] = Field(default_factory=list, description="List of issues")
    total: int = Field(description="Total count of issues returned")


class IssueGetResult(BaseModel):
    """Result from getting a single issue."""

    success: bool = Field(description="Whether fetch succeeded")
    issue: Optional[GitHubIssue] = Field(None, description="The issue if found")
    error: Optional[str] = Field(None, description="Error message if failed")


class IssueCloseResult(BaseModel):
    """Result from closing an issue."""

    success: bool = Field(description="Whether close succeeded")
    error: Optional[str] = Field(None, description="Error message if failed")


class IssueSummaryItem(BaseModel):
    """A single issue in the summary listing."""

    number: int = Field(description="Issue number")
    title: str = Field(description="Issue title")
    labels: List[str] = Field(default_factory=list, description="Issue labels")
    age_days: int = Field(description="Age in days since creation")
    url: str = Field(description="Issue URL")


class IssueSummaryResult(BaseModel):
    """Analytical summary of open GitHub issues.

    Groups issues by type (bug/feature/idea) and area (sbs/devtools/misc),
    with a full listing sorted by age. Also provides by_dimension grouping
    across all taxonomy dimensions.
    """

    total_open: int = Field(description="Total number of open issues")
    by_type: Dict[str, List[int]] = Field(
        default_factory=dict,
        description="Issue numbers grouped by type label (bug, feature, idea, unlabeled)",
    )
    by_area: Dict[str, List[int]] = Field(
        default_factory=dict,
        description="Issue numbers grouped by area label (sbs, devtools, misc, unlabeled)",
    )
    by_dimension: Dict[str, Dict[str, List[int]]] = Field(
        default_factory=dict,
        description=(
            "Issue numbers grouped by taxonomy dimension, then by label. "
            "E.g. {'origin': {'origin:user': [1,2]}, 'friction': {'friction:slow-feedback': [3]}}"
        ),
    )
    issues: List[IssueSummaryItem] = Field(
        default_factory=list,
        description="All open issues sorted by age (oldest first)",
    )
    oldest_age_days: Optional[int] = Field(
        None, description="Age of the oldest open issue in days"
    )
    newest_age_days: Optional[int] = Field(
        None, description="Age of the newest open issue in days"
    )
    error: Optional[str] = Field(None, description="Error message if fetch failed")


# =============================================================================
# GitHub Pull Request Tools
# =============================================================================


class GitHubPullRequest(BaseModel):
    """A GitHub pull request."""

    number: int = Field(description="PR number")
    title: str = Field(description="PR title")
    state: str = Field(description="PR state: open, closed, or merged")
    labels: List[str] = Field(default_factory=list, description="PR labels")
    url: str = Field(description="PR URL")
    body: Optional[str] = Field(None, description="PR body/description")
    base_branch: str = Field(description="Base branch (e.g., main)")
    head_branch: str = Field(description="Head branch (feature branch)")
    draft: bool = Field(default=False, description="Whether PR is a draft")
    mergeable: Optional[bool] = Field(None, description="Whether PR can be merged")
    created_at: Optional[str] = Field(None, description="Creation timestamp")


class PRCreateResult(BaseModel):
    """Result from creating a PR."""

    success: bool = Field(description="Whether creation succeeded")
    number: Optional[int] = Field(None, description="New PR number")
    url: Optional[str] = Field(None, description="New PR URL")
    error: Optional[str] = Field(None, description="Error message if failed")


class PRListResult(BaseModel):
    """Result from listing PRs."""

    pull_requests: List[GitHubPullRequest] = Field(
        default_factory=list, description="List of PRs"
    )
    total: int = Field(description="Total count of PRs returned")


class PRGetResult(BaseModel):
    """Result from getting a single PR."""

    success: bool = Field(description="Whether fetch succeeded")
    pull_request: Optional[GitHubPullRequest] = Field(
        None, description="The PR if found"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class PRMergeResult(BaseModel):
    """Result from merging a PR."""

    success: bool = Field(description="Whether merge succeeded")
    sha: Optional[str] = Field(None, description="Merge commit SHA")
    error: Optional[str] = Field(None, description="Error message if failed")


# =============================================================================
# Self-Improve Tools
# =============================================================================


class AnalysisFinding(BaseModel):
    """Single improvement finding from archive analysis."""

    pillar: str = Field(
        description="One of: user_effectiveness, claude_execution, alignment_patterns, system_engineering"
    )
    category: str = Field(
        description="Finding category (e.g., 'tool_usage', 'error_pattern', 'workflow')"
    )
    severity: str = Field(description="low, medium, high")
    description: str = Field(description="What was observed")
    recommendation: str = Field(description="Suggested improvement")
    evidence: List[str] = Field(
        default_factory=list,
        description="Entry IDs or data supporting this finding",
    )


class AnalysisSummary(BaseModel):
    """Summary of archive analysis for self-improvement."""

    total_entries: int = Field(description="Total archive entries analyzed")
    date_range: str = Field(description="Earliest to latest entry timestamp")
    entries_by_trigger: Dict[str, int] = Field(description="Count by trigger type")
    quality_metrics: Optional[Dict[str, float]] = Field(
        None, description="Average quality scores"
    )
    most_common_tags: List[str] = Field(
        default_factory=list, description="Top 10 tags"
    )
    projects_summary: Dict[str, int] = Field(
        default_factory=dict, description="Entry count per project"
    )
    findings: List[AnalysisFinding] = Field(
        default_factory=list, description="Improvement findings"
    )


class SelfImproveEntrySummary(BaseModel):
    """Lightweight summary of an archive entry for self-improve tools."""

    entry_id: str = Field(description="Entry ID")
    created_at: str = Field(description="ISO timestamp")
    project: str = Field(description="Project name")
    trigger: str = Field(description="Trigger type")
    notes: str = Field(default="", description="Entry notes")
    tags: List[str] = Field(default_factory=list, description="All tags")
    quality_score: Optional[float] = Field(
        None, description="Overall quality score if available"
    )


class SelfImproveEntries(BaseModel):
    """Entries since last self-improve invocation."""

    last_self_improve_entry: Optional[str] = Field(
        None, description="Entry ID of last self-improve"
    )
    last_self_improve_timestamp: Optional[str] = Field(
        None, description="ISO timestamp"
    )
    entries_since: List[SelfImproveEntrySummary] = Field(
        default_factory=list, description="Entries since last cycle"
    )
    count_by_trigger: Dict[str, int] = Field(
        default_factory=dict, description="Count by trigger type"
    )
    count: int = Field(
        default=0, description="Total count of entries since last self-improve"
    )


class SuccessPattern(BaseModel):
    """A successful interaction pattern identified from archive analysis."""

    pattern_type: str = Field(
        description="Type: completed_task, clean_execution, high_quality"
    )
    description: str = Field(description="What makes this pattern successful")
    evidence: List[str] = Field(
        default_factory=list, description="Supporting entry IDs"
    )
    frequency: int = Field(default=0, description="How often this pattern occurs")


class SuccessPatterns(BaseModel):
    """Result from success mining analysis."""

    patterns: List[SuccessPattern] = Field(default_factory=list)
    total_sessions_analyzed: int = Field(default=0)
    summary: str = Field(
        default="", description="Overall success pattern summary"
    )


class DiscriminatingFeature(BaseModel):
    """A feature that discriminates approved from rejected plans."""

    feature: str = Field(
        description="Feature name (e.g., plan_size, question_count)"
    )
    approved_value: str = Field(
        description="Typical value in approved plans"
    )
    rejected_value: str = Field(
        description="Typical value in rejected plans"
    )
    confidence: str = Field(
        default="low", description="Confidence level: low, medium, high"
    )


class ComparativeAnalysis(BaseModel):
    """Comparative analysis of approved vs rejected plans/proposals."""

    approved_count: int = Field(default=0)
    rejected_count: int = Field(default=0)
    features: List[DiscriminatingFeature] = Field(default_factory=list)
    summary: str = Field(
        default="", description="Key takeaways from comparison"
    )


class SystemHealthMetric(BaseModel):
    """A single system health measurement."""

    metric: str = Field(description="Metric name")
    value: float = Field(description="Current value")
    trend: str = Field(
        default="stable", description="Trend: improving, stable, degrading"
    )
    details: str = Field(default="", description="Additional context")


class SystemHealthReport(BaseModel):
    """System engineering health report from archive analysis."""

    build_metrics: List[SystemHealthMetric] = Field(default_factory=list)
    tool_error_rates: Dict[str, float] = Field(default_factory=dict)
    archive_friction: Dict[str, Any] = Field(default_factory=dict)
    findings: List[AnalysisFinding] = Field(default_factory=list)
    overall_health: str = Field(
        default="unknown",
        description="Overall: healthy, warning, degraded",
    )


class UserPatternAnalysis(BaseModel):
    """Analysis of user communication patterns correlated with session outcomes."""

    total_sessions_analyzed: int = Field(default=0)
    effective_patterns: List[str] = Field(
        default_factory=list,
        description="Patterns correlated with smooth sessions",
    )
    findings: List[AnalysisFinding] = Field(default_factory=list)
    summary: str = Field(
        default="",
        description="Key observations about user communication",
    )


# --- Interruption Analysis ---


class InterruptionEvent(BaseModel):
    """A single interruption event detected in a skill session."""

    entry_id: str = Field(description="Entry where interruption was detected")
    skill: str = Field(description="Skill that was interrupted")
    event_type: str = Field(
        description="Type: backward_transition, retry, correction_keyword, high_entry_count"
    )
    from_phase: Optional[str] = Field(None, description="Phase before interruption")
    to_phase: Optional[str] = Field(None, description="Phase after interruption")
    context: str = Field(description="Human-readable description")


class InterruptionAnalysisResult(BaseModel):
    """Result from interruption analysis across skill sessions."""

    events: List[InterruptionEvent] = Field(default_factory=list)
    total_sessions_analyzed: int = Field(default=0)
    sessions_with_interruptions: int = Field(default=0)
    findings: List[AnalysisFinding] = Field(default_factory=list)
    summary: str = Field(default="")


# --- Skill Stats ---


class SkillStatEntry(BaseModel):
    """Statistics for a single skill type."""

    skill: str = Field(description="Skill name")
    invocation_count: int = Field(default=0)
    completion_count: int = Field(default=0)
    completion_rate: float = Field(default=0.0)
    avg_duration_seconds: Optional[float] = Field(None)
    avg_entries_per_session: float = Field(default=0.0)
    common_failure_substates: List[str] = Field(default_factory=list)
    common_failure_tags: List[str] = Field(default_factory=list)


class SkillStatsResult(BaseModel):
    """Per-skill lifecycle metrics."""

    skills: Dict[str, SkillStatEntry] = Field(default_factory=dict)
    total_sessions: int = Field(default=0)
    findings: List[AnalysisFinding] = Field(default_factory=list)
    summary: str = Field(default="")


# --- Phase Transition Health ---


class PhaseTransitionReport(BaseModel):
    """Phase transition health report for a single skill."""

    skill: str = Field(description="Skill name")
    expected_sequence: List[str] = Field(default_factory=list)
    total_sessions: int = Field(default=0)
    backward_transitions: int = Field(default=0)
    backward_details: List[Dict[str, str]] = Field(
        default_factory=list, description="entry_id, from, to"
    )
    skipped_phases: Dict[str, int] = Field(
        default_factory=dict, description="Phase -> skip count"
    )
    time_in_phase: Dict[str, float] = Field(
        default_factory=dict, description="Phase -> avg seconds"
    )


class PhaseTransitionHealthResult(BaseModel):
    """Phase transition health analysis across all skills."""

    reports: List[PhaseTransitionReport] = Field(default_factory=list)
    findings: List[AnalysisFinding] = Field(default_factory=list)
    summary: str = Field(default="")


# --- Gate Failures ---


class GateFailureEntry(BaseModel):
    """A single gate validation failure."""

    entry_id: str = Field(description="Entry where gate failed")
    skill: Optional[str] = Field(None)
    substate: Optional[str] = Field(None)
    gate_findings: List[str] = Field(
        default_factory=list, description="Gate validation findings"
    )
    continued: bool = Field(
        default=False, description="Whether task continued despite failure"
    )


class GateFailureReport(BaseModel):
    """Analysis of gate validation failures."""

    total_gate_checks: int = Field(default=0)
    total_failures: int = Field(default=0)
    failure_rate: float = Field(default=0.0)
    failures: List[GateFailureEntry] = Field(default_factory=list)
    override_count: int = Field(default=0)
    common_findings: List[str] = Field(default_factory=list)
    findings: List[AnalysisFinding] = Field(default_factory=list)
    summary: str = Field(default="")


# --- Tag Effectiveness ---


class TagEffectivenessEntry(BaseModel):
    """Effectiveness analysis for a single auto-tag."""

    tag: str = Field(description="Auto-tag name")
    tag_era: str = Field(
        default="v2", description="'legacy' (pre-v2.0, no colon) or 'v2' (colon-delimited)"
    )
    frequency: int = Field(default=0)
    frequency_pct: float = Field(default=0.0)
    co_occurs_with_gate_failure: int = Field(default=0)
    co_occurs_with_backward_transition: int = Field(default=0)
    co_occurs_with_error_notes: int = Field(default=0)
    signal_score: float = Field(
        default=0.0, description="0-1: higher = more correlated with problems"
    )
    classification: str = Field(
        default="neutral", description="signal, noise, or neutral"
    )


class TagEffectivenessResult(BaseModel):
    """Analysis of auto-tag signal-to-noise ratio."""

    tags: List[TagEffectivenessEntry] = Field(default_factory=list)
    noisy_tags: List[str] = Field(default_factory=list)
    signal_tags: List[str] = Field(default_factory=list)
    findings: List[AnalysisFinding] = Field(default_factory=list)
    summary: str = Field(default="")


# --- AskUserQuestion Analysis ---


class QuestionInteraction(BaseModel):
    """A single AskUserQuestion interaction from a Claude Code session."""

    session_id: str = Field(description="Session ID where question occurred")
    timestamp: Optional[str] = Field(None, description="When the question was asked")
    questions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Question dicts: {question, header, options, multiSelect}",
    )
    answers: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of question text to selected answer",
    )
    context_before: Optional[str] = Field(
        None, description="What the assistant was doing before asking"
    )
    skill: Optional[str] = Field(
        None, description="Active skill when question was asked"
    )
    substate: Optional[str] = Field(
        None, description="Active substate when question was asked"
    )


class QuestionAnalysisResult(BaseModel):
    """Result from sbs_question_analysis."""

    interactions: List[QuestionInteraction] = Field(
        default_factory=list, description="AskUserQuestion interactions found"
    )
    total_found: int = Field(default=0, description="Total interactions found")
    sessions_searched: int = Field(
        default=0, description="Number of sessions searched"
    )


class QuestionStatsResult(BaseModel):
    """Result from sbs_question_stats."""

    total_questions: int = Field(default=0, description="Total AskUserQuestion calls")
    questions_by_skill: Dict[str, int] = Field(
        default_factory=dict, description="Question count per active skill"
    )
    questions_by_header: Dict[str, int] = Field(
        default_factory=dict, description="Question count per header text"
    )
    most_common_options_selected: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Most frequently selected options [{option, count}]",
    )
    multi_select_usage: int = Field(
        default=0, description="How many questions used multiSelect"
    )
    sessions_with_questions: int = Field(
        default=0, description="Sessions containing at least one AskUserQuestion"
    )
    sessions_without_questions: int = Field(
        default=0, description="Sessions with no AskUserQuestion calls"
    )


# =============================================================================
# Improvement Capture Tools
# =============================================================================


class ImprovementCaptureResult(BaseModel):
    """Result from capturing an improvement opportunity."""

    success: bool = Field(description="Whether capture succeeded")
    entry_id: Optional[str] = Field(None, description="Archive entry ID created")
    tags: List[str] = Field(default_factory=list, description="Tags applied to the entry")
    error: Optional[str] = Field(None, description="Error message if failed")


# =============================================================================
# Skill Management Tools
# =============================================================================


class SkillStatusResult(BaseModel):
    """Result of sbs_skill_status query."""

    active_skill: Optional[str] = Field(
        None, description="Current skill: task, self-improve, update-and-archive, or null if idle"
    )
    substate: Optional[str] = Field(
        None, description="Current phase within the skill"
    )
    can_start_new: bool = Field(
        description="Whether a new skill can be started (true if idle)"
    )
    entries_in_phase: int = Field(
        default=0, description="Archive entries since phase started"
    )
    phase_started_at: Optional[str] = Field(
        None, description="ISO timestamp when phase started"
    )


class SkillStartResult(BaseModel):
    """Result of sbs_skill_start operation."""

    success: bool = Field(description="Whether the skill started successfully")
    error: Optional[str] = Field(None, description="Error message if failed")
    archive_entry_id: Optional[str] = Field(
        None, description="Entry ID from archive upload"
    )
    global_state: Optional[Dict[str, Any]] = Field(
        None, description="New global state after start"
    )


class SkillTransitionResult(BaseModel):
    """Result of sbs_skill_transition operation."""

    success: bool = Field(description="Whether the transition succeeded")
    error: Optional[str] = Field(None, description="Error message if failed")
    from_phase: Optional[str] = Field(None, description="Previous phase")
    to_phase: str = Field(description="New phase")
    archive_entry_id: Optional[str] = Field(
        None, description="Entry ID from archive upload"
    )


class SkillEndResult(BaseModel):
    """Result of sbs_skill_end operation."""

    success: bool = Field(description="Whether the skill ended successfully")
    error: Optional[str] = Field(None, description="Error message if failed")
    archive_entry_id: Optional[str] = Field(
        None, description="Entry ID from archive upload"
    )


class SkillFailResult(BaseModel):
    """Result of recording a skill failure."""

    success: bool = Field(description="Whether the failure was recorded")
    error: Optional[str] = Field(None, description="Error if recording failed")
    archive_entry_id: Optional[str] = Field(
        None, description="Entry ID from archive upload"
    )
    reason: str = Field(description="Why the skill failed")
    failed_phase: Optional[str] = Field(
        None, description="Phase that was active when failure occurred"
    )


class SkillHandoffResult(BaseModel):
    """Result of sbs_skill_handoff operation."""

    success: bool = Field(description="Whether handoff succeeded")
    error: Optional[str] = Field(None, description="Error message if failed")
    from_skill: str = Field(description="Skill that was ended")
    from_phase: str = Field(description="Phase that was active when handoff occurred")
    to_skill: str = Field(description="Skill that was started")
    to_substate: str = Field(description="Initial substate of new skill")
    archive_entry_id: Optional[str] = Field(
        None, description="Entry ID recording the handoff"
    )


# =============================================================================
# Inspect Tools
# =============================================================================


class PageInspection(BaseModel):
    """Inspection data for a single page."""

    page_name: str = Field(description="Page name (e.g., 'dashboard', 'dep_graph')")
    screenshot_path: Optional[str] = Field(
        None, description="Absolute path to screenshot file, if it exists"
    )
    screenshot_exists: bool = Field(
        default=False, description="Whether a screenshot file was found"
    )
    suggested_prompt: str = Field(
        default="", description="What to look for when evaluating this page"
    )


class InspectResult(BaseModel):
    """Result from sbs_inspect_project."""

    project: str = Field(description="Normalized project name")
    pages: List[PageInspection] = Field(
        default_factory=list, description="Inspection data per page"
    )
    open_issues: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Open issues: [{number, title, labels, body_summary}]",
    )
    closed_issues: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recently closed issues: [{number, title, labels}]",
    )
    quality_scores: Optional[Dict[str, Any]] = Field(
        None, description="Latest T1-T8 scores from quality_ledger.json"
    )
    total_pages: int = Field(default=0, description="Total pages inspected")
    pages_with_screenshots: int = Field(
        default=0, description="Pages that have screenshot files"
    )