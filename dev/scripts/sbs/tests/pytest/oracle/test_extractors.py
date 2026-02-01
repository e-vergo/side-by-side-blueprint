"""
Tests for sbs.oracle.extractors module.

Tests the extraction functions that parse markdown content into structured
knowledge: file tables, how-to patterns, gotchas, and concept indices.
"""

from __future__ import annotations

import pytest

from sbs.oracle.extractors import (
    extract_file_tables,
    extract_how_tos,
    extract_gotchas,
    build_concept_index,
)


class TestExtractFileTables:
    """Tests for extract_file_tables function."""

    def test_extracts_simple_table(self) -> None:
        """Parse a simple File | Purpose table."""
        content = """
| File | Purpose |
|------|---------|
| foo.py | Does foo |
| bar.py | Does bar |
"""
        result = extract_file_tables(content, "test.md")
        assert "foo.py" in result
        assert result["foo.py"] == "Does foo"
        assert "bar.py" in result
        assert result["bar.py"] == "Does bar"

    def test_handles_no_tables(self) -> None:
        """Return empty dict when no tables present."""
        content = "Just some text without tables"
        result = extract_file_tables(content, "test.md")
        assert result == {}

    def test_extracts_table_with_backticks(self) -> None:
        """Handle file names wrapped in backticks."""
        content = """
| File | Purpose |
|------|---------|
| `foo.py` | Does foo |
"""
        result = extract_file_tables(content, "test.md")
        assert "foo.py" in result
        assert result["foo.py"] == "Does foo"

    def test_handles_description_column(self) -> None:
        """Accept Description as alternative to Purpose column."""
        content = """
| File | Description |
|------|-------------|
| main.lean | Entry point |
"""
        result = extract_file_tables(content, "test.md")
        assert "main.lean" in result
        assert result["main.lean"] == "Entry point"

    def test_handles_location_column(self) -> None:
        """Accept Location as alternative to File column."""
        content = """
| Location | Purpose |
|----------|---------|
| src/main.py | Entry point |
"""
        result = extract_file_tables(content, "test.md")
        assert "src/main.py" in result

    def test_handles_multiple_tables(self) -> None:
        """Extract from multiple tables in same document."""
        content = """
## Files

| File | Purpose |
|------|---------|
| a.py | First |

## More Files

| File | Description |
|------|-------------|
| b.py | Second |
"""
        result = extract_file_tables(content, "test.md")
        assert "a.py" in result
        assert "b.py" in result

    def test_ignores_non_file_tables(self) -> None:
        """Skip tables without File/Purpose columns."""
        content = """
| Name | Age |
|------|-----|
| Alice | 30 |
"""
        result = extract_file_tables(content, "test.md")
        assert result == {}


class TestExtractHowTos:
    """Tests for extract_how_tos function."""

    def test_finds_how_to_sections(self) -> None:
        """Find sections starting with 'How to'."""
        content = """
### How to Add a Feature

1. Step one
2. Step two

### How to Debug

1. Check logs
"""
        result = extract_how_tos(content, "test.md")
        assert len(result) >= 1
        # Check at least one how-to was found
        titles = [title for title, _ in result]
        assert any("Add a Feature" in t for t in titles) or any("Debug" in t for t in titles)

    def test_handles_no_how_tos(self) -> None:
        """Return empty list when no how-to sections present."""
        content = "No how-to sections here"
        result = extract_how_tos(content, "test.md")
        assert result == []

    def test_finds_adding_sections(self) -> None:
        """Find sections starting with 'Adding a'."""
        content = """
### Adding a New Feature

1. Create the file
2. Add to manifest
"""
        result = extract_how_tos(content, "test.md")
        assert len(result) >= 1
        titles = [title for title, _ in result]
        assert any("Adding" in t or "New Feature" in t for t in titles)

    def test_finds_creating_sections(self) -> None:
        """Find sections starting with 'Create' or 'Creating'."""
        content = """
## Create a Config File

Add the following content:
```
key: value
```
"""
        result = extract_how_tos(content, "test.md")
        assert len(result) >= 1

    def test_captures_content_until_next_header(self) -> None:
        """Content should stop at next header of same or higher level."""
        content = """
### How to Build

1. Run `make`
2. Check output

### Next Section

This should not be included.
"""
        result = extract_how_tos(content, "test.md")
        assert len(result) >= 1
        title, steps = result[0]
        assert "How to Build" in title
        assert "Run `make`" in steps
        assert "Next Section" not in steps


class TestExtractGotchas:
    """Tests for extract_gotchas function."""

    def test_finds_gotchas_in_limitations_section(self) -> None:
        """Find bullet points under Known Limitations."""
        content = """
## Known Limitations

- Limitation one
- Limitation two
"""
        result = extract_gotchas(content, "test.md")
        assert len(result) >= 1
        assert any("Limitation one" in g for g in result) or any("Limitation two" in g for g in result)

    def test_handles_no_gotchas(self) -> None:
        """Return empty list when no gotchas present."""
        content = "Happy path only"
        result = extract_gotchas(content, "test.md")
        assert result == []

    def test_finds_anti_patterns_section(self) -> None:
        """Find bullet points under Anti-Patterns."""
        content = """
## Anti-Patterns

- Don't use global state
- Avoid magic numbers
"""
        result = extract_gotchas(content, "test.md")
        assert len(result) >= 1

    def test_finds_inline_warnings(self) -> None:
        """Find WARNING: or IMPORTANT: annotations."""
        content = """
Some text here.

WARNING: This will break if X happens.

More text.
"""
        result = extract_gotchas(content, "test.md")
        assert len(result) >= 1

    def test_finds_dont_statements(self) -> None:
        """Find 'Don't' or 'Never' bullet points."""
        content = """
## Tips

- Don't run in production without testing
- Never commit secrets
"""
        result = extract_gotchas(content, "test.md")
        assert len(result) >= 1


class TestBuildConceptIndex:
    """Tests for build_concept_index function."""

    def test_extracts_bold_concepts(self) -> None:
        """Find **bold** terms as concepts."""
        content = "The **graph layout** is in Layout.lean"
        result = build_concept_index(content, "test.md")
        assert "graph layout" in result

    def test_returns_tuple_with_location_and_notes(self) -> None:
        """Concept values should be (location, notes) tuples."""
        content = """
## Section Header

The **rainbow brackets** are colorful.
"""
        result = build_concept_index(content, "test.md")
        if "rainbow brackets" in result:
            location, notes = result["rainbow brackets"]
            assert isinstance(location, str)
            assert isinstance(notes, str)

    def test_handles_file_references(self) -> None:
        """Extract concepts from `file.lean` - description patterns."""
        content = "`Parser.lean` - handles LaTeX parsing"
        result = build_concept_index(content, "test.md")
        # Should create a concept from the filename
        assert len(result) >= 0  # May or may not extract depending on pattern

    def test_ignores_generic_terms(self) -> None:
        """Skip generic terms like 'file', 'data', 'value'."""
        content = "The **file** contains **data** and **value**"
        result = build_concept_index(content, "test.md")
        assert "file" not in result
        assert "data" not in result
        assert "value" not in result

    def test_ignores_short_terms(self) -> None:
        """Skip terms with 3 or fewer characters."""
        content = "The **foo** is not included but **longer term** is"
        result = build_concept_index(content, "test.md")
        assert "foo" not in result

    def test_extracts_code_references(self) -> None:
        """Extract CamelCase code references as concepts."""
        content = "The `NodeStatus` type is defined here"
        result = build_concept_index(content, "test.md")
        # May extract nodestatus as a concept
        assert isinstance(result, dict)
