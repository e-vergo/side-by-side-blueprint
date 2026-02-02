"""Pydantic models for SBS-specific tool outputs.

This module contains models for the 11 SBS tools organized by category:
- Oracle tools: OracleQueryResult
- Archive state tools: ArchiveStateResult, EpochSummaryResult, ContextResult
- Testing tools: TestResult, ValidationResult
- Build tools: BuildResult, ServeResult
- Visual tools: ScreenshotResult, VisualHistoryResult
- Search tools: SearchResult
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
