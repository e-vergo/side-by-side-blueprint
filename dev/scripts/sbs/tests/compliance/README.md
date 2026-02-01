# sbs.tests.compliance - Visual Compliance Validation

Automated visual compliance testing using AI vision analysis.

## Modules

| Module | Purpose |
|--------|---------|
| `capture.py` | Screenshot capture using Playwright |
| `compare.py` | Screenshot diff and history commands |
| `criteria.py` | Page compliance criteria definitions |
| `criteria_design.py` | Design-focused criteria |
| `mapping.py` | Repo-to-page change detection |
| `validate.py` | Compliance orchestration and CLI |
| `ledger_ops.py` | Compliance ledger operations |

## Workflow

1. **Capture** - Take screenshots of 8 standard pages
2. **Validate** - AI vision analyzes each screenshot against criteria
3. **Track** - Pass/fail results saved to `compliance_ledger.json`
4. **Loop** - Repeat until 100% compliance

## CLI Commands

```bash
# Capture screenshots
sbs capture --project SBSTest
sbs capture --interactive  # Include interactive states

# Run compliance check
sbs compliance --project SBSTest
sbs compliance --full  # Force full re-validation
sbs compliance --interactive  # Include interactive validation

# Compare screenshots
sbs compare
sbs compare --baseline 2024-01-15
```

## Pages Validated

| Page | Description |
|------|-------------|
| `dashboard` | Dashboard homepage |
| `dep_graph` | Dependency graph |
| `paper_tex` | Paper [TeX] |
| `pdf_tex` | PDF [TeX] |
| `paper_verso` | Paper [Verso] |
| `pdf_verso` | PDF [Verso] |
| `blueprint_verso` | Blueprint [Verso] |
| `chapter` | First chapter page |

## Ledger Structure

```json
{
  "pages": {
    "dashboard": {
      "passed": true,
      "validated_at": "2024-01-15T10:30:00",
      "commit": "abc123"
    }
  },
  "last_full_validation": "2024-01-15T10:30:00"
}
```

## Usage

```python
from sbs.tests.compliance import (
    ComplianceLedger,
    load_ledger,
    save_ledger,
    is_fully_compliant,
)
from sbs.tests.compliance.capture import capture_screenshots
from sbs.tests.compliance.validate import run_compliance_loop
```
