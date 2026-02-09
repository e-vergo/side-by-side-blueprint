# SBS-Oracle & README Tooling Plan

## Summary

Build tooling for Claude agents to answer codebase questions instantly:
1. **SBS-Oracle agent** - Auto-populated markdown with developer-focused codebase knowledge
2. **Oracle compiler** - Extracts content from READMEs + CLAUDE.md into lookup-optimized format
3. **README staleness detector** - Reports what READMEs need updating (side quest)
4. **Hook architecture extension** - Support markdown generation in addition to tags

---

## Design Principles

- **Developer-focused**: How to modify code, not how to use the tool
- **Lookup-optimized**: Index for rapid queries, not sequential reading
- **Agent-written for agents**: Leverage existing README work
- **Auto-populated**: No manual maintenance of Oracle content

---

## Wave 1: Oracle Module Foundation

### Files to Create

```
dev/scripts/sbs/oracle/
├── __init__.py
├── compiler.py       # Main compilation logic
├── extractors.py     # Content extraction from READMEs/CLAUDE.md
└── templates.py      # Oracle markdown templates
```

### Implementation

**`sbs/oracle/compiler.py`**:
- `OracleCompiler` class
- `compile() -> str` - Returns full Oracle markdown
- Sources: All READMEs + CLAUDE.md
- Extracts: file tables, how-tos, gotchas, cross-repo impacts

**`sbs/oracle/extractors.py`**:
- `extract_file_tables(content) -> dict[str, str]` - Parse `| File | Purpose |` tables
- `extract_how_tos(content) -> list[tuple[str, str]]` - Find "How to X" sections
- `extract_gotchas(content) -> list[str]` - Find gotchas/limitations
- `build_concept_index(content, source) -> dict[str, tuple[str, str]]` - Concept → file mapping

**`sbs/oracle/templates.py`**:
- Oracle frontmatter template
- Section templates (Concept Index, File Map, How-Tos, etc.)

---

## Wave 2: Oracle CLI Command

### Files to Modify

- `dev/scripts/sbs/cli.py` - Add `sbs oracle compile` command

### Implementation

```python
# CLI additions
oracle_parser = subparsers.add_parser("oracle", help="Oracle management")
oracle_subparsers = oracle_parser.add_subparsers(dest="oracle_command")

oracle_compile = oracle_subparsers.add_parser("compile", help="Compile Oracle from sources")
oracle_compile.add_argument("--dry-run", action="store_true")
oracle_compile.add_argument("--output", help="Output path (default: .claude/agents/sbs-oracle.md)")
```

### Output

Running `sbs oracle compile`:
1. Scans all READMEs + CLAUDE.md
2. Extracts structured content
3. Generates Oracle markdown
4. Writes to `.claude/agents/sbs-oracle.md`

---

## Wave 3: Oracle Content Structure

### Target: `.claude/agents/sbs-oracle.md`

```markdown
---
name: sbs-oracle
description: Zero-shot question answering agent for SBS codebase
model: opus
color: blue
---

# SBS Oracle

Answer codebase questions without file reads. Flag uncertainty explicitly.

## Concept Index
| Concept | Primary File | Notes |
|---------|--------------|-------|
| dependency graph layout | Dress/Graph/Layout.lean | Sugiyama ~1500 lines |
| archive upload | sbs/archive/upload.py | ~/.claude extraction |
...

## File Purpose Map

### LeanArchitect
| File | Purpose |
|------|---------|
| Architect/Basic.lean | Node, NodeStatus types |
...

### Dress
...

### Runway
...

### Python Tooling
...

## How-To Patterns

### Add a CLI Command
1. Add parser in cli.py
2. Create handler module
3. Add dispatch

### Add a Validator
...

### Add a Tagging Hook
...

## Gotchas
- Status colors: Lean is source of truth
- Manual ToExpr required for Node
- >100 nodes: barycenter limited to 2 iterations
...

## Cross-Repo Impact Map
| When changing... | Also check... |
|------------------|---------------|
| LeanArchitect Node | Dress serialization, Runway loading |
...
```

---

## Wave 4: README Staleness Detector (Simplified)

### Purpose

Automate what `/update-and-archive` currently does manually: check git state across all repos and report which READMEs may need updating based on code changes.

### Files to Create

```
dev/scripts/sbs/readme/
├── __init__.py
└── check.py    # Single file - git-based staleness detection
```

### Implementation

