"""Oracle module for compiling codebase knowledge."""
from .compiler import OracleCompiler
from .extractors import (
    extract_file_tables,
    extract_how_tos,
    extract_gotchas,
    build_concept_index,
)
from .templates import (
    ORACLE_TEMPLATE,
    format_concept_index,
    format_file_map,
    format_how_tos,
    format_gotchas,
    format_cross_repo_impact,
)

__all__ = [
    "OracleCompiler",
    "extract_file_tables",
    "extract_how_tos",
    "extract_gotchas",
    "build_concept_index",
    "ORACLE_TEMPLATE",
    "format_concept_index",
    "format_file_map",
    "format_how_tos",
    "format_gotchas",
    "format_cross_repo_impact",
]
