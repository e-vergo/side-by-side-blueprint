"""
sbs.build - Build orchestration for Side-by-Side Blueprint.

Provides multi-repo build coordination with caching, compliance checks,
and metrics tracking.
"""

from sbs.build.config import (
    SBS_ROOT,
    CACHE_DIR,
    REPO_PATHS,
    REPO_NAMES,
    REQUIRED_MATHLIB_VERSION,
    TOOLCHAIN_BUILD_ORDER,
    Repo,
    BuildConfig,
    detect_project,
    get_lakefile_path,
)
from sbs.build.orchestrator import (
    BuildOrchestrator,
    parse_args,
    main,
)

__all__ = [
    # Constants
    "SBS_ROOT",
    "CACHE_DIR",
    "REPO_PATHS",
    "REPO_NAMES",
    "REQUIRED_MATHLIB_VERSION",
    "TOOLCHAIN_BUILD_ORDER",
    # Data classes
    "Repo",
    "BuildConfig",
    # Functions
    "detect_project",
    "get_lakefile_path",
    # Orchestrator
    "BuildOrchestrator",
    "parse_args",
    "main",
]
