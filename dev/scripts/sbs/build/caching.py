"""
Build caching for Side-by-Side Blueprint.

Provides caching of toolchain builds to speed up repeated builds.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Optional

from sbs.core.utils import log
from sbs.build.config import get_lakefile_path


# =============================================================================
# Cache Key Generation
# =============================================================================


def get_cache_key(repo_path: Path) -> str:
    """Generate a cache key based on lakefile content and lean-toolchain."""
    hasher = hashlib.sha256()

    # Include lakefile content
    lakefile_path, _ = get_lakefile_path(repo_path)
    if lakefile_path and lakefile_path.exists():
        hasher.update(lakefile_path.read_bytes())

    # Include lean-toolchain
    toolchain_path = repo_path / "lean-toolchain"
    if toolchain_path.exists():
        hasher.update(toolchain_path.read_bytes())

    return hasher.hexdigest()[:16]


# =============================================================================
# Cache Operations
# =============================================================================


def get_cached_build(cache_dir: Path, repo_name: str, cache_key: str) -> Optional[Path]:
    """Check if a cached build exists and return its path."""
    cache_path = cache_dir / repo_name / cache_key
    if cache_path.exists():
        return cache_path
    return None


def save_to_cache(
    cache_dir: Path,
    repo_name: str,
    cache_key: str,
    build_dir: Path,
    dry_run: bool = False,
) -> None:
    """Save build artifacts to cache."""
    if dry_run:
        log.info(f"[DRY-RUN] Would cache {repo_name} build to {cache_dir / repo_name / cache_key}")
        return

    cache_path = cache_dir / repo_name / cache_key
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        shutil.rmtree(cache_path)

    if build_dir.exists():
        shutil.copytree(build_dir, cache_path)


def restore_from_cache(
    cache_path: Path,
    build_dir: Path,
    dry_run: bool = False,
) -> None:
    """Restore build artifacts from cache."""
    if dry_run:
        log.info(f"[DRY-RUN] Would restore from cache {cache_path} to {build_dir}")
        return

    if build_dir.exists():
        shutil.rmtree(build_dir)

    build_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(cache_path, build_dir)