**`sbs/readme/check.py`**:
```python
from pathlib import Path
from dataclasses import dataclass
import subprocess

# All repos to check (main + 10 submodules)
REPOS = [
    ("Main", "."),
    ("subverso", "forks/subverso"),
    ("verso", "forks/verso"),
    ("LeanArchitect", "forks/LeanArchitect"),
    ("Dress", "toolchain/Dress"),
    ("Runway", "toolchain/Runway"),
    ("SBS-Test", "toolchain/SBS-Test"),
    ("dress-blueprint-action", "toolchain/dress-blueprint-action"),
    ("GCR", "showcase/General_Crystallographic_Restriction"),
    ("PNT", "showcase/PrimeNumberTheoremAnd"),
    ("storage", "dev/storage"),
]

@dataclass
class RepoStatus:
    name: str
    path: str
    readme_path: str
    has_uncommitted: bool
    has_unpushed: bool
    changed_files: list[str]

def check_repo_status(repo_root: Path, name: str, rel_path: str) -> RepoStatus:
    """Check git status for a single repo."""
    # git status --porcelain for uncommitted
    # git log origin/main..HEAD for unpushed
    # Return RepoStatus with findings

def check_all_repos(repo_root: Path) -> list[RepoStatus]:
    """Check all repos and return statuses."""

def format_report(statuses: list[RepoStatus]) -> str:
    """Format human-readable report for /update-and-archive skill."""

def format_json(statuses: list[RepoStatus]) -> str:
    """Format as JSON for programmatic use."""
```

### CLI Command

```bash
sbs readme-check              # Human-readable report
sbs readme-check --json       # JSON output
```

### Output Example (Human-Readable)

```
README Staleness Report
=======================

Repos with changes (READMEs may need updating):

1. Dress (toolchain/Dress)
   README: toolchain/Dress/README.md
   Status: uncommitted changes, unpushed commits
   Changed files:
     - Graph/Layout.lean
     - Graph/Svg.lean

2. Runway (toolchain/Runway)
   README: toolchain/Runway/README.md
   Status: uncommitted changes
   Changed files:
     - Theme.lean

Clean repos (no README updates needed):
  - subverso, verso, LeanArchitect, SBS-Test, ...

Summary: 2 repos need README review, 9 repos clean
```

### Output Example (JSON)

```json
{
  "repos_with_changes": [
    {
      "name": "Dress",
      "path": "toolchain/Dress",
      "readme_path": "toolchain/Dress/README.md",
      "has_uncommitted": true,
      "has_unpushed": true,
      "changed_files": ["Graph/Layout.lean", "Graph/Svg.lean"]
    }
  ],
  "clean_repos": ["subverso", "verso", "LeanArchitect", ...],
  "summary": {"needs_review": 2, "clean": 9}
}
```

---

## Wave 5: Documentation Updates

### Files to Modify

- `CLAUDE.md` - Add Oracle and README tooling documentation
- `.claude/agents/sbs-developer.md` - Add Oracle usage guidance for agents

### Changes

Add new section after "Tooling Hub":

```markdown
---

## SBS-Oracle Agent

Instant codebase Q&A for Claude agents. Use when you need to know "where is X?" or "how does Y work?" without searching.

### Invoking the Oracle

Spawn the oracle agent for single questions:
```
Task(subagent_type="sbs-oracle", prompt="Where is graph layout implemented?")
```

### What the Oracle Knows

- **Concept Index**: Concept → file location mapping
- **File Purpose Map**: One-liner summaries per file
- **How-To Patterns**: Add CLI command, add validator, add hook, etc.
- **Gotchas**: Status color source of truth, manual ToExpr, etc.
- **Cross-Repo Impact**: What to check when changing X

### When to Use

Use the oracle BEFORE searching when:
- Looking for where functionality lives
- Need to understand cross-repo dependencies
- Want to know the pattern for adding features
- Unsure what will break if you change something

### Keeping It Fresh

The oracle is auto-regenerated during `/update-and-archive`:
```bash
sbs oracle compile
```

---

## README Staleness Detection

Identifies which READMEs may need updating based on git state across all repos.

### Running Checks

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts

# Human-readable report
python -m sbs readme-check

# JSON output for programmatic use
python -m sbs readme-check --json
```

### What It Checks

- Uncommitted changes in each repo (main + 10 submodules)
- Unpushed commits
- List of changed files per repo

### Integration with /update-and-archive

The skill runs `sbs readme-check --json` at the start to determine which repos have changes. Agents only update READMEs for repos with actual code changes.
```

### sbs-developer.md Changes

Add new section after "Tooling Reference" section:

```markdown
---

## SBS-Oracle for Codebase Questions

When you need to know "where is X?" or "how does Y work?", spawn the Oracle BEFORE searching:

```python
Task(subagent_type="sbs-oracle", prompt="Where is graph layout implemented?")
```

The Oracle contains pre-compiled knowledge:
- **Concept Index**: Concept → file location
- **File Purpose Map**: One-liner summaries
- **How-To Patterns**: Add CLI command, add validator, etc.
- **Gotchas**: Known quirks and tribal knowledge
- **Cross-Repo Impact**: What to check when changing X

**Use Oracle BEFORE:**
- Grepping for file locations
- Reading multiple files to understand architecture
- Asking "where is X implemented?"
- Figuring out patterns for common modifications

The Oracle is auto-regenerated during `/update-and-archive`.

---

## README Staleness Check

