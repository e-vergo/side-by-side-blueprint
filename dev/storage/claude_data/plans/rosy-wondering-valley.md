# Issue Backlog Triage & Fix

## Scope

10 issues addressed: 2 closures, 3 code fixes, 3 doc fixes, 2 investigations.
3 architectural issues left open (#95, #99, #118). #119 staged for separate /task.

## Wave Structure

### Wave 0: Closures + Investigations (parallel, 2 agents)

**Agent 0a: Close superseded issues**
- Close #98 with comment: "Superseded by #110 -- fixing the root cause (entry-level tag discrimination) will give tag_effectiveness real data to work with."
- Close #102 with comment: "Subsumed by #95 -- skill architecture redesign will determine the fate of /update-and-archive."

**Agent 0b: Refresh stale investigation data**
- Run `sbs_skill_stats()` to get current task completion rate (was 85%, #114)
- Run `sbs_system_health()` to get current quality score coverage (was 3.1%, #111)
- Report findings. If data shows non-issues, close the relevant issues. If still relevant, update issue comments with fresh data.

### Wave 1: Documentation Fixes (parallel, 3 agents)

**Agent 1a: #116 -- Compress finalization confirmations**
- File: `.claude/skills/task/SKILL.md`
- Location: Phase 4 Finalization section (line ~257)
- Add after the PR merge block: compressed confirmation guidance for obvious closures (all gates pass, PR approved, issues clearly linked → single yes/no instead of step-by-step)

**Agent 1b: #112 -- Simplicity-matching guidance**
- File: `.claude/agents/sbs-developer.md`
- Location: Before the Anti-Patterns section (line ~985)
- Add new section: "Simplicity Matching" -- when user references an existing pattern, match its complexity. Don't propose alternatives unless asked. "Do not overcomplicate" = immediately implement minimal viable approach.

**Agent 1c: #113 -- Doing mode detection expansion**
- File: `CLAUDE.md`
- Location: "Doing Mode Detection" section (lines 393-399)
- Expand signals beyond 3+ Bash calls: include direct file edits by user (VSCode selections), user rejecting agent offers, user making changes between messages. Add explicit check before agent spawn during execution phase.

### Wave 2: Code Fixes (parallel, 3 agents)

**Agent 2a: #97 -- ensure_porcelain push gap**
- File: `dev/scripts/sbs/archive/upload.py`
- Location: `ensure_porcelain()` function (lines 138-175)
- Add: `repo_has_unpushed()` helper that checks `git log origin/<branch>..HEAD --oneline`
- Modify: Phase 1 loop to check both `repo_is_dirty()` OR `repo_has_unpushed()`
- Result: Submodules with pre-existing unpushed commits get pushed

**Agent 2b: #115 -- T6 threshold alignment**
- File: `dev/scripts/sbs/tests/validators/design/variable_coverage.py`
- Location: Line 403, default 0.95
- Change: Default from 0.95 to 0.90 to match plan gate conventions
- Also update: Docstring at line 364 ("default: 0.95" → "default: 0.90")

**Agent 2c: #110 -- Auto-tagger entry-level discrimination**
- File: `dev/scripts/sbs/archive/extractor.py`
- Location: `extract_claude_data()` lines 646-732
- Problem: `files_modified` is aggregated across ALL sessions into one set, then passed to every entry
- Fix: Return per-session file lists (or at minimum, don't aggregate across sessions for tagging purposes)
- Also touch: `upload.py` where `snapshot.files_modified` is passed to `build_tagging_context()` -- needs to receive per-entry context instead of session-wide union

### Wave 3: Validation

- Run evergreen test tier: `pytest sbs/tests/pytest -m evergreen --tb=short`
- Run `sbs_validate_project` for SBSTest (T5, T6)
- Verify ensure_porcelain changes don't break archive upload flow

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

## Files Modified

| Wave | File | Issue |
|------|------|-------|
| 1a | `.claude/skills/task/SKILL.md` | #116 |
| 1b | `.claude/agents/sbs-developer.md` | #112 |
| 1c | `CLAUDE.md` | #113 |
| 2a | `dev/scripts/sbs/archive/upload.py` | #97 |
| 2b | `dev/scripts/sbs/tests/validators/design/variable_coverage.py` | #115 |
| 2c | `dev/scripts/sbs/archive/extractor.py` + `upload.py` | #110 |

Note: Wave 2a and 2c both touch `upload.py` -- agents 2a and 2c must target non-overlapping functions (`ensure_porcelain()` vs `archive_upload()` call site). If overlap risk is too high, run 2c after 2a completes.

## Issue Closure Plan

After all waves complete and gates pass:
- Close: #97, #115, #110, #116, #112, #113
- Close or update: #111, #114 (based on Wave 0b investigation findings)
- Already closed in Wave 0a: #98, #102
