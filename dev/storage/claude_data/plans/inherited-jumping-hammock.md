# Crush Plan: 7 Issues in 3 Waves

**Issues:** #136, #137, #138, #139, #140, #141, #147
**Deferred:** #99, #142, #143, #146, #148, #149

---

## Wave 0: Direct Closure

**#138 — Defer auto-tagger improvement to DuckDB query layer**
- Close with comment: "Decision documented. Auto-tagger remains running; improvements deferred to DuckDB analytics layer per #118."
- No code changes.

---

## Wave 1: Documentation Batch (2 parallel agents)

### Agent A: SKILL.md updates (#136, #139, #140)

**File:** `.claude/skills/task/SKILL.md`

**#136 — Pre-flight checklist in planning phase**
- Insert after line 160 (after "Estimated scope" bullet), before "Agent concurrency":
```markdown
**Pre-flight checklist (REQUIRED before finalizing plan):**
- Read CLAUDE.md "Known Limitations" section — verify plan doesn't conflict with documented limitations
- Check open issues (`sbs_issue_list`) for related/duplicate work
```

**#139 — Probe quantitative success criteria during alignment**
- Insert after line 134 (after "Affected repositories" bullet), before "Agent concurrency":
```markdown
**For tasks producing artifacts (builds, screenshots, CSS, templates):**
- Probe for quantitative success criteria: "What score/threshold defines success?"
- Map criteria to specific gate definitions (T1-T8, test counts, regression bounds)
- If user doesn't specify, propose defaults based on affected repos
```

**#140 — Taxonomy test reminder in planning gates**
- Insert after line 177 ("Plans without gates are incomplete"), before "Test Tiers":
```markdown
**Taxonomy changes:** Plans modifying `dev/storage/labels/taxonomy.yaml` or tag dimensions MUST include taxonomy tests in gates:
```yaml
gates:
  tests: pytest sbs/tests/pytest/test_taxonomy.py -v
```
```

### Agent B: sbs-developer.md update (#137)

**File:** `.claude/agents/sbs-developer.md`

**#137 — Consult docs before subsystem-specific code**
- Insert new subsection after "Tooling Reference" (after line 243), before "/oracle Skill":
```markdown
## Documentation Consultation Protocol

Before modifying code in these subsystems, read the relevant documentation first:

| Subsystem | Read First |
|-----------|-----------|
| Archive / tagging | `dev/markdowns/permanent/Archive_Orchestration_and_Agent_Harmony.md` |
| Build pipeline | `dev/markdowns/permanent/ARCHITECTURE.md` |
| Validation / quality | `dev/storage/README.md` (already referenced above) |
| Skills / orchestration | `.claude/skills/<skill>/SKILL.md` + `CLAUDE.md` "Custom Skills" section |
| CSS / theme | `sbs-developer.md` "CSS Architecture" section (above) |
| Lean toolchain | `dev/markdowns/permanent/ARCHITECTURE.md` "Build Pipeline" section |

This prevents repeated mistakes from writing code that contradicts documented patterns.
```

---

## Wave 2: Code Fixes (2 parallel agents)

### Agent C: Zebra striping CSS (#147)

**File:** `toolchain/dress-blueprint-action/assets/blueprint.css`

- The `.sbs-container` has `background: var(--sbs-bg-surface)` (common.css:340). Zebra striping variables exist (`--sbs-bg-page` vs `--sbs-bg-surface`) but no alternating selectors exist.
- Add after the existing `.sbs-container` rule in blueprint.css (after line 234):
```css
/* Zebra striping for side-by-side containers */
.sbs-container:nth-child(even) {
  background: var(--sbs-bg-page);
}
```
- Odd containers keep `--sbs-bg-surface` from common.css base rule; even containers get `--sbs-bg-page`.
- Both light and dark mode variables are already defined, so this works in both themes.
- Verify with `sbs capture --project SBSTest --interactive` + visual inspection.

### Agent D: Fix sbs_entries_since_self_improve (#141)

**File:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_self_improve.py` (lines 983-1057)

**Bug:** Lines 1011-1015 find ANY entry with `skill: self-improve`, including the current active session's `phase_start`. Should find the last **completed** self-improve session.

**Fix:** Use `_group_entries_by_skill_session()` (already in same file, line 75) to find completed sessions:
```python
# Replace lines 1011-1015 with:
sessions = _group_entries_by_skill_session(list(index.entries.values()))
# Find most recent completed self-improve session
for session in reversed(sessions):
    if session.skill == "self-improve" and session.completed:
        last_self_improve_entry = session.last_entry_id
        last_self_improve_timestamp = session.end_time
        break
```

This reuses existing infrastructure and correctly distinguishes completed from active sessions.

---

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  regression: >= 0
```

No T5/T6 quality gates needed — CSS change is additive (zebra striping), not modifying existing color variables.

---

## Execution Order

1. Wave 0: Close #138 (orchestrator, no agent)
2. Wave 1: Agents A + B in parallel (docs)
3. Wave 2: Agents C + D in parallel (code)
4. Run evergreen tests
5. Visual verify #147 via screenshot
6. Finalize, merge, close issues

---

## Verification

- **#136, #139, #140:** Read SKILL.md, confirm new sections present
- **#137:** Read sbs-developer.md, confirm doc consultation table present
- **#147:** Build SBSTest, capture chapter screenshot, verify alternating row backgrounds
- **#141:** Run `sbs_entries_since_self_improve` MCP tool, verify it returns entries after last *completed* cycle (not current)
- **All:** `pytest sbs/tests/pytest -m evergreen --tb=short` passes
