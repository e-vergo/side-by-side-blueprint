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
# Lean Source Change Detection
# =============================================================================


def get_lean_sources_hash(repo_path: Path) -> str:
    """Hash all .lean files in a repo for change detection.

    Uses git ls-files + git hash-object for speed (O(tracked files), no disk reads).
    Falls back to reading files directly if not a git repo.

    Returns:
        16-char hex hash of all .lean file contents, or "" if no .lean files found.
    """
    import subprocess

    hasher = hashlib.sha256()
    found_any = False

    try:
        # Fast path: use git to list and hash tracked .lean files
        result = subprocess.run(
            ["git", "ls-files", "--", "*.lean"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            lean_files = sorted(result.stdout.strip().split("\n"))
            for f in lean_files:
                full_path = repo_path / f
                if full_path.exists():
                    hasher.update(full_path.read_bytes())
                    found_any = True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Fallback: walk directory manually
        for lean_file in sorted(repo_path.rglob("*.lean")):
            # Skip .lake directory
            if ".lake" in lean_file.parts:
                continue
            hasher.update(lean_file.read_bytes())
            found_any = True

    return hasher.hexdigest()[:16] if found_any else ""


def _lean_hash_path(cache_dir: Path, repo_name: str) -> Path:
    """Return the path where we store the last-known lean sources hash."""
    return cache_dir / repo_name / "lean_hash"


def save_lean_hash(cache_dir: Path, repo_name: str, lean_hash: str) -> None:
    """Save the current lean sources hash for a repo."""
    path = _lean_hash_path(cache_dir, repo_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(lean_hash)


def load_lean_hash(cache_dir: Path, repo_name: str) -> Optional[str]:
    """Load the last-saved lean sources hash for a repo.

    Returns None if no hash was previously saved.
    """
    path = _lean_hash_path(cache_dir, repo_name)
    if path.exists():
        return path.read_text().strip()
    return None


def has_lean_changes(repo_path: Path, cache_dir: Path, repo_name: str) -> bool:
    """Check if Lean sources have changed since last successful build.

    Compares current lean sources hash against the last-saved hash.
    Returns True if:
    - No previous hash exists (first build)
    - Current hash differs from saved hash
    - Hash computation fails (err on the side of building)
    """
    try:
        current_hash = get_lean_sources_hash(repo_path)
        if not current_hash:
            # No .lean files found — no changes possible
            return False

        saved_hash = load_lean_hash(cache_dir, repo_name)
        if saved_hash is None:
            log.info(f"  {repo_name}: No previous Lean hash (first build)")
            return True

        changed = current_hash != saved_hash
        if not changed:
            log.info(f"  {repo_name}: Lean sources unchanged (hash: {current_hash})")
        else:
            log.info(f"  {repo_name}: Lean sources changed ({saved_hash} -> {current_hash})")
        return changed
    except Exception as e:
        log.warning(f"  {repo_name}: Hash check failed ({e}), assuming changes")
        return True


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
