"""
Code statistics validator for LOC counts, file counts, and language breakdown.

This validator collects code metrics across specified directories, tracking
lines of code and file counts by language/extension. Primarily used for
metrics collection - it always passes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .base import BaseValidator, ValidationContext, ValidatorResult
from .registry import register_validator


# =============================================================================
# Language Detection
# =============================================================================

# Extension to language mapping
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".lean": "Lean",
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".css": "CSS",
    ".md": "Markdown",
    ".json": "JSON",
    ".toml": "TOML",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".html": "HTML",
    ".tex": "LaTeX",
}

# Directories to exclude from scanning
EXCLUDE_DIRS: set[str] = {
    ".lake",
    ".git",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".venv",
    "venv",
}

# Binary/non-text extensions to skip
BINARY_EXTENSIONS: set[str] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".svg",
    ".zip",
    ".tar",
    ".gz",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".pyc",
    ".pyo",
    ".o",
    ".a",
    ".olean",
}


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class FileStats:
    """Statistics for a single file."""

    path: Path
    extension: str
    language: str
    total_lines: int
    code_lines: int
    blank_lines: int


@dataclass
class AggregateStats:
    """Aggregated statistics across all files."""

    loc_by_language: dict[str, int] = field(default_factory=dict)
    files_by_language: dict[str, int] = field(default_factory=dict)
    by_extension: dict[str, dict[str, int]] = field(default_factory=dict)
    total_loc: int = 0
    total_files: int = 0
    total_blank_lines: int = 0

    def add_file(self, stats: FileStats) -> None:
        """Add a file's statistics to the aggregate."""
        lang = stats.language
        ext = stats.extension

        # Update language counts
        self.loc_by_language[lang] = self.loc_by_language.get(lang, 0) + stats.code_lines
        self.files_by_language[lang] = self.files_by_language.get(lang, 0) + 1

        # Update extension counts
        if ext not in self.by_extension:
            self.by_extension[ext] = {"files": 0, "loc": 0}
        self.by_extension[ext]["files"] += 1
        self.by_extension[ext]["loc"] += stats.code_lines

        # Update totals
        self.total_loc += stats.code_lines
        self.total_files += 1
        self.total_blank_lines += stats.blank_lines


# =============================================================================
# File Analysis
# =============================================================================


def _count_lines(path: Path) -> tuple[int, int, int]:
    """Count lines in a file.

    Returns:
        Tuple of (total_lines, code_lines, blank_lines).
    """
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        total = len(lines)
        blank = sum(1 for line in lines if not line.strip())
        code = total - blank
        return total, code, blank
    except (OSError, UnicodeDecodeError):
        return 0, 0, 0


def _analyze_file(path: Path) -> FileStats | None:
    """Analyze a single file for code statistics.

    Returns:
        FileStats if the file should be counted, None otherwise.
    """
    ext = path.suffix.lower()

    # Skip binary files
    if ext in BINARY_EXTENSIONS:
        return None

    # Skip files without extensions we track
    if ext not in EXTENSION_TO_LANGUAGE:
        return None

    language = EXTENSION_TO_LANGUAGE[ext]
    total, code, blank = _count_lines(path)

    return FileStats(
        path=path,
        extension=ext,
        language=language,
        total_lines=total,
        code_lines=code,
        blank_lines=blank,
    )


def _should_skip_dir(dir_path: Path) -> bool:
    """Check if a directory should be excluded from scanning."""
    return dir_path.name in EXCLUDE_DIRS


def _scan_directory(root: Path) -> AggregateStats:
    """Recursively scan a directory and collect code statistics.

    Args:
        root: Root directory to scan.

    Returns:
        AggregateStats with collected metrics.
    """
    stats = AggregateStats()

    if not root.exists() or not root.is_dir():
        return stats

    def walk(dir_path: Path) -> None:
        try:
            for entry in dir_path.iterdir():
                if entry.is_dir():
                    if not _should_skip_dir(entry):
                        walk(entry)
                elif entry.is_file():
                    file_stats = _analyze_file(entry)
                    if file_stats:
                        stats.add_file(file_stats)
        except PermissionError:
            pass

    walk(root)
    return stats


