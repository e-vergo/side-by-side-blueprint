"""
Tests for build staleness detection and skip_lake configuration.

Validates that BuildConfig correctly exposes the skip_lake field
and that the enhanced clean_build_artifacts removes lakefile.olean.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sbs.build.config import BuildConfig
from sbs.build.phases import clean_build_artifacts


# =============================================================================
# BuildConfig skip_lake Tests
# =============================================================================


@pytest.mark.evergreen
class TestBuildConfigSkipLake:
    """BuildConfig.skip_lake controls whether Lake builds are skipped."""

    def test_default_config_does_not_skip(self, tmp_path: Path) -> None:
        """Default BuildConfig has skip_lake=False."""
        config = BuildConfig(
            project_root=tmp_path,
            project_name="test",
            module_name="Test",
        )
        assert config.skip_lake is False

    def test_skip_lake_config_true(self, tmp_path: Path) -> None:
        """BuildConfig with skip_lake=True stores the value."""
        config = BuildConfig(
            project_root=tmp_path,
            project_name="test",
            module_name="Test",
            skip_lake=True,
        )
        assert config.skip_lake is True

    def test_skip_lake_default_means_always_build(self, tmp_path: Path) -> None:
        """When skip_lake=False (default), builds should always proceed.

        This tests the semantic contract: the default configuration
        never skips Lake builds, ensuring stale .olean files are caught.
        """
        config = BuildConfig(
            project_root=tmp_path,
            project_name="test",
            module_name="Test",
        )
        # Default skip_lake is False, meaning "do not skip" -> always build
        assert config.skip_lake is False
        # Verify it's a real bool, not a truthy/falsy stand-in
        assert isinstance(config.skip_lake, bool)


# =============================================================================
# clean_build_artifacts with lakefile.olean Tests
# =============================================================================


@pytest.mark.evergreen
class TestCleanBuildArtifactsLakefileOlean:
    """clean_build_artifacts removes lakefile.olean when requested."""

    def test_removes_lakefile_olean_by_default(self, tmp_path: Path) -> None:
        """lakefile.olean is removed when include_lakefile_olean=True (default)."""
        repo = tmp_path / "repo"
        repo.mkdir()
        lakefile = repo / "lakefile.olean"
        lakefile.write_bytes(b"\x00" * 50)

        clean_build_artifacts(repo)

        assert not lakefile.exists()

    def test_preserves_lakefile_olean_when_disabled(self, tmp_path: Path) -> None:
        """lakefile.olean is preserved when include_lakefile_olean=False."""
        repo = tmp_path / "repo"
        repo.mkdir()
        lakefile = repo / "lakefile.olean"
        lakefile.write_bytes(b"\x00" * 50)

        clean_build_artifacts(repo, include_lakefile_olean=False)

        assert lakefile.exists()

    def test_removes_build_dir_and_lakefile_olean(self, tmp_path: Path) -> None:
        """Both .lake/build/ and lakefile.olean are removed together."""
        repo = tmp_path / "repo"
        build_dir = repo / ".lake" / "build"
        build_dir.mkdir(parents=True)
        (build_dir / "lib.olean").write_bytes(b"\x00" * 100)

        lakefile = repo / "lakefile.olean"
        lakefile.write_bytes(b"\x00" * 50)

        clean_build_artifacts(repo)

        assert not build_dir.exists()
        assert not lakefile.exists()

    def test_dry_run_preserves_lakefile_olean(self, tmp_path: Path) -> None:
        """Dry run does not delete lakefile.olean."""
        repo = tmp_path / "repo"
        repo.mkdir()
        lakefile = repo / "lakefile.olean"
        lakefile.write_bytes(b"\x00" * 50)

        clean_build_artifacts(repo, dry_run=True)

        assert lakefile.exists()

    def test_removes_lean_hash_cache(self, tmp_path: Path) -> None:
        """Cache lean_hash file is removed when cache_dir and repo_name provided."""
        repo = tmp_path / "repo"
        repo.mkdir()

        cache_dir = tmp_path / "cache"
        hash_file = cache_dir / "myrepo" / "lean_hash"
        hash_file.parent.mkdir(parents=True)
        hash_file.write_text("abc123")

        clean_build_artifacts(
            repo,
            cache_dir=cache_dir,
            repo_name="myrepo",
        )

        assert not hash_file.exists()

    def test_no_error_when_nothing_exists(self, tmp_path: Path) -> None:
        """No error when repo has no build artifacts to clean."""
        repo = tmp_path / "empty_repo"
        repo.mkdir()

        # Should not raise
        clean_build_artifacts(repo)
