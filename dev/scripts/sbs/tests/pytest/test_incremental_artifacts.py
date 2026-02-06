"""
Lake-Native Incremental Artifact Behavior Tests (#248)

Validates that Lake's incremental compilation correctly handles Dress
artifact generation. Dress hooks write artifacts as side effects during
elaboration for every @[blueprint] declaration. Lake's incremental
compilation skips unchanged modules, so their artifacts won't be
regenerated.

Artifacts live in `.lake/build/dressed/{Module}/{sanitized-label}/` with files:
  decl.json, decl.tex, decl.html, decl.hovers.json, manifest.entry

Note: Labels containing colons are sanitized (`:` -> `-`) in directory names.

Behavioral model:
  - When Lake re-elaborates a module, ALL @[blueprint] declarations in that
    module have their artifacts written (either fresh or restored from the
    content-addressed cache in `.decl_cache/`). This updates mtimes for all
    artifacts in the module.
  - When Lake skips a module (no source changes), its artifacts are untouched.
  - Cross-module isolation: changes to one module do not affect artifacts in
    other modules.

Note on BLUEPRINT_DRESS: Until SBS-Test's lake-manifest.json is updated to
reference a Dress version with always-active hooks (#247), BLUEPRINT_DRESS=1
must be set for artifact generation. This test sets it in the build environment.

Test tier: dev (involves full Lake builds, ~30-90s each)
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Generator

import pytest


# =============================================================================
# Constants
# =============================================================================

SBS_TEST_ROOT = Path("/Users/eric/GitHub/Side-By-Side-Blueprint/toolchain/SBS-Test")
DRESSED_DIR = SBS_TEST_ROOT / ".lake" / "build" / "dressed" / "SBSTest"

# Artifact files produced per @[blueprint] declaration
ARTIFACT_FILES = ["decl.json", "decl.tex", "decl.html", "decl.hovers.json", "manifest.entry"]

# Files we'll modify during tests -- always restore after
STATUS_DEMO_PATH = SBS_TEST_ROOT / "SBSTest" / "StatusDemo.lean"
BRACKET_DEMO_PATH = SBS_TEST_ROOT / "SBSTest" / "BracketDemo.lean"
BLUEPRINT_LEAN_PATH = SBS_TEST_ROOT / "SBSTest" / "Blueprint.lean"


# =============================================================================
# Helpers
# =============================================================================


def lake_build(cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    """Run `lake build` with BLUEPRINT_DRESS=1 in the given directory.

    Sets BLUEPRINT_DRESS=1 to enable artifact generation (required until
    SBS-Test's manifest references always-active Dress).

    Args:
        cwd: Working directory (should contain lakefile.toml)
        timeout: Max seconds to wait for build

    Returns:
        CompletedProcess with stdout/stderr

    Raises:
        subprocess.TimeoutExpired: If build exceeds timeout
    """
    env = os.environ.copy()
    env["BLUEPRINT_DRESS"] = "1"
    result = subprocess.run(
        ["lake", "build"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    return result


def collect_artifact_mtimes(dressed_dir: Path) -> dict[str, float]:
    """Collect modification times for all artifact files under dressed_dir.

    Scans the Module/label/ directory structure (not .decl_cache/).

    Returns:
        Dict mapping relative path (e.g. "StatusDemo/foundation/decl.json")
        to its mtime as a float.
    """
    mtimes: dict[str, float] = {}
    if not dressed_dir.exists():
        return mtimes
    for module_dir in sorted(dressed_dir.iterdir()):
        if not module_dir.is_dir():
            continue
        # Skip hidden directories like .decl_cache
        if module_dir.name.startswith("."):
            continue
        for label_dir in sorted(module_dir.iterdir()):
            if not label_dir.is_dir():
                continue
            for artifact in sorted(label_dir.iterdir()):
                if artifact.is_file():
                    rel = artifact.relative_to(dressed_dir)
                    mtimes[str(rel)] = artifact.stat().st_mtime
    return mtimes


def changed_artifacts(
    before: dict[str, float],
    after: dict[str, float],
) -> tuple[set[str], set[str], set[str]]:
    """Compare two mtime snapshots and return (modified, added, removed).

    Args:
        before: Mtime snapshot before operation
        after: Mtime snapshot after operation

    Returns:
        Tuple of (modified_paths, added_paths, removed_paths)
    """
    before_keys = set(before.keys())
    after_keys = set(after.keys())

    added = after_keys - before_keys
    removed = before_keys - after_keys
    common = before_keys & after_keys

    modified = {k for k in common if before[k] != after[k]}

    return modified, added, removed


def artifacts_for_module(mtimes: dict[str, float], module_name: str) -> dict[str, float]:
    """Filter mtime dict to only entries under a specific module directory.

    Args:
        mtimes: Full mtime dict
        module_name: Module subdirectory name (e.g. "StatusDemo")

    Returns:
        Filtered dict with only that module's artifacts
    """
    prefix = f"{module_name}/"
    return {k: v for k, v in mtimes.items() if k.startswith(prefix)}


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def baseline_build() -> None:
    """Ensure SBS-Test has a clean BLUEPRINT_DRESS=1 build before incremental tests.

    This runs once per test module (scope="module") and establishes
    the baseline state that all tests build upon. It must produce
    dressed artifacts so subsequent incremental tests have something
    to compare against.
    """
    result = lake_build(SBS_TEST_ROOT, timeout=600)
    assert result.returncode == 0, (
        f"Baseline lake build failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # Verify artifacts exist
    assert DRESSED_DIR.exists(), f"Dressed dir not found at {DRESSED_DIR}"
    assert (DRESSED_DIR / "StatusDemo" / "foundation").exists(), (
        "Expected StatusDemo/foundation artifacts from baseline build"
    )
    # Verify artifacts have expected files
    foundation_dir = DRESSED_DIR / "StatusDemo" / "foundation"
    for f in ARTIFACT_FILES:
        assert (foundation_dir / f).exists(), (
            f"Missing artifact {f} in StatusDemo/foundation/"
        )


@pytest.fixture
def restore_status_demo() -> Generator[None, None, None]:
    """Backup and restore StatusDemo.lean after test."""
    original = STATUS_DEMO_PATH.read_text()
    yield
    STATUS_DEMO_PATH.write_text(original)
    # Brief pause for filesystem to settle
    time.sleep(0.1)


@pytest.fixture
def restore_bracket_demo() -> Generator[None, None, None]:
    """Backup and restore BracketDemo.lean after test."""
    original = BRACKET_DEMO_PATH.read_text()
    yield
    BRACKET_DEMO_PATH.write_text(original)
    time.sleep(0.1)


@pytest.fixture
def restore_blueprint_lean() -> Generator[None, None, None]:
    """Backup and restore Blueprint.lean after test."""
    original = BLUEPRINT_LEAN_PATH.read_text()
    yield
    BLUEPRINT_LEAN_PATH.write_text(original)
    time.sleep(0.1)


# =============================================================================
# Test Suite
# =============================================================================


@pytest.mark.dev
class TestIncrementalArtifacts:
    """Validate Lake-native incremental artifact generation.

    These tests verify that Lake's incremental compilation correctly
    handles Dress artifact generation:
    - Unchanged modules produce no artifact changes
    - Changed modules regenerate only their artifacts
    - New declarations produce new artifacts without disturbing others
    """

    def test_noop_rebuild_no_artifact_changes(self, baseline_build: None) -> None:
        """Test 1: No-op rebuild produces no artifact changes.

        Run `lake build` twice with no source changes. The second build
        should NOT modify any artifact files (mtimes should be identical)
        because Lake skips modules whose source hasn't changed.
        """
        # Snapshot after baseline (which ran in the fixture)
        before = collect_artifact_mtimes(DRESSED_DIR)
        assert len(before) > 0, "No artifacts found after baseline build"

        # Sleep to ensure filesystem mtime granularity is respected
        time.sleep(1.5)

        # Second build with no changes
        result = lake_build(SBS_TEST_ROOT)
        assert result.returncode == 0, (
            f"No-op rebuild failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        after = collect_artifact_mtimes(DRESSED_DIR)

        modified, added, removed = changed_artifacts(before, after)

        assert len(modified) == 0, (
            f"No-op rebuild modified {len(modified)} artifacts "
            f"(expected 0):\n{sorted(modified)}"
        )
        assert len(added) == 0, (
            f"No-op rebuild added {len(added)} artifacts:\n{sorted(added)}"
        )
        assert len(removed) == 0, (
            f"No-op rebuild removed {len(removed)} artifacts:\n{sorted(removed)}"
        )

    def test_single_declaration_change(
        self,
        baseline_build: None,
        restore_status_demo: None,
    ) -> None:
        """Test 2: Changing one @[blueprint] declaration only affects its module's artifacts.

        Modify the proof body of the `foundation` theorem in StatusDemo.lean.
        After rebuild, Lake re-elaborates StatusDemo, so ALL StatusDemo
        artifacts get new mtimes (even unchanged declarations, because
        the cache restore still writes files). But artifacts in other modules
        (BracketDemo/, SecurityTest/, etc.) should be completely untouched.
        """
        before = collect_artifact_mtimes(DRESSED_DIR)
        assert len(before) > 0, "No artifacts found"

        # Modify foundation theorem's proof body
        content = STATUS_DEMO_PATH.read_text()
        modified_content = content.replace(
            "theorem foundation : True := by\n"
            "  -- Even though we have a proof, the manual notReady flag takes precedence\n"
            "  -- This tests that manual status flags override auto-detection\n"
            "  trivial  -- simple proof for testing purposes",
            "theorem foundation : True := by\n"
            "  -- Even though we have a proof, the manual notReady flag takes precedence\n"
            "  -- This tests that manual status flags override auto-detection\n"
            "  exact trivial  -- modified proof for incremental test",
        )
        assert content != modified_content, "Failed to apply modification to StatusDemo.lean"

        # Ensure filesystem mtime granularity
        time.sleep(1.5)
        STATUS_DEMO_PATH.write_text(modified_content)

        result = lake_build(SBS_TEST_ROOT)
        assert result.returncode == 0, (
            f"Rebuild after modification failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        after = collect_artifact_mtimes(DRESSED_DIR)
        modified_paths, added, removed = changed_artifacts(before, after)

        # StatusDemo artifacts SHOULD be regenerated (Lake re-elaborates the whole module)
        status_modified = {
            p for p in modified_paths if p.startswith("StatusDemo/")
        }
        assert len(status_modified) > 0, (
            f"Expected StatusDemo artifacts to be regenerated after proof change, "
            f"but no StatusDemo artifacts changed. All modified: {sorted(modified_paths)}"
        )

        # Other modules' artifacts should NOT change
        non_status_modified = {
            p for p in modified_paths if not p.startswith("StatusDemo/")
        }
        non_status_added = {
            p for p in added if not p.startswith("StatusDemo/")
        }

        assert len(non_status_modified) == 0, (
            f"Modification to StatusDemo.lean caused changes in other modules:\n"
            f"{sorted(non_status_modified)}"
        )
        assert len(non_status_added) == 0, (
            f"Modification to StatusDemo.lean added artifacts in other modules:\n"
            f"{sorted(non_status_added)}"
        )
        assert len(removed) == 0, (
            f"Modification removed artifacts:\n{sorted(removed)}"
        )

    def test_new_declaration_creates_artifacts(
        self,
        baseline_build: None,
        restore_status_demo: None,
    ) -> None:
        """Test 3: Adding a new @[blueprint] declaration creates new artifacts.

        Add a new theorem with @[blueprint] to StatusDemo.lean. After rebuild,
        new artifacts should appear for the new label. Artifacts in other
        modules should be untouched.
        """
        import shutil

        new_label_prefix = "StatusDemo/incremental_test_new/"
        new_artifact_dir = DRESSED_DIR / "StatusDemo" / "incremental_test_new"

        # Clean up any leftover artifacts from previous test runs.
        # Dress does not clean up artifacts for removed declarations,
        # so they can persist across runs.
        if new_artifact_dir.exists():
            shutil.rmtree(new_artifact_dir)

        # Settle build to resolve stale state from previous tests
        settle = lake_build(SBS_TEST_ROOT)
        assert settle.returncode == 0, (
            f"Settle build failed:\nstdout: {settle.stdout}\nstderr: {settle.stderr}"
        )

        before = collect_artifact_mtimes(DRESSED_DIR)
        assert len(before) > 0, "No artifacts found"

        # Verify the new label doesn't exist after cleanup
        assert not any(k.startswith(new_label_prefix) for k in before), (
            "Test artifact still exists after cleanup -- unexpected"
        )

        # Add a new @[blueprint] declaration before the `end` statement
        content = STATUS_DEMO_PATH.read_text()
        new_declaration = (
            '\n-- Temporary theorem added by incremental artifact test\n'
            '@[blueprint "incremental_test_new"\n'
            '  (title := "Incremental Test")\n'
            '  (statement := /-- Temporary theorem for testing incremental builds. -/)]\n'
            'theorem incremental_test_new : True := trivial\n\n'
        )
        modified_content = content.replace(
            "end SBSTest.StatusDemo",
            f"{new_declaration}end SBSTest.StatusDemo",
        )
        assert content != modified_content, "Failed to inject new declaration"

        time.sleep(1.5)
        STATUS_DEMO_PATH.write_text(modified_content)

        result = lake_build(SBS_TEST_ROOT)
        assert result.returncode == 0, (
            f"Rebuild after adding declaration failed:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        after = collect_artifact_mtimes(DRESSED_DIR)
        modified_paths, added, removed = changed_artifacts(before, after)

        # New artifacts should exist for the new label
        new_artifacts = {p for p in added if p.startswith(new_label_prefix)}
        assert len(new_artifacts) > 0, (
            f"Expected new artifacts under {new_label_prefix}, "
            f"but none were added. All added: {sorted(added)}"
        )

        # Verify the expected artifact files were created
        expected_files = {
            f"{new_label_prefix}{f}" for f in ARTIFACT_FILES
        }
        assert new_artifacts == expected_files, (
            f"Expected artifact files {sorted(expected_files)}, "
            f"got {sorted(new_artifacts)}"
        )

        # Artifacts in OTHER modules should be untouched
        non_status_changes = {
            p for p in (modified_paths | added)
            if not p.startswith("StatusDemo/")
        }
        assert len(non_status_changes) == 0, (
            f"Adding declaration to StatusDemo caused changes in other modules:\n"
            f"{sorted(non_status_changes)}"
        )

    def test_non_blueprint_file_change_no_artifact_changes(
        self,
        baseline_build: None,
        restore_blueprint_lean: None,
    ) -> None:
        """Test 4: Modifying a file with no @[blueprint] declarations causes zero artifact changes.

        Blueprint.lean is a Verso document file that imports blueprint modules
        but defines no @[blueprint] declarations itself. Modifying it should
        not trigger artifact regeneration for any module.

        Note: We run a "settle" build before taking the baseline snapshot to
        ensure any leftover state from previous tests (stale .oleans from
        restored source files) is resolved.
        """
        # Settle build: ensures that source files restored by earlier tests
        # (which may have newer mtimes than their .oleans) are re-elaborated,
        # giving us a clean baseline.
        settle = lake_build(SBS_TEST_ROOT)
        assert settle.returncode == 0, (
            f"Settle build failed:\nstdout: {settle.stdout}\nstderr: {settle.stderr}"
        )

        before = collect_artifact_mtimes(DRESSED_DIR)
        assert len(before) > 0, "No artifacts found"

        # Modify Blueprint.lean by adding a comment
        content = BLUEPRINT_LEAN_PATH.read_text()
        modified_content = content + "\n-- Incremental test: this comment should not cause artifact changes\n"
        assert content != modified_content, "Failed to modify Blueprint.lean"

        time.sleep(1.5)
        BLUEPRINT_LEAN_PATH.write_text(modified_content)

        result = lake_build(SBS_TEST_ROOT)
        assert result.returncode == 0, (
            f"Rebuild after Blueprint.lean change failed:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        after = collect_artifact_mtimes(DRESSED_DIR)
        modified_paths, added, removed = changed_artifacts(before, after)

        assert len(modified_paths) == 0, (
            f"Non-blueprint file change modified {len(modified_paths)} artifacts "
            f"(expected 0):\n{sorted(modified_paths)}"
        )
        assert len(added) == 0, (
            f"Non-blueprint file change added artifacts:\n{sorted(added)}"
        )
        assert len(removed) == 0, (
            f"Non-blueprint file change removed artifacts:\n{sorted(removed)}"
        )

    def test_statement_only_change_regenerates_declaration(
        self,
        baseline_build: None,
        restore_bracket_demo: None,
    ) -> None:
        """Test 5: Modifying only a `statement` field regenerates that module's artifacts.

        Change the statement text of the `bracket:nested` declaration in
        BracketDemo.lean. Since this is a source-level change to the module,
        Lake re-elaborates BracketDemo, causing all its artifacts to be
        re-written (with updated mtimes). Other modules should be untouched.
        """
        # Settle build to resolve any stale state from previous tests
        settle = lake_build(SBS_TEST_ROOT)
        assert settle.returncode == 0, (
            f"Settle build failed:\nstdout: {settle.stdout}\nstderr: {settle.stderr}"
        )

        before = collect_artifact_mtimes(DRESSED_DIR)
        assert len(before) > 0, "No artifacts found"

        # Verify BracketDemo artifacts exist in baseline
        bracket_arts = artifacts_for_module(before, "BracketDemo")
        assert len(bracket_arts) > 0, "No BracketDemo artifacts in baseline"

        # Modify the statement field of bracket:nested
        content = BRACKET_DEMO_PATH.read_text()
        modified_content = content.replace(
            '(statement := /-- Associativity of addition with nested parentheses.',
            '(statement := /-- MODIFIED: Associativity of addition with nested parentheses.',
        )
        assert content != modified_content, "Failed to modify statement in BracketDemo.lean"

        time.sleep(1.5)
        BRACKET_DEMO_PATH.write_text(modified_content)

        result = lake_build(SBS_TEST_ROOT)
        assert result.returncode == 0, (
            f"Rebuild after statement change failed:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        after = collect_artifact_mtimes(DRESSED_DIR)
        modified_paths, added, removed = changed_artifacts(before, after)

        # BracketDemo artifacts should be regenerated
        bracket_modified = {p for p in modified_paths if p.startswith("BracketDemo/")}
        # At minimum, the changed declaration's artifacts should differ
        # (Lake re-elaborates the whole module, so all BracketDemo artifacts change)
        assert len(bracket_modified) > 0, (
            f"Statement-only change did not regenerate any BracketDemo artifacts. "
            f"All modified: {sorted(modified_paths)}"
        )

        # Other modules' artifacts should be untouched
        non_bracket_modified = {
            p for p in modified_paths if not p.startswith("BracketDemo/")
        }
        assert len(non_bracket_modified) == 0, (
            f"Statement change in BracketDemo caused changes in other modules:\n"
            f"{sorted(non_bracket_modified)}"
        )

    # =========================================================================
    # TODO: Future tests (harder to test reliably with Lake's behavior)
    # =========================================================================

    # TODO Test 6: Deleted declaration
    # Removing a @[blueprint] declaration should cause its artifacts to
    # disappear after rebuild. However, Dress writes artifacts as side effects
    # during elaboration -- it does NOT clean up stale artifacts. This means
    # deleted declarations leave orphaned artifacts behind. A separate cleanup
    # mechanism would be needed to test this properly.
    #
    # def test_deleted_declaration_removes_artifacts(self, ...):
    #     """Test 6: Removing a @[blueprint] declaration removes its artifacts."""
    #     pass

    # TODO Test 7: Dependency chain invalidation
    # If module A imports module B, and we change B, does Lake re-elaborate A?
    # This depends on whether the change affects B's .olean output. In SBS-Test,
    # StatusDemo doesn't import BracketDemo, so cross-module invalidation is
    # hard to test without restructuring the test project. The modules are
    # relatively independent (connected only through the root SBSTest.lean).
    #
    # def test_dependency_chain_invalidation(self, ...):
    #     """Test 7: Changes to an imported module trigger downstream rebuilds."""
    #     pass
