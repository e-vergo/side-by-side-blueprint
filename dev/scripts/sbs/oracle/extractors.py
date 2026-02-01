"""Extraction functions for parsing knowledge from markdown sources."""
import re
from typing import Optional


def extract_file_tables(content: str, source_path: str) -> dict[str, str]:
    """
    Parse markdown tables with | File | Purpose | format.
    Returns dict mapping file paths to their purpose descriptions.

    Handles variations like:
    - | File | Purpose |
    - | File | Description |
    - | File | Lines | Purpose |
    """
    files: dict[str, str] = {}

    # Pattern to match markdown table rows
    # Looking for tables with File column and Purpose/Description column
    table_header_pattern = re.compile(
        r'^\|\s*(?:File|Location)\s*\|.*?(?:Purpose|Description|Scope)\s*\|',
        re.IGNORECASE | re.MULTILINE
    )

    # Find all potential table starts
    lines = content.split('\n')
    in_table = False
    file_col_idx: Optional[int] = None
    purpose_col_idx: Optional[int] = None

    for i, line in enumerate(lines):
        line = line.strip()

        # Check for table header
        if '|' in line and not in_table:
            cols = [c.strip().lower() for c in line.split('|')]

            # Find file and purpose columns
            for idx, col in enumerate(cols):
                if col in ('file', 'location', 'path'):
                    file_col_idx = idx
                elif col in ('purpose', 'description', 'scope', 'contents'):
                    purpose_col_idx = idx

            if file_col_idx is not None and purpose_col_idx is not None:
                in_table = True
                continue

        # Skip separator row
        if in_table and re.match(r'^\|[\s\-:|]+\|$', line):
            continue

        # Parse data row
        if in_table and '|' in line:
            cols = [c.strip() for c in line.split('|')]

            # Check if row is valid
            if len(cols) > max(file_col_idx or 0, purpose_col_idx or 0):
                file_val = cols[file_col_idx] if file_col_idx is not None else ''
                purpose_val = cols[purpose_col_idx] if purpose_col_idx is not None else ''

                # Skip empty or header-like rows
                if file_val and purpose_val and not file_val.lower() in ('file', 'location', 'path'):
                    # Clean up backticks and formatting
                    file_val = file_val.strip('`').strip()
                    # Skip if it looks like a separator
                    if not re.match(r'^[\-:]+$', file_val):
                        files[file_val] = purpose_val

        # End of table (empty line or non-table content)
        elif in_table and (not line or not line.startswith('|')):
            in_table = False
            file_col_idx = None
            purpose_col_idx = None

    return files


def extract_how_tos(content: str, source_path: str) -> list[tuple[str, str]]:
    """
    Find "How to X" or "### Add a Y" type sections.
    Returns list of (title, steps_content) tuples.

    Looks for patterns like:
    - ### How to ...
    - ### Adding a ...
    - ## Create a ...
    - Numbered step lists
    """
    how_tos: list[tuple[str, str]] = []

    # Patterns for how-to section headers
    how_to_patterns = [
        r'^#{2,4}\s+(How\s+to\s+.+?)$',
        r'^#{2,4}\s+(Add(?:ing)?\s+(?:a|an|the)\s+.+?)$',
        r'^#{2,4}\s+(Creat(?:e|ing)\s+(?:a|an|the)?\s*.+?)$',
        r'^#{2,4}\s+(Implement(?:ing)?\s+.+?)$',
        r'^#{2,4}\s+(Fix(?:ing)?\s+.+?)$',
        r'^#{2,4}\s+(Debug(?:ging)?\s+.+?)$',
        r'^#{2,4}\s+(Running\s+.+?)$',
        r'^#{2,4}\s+(Setting\s+up\s+.+?)$',
        r'^#{2,4}\s+(Configur(?:e|ing)\s+.+?)$',
    ]

    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check each how-to pattern
        for pattern in how_to_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                header_level = len(re.match(r'^(#+)', line).group(1))

                # Collect content until next header of same or higher level
                content_lines = []
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    # Check for next header
                    header_match = re.match(r'^(#+)\s+', next_line)
                    if header_match and len(header_match.group(1)) <= header_level:
                        break
                    content_lines.append(next_line)
                    i += 1

                steps_content = '\n'.join(content_lines).strip()
                if steps_content:
                    how_tos.append((title, steps_content))
                break
        else:
            i += 1

    return how_tos


