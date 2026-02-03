"""
Shared pytest fixtures for validator tests.

This module provides common fixtures used across multiple validator test files,
reducing duplication and ensuring consistent test setup.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator

import pytest


# =============================================================================
# Constants
# =============================================================================

# Default pages used by multi-page validators (T4, T7, T8)
DEFAULT_PAGES = ["dashboard", "chapter", "dep_graph"]


# =============================================================================
# Screenshot Directory Fixtures
# =============================================================================


@pytest.fixture
def temp_screenshots_dir() -> Generator[Path, None, None]:
    """Create a temporary directory with mock screenshots for common pages.

    Creates empty .png files for: dashboard, chapter, dep_graph.
    These are the pages commonly checked by multi-page validators.

    Yields:
        Path to the temporary directory containing mock screenshots.
    """
    with tempfile.TemporaryDirectory(prefix="sbs_validator_test_") as tmpdir:
        path = Path(tmpdir)
        for page in DEFAULT_PAGES:
            (path / f"{page}.png").touch()
        yield path


@pytest.fixture
def empty_screenshots_dir() -> Generator[Path, None, None]:
    """Create an empty temporary directory.

    Useful for testing edge cases where no screenshots exist.

    Yields:
        Path to an empty temporary directory.
    """
    with tempfile.TemporaryDirectory(prefix="sbs_validator_empty_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def single_page_screenshots_dir() -> Generator[Path, None, None]:
    """Create a temporary directory with only a chapter screenshot.

    Useful for testing single-page validators or edge cases where
    only one page is available.

    Yields:
        Path to the temporary directory containing one chapter.png file.
    """
    with tempfile.TemporaryDirectory(prefix="sbs_validator_single_") as tmpdir:
        path = Path(tmpdir)
        (path / "chapter.png").touch()
        yield path


# =============================================================================
# CSS Path Fixtures
# =============================================================================


@pytest.fixture
def common_css_path() -> Path:
    """Get the path to the real common.css file.

    Returns the path to the canonical common.css file in the
    dress-blueprint-action/assets directory. This fixture is used
    by T5 (status color match) and T6 (CSS variable coverage) validators.

    Returns:
        Path to common.css in the toolchain assets directory.
    """
    # Navigate from conftest.py to the CSS file:
    # sbs/tests/pytest/validators/conftest.py
    # -> dev/scripts/sbs/tests/pytest/validators/
    # Need to go up to dev/, then to monorepo root, then into toolchain
    conftest_file = Path(__file__).resolve()
    # Go up: validators -> pytest -> tests -> sbs -> scripts -> dev -> monorepo
    dev_dir = conftest_file.parent.parent.parent.parent.parent.parent
    return dev_dir.parent / "toolchain" / "dress-blueprint-action" / "assets" / "common.css"


@pytest.fixture
def real_css_dir() -> Path:
    """Get the path to the real CSS assets directory.

    Returns the path to the dress-blueprint-action/assets directory
    containing all CSS files (common.css, blueprint.css, paper.css, dep_graph.css).

    Returns:
        Path to the CSS assets directory.
    """
    conftest_file = Path(__file__).resolve()
    dev_dir = conftest_file.parent.parent.parent.parent.parent.parent
    return dev_dir.parent / "toolchain" / "dress-blueprint-action" / "assets"