Before updating READMEs, check which repos have changes:

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python -m sbs readme-check --json
```

This checks git state across all repos and reports:
- Which repos have uncommitted changes
- Which repos have unpushed commits
- List of changed files per repo

Focus README updates on repos that actually changed.
```

---

## Wave 6: Integration with /update-and-archive

### Changes to SKILL.md

Update the skill file at `.claude/skills/update-and-archive/SKILL.md`:

**Add new Part 0 (before Part 1):**

```markdown
## Part 0: README Staleness Check

Before updating READMEs, run the staleness check:

\`\`\`bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python -m sbs readme-check
\`\`\`

This reports which repos have changes. Only update READMEs for repos that appear in this report.

**Agent allocation:** Base agent count on the staleness report:
- 0-2 repos changed → Single agent
- 3-5 repos changed → 2 agents (grouped by wave)
- 6+ repos changed → 3 agents (one per wave)
```

**Add new Part 3 (before current Part 3, renumber to Part 4):**

```markdown
## Part 3: Oracle Regeneration

After documentation updates, regenerate the Oracle:

\`\`\`bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python -m sbs oracle compile
\`\`\`

This extracts content from all READMEs and CLAUDE.md into `.claude/agents/sbs-oracle.md`.

**Validation:**
- Oracle must have all sections populated
- File paths must be valid
```

**Final structure:**
- Part 0: README Staleness Check (NEW)
- Part 1: README Updates (existing)
- Part 2: Core Documentation (existing)
- Part 3: Oracle Regeneration (NEW)
- Part 4: Finalization (was Part 3)

---

## Wave 7: Unit Tests

### Files to Create

```
dev/scripts/sbs/tests/pytest/oracle/
├── __init__.py
├── test_compiler.py      # Oracle compilation tests
├── test_extractors.py    # Content extraction tests
└── fixtures/
    └── sample_readme.md  # Test fixture

dev/scripts/sbs/tests/pytest/readme/
├── __init__.py
└── test_check.py         # Git-based staleness detection tests
```

### Test Cases

**Oracle Compiler:**
- Extracts file tables from markdown
- Builds concept index from headers
- Generates valid Oracle markdown
- Handles missing sections gracefully

**README Check:**
- Parses git status output correctly
- Identifies repos with uncommitted changes
- Identifies repos with unpushed commits
- Formats human-readable report correctly
- Formats JSON output correctly

---

## Wave 8: Integration Test

### Files to Create

- `dev/scripts/sbs/tests/pytest/test_oracle_integration.py`

### Test Cases

1. Full compilation produces valid Oracle
2. Oracle contains expected sections
3. File paths in Oracle are valid
4. README check runs without errors
5. Check report format is parseable

---

## Critical Files

| File | Action | Purpose |
|------|--------|---------|
| `sbs/oracle/compiler.py` | Create | Main compilation logic |
| `sbs/oracle/extractors.py` | Create | Content extraction |
| `sbs/oracle/templates.py` | Create | Oracle markdown templates |
| `sbs/readme/check.py` | Create | Git-based staleness detection |
| `sbs/cli.py` | Modify | Add oracle + readme-check commands |
| `CLAUDE.md` | Modify | Add Oracle + README check documentation |
| `.claude/agents/sbs-developer.md` | Modify | Add Oracle usage guidance for agents |
| `.claude/agents/sbs-oracle.md` | Output | Oracle content destination |
| `.claude/skills/update-and-archive/SKILL.md` | Modify | Add Part 0 (staleness check) + Part 3 (Oracle regen) |

---

## Verification

### After Wave 2 (CLI):
```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python -m sbs oracle compile --dry-run
```

### After Wave 4 (README check):
```bash
python -m sbs readme-check
```

### After Wave 6 (Tests):
```bash
python -m pytest sbs/tests/pytest/oracle -v
python -m pytest sbs/tests/pytest/readme -v
```

### Full Integration:
```bash
# 1. Compile Oracle
python -m sbs oracle compile

# 2. Verify Oracle content
cat ../../.claude/agents/sbs-oracle.md | head -100

# 3. Check READMEs
python -m sbs readme-check --json

# 4. Run all tests
python -m pytest sbs/tests/pytest -v
```

---

## Out of Scope

- Hook architecture changes (deferred - current approach is simpler)
- Math/proof content from showcase repos
- Temporal/session data in Oracle
- Auto-fixing README issues (report only)

---

## Success Criteria

1. `sbs oracle compile` generates valid Oracle markdown
2. Oracle contains: Concept Index, File Map, How-Tos, Gotchas, Cross-Repo Impact
3. `sbs readme-check` reports which repos have git changes (uncommitted/unpushed)
4. CLAUDE.md documents Oracle usage and README check workflow
5. sbs-developer.md documents Oracle as first-choice for codebase questions
6. `/update-and-archive` skill uses README check to determine agent allocation
7. All new code has unit tests
8. 230+ existing tests still pass
