---
name: qa
description: Live interactive QA agent driven by test catalog
version: 1.0.0
---

# /qa - Live Interactive QA

Browser-driven visual and interactive QA against a running SBS blueprint site. Uses compliance criteria and the test catalog to systematically verify every visual and interactive element.

---

## Invocation

| Pattern | Behavior |
|---------|----------|
| `/qa` | Interactive: pick project, run full review |
| `/qa SBSTest` | Review specific project (all pages) |
| `/qa SBSTest dashboard dep_graph` | Review specific pages only |

### Argument Parsing

- First argument (if any) is the project name: `SBSTest`, `GCR`, or `PNT`
- Remaining arguments are page names to scope the review: `dashboard`, `dep_graph`, `paper_tex`, `pdf_tex`, `chapter`
- No arguments: prompt user to select project via AskUserQuestion

---

## Mandatory Archive Protocol

**This is not optional. Violations break the skill contract.**

### First Action on Invocation

Before doing ANYTHING else:

1. Call `sbs_archive_state()` via MCP
2. Check `global_state` field:
   - `null` -> Fresh QA run, proceed to setup
   - `{skill: "qa", substate: X}` -> Resume from substate X
   - `{skill: "other", ...}` -> Error: state conflict, do NOT proceed

### Phase Transitions

Every phase change MUST use the MCP skill lifecycle tools:

- **Start:** `sbs_skill_start(skill="qa", initial_substate="setup")`
- **Transition:** `sbs_skill_transition(skill="qa", to_phase="<next_phase>")`
- **End:** `sbs_skill_end(skill="qa")`
- **Failure:** `sbs_skill_fail(skill="qa", reason="<description>")`

Phases: `setup` -> `review` -> `report`

### State Conflict

If `global_state.skill != "qa"` and `global_state` is not `null`:
- Another skill owns the state
- Do NOT proceed
- Report error: "State conflict: skill '<other_skill>' currently owns global state"
- Wait for user resolution

---

## Phase 1: Setup

**Purpose:** Build the project, start the dev server, load review criteria, capture baselines.

### Entry

```
sbs_skill_start(skill="qa", initial_substate="setup")
```

### Actions

1. **Build project** via `sbs_build_project(project="<name>")`
   - If build fails: `sbs_skill_fail(skill="qa", reason="Build failed: <details>")` and stop
2. **Start dev server** via `sbs_serve_project(project="<name>", action="start")`
   - If server fails to start: `sbs_skill_fail(skill="qa", reason="Server failed to start")` and stop
3. **Load criteria** by reading `dev/scripts/sbs/tests/compliance/criteria.py`
   - Extract `PAGE_CRITERIA`, `GLOBAL_CRITERIA`, `SIDEBAR_CRITERIA`
   - Filter to visual and interactive categories only: `layout`, `color`, `interaction`, `content`, `visual`
   - Exclude `functional` and `technical` categories (these are covered by automated tests)
4. **Determine page scope:**
   - If specific pages provided in invocation, use those
   - Otherwise, use all pages: `dashboard`, `dep_graph`, `paper_tex`, `pdf_tex`, `chapter`
   - Pages that return HTTP 404 are skipped without error
5. **Capture baseline screenshots** of all target pages via `browser_screenshot` after `browser_navigate`

### Transition

```
sbs_skill_transition(skill="qa", to_phase="review")
```

---

## Phase 2: Review

**Purpose:** Systematically evaluate every criterion on every page using browser tools.

### Entry

```
sbs_skill_transition(skill="qa", to_phase="review")
```

### Review Loop

For each page in scope:

1. **Navigate:** `browser_navigate` to `http://localhost:8000/<page_path>`
   - Dashboard: `/` or `/index.html`
   - Dependency graph: `/dep_graph.html`
   - Paper: `/paper.html`
   - PDF: `/pdf.html`
   - Chapter: auto-detect first chapter from sidebar links

2. **Baseline capture:** `browser_screenshot` for the page in its default state

