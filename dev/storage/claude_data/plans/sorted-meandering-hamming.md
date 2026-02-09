# Plan: /qa Skill + Browser Tools (#144)

## Deliverables

Two components, in dependency order:

### D1: General Browser Tools in sbs-lsp-mcp

**New file:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/browser_tools.py`

5 tools with **persistent active page** pattern (unlike Zulip's stateless per-call pages):

| Tool | Purpose | Key params |
|------|---------|------------|
| `browser_navigate` | Open URL, return title + page info | `url` |
| `browser_click` | Click element on active page | `selector` |
| `browser_screenshot` | Capture active page | `name?`, `full_page?`, `selector?` |
| `browser_evaluate` | Run JS on active page | `script` |
| `browser_get_elements` | List matching elements with text/attrs | `selector`, `limit?` |

**Active page lifecycle:**
- `AppContext` gets new field: `active_page: Page | None = None`
- `browser_navigate`: creates page if none exists, navigates it
- Other tools operate on active page (error if none)
- Page persists across tool calls for stateful interaction (navigate -> click -> screenshot)
- `browser_navigate` to a new URL reuses the same page

**Models:** Add to `sbs_models.py`:
- `BrowserNavigateResult(url, title, status_code)`
- `BrowserClickResult(selector, clicked, element_text)`
- `BrowserScreenshotResult(image_path, url, captured_at, hash)`
- `BrowserEvaluateResult(result, type)`
- `BrowserElementsResult(selector, elements: List[ElementInfo], count)`

**Registration:** In `server.py`, conditional on `browser_context` existing (piggybacks on existing ZULIP_ENABLED). No new env var needed.

**Screenshots storage:** `dev/storage/<project>/qa/` (separate from compliance captures)

### D2: /qa Skill Definition

**New file:** `.claude/skills/qa/SKILL.md`

Multi-phase skill with 3 substates:

| Phase | Purpose | Agent model |
|-------|---------|-------------|
| `setup` | Build, serve, load catalog, baseline | Single agent or orchestrator |
| `review` | Browser-driven page review per catalog | Up to 2 parallel agents (by page group) |
| `report` | Generate ledger, log issues, summarize | Single agent |

**Invocation patterns:**
- `/qa` - Interactive: pick project, run full review
- `/qa SBSTest` - Review specific project
- `/qa SBSTest dashboard dep_graph` - Review specific pages only

**Review checklist source:** `dev/scripts/sbs/tests/compliance/criteria.py` (structured criteria) + `TEST_CATALOG.md` (interactive tests section). The skill reads criteria programmatically for each page, checks them via browser tools, and reports pass/fail.

**Review loop (per page):**
1. `browser_navigate` to page URL
2. `browser_screenshot` for baseline
3. For each criterion in page: evaluate via `browser_get_elements`/`browser_evaluate`
4. For each interactive element: `browser_click`, then `browser_screenshot`
5. Report findings in dialogue as they're discovered
6. `sbs_issue_log` for clear bugs (autonomous)

**Output:** `dev/storage/<project>/qa_ledger.json`
```json
{
  "version": "1.0",
  "project": "SBSTest",
  "run_id": "...",
  "timestamp": "...",
  "pages": {
    "dashboard": {
      "status": "pass|fail|warn",
      "criteria_checked": 13,
      "criteria_passed": 12,
      "findings": ["..."],
      "screenshots": ["dashboard_baseline.png", "dashboard_theme_toggle.png"],
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

**Archive protocol:** Same pattern as /task and /self-improve:
- `sbs_skill_start(skill="qa", initial_substate="setup")`
- Transitions: setup -> review -> report
- `sbs_skill_end(skill="qa")` at completion
- Recovery: check `sbs_archive_state()`, resume from substate

## Execution Waves

### Wave 1: Browser tools (sbs-developer agent)
**Files modified:**
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/browser_tools.py` (NEW)
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` (add models)
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/server.py` (add active_page to AppContext, register tools)

### Wave 2: Skill definition (sbs-developer agent, parallel with Wave 1)
**Files modified:**
- `.claude/skills/qa/SKILL.md` (NEW)

### Wave 3: Integration test
- Restart MCP server (picks up new tools)
- Build SBS-Test, start dev server
- Exercise browser tools manually against live site
- Run one page through the review loop

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  quality:
    T5: >= 0.8
    T6: >= 0.9
  regression: >= 0
```

No new tests added in this task (the skill itself IS the testing tool). Evergreen suite must still pass.

## Verification

1. MCP server restarts without errors with browser tools registered
2. `browser_navigate` successfully loads SBS-Test dashboard
3. `browser_screenshot` produces a valid PNG
4. `browser_click` toggles theme and `browser_screenshot` captures the change
5. `browser_get_elements` returns node list from dep_graph
6. Skill definition follows conventions (frontmatter, archive protocol, recovery)
