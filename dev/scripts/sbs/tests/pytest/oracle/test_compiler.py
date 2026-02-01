"""
Tests for sbs.oracle.compiler module.

Tests the OracleCompiler class that aggregates knowledge from multiple
README files into a single Oracle agent file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sbs.oracle.compiler import OracleCompiler


class TestOracleCompiler:
    """Tests for OracleCompiler class."""

    def test_compile_returns_string(self, tmp_path: Path) -> None:
        """compile() returns a non-empty string."""
        # Create minimal structure
        (tmp_path / "CLAUDE.md").write_text("# Test\n")
        (tmp_path / "forks").mkdir()
        (tmp_path / "toolchain").mkdir()
        (tmp_path / "showcase").mkdir()
        (tmp_path / "dev").mkdir()

        compiler = OracleCompiler(tmp_path)
        result = compiler.compile()

        assert isinstance(result, str)
        assert len(result) > 0

    def test_compile_includes_frontmatter(self, tmp_path: Path) -> None:
        """Output includes YAML frontmatter."""
        (tmp_path / "CLAUDE.md").write_text("# Test\n")
        for d in ["forks", "toolchain", "showcase", "dev"]:
            (tmp_path / d).mkdir()

        compiler = OracleCompiler(tmp_path)
        result = compiler.compile()

        assert result.startswith("---")
        assert "sbs-oracle" in result

    def test_compile_includes_sections(self, tmp_path: Path) -> None:
        """Output includes expected section headers."""
        (tmp_path / "CLAUDE.md").write_text("# Test\n")
        for d in ["forks", "toolchain", "showcase", "dev"]:
            (tmp_path / d).mkdir()

        compiler = OracleCompiler(tmp_path)
        result = compiler.compile()

        assert "Concept Index" in result
        assert "File Purpose Map" in result
        assert "How-To Patterns" in result
        assert "Gotchas" in result
        assert "Cross-Repo Impact" in result

    def test_collects_readme_files(self, tmp_path: Path) -> None:
        """Finds README.md files in source directories."""
        (tmp_path / "CLAUDE.md").write_text("# Root\n")
        (tmp_path / "forks").mkdir()
        (tmp_path / "forks" / "subverso").mkdir()
        (tmp_path / "forks" / "subverso" / "README.md").write_text("# SubVerso\n")
        (tmp_path / "toolchain").mkdir()
        (tmp_path / "showcase").mkdir()
        (tmp_path / "dev").mkdir()

        compiler = OracleCompiler(tmp_path)
        sources = compiler._collect_sources()

        # Should find CLAUDE.md and subverso README
        paths = [str(p.relative_to(tmp_path)) for p, _ in sources]
        assert "CLAUDE.md" in paths
        assert "forks/subverso/README.md" in paths

    def test_excludes_lake_packages(self, tmp_path: Path) -> None:
        """Skip .lake/packages directories."""
        (tmp_path / "CLAUDE.md").write_text("# Root\n")
        (tmp_path / "forks").mkdir()
        (tmp_path / "toolchain").mkdir()
        (tmp_path / "toolchain" / ".lake").mkdir()
        (tmp_path / "toolchain" / ".lake" / "packages").mkdir()
        (tmp_path / "toolchain" / ".lake" / "packages" / "README.md").write_text("# Skip\n")
        (tmp_path / "showcase").mkdir()
        (tmp_path / "dev").mkdir()

        compiler = OracleCompiler(tmp_path)
        sources = compiler._collect_sources()

        paths = [str(p) for p, _ in sources]
        assert not any(".lake/packages" in p for p in paths)

    def test_extracts_file_tables_from_readme(self, tmp_path: Path) -> None:
        """File tables from README are extracted."""
        readme_content = """
# Test Repo

| File | Purpose |
|------|---------|
| main.lean | Entry point |
| utils.lean | Helpers |
"""
        (tmp_path / "CLAUDE.md").write_text("# Root\n")
        (tmp_path / "forks").mkdir()
        (tmp_path / "toolchain").mkdir()
        (tmp_path / "toolchain" / "Dress").mkdir()
        (tmp_path / "toolchain" / "Dress" / "README.md").write_text(readme_content)
        (tmp_path / "showcase").mkdir()
        (tmp_path / "dev").mkdir()

        compiler = OracleCompiler(tmp_path)
        result = compiler.compile()

        # Should include the file entries somewhere
        assert "main.lean" in result or "Entry point" in result

    def test_write_oracle_creates_file(self, tmp_path: Path) -> None:
        """write_oracle creates the output file."""
        (tmp_path / "CLAUDE.md").write_text("# Test\n")
        for d in ["forks", "toolchain", "showcase", "dev"]:
            (tmp_path / d).mkdir()

        compiler = OracleCompiler(tmp_path)
        output_path = tmp_path / "test-oracle.md"
        result_path = compiler.write_oracle(output_path)

        assert result_path == output_path
        assert output_path.exists()
        content = output_path.read_text()
        assert len(content) > 0

    def test_write_oracle_default_path(self, tmp_path: Path) -> None:
        """write_oracle uses default path when not specified."""
        (tmp_path / "CLAUDE.md").write_text("# Test\n")
        for d in ["forks", "toolchain", "showcase", "dev"]:
            (tmp_path / d).mkdir()

        compiler = OracleCompiler(tmp_path)
        result_path = compiler.write_oracle()

        expected = tmp_path / ".claude" / "agents" / "sbs-oracle.md"
        assert result_path == expected
        assert expected.exists()

    def test_raises_for_nonexistent_root(self) -> None:
        """Raise ValueError for nonexistent repo root."""
        with pytest.raises(ValueError, match="does not exist"):
            OracleCompiler(Path("/nonexistent/path"))

    def test_extract_repo_name_from_path(self, tmp_path: Path) -> None:
        """_extract_repo_name identifies repo from path."""
        (tmp_path / "CLAUDE.md").write_text("# Test\n")
        for d in ["forks", "toolchain", "showcase", "dev"]:
            (tmp_path / d).mkdir()

        compiler = OracleCompiler(tmp_path)

        # Test different path patterns
        path1 = tmp_path / "forks" / "subverso" / "README.md"
        assert compiler._extract_repo_name(path1) == "subverso"

        path2 = tmp_path / "toolchain" / "Dress" / "README.md"
        assert compiler._extract_repo_name(path2) == "Dress"

        path3 = tmp_path / "CLAUDE.md"
        assert compiler._extract_repo_name(path3) == "root"

    def test_cross_repo_impacts_included(self, tmp_path: Path) -> None:
        """Cross-repo impact map is included in output."""
        (tmp_path / "CLAUDE.md").write_text("# Test\n")
        for d in ["forks", "toolchain", "showcase", "dev"]:
            (tmp_path / d).mkdir()

        compiler = OracleCompiler(tmp_path)
        result = compiler.compile()

        # Should include some of the known cross-repo impacts
        assert "SubVerso" in result or "LeanArchitect" in result or "Dress" in result
