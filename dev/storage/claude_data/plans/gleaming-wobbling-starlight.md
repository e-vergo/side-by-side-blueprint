# Plan: Capture L4 Meta-Introspection Findings

## Summary

Persist the L4 meta-introspection synthesis as durable artifacts: one L4 report, one user operational profile, 9 child issues, and 1 master tracking issue.

## Wave Structure

### Wave 1: Write Documents (2 parallel `sbs-developer` agents)

**Agent 1A** writes `dev/storage/archive/meta-summaries/L4-{timestamp}.md`
- Full L4 synthesis report following L3 format convention
- Sections: Central Finding, User Profile (summary), CLAUDE.md Gap Analysis, Strange Loops, Information Architecture, Recommendations, Cross-References
- Placeholder `Master Issue: #TBD` in Cross-References (patched in Wave 3)
- Orchestrator provides full content; agent writes it

**Agent 1B** writes `dev/markdowns/permanent/USER_PROFILE.md`
- Operational guide derived from 659 user interactions
- Sections: Communication Patterns, Decision Patterns, Scope Calibration, Delegation Signals, Friction Points, Leverage Points, Anti-Patterns, Session Rhythm
- Orchestrator provides full content from Wave 2 user effectiveness agent output

**No file overlap.** Gate: both files exist and are non-empty.

### Wave 2: Create 9 Child Issues (1 `sbs-developer` agent)

Sequential `sbs_issue_log` calls. Agent records all returned issue numbers.

| # | Title | Labels |
|---|-------|--------|
| 1 | Merge improvement captures into L2 discovery pipeline | `feature:new`, `area:devtools:archive` |
| 2 | Reduce header taxonomy from 10 aspirational to ~6 effective | `housekeeping:cleanup`, `area:devtools:archive` |
| 3 | Adaptive retrospective templates for clean sessions | `feature:new`, `area:devtools:archive` |
| 4 | Instrument oracle-first compliance observability | `feature:new`, `area:devtools:archive` |
| 5 | Add visual verification gate to task finalization | `feature:new`, `area:devtools:archive` |
| 6 | Fix tag signal pipeline via DuckDB entry-level extraction | `bug:functional`, `area:devtools:archive` |
| 7 | Investigate finalization failure patterns | `investigation`, `area:devtools:archive` |
| 8 | Replace closure rate metric with verification rate | `feature:new`, `area:devtools:archive` |
| 9 | Store and reference user operational profile in CLAUDE.md | `housekeeping:cleanup` |

Each issue body references the L4 report path and relevant section. Gate: 9 issues created, numbers collected.

### Wave 3: Master Issue + Updates (1 `sbs-developer` agent)

1. **Create master issue** via `sbs_issue_log`:
   - Title: `L4 Meta-Introspection: Close the Observation-Action Gap`
   - Labels: `scope:architectural`
   - Body: summary + checklist of all 9 child issues with numbers
2. **Edit** `L4-{ts}.md` to replace `#TBD` with master issue number
3. **Edit** `CLAUDE.md` line ~415 to add `USER_PROFILE.md` row to Reference Documents table

Gate: master issue created, L4 report back-patched, CLAUDE.md updated.

## Files Modified

| File | Wave | Action |
|------|------|--------|
| `dev/storage/archive/meta-summaries/L4-{ts}.md` | 1, 3 | Create, then patch |
| `dev/markdowns/permanent/USER_PROFILE.md` | 1 | Create |
| `CLAUDE.md` | 3 | Add table row at line ~415 |

## Verification

1. Confirm L4 report exists in `dev/storage/archive/meta-summaries/` with correct L4 prefix
2. Confirm USER_PROFILE.md exists in `dev/markdowns/permanent/`
3. Run `sbs_issue_list(state="open")` -- should show 9 new child issues + 1 master (17 total open)
4. Verify master issue body contains all 9 child issue numbers as checklist items
5. Verify L4 report cross-references section contains master issue number
6. Verify CLAUDE.md Reference Documents table includes USER_PROFILE.md row
