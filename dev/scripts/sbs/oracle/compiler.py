"""OracleCompiler: Compiles codebase knowledge from READMEs into Oracle agent file."""
import logging
from pathlib import Path
from typing import Optional

from .extractors import (
    extract_file_tables,
    extract_how_tos,
    extract_gotchas,
    build_concept_index,
)
from .templates import generate_oracle_content

logger = logging.getLogger(__name__)


class OracleCompiler:
    """
    Compiles developer-focused codebase knowledge from READMEs into a single
    Oracle agent markdown file.
    """

    # Directories to scan for README files
    SOURCE_DIRS = [
        "forks",
        "toolchain",
        "showcase",
        "dev",
    ]

    # Additional root-level files to include
    ROOT_FILES = [
        "CLAUDE.md",
    ]

    # Paths to exclude (contain external dependencies, not SBS code)
    EXCLUDE_PATTERNS = [
        ".lake/packages",
        ".lake/build",
        "node_modules",
        "vendored-js",
        ".git",
    ]

    # Known cross-repo dependencies for the impact map
    CROSS_REPO_IMPACTS = [
        ("SubVerso", "LeanArchitect", "InfoTable structure changes affect attribute processing"),
        ("SubVerso", "Verso", "Highlighting token types affect genre rendering"),
        ("LeanArchitect", "Dress", "Node/NodeStatus types must stay in sync"),
        ("LeanArchitect", "Runway", "Node types used in manifest parsing"),
        ("Dress", "Runway", "Manifest JSON schema must match"),
        ("Dress", "Runway", "Graph layout changes affect rendering"),
        ("Verso", "Dress", "Rainbow bracket rendering must coordinate"),
        ("dress-blueprint-action", "Runway", "CSS classes must match generated HTML"),
        ("dress-blueprint-action", "Dress", "Status colors must match Svg.lean hex values"),
    ]

    def __init__(self, repo_root: Path):
        """
        Initialize compiler with repository root path.

        Args:
            repo_root: Path to the Side-By-Side-Blueprint repository root
        """
        self.repo_root = Path(repo_root).resolve()
        if not self.repo_root.exists():
            raise ValueError(f"Repository root does not exist: {self.repo_root}")

    def compile(self) -> str:
        """
        Compile all sources into Oracle markdown content.

        Returns:
            Complete Oracle markdown string ready for writing to file
        """
        sources = self._collect_sources()
        logger.info(f"Found {len(sources)} source files to process")

        # Extract knowledge from all sources
        all_concepts: dict[str, tuple[str, str]] = {}
        all_files: dict[str, dict[str, str]] = {}
        all_how_tos: list[tuple[str, str]] = []
        all_gotchas: list[str] = []

        for source_path, content in sources:
            rel_path = str(source_path.relative_to(self.repo_root))
            repo_name = self._extract_repo_name(source_path)

            logger.debug(f"Processing: {rel_path}")

            try:
                # Extract file tables
                files = extract_file_tables(content, rel_path)
                if files:
                    if repo_name not in all_files:
                        all_files[repo_name] = {}
                    all_files[repo_name].update(files)
                    logger.debug(f"  - Extracted {len(files)} file entries")

                # Extract how-tos
                how_tos = extract_how_tos(content, rel_path)
                if how_tos:
                    all_how_tos.extend(how_tos)
                    logger.debug(f"  - Extracted {len(how_tos)} how-to patterns")

                # Extract gotchas
                gotchas = extract_gotchas(content, rel_path)
                if gotchas:
                    all_gotchas.extend(gotchas)
                    logger.debug(f"  - Extracted {len(gotchas)} gotchas")

                # Build concept index
                concepts = build_concept_index(content, rel_path)
                if concepts:
                    # Merge without overwriting existing entries
                    for concept, (loc, notes) in concepts.items():
                        if concept not in all_concepts:
                            all_concepts[concept] = (loc, notes)
                    logger.debug(f"  - Extracted {len(concepts)} concepts")

            except Exception as e:
                logger.warning(f"Error processing {rel_path}: {e}")
                continue

        # Generate the final content
        logger.info(
            f"Compilation complete: {len(all_concepts)} concepts, "
            f"{sum(len(f) for f in all_files.values())} files, "
            f"{len(all_how_tos)} how-tos, {len(all_gotchas)} gotchas"
        )

        return generate_oracle_content(
            concept_index=all_concepts,
            files_by_repo=all_files,
            how_tos=all_how_tos,
            gotchas=all_gotchas,
            cross_repo_impacts=self.CROSS_REPO_IMPACTS,
        )

    def _collect_sources(self) -> list[tuple[Path, str]]:
        """
        Collect all README and CLAUDE.md source files.

        Returns:
            List of (path, content) tuples for each source file
        """
        sources: list[tuple[Path, str]] = []

        # Collect root-level files
        for filename in self.ROOT_FILES:
            filepath = self.repo_root / filename
            content = self._read_file(filepath)
            if content is not None:
                sources.append((filepath, content))

        # Collect README files from source directories
        for dirname in self.SOURCE_DIRS:
            dirpath = self.repo_root / dirname
            if not dirpath.exists():
                logger.warning(f"Source directory not found: {dirpath}")
                continue

            # Find all README.md files recursively
            for readme in dirpath.rglob("README.md"):
                # Skip excluded paths
                if self._should_exclude(readme):
                    continue
                content = self._read_file(readme)
                if content is not None:
                    sources.append((readme, content))

        return sources

    def _should_exclude(self, filepath: Path) -> bool:
        """
        Check if a file path should be excluded from processing.

        Args:
            filepath: Path to check

        Returns:
            True if path should be excluded
        """
        path_str = str(filepath)
        for pattern in self.EXCLUDE_PATTERNS:
            if pattern in path_str:
                return True
        return False

    def _read_file(self, filepath: Path) -> Optional[str]:
        """
        Read file content with error handling.

        Args:
            filepath: Path to file to read

        Returns:
            File content as string, or None if read failed
        """
        if not filepath.exists():
            logger.debug(f"File not found: {filepath}")
            return None

        try:
            return filepath.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {filepath}: {e}")
            return None

    def _extract_repo_name(self, source_path: Path) -> str:
        """
        Extract repository/component name from source file path.

        Args:
            source_path: Absolute path to source file

        Returns:
            Repository or component name
        """
        try:
            rel_path = source_path.relative_to(self.repo_root)
            parts = rel_path.parts

            # Handle root files
            if len(parts) == 1:
                return "root"

            # First part is the category (forks, toolchain, etc.)
            # Second part is the repo/component name
            if len(parts) >= 2 and parts[0] in self.SOURCE_DIRS:
                return parts[1]

            return parts[0]
        except ValueError:
            return "unknown"

    def write_oracle(self, output_path: Optional[Path] = None) -> Path:
        """
        Compile and write Oracle to file.

        Args:
            output_path: Optional output path. Defaults to .claude/agents/sbs-oracle.md

        Returns:
            Path to written file
        """
        if output_path is None:
            output_path = self.repo_root / ".claude" / "agents" / "sbs-oracle.md"

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Compile and write
        content = self.compile()
        output_path.write_text(content, encoding="utf-8")

        logger.info(f"Oracle written to: {output_path}")
        return output_path
