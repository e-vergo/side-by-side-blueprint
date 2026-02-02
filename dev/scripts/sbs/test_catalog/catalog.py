"""
Test catalog implementation.

Lists all testable components: MCP tools, pytest tests, and CLI commands.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class MCPTool:
    """Represents an MCP tool."""

    name: str
    category: str
    read_only: bool
    plugged_in: bool = True


@dataclass
class PytestTest:
    """Represents a pytest test."""

    name: str
    file: str
    tier: str  # evergreen, dev, temporary, or unmarked


@dataclass
class CLICommand:
    """Represents a CLI command."""

    name: str
    description: str
    available: bool = True


@dataclass
class TestCatalog:
    """Complete test catalog."""

    mcp_tools: list[MCPTool] = field(default_factory=list)
    pytest_tests: list[PytestTest] = field(default_factory=list)
    cli_commands: list[CLICommand] = field(default_factory=list)


# =============================================================================
# MCP Tools
# =============================================================================


# SBS MCP tools (11 total)
SBS_MCP_TOOLS = [
    MCPTool("sbs_oracle_query", "Orchestration", True),
    MCPTool("sbs_archive_state", "Orchestration", True),
    MCPTool("sbs_epoch_summary", "Orchestration", True),
    MCPTool("sbs_context", "Orchestration", True),
    MCPTool("sbs_run_tests", "Testing", True),
    MCPTool("sbs_validate_project", "Testing", True),
    MCPTool("sbs_build_project", "Build", False),
    MCPTool("sbs_serve_project", "Build", False),
    MCPTool("sbs_last_screenshot", "Investigation", True),
    MCPTool("sbs_visual_history", "Investigation", True),
    MCPTool("sbs_search_entries", "Investigation", True),
]


def get_mcp_tools() -> list[MCPTool]:
    """Get list of SBS MCP tools."""
    return SBS_MCP_TOOLS.copy()


# =============================================================================
# Pytest Tests
# =============================================================================


def get_pytest_tests(
    scripts_dir: Path | None = None,
    tier_filter: str | None = None,
) -> list[PytestTest]:
    """Collect pytest tests with their tier markers.

    Args:
        scripts_dir: Path to dev/scripts directory
        tier_filter: Optional tier to filter by (evergreen, dev, temporary)

    Returns:
        List of PytestTest objects
    """
    if scripts_dir is None:
        # Default to dev/scripts relative to this file
        scripts_dir = Path(__file__).resolve().parent.parent.parent

    tests: list[PytestTest] = []

    # Run pytest --collect-only to get test list
    # Try to find pytest executable - prefer direct pytest over python -m pytest
    pytest_path = shutil.which("pytest")

    try:
        if pytest_path:
            # Use direct pytest path with -qq for node ID format output
            cmd = [pytest_path, "sbs/tests/pytest", "--collect-only", "-qq"]
        else:
            # Fall back to python -m pytest using current interpreter
            cmd = [sys.executable, "-m", "pytest", "sbs/tests/pytest", "--collect-only", "-qq"]

        result = subprocess.run(
            cmd,
            cwd=scripts_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return tests

    # Parse output lines like: sbs/tests/pytest/test_cli.py::TestArchiveCLI::test_archive_tag_adds_tag
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line or "::" not in line:
            continue
        # Skip pytest header/footer lines (start with =) and collection errors (ERROR in path)
        if line.startswith("=") or line.startswith("ERROR"):
            continue

        # Extract file and test name
        parts = line.split("::")
        if len(parts) < 2:
            continue

        file_path = parts[0]
        test_name = "::".join(parts[1:])

        # Determine tier by checking file for marker
        tier = _get_test_tier(scripts_dir / file_path, test_name)

        test = PytestTest(
            name=f"{file_path}::{test_name}",
            file=file_path,
            tier=tier,
        )

        # Apply tier filter
        if tier_filter is None or tier == tier_filter:
            tests.append(test)

    return tests


def _get_test_tier(file_path: Path, test_name: str) -> str:
    """Determine the tier of a test by checking for markers.

    Args:
        file_path: Path to the test file
        test_name: Name of the test (class::method format)

    Returns:
        Tier name: evergreen, dev, temporary, or unmarked
    """
    if not file_path.exists():
        return "unmarked"

    try:
        content = file_path.read_text()
    except (IOError, OSError):
        return "unmarked"

    # Extract class name if present
    class_name = None
    if "::" in test_name:
        parts = test_name.split("::")
        class_name = parts[0]

    # Look for markers
    # First check for class-level markers
    if class_name:
        # Pattern: @pytest.mark.TIER followed by class ClassName
        pattern = rf"@pytest\.mark\.(evergreen|dev|temporary)\s*\nclass {class_name}"
        match = re.search(pattern, content)
        if match:
            return match.group(1)

    # Check for function-level markers (less common but possible)
    method_name = test_name.split("::")[-1] if "::" in test_name else test_name
    pattern = rf"@pytest\.mark\.(evergreen|dev|temporary)\s*\n\s*def {method_name}"
    match = re.search(pattern, content)
    if match:
        return match.group(1)

    return "unmarked"


# =============================================================================
# CLI Commands
# =============================================================================


# CLI commands from sbs/cli.py
CLI_COMMANDS = [
    CLICommand("sbs capture", "Capture screenshots of generated site"),
    CLICommand("sbs compare", "Compare latest screenshots to previous capture"),
    CLICommand("sbs history", "List capture history for a project"),
    CLICommand("sbs inspect", "Show build state, artifact locations, manifest contents"),
    CLICommand("sbs validate", "Run validation checks on generated site"),
    CLICommand("sbs compliance", "Visual compliance validation loop"),
    CLICommand("sbs validate-all", "Run compliance + quality score evaluation"),
    CLICommand("sbs status", "Show git status across all repos"),
    CLICommand("sbs diff", "Show changes across all repos"),
    CLICommand("sbs sync", "Ensure all repos are synced (commit + push)"),
    CLICommand("sbs versions", "Show dependency versions across repos"),
    CLICommand("sbs archive list", "List archive entries"),
    CLICommand("sbs archive tag", "Add tags to an archive entry"),
    CLICommand("sbs archive note", "Add or update note on an archive entry"),
    CLICommand("sbs archive show", "Show details of an archive entry"),
    CLICommand("sbs archive charts", "Generate all charts from unified ledger"),
    CLICommand("sbs archive sync", "Sync archive to iCloud"),
    CLICommand("sbs archive upload", "Extract Claude data and upload to archive"),
    CLICommand("sbs oracle compile", "Compile Oracle from sources"),
    CLICommand("sbs readme-check", "Check which READMEs may need updating"),
    CLICommand("sbs test-catalog", "List all testable components"),
]


def get_cli_commands() -> list[CLICommand]:
    """Get list of CLI commands."""
    return CLI_COMMANDS.copy()


# =============================================================================
# Catalog Building
# =============================================================================


def build_catalog(
    scripts_dir: Path | None = None,
    tier_filter: str | None = None,
) -> TestCatalog:
    """Build a complete test catalog.

    Args:
        scripts_dir: Path to dev/scripts directory
        tier_filter: Optional tier to filter pytest tests by

    Returns:
        TestCatalog with all components
    """
    return TestCatalog(
        mcp_tools=get_mcp_tools(),
        pytest_tests=get_pytest_tests(scripts_dir, tier_filter),
        cli_commands=get_cli_commands(),
    )


# =============================================================================
# Formatting
# =============================================================================


def format_catalog(catalog: TestCatalog) -> str:
    """Format catalog for human-readable output.

    Args:
        catalog: TestCatalog to format

    Returns:
        Formatted string
    """
    lines: list[str] = []

    lines.append("=== SBS Test Catalog ===")
    lines.append("")

    # MCP Tools
    lines.append(f"MCP Tools ({len(catalog.mcp_tools)}):")
    for tool in catalog.mcp_tools:
        status = "[+]" if tool.plugged_in else "[-]"
        read_only = "Read-only" if tool.read_only else "Read-write"
        lines.append(f"  {status} {tool.name:<25} {tool.category:<15} {read_only}")
    lines.append("")

    # Pytest Tests
    tier_counts = {"evergreen": 0, "dev": 0, "temporary": 0, "unmarked": 0}
    for test in catalog.pytest_tests:
        tier_counts[test.tier] = tier_counts.get(test.tier, 0) + 1

    lines.append(f"Pytest Tests ({len(catalog.pytest_tests)}):")
    lines.append(f"  Evergreen: {tier_counts['evergreen']}")
    lines.append(f"  Dev: {tier_counts['dev']}")
    lines.append(f"  Temporary: {tier_counts['temporary']}")
    lines.append(f"  Unmarked: {tier_counts['unmarked']}")
    lines.append("")

    # Show first 10 tests
    shown = 0
    for test in catalog.pytest_tests:
        if shown >= 10:
            remaining = len(catalog.pytest_tests) - shown
            lines.append(f"  ... and {remaining} more tests")
            break
        lines.append(f"  [{test.tier}] {test.name}")
        shown += 1
    lines.append("")

    # CLI Commands
    lines.append(f"CLI Commands ({len(catalog.cli_commands)}):")
    for cmd in catalog.cli_commands:
        status = "[+]" if cmd.available else "[-]"
        lines.append(f"  {status} {cmd.name}")
    lines.append("")

    return "\n".join(lines)


def format_catalog_json(catalog: TestCatalog) -> str:
    """Format catalog as JSON.

    Args:
        catalog: TestCatalog to format

    Returns:
        JSON string
    """
    data: dict[str, Any] = {
        "mcp_tools": [
            {
                "name": tool.name,
                "category": tool.category,
                "read_only": tool.read_only,
                "plugged_in": tool.plugged_in,
            }
            for tool in catalog.mcp_tools
        ],
        "pytest_tests": [
            {
                "name": test.name,
                "file": test.file,
                "tier": test.tier,
            }
            for test in catalog.pytest_tests
        ],
        "cli_commands": [
            {
                "name": cmd.name,
                "description": cmd.description,
                "available": cmd.available,
            }
            for cmd in catalog.cli_commands
        ],
        "summary": {
            "mcp_tools_count": len(catalog.mcp_tools),
            "pytest_tests_count": len(catalog.pytest_tests),
            "cli_commands_count": len(catalog.cli_commands),
            "tier_counts": _count_tiers(catalog.pytest_tests),
        },
    }

    return json.dumps(data, indent=2)


def _count_tiers(tests: list[PytestTest]) -> dict[str, int]:
    """Count tests by tier."""
    counts: dict[str, int] = {"evergreen": 0, "dev": 0, "temporary": 0, "unmarked": 0}
    for test in tests:
        counts[test.tier] = counts.get(test.tier, 0) + 1
    return counts