3. **Evaluate static criteria** (layout, color, content, visual):
   - For criteria with `selector`: use `browser_get_elements` to verify element presence
   - For criteria with `hex_color`: use `browser_evaluate` to compute styles and compare colors
   - For layout criteria: use `browser_evaluate` to check overflow, dimensions, grid properties
   - For content criteria: use `browser_get_elements` to verify text content exists

4. **Evaluate interactive criteria:**
   For each `interactive_element` defined for the page:
   a. `browser_click` the element (using the defined `selector`)
   b. `browser_screenshot` to capture post-interaction state
   c. Verify the expected behavior occurred (e.g., theme changed, modal opened, proof expanded)
   d. Reset state if needed (e.g., click toggle again, close modal)

5. **Report findings in dialogue** as discovered -- do not wait until all pages are done

6. **Log bugs autonomously:** For clear failures (element missing, wrong color, broken interaction), call `sbs_issue_log` immediately:
   ```
   sbs_issue_log(
       title="<concise bug description>",
       body="Page: <page>\nCriterion: <id>\nExpected: <expected>\nActual: <actual>",
       labels=["bug:visual", "area:sbs:theme", "origin:agent"]
   )
   ```

### Agent Concurrency

Up to 2 `sbs-developer` agents may review different page groups in parallel:

| Agent | Pages |
|-------|-------|
| Agent 1 | `dashboard`, `dep_graph` |
| Agent 2 | `paper_tex`, `pdf_tex`, `chapter` |

Each agent maintains its own browser session (separate processes). The orchestrator spawns both agents in a single message and collects results.

For single-page reviews or narrow scope, use 1 agent.

### Criteria Reference

The following criteria categories are checked during review:

| Category | What to Check | Browser Tool |
|----------|---------------|--------------|
| `layout` | Element positioning, grid, overflow, alignment | `browser_evaluate` (computed styles) |
| `color` | Status colors, bracket colors, comment colors | `browser_evaluate` (getComputedStyle) |
| `interaction` | Click responses, toggles, hovers, modals | `browser_click` + `browser_screenshot` |
| `content` | Text presence, rendered math, code blocks | `browser_get_elements` |
| `visual` | Zebra striping, styling consistency | `browser_screenshot` + visual inspection |

### Transition

After all pages reviewed:

```
sbs_skill_transition(skill="qa", to_phase="report")
```

---

## Phase 3: Report

**Purpose:** Generate structured ledger, present summary, clean up.

### Entry

```
sbs_skill_transition(skill="qa", to_phase="report")
```

### Actions

1. **Generate QA ledger** at `dev/storage/<project>/qa_ledger.json`:

```json
{
  "version": "1.0",
  "project": "SBSTest",
  "run_id": "<ISO-timestamp>-<short-hash>",
  "timestamp": "<ISO-timestamp>",
  "pages": {
    "<page_name>": {
      "status": "pass|fail|warn",
      "criteria_checked": 13,
      "criteria_passed": 12,
      "findings": ["human-readable finding strings"],
      "screenshots": ["screenshot_filenames"],
      "interactions_tested": 3
    }
  },
  "summary": {
    "pages_reviewed": 5,
    "total_criteria": 61,
    "passed": 58,
    "failed": 2,
    "warnings": 1,
    "issues_logged": [142, 143]
  }
}
```

Page status rules:
- `pass`: All criteria passed
- `fail`: Any required criterion failed
- `warn`: Only recommended/optional criteria failed

2. **Present summary to user** in dialogue:
   - Per-page pass/fail with finding counts
   - List of issues logged (with numbers and titles)
   - Overall pass rate

3. **Stop dev server** via `sbs_serve_project(project="<name>", action="stop")`

4. **End skill:**
```
sbs_skill_end(skill="qa")
```

---

## Recovery Semantics

### Compaction Survival

If context compacts mid-run:

1. New context queries `sbs_archive_state()`
2. Reads current `global_state.substate`
3. Resumes from **start** of that substate

### Substate Resume Behavior