def extract_gotchas(content: str, source_path: str) -> list[str]:
    """
    Find gotchas, limitations, known issues, caveats.
    Look for sections with these keywords or bullet lists with warning indicators.
    Returns list of gotcha strings.
    """
    gotchas: list[str] = []

    # Pattern for gotcha section headers (top-level)
    gotcha_section_patterns = [
        r'^#{2,3}\s+(?:Known\s+)?(?:Limitations?|Issues?|Gotchas?|Caveats?|Warnings?|Anti[- ]?Patterns?)',
        r'^#{2,3}\s+(?:What|Things)\s+(?:to\s+)?(?:Avoid|Watch\s+Out)',
        r'^#{2,3}\s+(?:Common\s+)?(?:Mistakes?|Pitfalls?|Problems?)',
    ]

    # Pattern for subsection headers within gotcha sections
    subsection_pattern = r'^#{3,4}\s+(.+)$'

    lines = content.split('\n')
    i = 0

    # First pass: find gotcha sections
    while i < len(lines):
        line = lines[i]

        for pattern in gotcha_section_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                header_level = len(re.match(r'^(#+)', line).group(1))
                i += 1

                # Collect content from this section
                current_subsection = None
                subsection_content = []

                while i < len(lines):
                    next_line = lines[i]

                    # Check for next header at same or higher level (end of section)
                    header_match = re.match(r'^(#+)\s+', next_line)
                    if header_match and len(header_match.group(1)) <= header_level:
                        break

                    # Check for subsection header
                    subsection_match = re.match(subsection_pattern, next_line)
                    if subsection_match:
                        # Save previous subsection if any
                        if current_subsection and subsection_content:
                            combined = f"{current_subsection}: {' '.join(subsection_content)}"
                            gotchas.append(combined)
                        current_subsection = subsection_match.group(1).strip()
                        subsection_content = []
                        i += 1
                        continue

                    # Extract bullet points
                    bullet_match = re.match(r'^\s*[-*]\s+(.+)$', next_line)
                    if bullet_match:
                        gotcha_text = bullet_match.group(1).strip()
                        if gotcha_text:
                            gotchas.append(gotcha_text)
                    # Extract paragraph content within subsections
                    elif current_subsection and next_line.strip() and not next_line.startswith('#'):
                        # Skip horizontal rules and empty lines
                        if not re.match(r'^[-=]+$', next_line.strip()):
                            subsection_content.append(next_line.strip())

                    i += 1

                # Save final subsection if any
                if current_subsection and subsection_content:
                    combined = f"{current_subsection}: {' '.join(subsection_content)}"
                    gotchas.append(combined)

                break
        else:
            i += 1

    # Second pass: find inline warnings/notes
    warning_patterns = [
        r'(?:^|\s)(?:WARNING|CAUTION|NOTE|IMPORTANT|CRITICAL):\s*(.+?)(?:\.|$)',
        r'\*\*(?:Warning|Caution|Note|Important)\*\*:?\s*(.+?)(?:\.|$)',
    ]

    for line in lines:
        for pattern in warning_patterns:
            matches = re.findall(pattern, line, re.IGNORECASE)
            for match in matches:
                if match.strip() and match.strip() not in gotchas:
                    gotchas.append(match.strip())

    # Third pass: find "Don't" or "Never" statements in bullet lists
    dont_patterns = [
        r'^\s*[-*]\s+(?:Don\'?t|Never|Avoid|Do\s+NOT)\s+(.+?)$',
    ]

    for line in lines:
        for pattern in dont_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                gotcha_text = f"Don't {match.group(1).strip()}"
                if gotcha_text not in gotchas:
                    gotchas.append(gotcha_text)

    return gotchas


def build_concept_index(content: str, source_path: str) -> dict[str, tuple[str, str]]:
    """
    Build concept -> (primary_file, notes) mapping.
    Extract from headers, key terms in bold, and file references.

    Returns dict where:
    - key: concept name (e.g., "rainbow brackets", "status colors")
    - value: (primary_file_path, brief_notes)
    """
    concepts: dict[str, tuple[str, str]] = {}

    # Extract repo/component name from source path
    source_component = _extract_component_from_path(source_path)

    lines = content.split('\n')
    current_header = ""

    for i, line in enumerate(lines):
        # Track current section header
        header_match = re.match(r'^#{1,4}\s+(.+)$', line)
        if header_match:
            current_header = header_match.group(1).strip()

        # Find bold terms that look like concepts
        bold_matches = re.findall(r'\*\*([^*]+)\*\*', line)
        for term in bold_matches:
            term_lower = term.lower().strip()
            # Skip generic terms and short ones
            if len(term_lower) > 3 and not _is_generic_term(term_lower):
                if term_lower not in concepts:
                    concepts[term_lower] = (source_path, current_header)

        # Find file references with descriptions
        # Pattern: `file.lean` - description or `file.lean`: description
        file_ref_match = re.match(r'.*`([^`]+\.\w+)`\s*[-:]\s*(.+)$', line)
        if file_ref_match:
            filename = file_ref_match.group(1)
            description = file_ref_match.group(2).strip()
            # Create concept from filename
            concept_name = _filename_to_concept(filename)
            if concept_name and concept_name not in concepts:
                concepts[concept_name] = (f"{source_component}/{filename}", description[:100])

        # Find inline code references that might be concepts
        code_refs = re.findall(r'`([A-Z][a-zA-Z]+(?:\.[A-Z][a-zA-Z]+)*)`', line)
        for ref in code_refs:
            ref_lower = ref.lower()
            if ref_lower not in concepts and len(ref_lower) > 4:
                concepts[ref_lower] = (source_path, current_header)

    return concepts


def _extract_component_from_path(path: str) -> str:
    """Extract component/repo name from file path."""
    parts = path.replace('\\', '/').split('/')

    # Look for known directories
    for keyword in ['forks', 'toolchain', 'showcase', 'dev']:
        if keyword in parts:
            idx = parts.index(keyword)
            if idx + 1 < len(parts):
                return parts[idx + 1]

    # Fallback to parent directory
    if len(parts) >= 2:
        return parts[-2]
    return parts[-1] if parts else "unknown"


def _is_generic_term(term: str) -> bool:
    """Check if term is too generic to be a useful concept."""
    generic_terms = {
        'the', 'this', 'that', 'file', 'files', 'code', 'note', 'notes',
        'example', 'examples', 'section', 'see', 'also', 'more', 'info',
        'true', 'false', 'none', 'null', 'data', 'value', 'values',
        'name', 'names', 'type', 'types', 'path', 'paths', 'line', 'lines',
        'important', 'warning', 'caution', 'todo', 'fixme', 'hack',
    }
    return term in generic_terms


def _filename_to_concept(filename: str) -> str:
    """Convert filename to concept name."""
    # Remove extension
    name = re.sub(r'\.\w+$', '', filename)
    # Convert CamelCase to spaces
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    # Convert underscores/hyphens to spaces
    name = name.replace('_', ' ').replace('-', ' ')
    return name.lower().strip()
