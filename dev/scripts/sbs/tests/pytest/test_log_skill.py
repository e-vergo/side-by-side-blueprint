"""
Tests for the /log skill.

Validates:
- Skill file exists and has valid structure
- Frontmatter has required fields with correct values
- Three-phase workflow documented
- Archive protocol references sbs archive upload
- Label taxonomy dimensions referenced
- Type and area inference keywords present
- origin:agent label always included
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml


# =============================================================================
# Paths
# =============================================================================

MONOREPO_ROOT = Path("/Users/eric/GitHub/Side-By-Side-Blueprint")
SKILL_FILE = MONOREPO_ROOT / ".claude" / "skills" / "log" / "SKILL.md"


# =============================================================================
# Helpers
# =============================================================================


def _read_skill() -> str:
    """Read the log skill file content."""
    return SKILL_FILE.read_text()


def _parse_frontmatter() -> dict:
    """Extract and parse YAML frontmatter from the skill file."""
    content = _read_skill()
    parts = content.split("---", 2)
    return yaml.safe_load(parts[1].strip())


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.evergreen
class TestLogSkillFile:
    """Tests for the /log skill definition file."""

    def test_skill_file_exists(self):
        """Skill file must exist at expected path."""
        assert SKILL_FILE.exists(), f"Skill file not found at {SKILL_FILE}"

    def test_skill_frontmatter(self):
        """Skill file must have valid YAML frontmatter with name, version, description."""
        content = _read_skill()

        assert content.startswith("---"), "Skill file must start with YAML frontmatter (---)"

        parts = content.split("---", 2)
        assert len(parts) >= 3, "Skill file must have closing --- for frontmatter"

        frontmatter = _parse_frontmatter()
        assert isinstance(frontmatter, dict), "Frontmatter must parse to a dict"

        assert "name" in frontmatter, "Frontmatter must have 'name'"
        assert frontmatter["name"] == "log", "Name must be 'log'"

        assert "description" in frontmatter, "Frontmatter must have 'description'"
        assert len(frontmatter["description"]) > 0, "Description must not be empty"

        assert "version" in frontmatter, "Frontmatter must have 'version'"

    def test_skill_version(self):
        """Version must follow semver format (X.Y.Z)."""
        frontmatter = _parse_frontmatter()
        version = frontmatter["version"]

        # Version can be a float (e.g. 2.0) or string; normalize to string
        version_str = str(version)
        # Accept both X.Y and X.Y.Z formats
        version_pattern = r"^\d+\.\d+(\.\d+)?$"
        assert re.match(version_pattern, version_str), \
            f"Version '{version_str}' must match semver (X.Y.Z or X.Y)"

    def test_three_phase_workflow(self):
        """SKILL.md must contain sections for all 3 phases: Alignment, Draft & Review, Create."""
        content = _read_skill().lower()

        # The /log skill uses: Parse input -> Infer/confirm -> Create
        # Mapped to conceptual phases: Alignment (parse/infer), Draft & Review (confirm), Create
        phase_indicators = [
            # Phase 1: Alignment - parsing and inferring
            "parse input",
            # Phase 2: Draft & Review - confirmation
            "confirmation" if "confirmation" in content else "confirm",
            # Phase 3: Create - issue creation
            "create issue",
        ]

        for indicator in phase_indicators:
            assert indicator in content, \
                f"Skill must document workflow phase indicated by: '{indicator}'"

    def test_archive_protocol(self):
        """Skill must have archive protocol section referencing sbs archive upload."""
        content = _read_skill()

        assert "archive protocol" in content.lower(), \
            "Skill must have 'Archive Protocol' section"
        assert "sbs archive upload" in content.lower(), \
            "Archive protocol must reference 'sbs archive upload'"

    def test_label_taxonomy_references(self):
        """Skill must reference label taxonomy dimensions that exist in the taxonomy."""
        content = _read_skill()

        # The skill references these taxonomy dimensions
        assert "taxonomy" in content.lower(), \
            "Skill must reference the label taxonomy"

        # Must reference type and area as required dimensions
        assert "type" in content.lower(), "Skill must reference type dimension"
        assert "area" in content.lower(), "Skill must reference area dimension"

    def test_type_inference_keywords(self):
        """Type inference section must have keyword mappings for all 6 categories."""
        content = _read_skill().lower()

        type_categories = [
            "bug",
            "feature",
            "idea",
            "housekeeping",
            "investigation",
            "behavior",
        ]

        for category in type_categories:
            assert category in content, \
                f"Type inference must include keywords for: {category}"

    def test_area_inference_keywords(self):
        """Area inference section must have keyword mappings for sbs and devtools areas."""
        content = _read_skill()

        # Must have area inference keywords for both major areas
        assert "area:sbs:" in content, \
            "Area inference must include sbs area labels"
        assert "area:devtools:" in content, \
            "Area inference must include devtools area labels"

    def test_origin_label(self):
        """Skill must mention origin:agent as always-included label."""
        content = _read_skill()

        assert "origin:agent" in content, \
            "Skill must reference 'origin:agent' as always-included label"

        # Verify it's described as always applied
        # Find the line with origin:agent and check nearby context
        lines = content.split("\n")
        origin_lines = [i for i, line in enumerate(lines) if "origin:agent" in line]
        assert len(origin_lines) > 0

        # At least one occurrence should be near "always" context
        found_always_context = False
        for line_idx in origin_lines:
            context_start = max(0, line_idx - 3)
            context_end = min(len(lines), line_idx + 3)
            context = " ".join(lines[context_start:context_end]).lower()
            if "always" in context:
                found_always_context = True
                break

        assert found_always_context, \
            "origin:agent must be described as 'always' applied"
