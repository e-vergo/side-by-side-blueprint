"""sbs clean -- Remove build artifacts and caches."""

from __future__ import annotations

import shutil
from pathlib import Path

from sbs_core.utils import log, SBS_ROOT, CACHE_DIR, REPO_PATHS

try:
    from sbs.build.config import TOOLCHAIN_BUILD_ORDER
except ImportError:
    # Fallback: define inline if sbs.build is not available
    TOOLCHAIN_BUILD_ORDER = ["subverso", "LeanArchitect", "Dress", "Runway"]


# =============================================================================
# Constants
# =============================================================================

# Project name -> relative path from SBS_ROOT
PROJECT_PATHS: dict[str, str] = {
    "SBSTest": "toolchain/SBS-Test",
    "GCR": "showcase/General_Crystallographic_Restriction",
    "PNT": "showcase/PrimeNumberTheoremAnd",
}

# Project name -> repo key in REPO_PATHS (for cache dir naming)
PROJECT_REPO_KEYS: dict[str, str] = {
    "SBSTest": "SBS-Test",
    "GCR": "General_Crystallographic_Restriction",
    "PNT": "PrimeNumberTheoremAnd",
}


# =============================================================================
# Utilities
# =============================================================================


def _get_dir_size(path: Path) -> int:
    """Get total size of a directory in bytes."""
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    if size_bytes == 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            if unit == "B":
                return f"{size_bytes} {unit}"
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _collect_clean_targets(
    repo_name: str,
    repo_path: Path,
    cache_dir: Path,
    full: bool = False,
) -> list[tuple[Path, int]]:
    """Collect paths that would be cleaned for a repo.

    Returns list of (path, size_in_bytes) for existing targets.
    """
    targets: list[tuple[Path, int]] = []

    # .lake/build (always)
    build_dir = repo_path / ".lake" / "build"
    if build_dir.exists():
        targets.append((build_dir, _get_dir_size(build_dir)))

    # lakefile.olean (always)
    lakefile_olean = repo_path / "lakefile.olean"
    if lakefile_olean.exists():
        targets.append((lakefile_olean, lakefile_olean.stat().st_size))

    # Cache dir for this repo (always, if exists)
    repo_cache = cache_dir / repo_name
    if repo_cache.exists():
        targets.append((repo_cache, _get_dir_size(repo_cache)))

    # .lake/packages (only if full)
    if full:
        packages_dir = repo_path / ".lake" / "packages"
        if packages_dir.exists():
            targets.append((packages_dir, _get_dir_size(packages_dir)))

    return targets


# =============================================================================
# Core Clean Logic
# =============================================================================


def clean_repo(
    repo_name: str,
    repo_path: Path,
    cache_dir: Path,
    full: bool = False,
    dry_run: bool = False,
) -> list[str]:
    """Clean build artifacts for a single repo.

    Returns list of removed (or would-remove) paths as strings.
    """
    targets = _collect_clean_targets(repo_name, repo_path, cache_dir, full)
    removed: list[str] = []

    for path, size in targets:
        size_str = _format_size(size)
        if dry_run:
            log.info(f"[DRY-RUN] Would remove {path} ({size_str})")
        else:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            log.info(f"Removed {path} ({size_str})")
        removed.append(str(path))

    return removed


# =============================================================================
# CLI Handler
# =============================================================================


def cmd_clean(args) -> int:
    """Handle 'sbs clean' command."""
    dry_run = getattr(args, "check", False)
    full = getattr(args, "full", False)
    project = getattr(args, "project", None)
    all_repos = getattr(args, "all", False)
    force = getattr(args, "force", False)

    # --all without --force is dry-run
    if all_repos and not force:
        dry_run = True
        log.warning("--all without --force: showing what would be cleaned (dry run)")
        log.info("Add --force to actually delete.\n")

    if not project and not all_repos:
        log.error("Specify --project <name> or --all to select what to clean.")
        log.info("  sbs clean --project SBSTest --check   # Preview")
        log.info("  sbs clean --project SBSTest           # Clean project + toolchain")
        log.info("  sbs clean --all --force               # Clean everything")
        return 1

    # Build list of (display_name, repo_key, repo_path) to clean
    repos_to_clean: list[tuple[str, str, Path]] = []

    if project:
        # Resolve project path
        if project not in PROJECT_PATHS:
            log.error(f"Unknown project: {project}. Choose from: {', '.join(PROJECT_PATHS)}")
            return 1

        # Add toolchain repos (upstream dependencies)
        for tc_name in TOOLCHAIN_BUILD_ORDER:
            if tc_name in REPO_PATHS:
                tc_path = SBS_ROOT / REPO_PATHS[tc_name]
                if tc_path.exists():
                    repos_to_clean.append((tc_name, tc_name, tc_path))

        # Add the project itself
        proj_path = SBS_ROOT / PROJECT_PATHS[project]
        repo_key = PROJECT_REPO_KEYS.get(project, project)
        if proj_path.exists():
            repos_to_clean.append((project, repo_key, proj_path))

    elif all_repos:
        # All toolchain repos
        for tc_name in TOOLCHAIN_BUILD_ORDER:
            if tc_name in REPO_PATHS:
                tc_path = SBS_ROOT / REPO_PATHS[tc_name]
                if tc_path.exists():
                    repos_to_clean.append((tc_name, tc_name, tc_path))

        # All projects
        for proj_name, proj_rel in PROJECT_PATHS.items():
            proj_path = SBS_ROOT / proj_rel
            repo_key = PROJECT_REPO_KEYS.get(proj_name, proj_name)
            if proj_path.exists():
                repos_to_clean.append((proj_name, repo_key, proj_path))

    # Execute cleaning and collect summary
    mode_label = "DRY RUN" if dry_run else "CLEAN"
    log.header(f"{mode_label}: {project or 'all repos'}")
    if full:
        log.warning("Full mode: .lake/packages/ will also be removed\n")

    summary: list[tuple[str, str, str, str]] = []  # (name, path, size, status)
    total_size = 0

    for display_name, repo_key, repo_path in repos_to_clean:
        targets = _collect_clean_targets(repo_key, repo_path, CACHE_DIR, full)

        if not targets:
            summary.append((display_name, str(repo_path), "0 B", "clean"))
            continue

        repo_size = sum(s for _, s in targets)
        total_size += repo_size

        removed = clean_repo(repo_key, repo_path, CACHE_DIR, full, dry_run)
        status = "would remove" if dry_run else "removed"
        summary.append((display_name, str(repo_path), _format_size(repo_size), status))

    # Print summary table
    print()
    log.header("Summary")

    # Column widths
    name_w = max(len(s[0]) for s in summary) if summary else 10
    size_w = max(len(s[2]) for s in summary) if summary else 6

    for name, path, size, status in summary:
        log.info(f"{name:<{name_w}}  {size:>{size_w}}  {status}")

    print()
    log.info(f"Total: {_format_size(total_size)}")

    if dry_run and not getattr(args, "check", False):
        # Was auto-dry-run from --all without --force
        log.info("\nRe-run with --force to actually delete.")

    return 0
