"""
Test catalog module for listing all testable components.

Provides the `sbs test-catalog` command that lists:
- SBS MCP tools with status
- Pytest tests with tier markers
- CLI commands
"""

from .catalog import (
    TestCatalog,
    get_mcp_tools,
    get_pytest_tests,
    get_cli_commands,
    build_catalog,
    format_catalog,
    format_catalog_json,
)

__all__ = [
    "TestCatalog",
    "get_mcp_tools",
    "get_pytest_tests",
    "get_cli_commands",
    "build_catalog",
    "format_catalog",
    "format_catalog_json",
]
