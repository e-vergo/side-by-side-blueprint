"""
Shared utilities for the sbs CLI.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

# =============================================================================
# Constants
# =============================================================================

SBS_ROOT = Path("/Users/eric/GitHub/Side-By-Side-Blueprint")
IMAGES_DIR = SBS_ROOT / "images"
CACHE_DIR = Path.home() / ".sbs-cache"

# Known repos in the workspace
REPO_NAMES = [
    "subverso",
    "LeanArchitect",
    "Dress",
    "Runway",
    "verso",
    "dress-blueprint-action",
    "SBS-Test",
    "General_Crystallographic_Restriction",
    "PrimeNumberTheoremAnd",
]


# =============================================================================
# Logging
# =============================================================================


class Logger:
    """Simple colored logger with --no-color support."""

    COLORS = {
        "reset": "\033[0m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "bold": "\033[1m",
        "dim": "\033[2m",
    }

    def __init__(self, use_color: Optional[bool] = None):
        if use_color is None:
            self._use_color = sys.stdout.isatty()
        else:
            self._use_color = use_color

    def set_color(self, use_color: bool) -> None:
        """Set whether to use color output."""
        self._use_color = use_color

    def _color(self, text: str, color: str) -> str:
        if not self._use_color:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def header(self, message: str) -> None:
        """Print a section header."""
        print(f"\n{self._color('===', 'cyan')} {self._color(message, 'bold')} {self._color('===', 'cyan')}")

    def info(self, message: str) -> None:
        """Print an info message."""
        print(f"  {message}")

    def success(self, message: str) -> None:
        """Print a success message."""
        print(f"  {self._color('[OK]', 'green')} {message}")

    def warning(self, message: str) -> None:
        """Print a warning message."""
        print(f"  {self._color('[WARN]', 'yellow')} {message}")

    def error(self, message: str) -> None:
        """Print an error message."""
        print(f"  {self._color('[ERROR]', 'red')} {message}")

    def dim(self, message: str) -> None:
        """Print a dim/secondary message."""
        print(f"  {self._color(message, 'dim')}")

    def table_row(self, col1: str, col2: str, col1_width: int = 30) -> None:
        """Print a table row with two columns."""
        print(f"  {col1:<{col1_width}} {col2}")


# Global logger instance
log = Logger()


# =============================================================================
# Path Utilities
# =============================================================================


def get_sbs_root() -> Path:
    """Get the SBS workspace root directory."""
    return SBS_ROOT


def get_project_root(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Find project root (directory containing runway.json).

    Searches from start_dir (or cwd) upward until SBS_ROOT.
    """
    if start_dir is None:
        start_dir = Path.cwd()

    current = start_dir.resolve()
    sbs_root = get_sbs_root()

    while current != current.parent:
        if (current / "runway.json").exists():
            return current
        if current == sbs_root:
            break
        current = current.parent

    return None


def detect_project(project_root: Optional[Path] = None) -> tuple[str, Path]:
    """Detect project name and root from runway.json.

    Returns (project_name, project_root).
    Raises RuntimeError if not in a project.
    """
    if project_root is None:
        project_root = get_project_root()

    if project_root is None:
        raise RuntimeError("Not in a project directory (runway.json not found)")

    runway_json = project_root / "runway.json"
    if not runway_json.exists():
        raise RuntimeError(f"runway.json not found in {project_root}")

    data = json.loads(runway_json.read_text())
    project_name = data.get("projectName", project_root.name)

    return project_name, project_root


def get_repos() -> list[tuple[str, Path]]:
    """Get list of (name, path) for all repos in workspace.

    Only returns repos that actually exist.
    """
    repos = []
    sbs_root = get_sbs_root()

    for name in REPO_NAMES:
        path = sbs_root / name
        if path.exists():
            repos.append((name, path))

    return repos


# =============================================================================
# Git Utilities
# =============================================================================


def get_git_commit(directory: Path, short: bool = True) -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=directory,
            capture_output=True,
            text=True,
            check=True,
        )
        commit = result.stdout.strip()
        return commit[:12] if short else commit
    except Exception:
        return "unknown"


def get_git_branch(directory: Path) -> str:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=directory,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def git_has_changes(repo_path: Path) -> bool:
    """Check if a repo has uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def git_status_short(repo_path: Path) -> str:
    """Get short git status output."""
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def git_diff_stat(repo_path: Path) -> str:
    """Get git diff --stat output."""
    result = subprocess.run(
        ["git", "diff", "--stat"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


# =============================================================================
# Lakefile Parsing
# =============================================================================


def parse_lakefile(repo_path: Path) -> list[dict[str, Any]]:
    """Parse lakefile.toml or lakefile.lean and return requirements."""
    toml_path = repo_path / "lakefile.toml"
    lean_path = repo_path / "lakefile.lean"

    if toml_path.exists():
        return _parse_lakefile_toml(toml_path)
    elif lean_path.exists():
        return _parse_lakefile_lean(lean_path)
    else:
        return []


def _parse_lakefile_toml(path: Path) -> list[dict[str, Any]]:
    """Parse a lakefile.toml and return the list of requirements."""
    try:
        import tomllib
    except ImportError:
        try:
            import toml as tomllib  # type: ignore
        except ImportError:
            return []

    content = path.read_text()

    if hasattr(tomllib, 'loads'):
        data = tomllib.loads(content)
    else:
        data = tomllib.load(path.open('rb'))

    return data.get("require", [])


def _parse_lakefile_lean(path: Path) -> list[dict[str, Any]]:
    """Parse a lakefile.lean and extract requirements."""
    import re

    content = path.read_text()
    requirements = []

    pattern = r'require\s+(\w+)\s+from\s+git\s+"([^"]+)"(?:\s*@\s*|\s+@\s+)"([^"]+)"'

    for match in re.finditer(pattern, content):
        name, git, rev = match.groups()
        requirements.append({
            "name": name,
            "git": git,
            "rev": rev,
        })

    return requirements


def get_lean_toolchain(repo_path: Path) -> Optional[str]:
    """Get the lean-toolchain version for a repo."""
    toolchain_path = repo_path / "lean-toolchain"
    if toolchain_path.exists():
        return toolchain_path.read_text().strip()
    return None


# =============================================================================
# Runtime Utilities
# =============================================================================


def run_cmd(
    cmd: list[str],
    cwd: Optional[Path] = None,
    capture: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run a command with proper error handling."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture,
            text=True,
            check=check,
        )
        return result
    except subprocess.CalledProcessError as e:
        if capture:
            log.error(f"Command failed: {' '.join(cmd)}")
            if e.stdout:
                log.error(f"stdout: {e.stdout}")
            if e.stderr:
                log.error(f"stderr: {e.stderr}")
        raise
