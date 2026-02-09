# Batch Issue Resolution: 10 Issues in 4 Waves

**Task:** Disposition 10 issues efficiently via wave-based execution
**Strategy:** Group by type, sequential waves, 100% pass required
**Issues:** #17, #20, #21, #19, #46, #42, #38, #43, #31, #28

---

## Wave Overview

| Wave | Type | Issues | Files | Gate |
|------|------|--------|-------|------|
| 1 | Documentation | #17, #20, #21 | CLAUDE.md | Content review |
| 2 | Python Filters | #19, #46 | 2 Python files | `sbs_run_tests` |
| 3 | CSS/Sidebar | #42, #38, #43 | common.css, DepGraph.lean | Visual compliance |
| 4 | Features | #31, #28 | Theme.lean, sbs_tools.py | Tests + visual |

---

## Wave 1: Documentation (Issues #17, #20, #21)

**Goal:** Add 3 guidance sections to CLAUDE.md

### #17: macOS Platform Conventions
**Location:** New section after "Oracle-First Approach"
```markdown
### macOS Platform Notes

- Always use `python3` not `python` (macOS doesn't have `python` by default)
- Avoid GNU-specific options: no `cat -A`, use `od -c` instead
- Commands like `tree` aren't installed - use `find` or `ls -R` instead
- Use `/opt/homebrew/bin/python3` for explicit homebrew path if needed
```

### #20: Plan Size Guidance
**Location:** Add to "Planning Discipline" section
```markdown
### Plan Size Guidelines

- Keep plans under 10K characters when possible
- If a plan exceeds 10K chars, consider splitting into phases
- Comprehensive roadmaps: present as high-level overview + detailed first phase
- User preference: focused, incremental plans over comprehensive documents
```

### #21: Doing Mode Detection
**Location:** Add to "Agent Orchestration" section
```markdown
### Doing Mode Detection

When the orchestrator has executed 3+ Bash calls in sequence, recognize this as "doing mode":
- User is actively working, not looking to delegate
- Avoid spawning agents during these sequences
- Wait for a natural pause before offering delegation
- If you must suggest an agent, phrase as an offer: "Would you like me to delegate this?"
```

**File:** `/Users/eric/GitHub/Side-By-Side-Blueprint/CLAUDE.md`
**Gate:** Manual review (no build needed)

---

## Wave 2: Python Filters (Issues #19, #46)

**Goal:** Fix two overly-sensitive filters in Python tooling

### #19: Refine bash-error-rate-high Auto-tag
**File:** `dev/storage/tagging/hooks/cli_arg_misfires.py`

**Current:** Counts ALL errors including user rejections
**Fix:** Filter non-actionable patterns before counting

```python
NON_ERROR_PATTERNS = [
    "user doesn't want",
    "sibling tool call errored",
    "nothing to commit",
    "already up to date",
    "already exists",
    "ignored by one of your .gitignore",
]

def detect_misfires(entry, sessions):
    tags = []
    bash_errors = 0
    bash_calls = 0

    for session in sessions:
        for tc in session.tool_calls:
            if tc.tool_name == "Bash":
                bash_calls += 1
                if tc.error:
                    # Filter non-actionable errors
                    error_text = str(tc.error).lower()
                    if not any(p in error_text for p in NON_ERROR_PATTERNS):
                        bash_errors += 1

    if bash_calls > 10 and bash_errors / bash_calls > 0.1:
        tags.append("bash-error-rate-high")

    return tags
```

### #46: Filter Retroactive Entries
**File:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_self_improve.py`

**Current:** Returns backdated retroactive entries
**Fix:** Filter entries tagged "retroactive"

In `sbs_entries_since_self_improve_impl()`, add filter after line 183:

```python
for entry in sorted_entries:
    # Stop when we reach the last self-improve entry
    if last_self_improve_entry and entry.entry_id <= last_self_improve_entry:
        break

    # Skip retroactive entries (backdated migrations)
    if "retroactive" in entry.tags + entry.auto_tags:
        continue

    # ... rest of loop
