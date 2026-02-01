# Visual Compliance Validation System

Automated visual compliance checking for Side-by-Side Blueprint sites using AI vision analysis.

## Build Workflow (Required)

**All screenshot generation must use the Python build script.** Never skip commits or pushes.

```bash
# Standard workflow: build then capture
cd /Users/eric/GitHub/Side-By-Side-Blueprint/toolchain/SBS-Test
python ../../dev/scripts/build.py                    # Full build with git sync
python ../../dev/scripts/sbs capture --interactive   # Capture screenshots
```

The build script commits and pushes all repo changes (no skip option exists by design), ensuring:
- Reproducible builds tied to specific commits
- Ledger tracks actual deployed state
- Change detection works correctly

The build script handles:
1. Git commit and push for all repos
2. Lake manifest updates
3. Toolchain builds (SubVerso → LeanArchitect → Dress → Runway)
4. Project build with `BLUEPRINT_DRESS=1`
5. Site generation
6. Server startup at localhost:8000

## Overview

The compliance system provides:
- Screenshot capture of all pages including interactive states
- AI vision analysis for compliance checking
- Persistent ledger tracking (JSON + Markdown)
- Smart repo-to-page change detection
- Iterative validation loop until 100% compliance

## Commands

### `sbs compliance`

Run visual compliance validation.

```bash
# Check compliance with smart reset (only re-validate changed pages)
python3 -m sbs compliance

# Force full re-validation
python3 -m sbs compliance --full

# Validate specific page
python3 -m sbs compliance --page dashboard

# Include interactive state validation
python3 -m sbs compliance --interactive
```

### `sbs capture`

Capture screenshots for validation.

```bash
# Capture static pages
python3 -m sbs capture

# Capture with interactive states
python3 -m sbs capture --interactive

# Rediscover interactive elements (ignore saved manifests)
python3 -m sbs capture --interactive --rediscover
```

## File Locations

| File | Purpose |
|------|---------|
| `compliance_ledger.json` | Machine-readable ledger with pass/fail status |
| `COMPLIANCE_STATUS.md` | Human-readable compliance report |
| `manifests/{page}_manifest.json` | Frozen interactive element definitions |
| `../../storage/{project}/latest/*.png` | Screenshot captures |

## Compliance Criteria

### Global Criteria (all pages)

- Theme toggle visible in header
- No horizontal scrollbar or content overflow
- Sidebar navigation present and visible
- Current page highlighted in sidebar

### Page-Specific Criteria

#### dashboard
- No secondary sidebar (chapter panel)
- Stats panel shows node counts
- Key theorems panel present
- 2-column grid layout

#### dep_graph
- All 6 status colors visible in legend
- Graph centered in viewport
- Zoom controls visible
- Nodes and edges rendered correctly

#### chapter
- Side-by-side displays aligned
- Rainbow brackets visible (6 colors)
- Syntax highlighting applied
- LaTeX content rendered
- Proof expand/collapse synchronized

## Repo-to-Page Mapping

Changes to these repos trigger revalidation of specific pages:

| Repo Changed | Pages to Revalidate |
|--------------|---------------------|
| subverso | ALL |
| LeanArchitect | dep_graph, chapter |
| Dress | dep_graph, chapter |
| Runway | ALL |
| verso | paper_verso, blueprint_verso |
| dress-blueprint-action | ALL |

## Interactive Elements

The system discovers and captures interactive states:

- **Theme toggle**: Light/dark mode switching
- **Zoom controls**: Dependency graph zoom in/out/fit
- **Node clicks**: Modal popups on dependency graph
- **Proof toggles**: Expand/collapse proof bodies
- **Tactic toggles**: Show/hide tactic states
- **Hover tokens**: Syntax hover information

## Validation Workflow

1. **Initialize**: Load or create ledger for project
2. **Detect changes**: Compare repo commits against ledger
3. **Determine scope**: Map changed repos to affected pages
4. **Capture**: Take screenshots of pages needing validation
5. **Validate**: AI vision analysis against criteria
6. **Update ledger**: Record pass/fail results
7. **Report**: Generate markdown summary
8. **Loop**: Repeat until 100% compliance

## Agent Protocol

The compliance system generates prompts for AI validation agents:

```
Task: Validate {page} screenshot for visual compliance

Read the screenshot at: {path}

Check against these criteria:
{criteria}

Return JSON:
{
    "page": "{page}",
    "pass": true/false,
    "findings": ["issue 1", "issue 2"],
    "confidence": 0.95
}
```

## Ledger Format

```json
{
  "version": "1.0",
  "project": "SBSTest",
  "commit": "abc123",
  "repo_commits": {
    "Dress": "def456",
    "Runway": "789abc"
  },
  "pages": {
    "dashboard": {
      "status": "pass",
      "findings": [],
      "interactions": {
        "theme_toggle": {"status": "pass"}
      }
    }
  },
  "summary": {
    "total_checks": 24,
    "passed": 24,
    "compliance_percent": 100.0
  }
}
```

## Module Architecture

| Module | Responsibility |
|--------|---------------|
| `criteria.py` | Compliance criteria definitions |
| `ledger.py` | Ledger read/write, reset operations |
| `mapping.py` | Repo-to-page change detection |
| `validate.py` | Validation orchestration |
| `capture.py` | Screenshot and interactive capture |

## Validator Plugin Integration

The visual compliance system is now available as a validator plugin in the pluggable architecture.

### Using the Visual Validator

```python
from sbs.validators import discover_validators, registry, ValidationContext
from pathlib import Path

# Discover validators
discover_validators()

# Get the visual compliance validator
validator = registry.get('visual-compliance')

# Create context
context = ValidationContext(
    project='SBSTest',
    project_root=Path('/Users/eric/GitHub/Side-By-Side-Blueprint/toolchain/SBS-Test'),
    commit='abc123',
    screenshots_dir=Path('/Users/eric/GitHub/Side-By-Side-Blueprint/storage/SBSTest/latest'),
    extra={
        'pages': ['dashboard', 'dep_graph'],  # Optional: filter pages
        'include_interactive': True
    }
)

# Generate validation prompts (for AI vision analysis)
result = validator.validate(context)

# Prompts are in result.details['prompts']
```

### Unified Ledger

Visual compliance results are now stored in the unified ledger at `storage/unified_ledger.json` alongside build metrics and other validators.

### Other Validators

The plugin system includes additional validators:
- `timing` - Build phase timing metrics
- `git-metrics` - Commit/diff tracking
- `code-stats` - LOC and file counts

See `dev/scripts/sbs/tests/validators/` for the full plugin architecture.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | 100% compliance achieved |
| 1 | Validation needed or failures present |
| 130 | Interrupted (Ctrl+C) |