| Substate | Resume Action |
|----------|---------------|
| `setup` | Check if server is running via `sbs_serve_project(action="status")`. If running, skip build. If not, rebuild and restart. |
| `review` | Check `dev/storage/<project>/qa/` for existing screenshots. Resume from first page without screenshots. Re-read criteria file. |
| `report` | Re-read all findings from screenshots and notes in storage. Regenerate `qa_ledger.json`. |

---

## Substates

| Substate | Description | Transition |
|----------|-------------|------------|
| `setup` | Build project, start server, load criteria | -> review |
| `review` | Browser-driven page-by-page evaluation | -> report |
| `report` | Generate ledger, present summary, clean up | -> (end) |

Each substate transition is recorded via `sbs_skill_transition`. The final `sbs_skill_end` clears `global_state` to `null`.

---

## Error Handling

| Error | Response |
|-------|----------|
| Build failure | `sbs_skill_fail(skill="qa", reason="Build failed: <details>")` |
| Server won't start | `sbs_skill_fail(skill="qa", reason="Server failed to start")` |
| Browser tool failure | Retry once. If still fails, skip element and record finding: "Could not evaluate: <criterion_id>" |
| Page returns 404 | Skip page, record in findings: "Page not found: <page_name>" |
| All browser tools failing | `sbs_skill_fail(skill="qa", reason="Browser tools unavailable")` |

All findings are surfaced in dialogue. Nothing is silently ignored.

---

## Review Scope

### What IS checked (visual + interactive):
- Layout correctness (grid, alignment, overflow)
- Color accuracy (6-status model, rainbow brackets, comment styling)
- Interactive element behavior (theme toggle, zoom, modals, proof toggles, tactic toggles)
- Content presence (stats, key theorems, rendered math, code blocks)
- Visual consistency (zebra striping, sidebar highlights)

### What is NOT checked (automated tests cover these):
- Functional correctness (pytest suite, T1/T2 validators)
- Technical constraints (viewBox origin, CSS variable coverage -- T5/T6 validators)
- Build pipeline integrity
- Manifest data accuracy

### Criteria Sources

| Source | Location | What It Provides |
|--------|----------|-----------------|
| Compliance criteria | `dev/scripts/sbs/tests/compliance/criteria.py` | Structured per-page criteria with selectors, colors, categories |
| Test catalog | `dev/storage/TEST_CATALOG.md` | Interactive test entries, CLI commands |
| Global criteria | `GLOBAL_CRITERIA` in criteria.py | Cross-page requirements (theme toggle, overflow, sidebar) |
| Sidebar criteria | `SIDEBAR_CRITERIA` in criteria.py | Sidebar-specific checks (consistency, highlights) |

---

## Tool Reference

### Browser Tools

| Tool | Use For |
|------|---------|
| `browser_navigate` | Navigate to page URL |
| `browser_screenshot` | Capture current page state |
| `browser_click` | Click interactive elements |
| `browser_get_elements` | Query DOM for element presence |
| `browser_evaluate` | Run JavaScript for computed styles, dimensions |

### SBS MCP Tools

| Tool | Use For |
|------|---------|
| `sbs_build_project` | Build the project before QA |
| `sbs_serve_project` | Start/stop/check dev server |
| `sbs_skill_start` | Begin QA skill session |
| `sbs_skill_transition` | Move between phases |
| `sbs_skill_end` | Complete QA and clear state |
| `sbs_skill_fail` | Record failure and release state |
| `sbs_issue_log` | Log bugs found during review |

### File Tools

| Tool | Use For |
|------|---------|
| `Read` | Load criteria.py, read existing screenshots |
| `Write` | Write qa_ledger.json |
| `Glob` | Find existing QA screenshots for recovery |

---

## Anti-Patterns

- **Skipping browser verification**: Do not mark criteria as passed without actually checking via browser tools
- **Silent failures**: Every finding must be reported in dialogue, even skipped elements
- **Running without a server**: Always verify the server is running before navigating
- **Mixing automated and manual checks**: This skill handles visual/interactive only; do not duplicate T1-T8 validator work
- **Logging uncertain bugs**: Only `sbs_issue_log` for clear, unambiguous failures. Uncertain observations go in the findings list, not as issues
