"""Templates for generating the Oracle markdown output."""


ORACLE_TEMPLATE = '''---
name: sbs-oracle
description: Zero-shot question answering agent for SBS codebase
model: opus
color: blue
---

# SBS Oracle

Answer codebase questions without file reads. Flag uncertainty explicitly.

**Priority order:**
1. Factual correctness (accuracy/precision of answer)
2. Response formatting (efficient tokens, full clarity)
3. Speed

---

## Concept Index

{concept_index}

---

## File Purpose Map

{file_purpose_map}

---

## How-To Patterns

{how_to_patterns}

---

## Gotchas & Anti-Patterns

{gotchas}

---

## Cross-Repo Impact Map

{cross_repo_impact}
'''


def format_concept_index(concepts: dict[str, tuple[str, str]]) -> str:
    """
    Format concept index as markdown table.

    Args:
        concepts: Dict mapping concept name to (primary_file, notes)

    Returns:
        Formatted markdown table string
    """
    if not concepts:
        return "_No concepts extracted._"

    lines = [
        "| Concept | Primary Location | Notes |",
        "|---------|-----------------|-------|",
    ]

    # Sort concepts alphabetically
    for concept in sorted(concepts.keys()):
        location, notes = concepts[concept]
        # Truncate long notes
        notes_display = notes[:80] + "..." if len(notes) > 80 else notes
        # Escape pipe characters
        notes_display = notes_display.replace("|", "\\|")
        lines.append(f"| {concept} | `{location}` | {notes_display} |")

    return "\n".join(lines)


def format_file_map(files_by_repo: dict[str, dict[str, str]]) -> str:
    """
    Format file purpose map grouped by repo.

    Args:
        files_by_repo: Dict mapping repo name to {file_path: purpose}

    Returns:
        Formatted markdown sections string
    """
    if not files_by_repo:
        return "_No file mappings extracted._"

    sections = []

    for repo in sorted(files_by_repo.keys()):
        files = files_by_repo[repo]
        if not files:
            continue

        lines = [
            f"### {repo}",
            "",
            "| File | Purpose |",
            "|------|---------|",
        ]

        for filepath in sorted(files.keys()):
            purpose = files[filepath]
            # Truncate long purposes
            purpose_display = purpose[:100] + "..." if len(purpose) > 100 else purpose
            # Escape pipe characters
            purpose_display = purpose_display.replace("|", "\\|")
            lines.append(f"| `{filepath}` | {purpose_display} |")

        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def format_how_tos(how_tos: list[tuple[str, str]]) -> str:
    """
    Format how-to patterns section.

    Args:
        how_tos: List of (title, steps_content) tuples

    Returns:
        Formatted markdown string with collapsible sections
    """
    if not how_tos:
        return "_No how-to patterns extracted._"

    sections = []

    for title, content in how_tos:
        # Use details/summary for collapsibility
        section = f"""<details>
<summary><strong>{title}</strong></summary>

{content}

</details>"""
        sections.append(section)

    return "\n\n".join(sections)


def format_gotchas(gotchas: list[str]) -> str:
    """
    Format gotchas as bullet list.

    Args:
        gotchas: List of gotcha strings

    Returns:
        Formatted markdown bullet list
    """
    if not gotchas:
        return "_No gotchas extracted._"

    # Deduplicate while preserving order
    seen = set()
    unique_gotchas = []
    for g in gotchas:
        g_normalized = g.lower().strip()
        if g_normalized not in seen:
            seen.add(g_normalized)
            unique_gotchas.append(g)

    lines = []
    for gotcha in unique_gotchas:
        # Ensure proper sentence ending
        if not gotcha.endswith(('.', '!', '?')):
            gotcha = gotcha + "."
        lines.append(f"- {gotcha}")

    return "\n".join(lines)


def format_cross_repo_impact(impacts: list[tuple[str, str, str]]) -> str:
    """
    Format cross-repo impact map as table.

    Args:
        impacts: List of (source_repo, target_repo, impact_description) tuples

    Returns:
        Formatted markdown table string
    """
    if not impacts:
        return "_No cross-repo impacts documented._"

    lines = [
        "| Change In | Affects | Impact |",
        "|-----------|---------|--------|",
    ]

    for source, target, impact in impacts:
        # Escape pipe characters
        impact_display = impact.replace("|", "\\|")
        lines.append(f"| {source} | {target} | {impact_display} |")

    return "\n".join(lines)


def generate_oracle_content(
    concept_index: dict[str, tuple[str, str]],
    files_by_repo: dict[str, dict[str, str]],
    how_tos: list[tuple[str, str]],
    gotchas: list[str],
    cross_repo_impacts: list[tuple[str, str, str]],
) -> str:
    """
    Generate complete Oracle markdown content.

    Args:
        concept_index: Concept -> (location, notes) mapping
        files_by_repo: Repo -> {file: purpose} mapping
        how_tos: List of (title, content) tuples
        gotchas: List of gotcha strings
        cross_repo_impacts: List of (source, target, impact) tuples

    Returns:
        Complete formatted Oracle markdown
    """
    return ORACLE_TEMPLATE.format(
        concept_index=format_concept_index(concept_index),
        file_purpose_map=format_file_map(files_by_repo),
        how_to_patterns=format_how_tos(how_tos),
        gotchas=format_gotchas(gotchas),
        cross_repo_impact=format_cross_repo_impact(cross_repo_impacts),
    )
