# Task #51: Document Archival-First Push Workflow

## Summary

Document the intentional `git push` hook restriction across 4 files so agents and future sessions understand that all pushes must flow through `sbs archive upload` or build scripts.

## Files to Modify

### 1. `CLAUDE.md` (line ~186, after "Standards" section)

Add a new section **"Git Push Restriction (Archival-First Design)"** explaining:
- Direct `git push` from Claude Code is denied by hooks (by design)
- All pushes must go through:
  - `sbs archive upload` (preferred — calls `ensure_porcelain()` internally)
  - Build scripts (`dev/build-*.sh`) which run git ops via subprocess
- Why: ensures every push is accompanied by an archive entry and porcelain state check

**Placement:** Between the "Standards" section (line 186) and "Quality Validation Framework" section (line 199). This keeps it near the existing build/commit guidance in Standards.

### 2. `.claude/skills/task/SKILL.md`

**A. PR Creation section (line ~152-189):** Update the `git push -u origin` command in the branch creation example to note that direct push is denied — branch creation and initial push happen via `sbs archive upload` during the execution phase, or via the MCP `sbs_pr_create` tool which handles this internally.

**B. Phase 3: Execution section (line ~193-218):** Add a note that all commits on the feature branch are pushed automatically by `sbs archive upload` during phase transitions, not by direct `git push`.

### 3. `.claude/agents/sbs-developer.md`

Add a section in the "Anti-Patterns" block (line ~941) or as a new section near "Local Development Workflow":
- Agents should never need direct `git push`
- The orchestrator handles pushes through the archival process
- If an agent encounters a push failure, it should report it rather than retry

### 4. `.claude/skills/update-and-archive/SKILL.md`

**Git Porcelain section (line ~315-331):** Add a note explaining that `ensure_porcelain()` (called by `sbs archive upload`) is the mechanism that actually pushes, and this bypasses the hook restriction because it runs via Python subprocess rather than direct Bash.

## Execution

Single `sbs-developer` agent wave — all 4 files are documentation edits with no code changes or collision risk.

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  regression: >= 0
```

No quality validators needed (no visual/CSS/build changes).

## Verification

- Read all 4 modified files to confirm accuracy
- Run evergreen tests to confirm no breakage
- Verify the documentation is internally consistent across all 4 files
