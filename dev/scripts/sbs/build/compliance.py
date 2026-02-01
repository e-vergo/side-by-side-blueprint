"""
Compliance checks for Side-by-Side Blueprint builds.

Validates mathlib version and internal dependency configurations.
"""

from __future__ import annotations

from typing import Any

from sbs.core.utils import parse_lakefile
from sbs.build.config import REQUIRED_MATHLIB_VERSION, Repo


# =============================================================================
# Individual Checks
# =============================================================================


def check_mathlib_version(requirements: list[dict[str, Any]], repo_name: str) -> list[str]:
    """Check that mathlib is at the required version. Returns list of errors."""
    errors = []

    for req in requirements:
        if req.get("name") == "mathlib":
            rev = req.get("rev", "")
            if rev != REQUIRED_MATHLIB_VERSION:
                errors.append(
                    f"{repo_name}: mathlib version {rev} != required {REQUIRED_MATHLIB_VERSION}"
                )

    return errors


def check_deps_point_to_main(requirements: list[dict[str, Any]], repo_name: str) -> list[str]:
    """Check that internal deps point to main branch. Returns list of errors."""
    errors = []

    # Internal repos that should point to main
    internal_repos = {"LeanArchitect", "Dress", "Runway", "subverso", "verso"}

    for req in requirements:
        name = req.get("name", "")
        if name in internal_repos:
            rev = req.get("rev", "")
            if rev != "main":
                errors.append(
                    f"{repo_name}: {name} points to '{rev}' instead of 'main'"
                )

    return errors


# =============================================================================
# Aggregate Check
# =============================================================================


def run_compliance_checks(repos: dict[str, Repo]) -> list[str]:
    """Run all compliance checks across repos. Returns list of errors."""
    errors = []

    for name, repo in repos.items():
        if not repo.exists():
            continue

        requirements = parse_lakefile(repo.path)

        # Only check mathlib version for consumer projects (not toolchain)
        if not repo.is_toolchain:
            errors.extend(check_mathlib_version(requirements, name))

        # Check internal deps point to main
        errors.extend(check_deps_point_to_main(requirements, name))

    return errors
