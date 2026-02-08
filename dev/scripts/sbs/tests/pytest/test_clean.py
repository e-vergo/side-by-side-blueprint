"""
Tests for sbs clean command: target collection and repo cleaning.

Validates that _collect_clean_targets identifies the correct paths
and clean_repo removes them (or preserves them in dry-run mode).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sbs.commands.clean import _collect_clean_targets, clean_repo


# =============================================================================
# Target Collection Tests
# =============================================================================


@pytest.mark.evergreen
class TestCleanTargetCollection:
    """_collect_clean_targets returns correct paths for various configurations."""

    def test_collect_targets_includes_build_dir(self, tmp_path: Path) -> None:
        """Build dir (.lake/build/) is included when it exists."""
        repo = tmp_path / "repo"
        build_dir = repo / ".lake" / "build"
        build_dir.mkdir(parents=True)
        (build_dir / "lib.olean").write_bytes(b"\x00" * 100)

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        targets = _collect_clean_targets("repo", repo, cache_dir)
        target_paths = [p for p, _ in targets]

        assert build_dir in target_paths

    def test_collect_targets_includes_lakefile_olean(self, tmp_path: Path) -> None:
        """lakefile.olean is included when it exists."""
        repo = tmp_path / "repo"
        repo.mkdir()
        lakefile = repo / "lakefile.olean"
        lakefile.write_bytes(b"\x00" * 50)

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        targets = _collect_clean_targets("repo", repo, cache_dir)
        target_paths = [p for p, _ in targets]

        assert lakefile in target_paths

    def test_collect_targets_includes_cache_dir(self, tmp_path: Path) -> None:
        """Cache directory for the repo is included when it exists."""
        repo = tmp_path / "repo"
        repo.mkdir()

        cache_dir = tmp_path / "cache"
        repo_cache = cache_dir / "repo"
        repo_cache.mkdir(parents=True)
        (repo_cache / "lean_hash").write_text("abc123")

        targets = _collect_clean_targets("repo", repo, cache_dir)
        target_paths = [p for p, _ in targets]

        assert repo_cache in target_paths

    def test_collect_targets_full_includes_packages(self, tmp_path: Path) -> None:
        """.lake/packages/ is included when full=True."""
        repo = tmp_path / "repo"
        packages_dir = repo / ".lake" / "packages"
        packages_dir.mkdir(parents=True)
        (packages_dir / "mathlib").mkdir()

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        targets = _collect_clean_targets("repo", repo, cache_dir, full=True)
        target_paths = [p for p, _ in targets]

        assert packages_dir in target_paths

    def test_collect_targets_full_false_excludes_packages(self, tmp_path: Path) -> None:
        """.lake/packages/ is NOT included when full=False."""
        repo = tmp_path / "repo"
        packages_dir = repo / ".lake" / "packages"
        packages_dir.mkdir(parents=True)
        (packages_dir / "mathlib").mkdir()

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        targets = _collect_clean_targets("repo", repo, cache_dir, full=False)
        target_paths = [p for p, _ in targets]

        assert packages_dir not in target_paths

    def test_collect_targets_missing_dirs_skipped(self, tmp_path: Path) -> None:
        """Non-existent repo path returns empty target list."""
        repo = tmp_path / "nonexistent_repo"
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        targets = _collect_clean_targets("nonexistent", repo, cache_dir)

        assert targets == []


# =============================================================================
# Repo Cleaning Tests
# =============================================================================


@pytest.mark.evergreen
class TestCleanRepo:
    """clean_repo removes targets or preserves them in dry-run mode."""

    def test_clean_repo_removes_build_dir(self, tmp_path: Path) -> None:
        """.lake/build/ is removed after clean_repo."""
        repo = tmp_path / "repo"
        build_dir = repo / ".lake" / "build"
        build_dir.mkdir(parents=True)
        (build_dir / "lib.olean").write_bytes(b"\x00" * 100)

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        removed = clean_repo("repo", repo, cache_dir)

        assert not build_dir.exists()
        assert any(".lake/build" in r for r in removed)

    def test_clean_repo_removes_lakefile_olean(self, tmp_path: Path) -> None:
        """lakefile.olean is removed after clean_repo."""
        repo = tmp_path / "repo"
        repo.mkdir()
        lakefile = repo / "lakefile.olean"
        lakefile.write_bytes(b"\x00" * 50)

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        removed = clean_repo("repo", repo, cache_dir)

        assert not lakefile.exists()
        assert any("lakefile.olean" in r for r in removed)

    def test_clean_repo_dry_run_preserves_all(self, tmp_path: Path) -> None:
        """With dry_run=True, all files are preserved."""
        repo = tmp_path / "repo"
        build_dir = repo / ".lake" / "build"
        build_dir.mkdir(parents=True)
        (build_dir / "lib.olean").write_bytes(b"\x00" * 100)

        lakefile = repo / "lakefile.olean"
        lakefile.write_bytes(b"\x00" * 50)

        cache_dir = tmp_path / "cache"
        repo_cache = cache_dir / "repo"
        repo_cache.mkdir(parents=True)
        (repo_cache / "lean_hash").write_text("abc123")

        removed = clean_repo("repo", repo, cache_dir, dry_run=True)

        # Everything still exists
        assert build_dir.exists()
        assert lakefile.exists()
        assert repo_cache.exists()

        # But paths were still reported
        assert len(removed) > 0

    def test_clean_repo_nonexistent_is_noop(self, tmp_path: Path) -> None:
        """Cleaning a non-existent repo path does not error."""
        repo = tmp_path / "nonexistent_repo"
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        removed = clean_repo("nonexistent", repo, cache_dir)

        assert removed == []
