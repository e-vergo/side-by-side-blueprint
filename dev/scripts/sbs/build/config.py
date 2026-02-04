"""
Build configuration for Side-by-Side Blueprint.

Constants, dataclasses, and project detection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# =============================================================================
# Constants
# =============================================================================

# Import shared constants from core
from sbs.core.utils import SBS_ROOT, CACHE_DIR, REPO_PATHS, REPO_NAMES

# Re-export for backwards compatibility
__all__ = [
    "SBS_ROOT",
    "CACHE_DIR",
    "REPO_PATHS",
    "REPO_NAMES",
    "REQUIRED_MATHLIB_VERSION",
    "TOOLCHAIN_BUILD_ORDER",
    "Repo",
    "BuildConfig",
    "detect_project",
    "get_lakefile_path",
]

# Required mathlib version (enforced across all projects)
REQUIRED_MATHLIB_VERSION = "v4.27.0"

# Toolchain build order
TOOLCHAIN_BUILD_ORDER = ["subverso", "LeanArchitect", "Dress", "Runway"]


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Repo:
    """Represents a repository in the build system."""

    name: str
    path: Path
    dependencies: list[str] = field(default_factory=list)
    is_toolchain: bool = False
    has_lakefile: bool = False
    lakefile_type: str = ""  # "toml" or "lean"

    def exists(self) -> bool:
        return self.path.exists()


@dataclass
class BuildConfig:
    """Configuration for a build run."""

    project_root: Path
    project_name: str
    module_name: str
    sbs_root: Path = field(default_factory=lambda: SBS_ROOT)
    cache_dir: Path = field(default_factory=lambda: CACHE_DIR)
    skip_cache: bool = False
    skip_validation: bool = False  # Skip pre-flight validation checks
    dry_run: bool = False
    verbose: bool = False
    capture: bool = False
    capture_url: str = "http://localhost:8000"
    force_lake: bool = False  # Force Lake builds even if Lean sources unchanged
    force_clean: bool = False  # Force full cleanup of build artifacts
    force_full_build: bool = False  # Force full build even if CSS-only change detected


# =============================================================================
# Project Detection
# =============================================================================


def get_lakefile_path(repo_path: Path) -> tuple[Optional[Path], str]:
    """Find the lakefile in a repo and return its path and type."""
    toml_path = repo_path / "lakefile.toml"
    lean_path = repo_path / "lakefile.lean"

    if toml_path.exists():
        return toml_path, "toml"
    elif lean_path.exists():
        return lean_path, "lean"
    else:
        return None, ""


def detect_project(project_root: Path) -> tuple[str, str]:
    """Detect project name and module name from runway.json.

    Returns (project_name, module_name).
    """
    runway_json = project_root / "runway.json"

    if not runway_json.exists():
        raise RuntimeError(f"runway.json not found in {project_root}")

    data = json.loads(runway_json.read_text())
    project_name = data.get("projectName")

    if not project_name:
        raise RuntimeError("Could not extract projectName from runway.json")

    # Module name is same as project name
    return project_name, project_name
