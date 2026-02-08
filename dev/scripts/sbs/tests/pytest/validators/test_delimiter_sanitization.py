"""
Tests for delimiter sanitization in Dress artifact output paths.

Verifies that raw /-%%...%%-/ delimiter markers do not leak into built
artifacts (HTML, hover JSON, TeX base64 content). See #273 for background.

These tests run against actual SBS-Test build artifacts in
.lake/build/dressed/. If artifacts are not present (no recent build),
tests are skipped.
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

import pytest


# =============================================================================
# Constants
# =============================================================================

# Monorepo root, derived from this file's location:
# dev/scripts/sbs/tests/pytest/validators/test_delimiter_sanitization.py
_THIS_FILE = Path(__file__).resolve()
_MONOREPO_ROOT = _THIS_FILE.parent.parent.parent.parent.parent.parent.parent

# SBS-Test dressed artifacts directory
_DRESSED_DIR = _MONOREPO_ROOT / "toolchain" / "SBS-Test" / ".lake" / "build" / "dressed"

# Raw delimiter markers that should NOT appear in output
BLOCK_OPEN = "/-%%"
BLOCK_CLOSE = "%%-/"


def _has_artifacts() -> bool:
    """Check if SBS-Test build artifacts exist."""
    return _DRESSED_DIR.exists() and any(_DRESSED_DIR.rglob("decl.html"))


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def dressed_dir() -> Path:
    """Return the dressed artifacts directory, skipping if not built."""
    if not _has_artifacts():
        pytest.skip("SBS-Test artifacts not built; run build.py first")
    return _DRESSED_DIR


@pytest.fixture
def html_artifacts(dressed_dir: Path) -> list[Path]:
    """Collect all decl.html artifact files."""
    files = sorted(dressed_dir.rglob("decl.html"))
    assert len(files) > 0, "No decl.html files found in dressed directory"
    return files


@pytest.fixture
def hover_artifacts(dressed_dir: Path) -> list[Path]:
    """Collect all decl.hovers.json artifact files."""
    files = sorted(dressed_dir.rglob("decl.hovers.json"))
    assert len(files) > 0, "No decl.hovers.json files found in dressed directory"
    return files


@pytest.fixture
def tex_artifacts(dressed_dir: Path) -> list[Path]:
    """Collect all decl.tex artifact files."""
    files = sorted(dressed_dir.rglob("decl.tex"))
    assert len(files) > 0, "No decl.tex files found in dressed directory"
    return files


# =============================================================================
# HTML Artifact Tests
# =============================================================================


@pytest.mark.evergreen
class TestHtmlDelimiterSanitization:
    """Verify decl.html files do not contain raw delimiter markers."""

    def test_no_block_open_in_html(self, html_artifacts: list[Path]) -> None:
        """No decl.html file should contain the /-%% block open marker."""
        violations = []
        for path in html_artifacts:
            content = path.read_text(encoding="utf-8", errors="replace")
            if BLOCK_OPEN in content:
                rel = path.relative_to(_DRESSED_DIR)
                violations.append(str(rel))
        assert not violations, (
            f"Raw /-%% delimiter found in {len(violations)} HTML artifact(s): "
            + ", ".join(violations[:5])
        )

    def test_no_block_close_in_html(self, html_artifacts: list[Path]) -> None:
        """No decl.html file should contain the %%-/ block close marker."""
        violations = []
        for path in html_artifacts:
            content = path.read_text(encoding="utf-8", errors="replace")
            if BLOCK_CLOSE in content:
                rel = path.relative_to(_DRESSED_DIR)
                violations.append(str(rel))
        assert not violations, (
            f"Raw %%-/ delimiter found in {len(violations)} HTML artifact(s): "
            + ", ".join(violations[:5])
        )


# =============================================================================
# Hover JSON Artifact Tests
# =============================================================================


@pytest.mark.evergreen
class TestHoverJsonDelimiterSanitization:
    """Verify decl.hovers.json files do not contain raw delimiter markers."""

    def test_no_block_open_in_hovers(self, hover_artifacts: list[Path]) -> None:
        """No decl.hovers.json file should contain the /-%% block open marker."""
        violations = []
        for path in hover_artifacts:
            content = path.read_text(encoding="utf-8", errors="replace")
            if BLOCK_OPEN in content:
                rel = path.relative_to(_DRESSED_DIR)
                violations.append(str(rel))
        assert not violations, (
            f"Raw /-%% delimiter found in {len(violations)} hover JSON artifact(s): "
            + ", ".join(violations[:5])
        )

    def test_no_block_close_in_hovers(self, hover_artifacts: list[Path]) -> None:
        """No decl.hovers.json file should contain the %%-/ block close marker."""
        violations = []
        for path in hover_artifacts:
            content = path.read_text(encoding="utf-8", errors="replace")
            if BLOCK_CLOSE in content:
                rel = path.relative_to(_DRESSED_DIR)
                violations.append(str(rel))
        assert not violations, (
            f"Raw %%-/ delimiter found in {len(violations)} hover JSON artifact(s): "
            + ", ".join(violations[:5])
        )


# =============================================================================
# TeX Artifact Tests (base64-encoded content)
# =============================================================================

# Regex to extract base64 content from TeX macros
_BASE64_MACRO_RE = re.compile(
    r"\\(?:leansignaturesourcehtml|leanproofsourcehtml|leanhoverdata)"
    r"\{([A-Za-z0-9+/=]+)\}"
)


@pytest.mark.evergreen
class TestTexBase64DelimiterSanitization:
    """Verify base64-encoded content in decl.tex does not contain raw delimiters."""

    def test_no_delimiters_in_tex_base64(self, tex_artifacts: list[Path]) -> None:
        """Decode base64 content from TeX macros and check for delimiter markers.

        Checks \\leansignaturesourcehtml, \\leanproofsourcehtml, and
        \\leanhoverdata macros.
        """
        violations = []
        for path in tex_artifacts:
            content = path.read_text(encoding="utf-8", errors="replace")
            for match in _BASE64_MACRO_RE.finditer(content):
                b64_str = match.group(1)
                try:
                    decoded = base64.b64decode(b64_str).decode("utf-8", errors="replace")
                except Exception:
                    continue  # Skip malformed base64
                if BLOCK_OPEN in decoded or BLOCK_CLOSE in decoded:
                    rel = path.relative_to(_DRESSED_DIR)
                    macro_name = match.group(0)[:40] + "..."
                    violations.append(f"{rel} ({macro_name})")

        assert not violations, (
            f"Raw delimiter markers found in base64-decoded TeX content in "
            f"{len(violations)} location(s): " + ", ".join(violations[:5])
        )

    def test_artifacts_have_expected_macros(self, tex_artifacts: list[Path]) -> None:
        """At least some TeX artifacts should contain base64 macros.

        This guards against the regex pattern becoming stale and silently
        matching nothing.
        """
        total_macros = 0
        for path in tex_artifacts:
            content = path.read_text(encoding="utf-8", errors="replace")
            total_macros += len(_BASE64_MACRO_RE.findall(content))

        assert total_macros > 0, (
            "No base64 macros (leansignaturesourcehtml, leanproofsourcehtml, "
            "leanhoverdata) found in any decl.tex file. Pattern may be stale."
        )