```

**Gate:** `sbs_run_tests` passes (tier: evergreen)

---

## Wave 3: CSS/Sidebar (Issues #42, #38, #43)

**Goal:** Fix sidebar styling issues and consolidate rendering logic

### #42: Sidebar Text Layout Too Tight
**File:** `toolchain/dress-blueprint-action/assets/common.css`

**Changes:**
- Reduce sidebar font-size slightly (0.875rem → 0.8125rem)
- Increase line-height (1.4 → 1.5)
- Add vertical padding to sidebar items

```css
/* In sidebar item section, adjust: */
.sidebar-item {
  font-size: 0.8125rem;  /* Was 0.875rem */
  line-height: 1.5;      /* Was 1.4 */
  padding: 0.35rem 0;    /* Was 0.25rem */
}
```

### #38: Sidebar Highlight Color Mismatch
**File:** `toolchain/dress-blueprint-action/assets/common.css`

**Design intent:** Active sidebar item should visually "connect" to the content area - the highlight breaks out of the steel blue sidebar and merges with the page background, creating a tab-like effect.

**Problem:**
- Light mode: `--sidebar-active-bg: #ffffff` but content uses `--sbs-bg-surface: #ffffff` and page uses `--sbs-bg-page: #ebebeb`
- These are close but not identical, breaking the visual connection

**Fix:** Bind highlight to content surface color

```css
/* Light mode (line ~120): */
--sidebar-active-bg: var(--sbs-bg-surface);  /* Match content area */
--sidebar-active-text: var(--sbs-text);

/* Dark mode (line ~305): */
--sidebar-active-bg: var(--sbs-bg-surface);  /* Match content area */
--sidebar-active-text: var(--sbs-text);
```

This ensures the highlight always tracks the content background, maintaining the "connected tab" visual.

### #43: Sidebar Rendering Consolidation
**File:** `toolchain/Runway/Runway/DepGraph.lean`

**Problem:** Two separate sidebar implementations (renderSidebar vs renderDepGraphSidebar)
**Fix:**
1. Remove `renderDepGraphSidebar` function (lines 377-445)
2. Import `Runway.Theme` if not already
3. In `fullPageGraph`, replace call with `Theme.renderSidebar site (some "dep_graph")`

**Gate:** Visual compliance on SBSTest
- **Before screenshots:** Dashboard, dep_graph, chapter page
- **After screenshots:** Same pages
- Visual diff should show only intended changes

---

## Wave 4: Features (Issues #31, #28)

### #31: Blueprint [TeX] Links to First Chapter
**File:** `toolchain/Runway/Runway/Theme.lean`

**Current (line 139):**
```lean
let texBlueprint := mkDocItem "Blueprint [TeX]" "index.html" "" availDocs.blueprintTex
```

**Fix:** Link to first chapter instead of index.html
```lean
let firstChapterSlug := site.chapters.get? 0 |>.map (·.slug) |>.getD ""
let texBlueprintHref := if firstChapterSlug.isEmpty then "index.html" else s!"{firstChapterSlug}.html"
let texBlueprint := mkDocItem "Blueprint [TeX]" texBlueprintHref firstChapterSlug availDocs.blueprintTex
```

**Consideration:** When no chapters exist (single-page mode), fall back to index.html.

### #28: Add MCP Tool for Issue Summary
**File:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py`

**New tool:** `sbs_issue_summary`

Agent designs output format. Rough spec:
- Total count of open issues
- Issues grouped by label type (bug/feature/idea)
- Issues grouped by area (sbs/devtools/misc)
- List with: number, title, labels, age

**Gate:** Tests pass + visual compliance on SBSTest

---

## Gates Definition

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  quality:
    T5: ">= 0.8"   # Status color match
    T6: ">= 0.8"   # CSS variable coverage
  regression: ">= 0"
```

---

## Verification Plan

### Wave 1 (Docs)
- Read CLAUDE.md after edit
- Verify sections are in correct locations
- No structural/formatting issues

### Wave 2 (Python)
- Run `sbs_run_tests --tier evergreen`
- Verify filters work as intended (no regressions in existing tests)

### Wave 3 (CSS/Sidebar)
- Capture before screenshots: `sbs capture --project SBSTest --interactive`
- Make CSS changes
- Build: `python build.py` in SBS-Test
- Capture after screenshots
- Run `sbs compliance --project SBSTest`
- Visual diff: sidebar should look better, no unintended changes

### Wave 4 (Features)
- Build SBS-Test after Theme.lean change
- Verify "Blueprint [TeX]" now links to first chapter
- Test sbs_issue_summary MCP tool directly
- Run full test suite

---

## Issue Closure

After all waves pass, close issues #17, #20, #21, #19, #46, #42, #38, #43, #31, #28 via `sbs_issue_close`.

---

## Execution Order

1. **Wave 1** → Single agent, CLAUDE.md edits
2. **Wave 2** → Single agent, Python filter fixes
3. **Wave 3** → Single agent, CSS + Lean sidebar consolidation
4. **Wave 4** → Two sequential agents: #31 (Lean), then #28 (Python)

Each wave completes fully before next begins. 100% pass required.
