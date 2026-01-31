"""
Dependency version checking for Side-by-Side Blueprint.

Shows versions across repos and highlights mismatches.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .utils import (
    get_repos,
    get_lean_toolchain,
    parse_lakefile,
    log,
)


# =============================================================================
# Version Extraction
# =============================================================================


def get_repo_versions(repo_path: Path) -> dict[str, Any]:
    """Get all relevant versions for a repo.

    Returns dict with: lean_toolchain, dependencies (name -> version)
    """
    versions = {
        "lean_toolchain": get_lean_toolchain(repo_path),
        "dependencies": {},
    }

    requirements = parse_lakefile(repo_path)
    for req in requirements:
        name = req.get("name", "")
        rev = req.get("rev", "")
        if name and rev:
            versions["dependencies"][name] = rev

    return versions


def collect_all_versions() -> dict[str, dict[str, Any]]:
    """Collect versions from all repos.

    Returns dict mapping repo_name -> versions dict
    """
    all_versions = {}

    for name, path in get_repos():
        all_versions[name] = get_repo_versions(path)

    return all_versions


def find_version_mismatches(all_versions: dict) -> list[dict]:
    """Find version mismatches across repos.

    Returns list of dicts with: dependency, repos (list of (repo, version))
    """
    # Collect all versions per dependency
    dep_versions: dict[str, list[tuple[str, str]]] = {}

    for repo_name, versions in all_versions.items():
        for dep_name, dep_version in versions.get("dependencies", {}).items():
            if dep_name not in dep_versions:
                dep_versions[dep_name] = []
            dep_versions[dep_name].append((repo_name, dep_version))

    # Find mismatches
    mismatches = []
    for dep_name, repos in dep_versions.items():
        versions_set = set(v for _, v in repos)
        if len(versions_set) > 1:
            mismatches.append({
                "dependency": dep_name,
                "repos": repos,
            })

    return mismatches


# =============================================================================
# Table Formatting
# =============================================================================


def format_versions_table(all_versions: dict) -> list[str]:
    """Format versions as a table.

    Returns list of lines.
    """
    lines = []

    # Collect all dependencies
    all_deps = set()
    for versions in all_versions.values():
        all_deps.update(versions.get("dependencies", {}).keys())

    # Sort repos and deps
    repos = sorted(all_versions.keys())
    deps = sorted(all_deps)

    # Header
    col_width = max(len(r) for r in repos) + 2
    header = f"{'Dependency':<20}"
    for repo in repos:
        header += f" {repo:<{col_width}}"
    lines.append(header)
    lines.append("-" * len(header))

    # Lean toolchain row
    row = f"{'lean-toolchain':<20}"
    for repo in repos:
        tc = all_versions[repo].get("lean_toolchain", "-") or "-"
        row += f" {tc:<{col_width}}"
    lines.append(row)

    # Dependency rows
    for dep in deps:
        row = f"{dep:<20}"
        versions_in_row = []
        for repo in repos:
            version = all_versions[repo].get("dependencies", {}).get(dep, "-")
            versions_in_row.append(version)
            row += f" {version:<{col_width}}"

        # Check for mismatch
        unique = set(v for v in versions_in_row if v != "-")
        if len(unique) > 1:
            row += " [MISMATCH]"

        lines.append(row)

    return lines


# =============================================================================
# CLI Entry Point
# =============================================================================


def cmd_versions(args) -> int:
    """Main entry point for the versions command."""
    log.header("Dependency Versions Across Repos")

    try:
        # Collect versions
        all_versions = collect_all_versions()

        if not all_versions:
            log.warning("No repos found")
            return 1

        print()

        # Find mismatches
        mismatches = find_version_mismatches(all_versions)

        if args.table:
            # Table view
            lines = format_versions_table(all_versions)
            for line in lines:
                print(f"  {line}")
        else:
            # Condensed view
            # Group by lean toolchain
            toolchains = {}
            for repo, versions in all_versions.items():
                tc = versions.get("lean_toolchain", "unknown")
                if tc not in toolchains:
                    toolchains[tc] = []
                toolchains[tc].append(repo)

            log.info("Lean Toolchains:")
            for tc, repos in sorted(toolchains.items(), key=lambda x: x[0] or ""):
                log.info(f"  {tc}: {', '.join(repos)}")

            print()

            # Key dependencies
            key_deps = ["mathlib", "LeanArchitect", "Dress", "Runway", "SubVerso"]
            log.info("Key Dependencies:")

            for dep in key_deps:
                versions_found = []
                for repo, versions in all_versions.items():
                    v = versions.get("dependencies", {}).get(dep)
                    if v:
                        versions_found.append((repo, v))

                if versions_found:
                    unique = set(v for _, v in versions_found)
                    if len(unique) == 1:
                        v = list(unique)[0]
                        repos = [r for r, _ in versions_found]
                        log.info(f"  {dep}: {v} ({len(repos)} repos)")
                    else:
                        log.warning(f"  {dep}: MISMATCH")
                        for repo, v in versions_found:
                            log.dim(f"    {repo}: {v}")

        print()

        # Report mismatches
        if mismatches:
            log.header("Version Mismatches")
            for mismatch in mismatches:
                dep = mismatch["dependency"]
                log.warning(f"{dep}:")
                for repo, version in mismatch["repos"]:
                    log.dim(f"  {repo}: {version}")
            print()
            log.error(f"Found {len(mismatches)} version mismatch(es)")
            return 1
        else:
            log.success("No version mismatches found")
            return 0

    except KeyboardInterrupt:
        log.warning("Interrupted")
        return 130
    except Exception as e:
        log.error(str(e))
        return 1