# =============================================================================
# Validator
# =============================================================================


@register_validator
class CodeStatsValidator(BaseValidator):
    """Collects code statistics: LOC, file counts, language breakdown.

    This validator scans directories and collects metrics about the codebase.
    It always passes - it's purely for metrics collection.

    Expected context.extra keys:
        code_dirs: list[str | Path] - Directories to scan (default: project_root)

    Recorded metrics:
        loc_by_language: dict[str, int] - Lines of code per language
        files_by_language: dict[str, int] - File count per language
        total_loc: int - Total lines of code
        total_files: int - Total file count
        total_blank_lines: int - Total blank lines
        by_extension: dict[str, dict] - Stats per extension {files, loc}
    """

    def __init__(self) -> None:
        super().__init__("code-stats", "code")

    def validate(self, context: ValidationContext) -> ValidatorResult:
        """Collect code statistics from configured directories.

        Args:
            context: Validation context with optional code_dirs in extra.

        Returns:
            ValidatorResult with code metrics. Always passes.
        """
        # Determine directories to scan
        code_dirs: list[Path] = []
        raw_dirs = context.extra.get("code_dirs", [])

        if raw_dirs:
            for d in raw_dirs:
                path = Path(d) if isinstance(d, str) else d
                if not path.is_absolute():
                    path = context.project_root / path
                code_dirs.append(path)
        else:
            code_dirs = [context.project_root]

        # Collect stats from all directories
        combined = AggregateStats()

        for dir_path in code_dirs:
            dir_stats = _scan_directory(dir_path)
            # Merge into combined
            for lang, loc in dir_stats.loc_by_language.items():
                combined.loc_by_language[lang] = (
                    combined.loc_by_language.get(lang, 0) + loc
                )
            for lang, count in dir_stats.files_by_language.items():
                combined.files_by_language[lang] = (
                    combined.files_by_language.get(lang, 0) + count
                )
            for ext, ext_stats in dir_stats.by_extension.items():
                if ext not in combined.by_extension:
                    combined.by_extension[ext] = {"files": 0, "loc": 0}
                combined.by_extension[ext]["files"] += ext_stats["files"]
                combined.by_extension[ext]["loc"] += ext_stats["loc"]
            combined.total_loc += dir_stats.total_loc
            combined.total_files += dir_stats.total_files
            combined.total_blank_lines += dir_stats.total_blank_lines

        # Build metrics
        metrics: dict[str, Any] = {
            "loc_by_language": combined.loc_by_language,
            "files_by_language": combined.files_by_language,
            "total_loc": combined.total_loc,
            "total_files": combined.total_files,
            "total_blank_lines": combined.total_blank_lines,
            "by_extension": combined.by_extension,
        }

        # Build findings summary
        findings: list[str] = []
        findings.append(
            f"Scanned {len(code_dirs)} director{'y' if len(code_dirs) == 1 else 'ies'}: "
            f"{combined.total_files} files, {combined.total_loc} LOC"
        )

        # Language breakdown (sorted by LOC descending)
        if combined.loc_by_language:
            sorted_langs = sorted(
                combined.loc_by_language.items(), key=lambda x: x[1], reverse=True
            )
            lang_summary = ", ".join(
                f"{lang}: {loc} LOC ({combined.files_by_language.get(lang, 0)} files)"
                for lang, loc in sorted_langs[:5]  # Top 5
            )
            findings.append(f"Top languages: {lang_summary}")

        return self._make_pass(
            findings=findings,
            metrics=metrics,
            confidence=1.0,
            details={
                "directories_scanned": [str(d) for d in code_dirs],
                "languages_found": list(combined.loc_by_language.keys()),
            },
        )
