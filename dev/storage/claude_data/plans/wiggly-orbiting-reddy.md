# Task: Batch Issue Resolution (15 Issues, 3 Waves)

**Branch:** `task/batch-10-issues`
**Issues:** #32, #33, #16, #11, #15, #18, #22, #23, #24, #25, #26, #45, #7, #12, #10
**Already closed:** #6, #9 (resolved prior to this task)
**Deferred:** #1 (Verso PDF -- long-term feature, kept open)

---

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
```

**Baseline:** 467 passed, 0 failed, 38 skipped (0.69s)
**Gate enforcement:** Run after each wave. 0 failures required to proceed.

No T1-T8 quality validators -- no visual/build/CSS changes in scope.

---

## Wave 1: Infrastructure Fixes

**Issues:** #32, #33, #16, #11, #15, #18
**Scope:** 7 files modified + test updates

### #32 -- Strict gate validation

| Change | File | Detail |
|--------|------|--------|
| Fix pytest path | `dev/scripts/sbs/archive/gates.py:95-101` | Replace `/opt/homebrew/bin/pytest` with `sys.executable, "-m", "pytest"` |
| Fix python path | `gates.py:157-161` | Replace `/opt/homebrew/bin/python3` with `sys.executable` |
| Remove --force (4 sites) | `gates.py:228,238-239` | Remove `force` param + early return |
| | `dev/scripts/sbs/cli.py:477-481` | Remove `--force` argument |
| | `dev/scripts/sbs/archive/upload.py:250,383` | Remove `force` param + usage |
| Missing score = FAIL | `gates.py:209-211` | Set `all_passed = False` when `score_data is None` |

**Tests:** Update `test_gates.py` -- remove force-flag tests, add `test_missing_score_fails_quality_gate`.

### #33 -- Add `added_at` field

| File | Change |
|------|--------|
| `dev/scripts/sbs/archive/entry.py` | Add `added_at: Optional[str] = None` + serialization |
| `dev/scripts/sbs/archive/upload.py` | Set `added_at = datetime.now(timezone.utc).isoformat()` on creation |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_self_improve.py` | Use `added_at` (fallback `created_at`) in time queries |

**Tests:** Update `test_archive_invariants.py` roundtrip test to include `added_at`.

### #16 -- Fix editing-heavy threshold

| File | Change |
|------|--------|
| `dev/storage/tagging/hooks/session_quality.py:42` | Replace `total_edits > 20` with `total_calls > 50 and total_edits / total_calls > 0.5` |

### #11 -- PR creation before first commit

| File | Change |
|------|--------|
| `.claude/skills/task/SKILL.md:156-162` | Insert step: `git commit --allow-empty -m "chore: initialize task branch"` before PR creation |

### #15 -- Quality score auto-population

| File | Change |
|------|--------|
| `dev/scripts/sbs/archive/upload.py` | After entry creation, if `trigger=="build"` and `quality_scores is None`, run T5+T6 validators and populate |

### #18 -- Python tracebacks (subsumed by #32)

Root cause (wrong python path) fixed by #32. No additional changes.

**Wave 1 gate:** `pytest evergreen` -- all pass, 0 fail.

---

## Wave 2: Self-Improve MCP Enhancement

**Issues:** #22, #23, #24, #25, #26, #45
**Scope:** 4 new MCP tools + models + SKILL.md update

### New models (`sbs_models.py`, after line 613)

| Model | For Issue | Fields |
|-------|-----------|--------|
| `SuccessPattern` + `SuccessPatterns` | #22 | pattern_type, description, evidence |
| `DiscriminatingFeature` + `ComparativeAnalysis` | #23 | feature, approved_value, rejected_value, counts |
| `SystemHealthReport` | #24 | build_timing_trends, tool_error_rates, archive_friction, findings |
| `UserPatternAnalysis` | #25 | avg_message_length, structured_vs_open, effective_patterns, findings |

### New impl functions (`sbs_self_improve.py`)

| Function | Issue | What it does |
|----------|-------|-------------|
| `sbs_successful_sessions_impl()` | #22 | Mines low-rejection sessions, first-try approvals, fast alignments |
| `sbs_comparative_analysis_impl()` | #23 | Groups approved vs rejected plans, identifies discriminating features |
| `sbs_system_health_impl()` | #24 | Build timing trends, tool error rates, archive friction |
| `sbs_user_patterns_impl()` | #25 | Message length analysis, structured vs open requests, effective patterns |

### MCP tool registration (`sbs_tools.py`)

4 new `@mcp.tool()` definitions following existing patterns.

### #26 -- Rebalance discovery

Update `.claude/skills/self-improve/SKILL.md` discovery phase: require minimum 1 finding per pillar before proceeding to selection. Document absence explicitly if a pillar yields nothing.

### #45 -- Umbrella

Closes when #22-#26 close. No code changes.

**Tests:** Add `TestNewAnalysisFunctions` class in `test_self_improve.py` (dev tier) with 4 tests validating return types.

**Wave 2 gate:** `pytest evergreen` -- all pass, 0 fail.

---

## Wave 3: Submodule Workflow

**Issues:** #7, #12, #10
**Scope:** 2 files modified

### #7 + #12 -- Storage chasing pattern (duplicates)

| File | Change |
|------|--------|
| `dev/scripts/sbs/archive/upload.py:137-159` | Refactor `ensure_porcelain()`: Phase 1 collects all dirty repos, Phase 2 commits+pushes all. Same behavior, clearer structure, enables future batching. |

### #10 -- Submodule workflow documentation

| File | Change |
|------|--------|
| `CLAUDE.md` | Add "Submodule Commit Workflow" section under Cross-Repo Editing explaining the commit-inside-then-update-pointer pattern |

**Wave 3 gate:** `pytest evergreen` -- all pass, 0 fail.

---

## Verification

After all waves:

1. **Final gate:** `sbs_run_tests(tier="evergreen")` -- 467+ passed, 0 failed
2. **Spot checks:**
   - `grep -r "force" dev/scripts/sbs/archive/gates.py` returns nothing
   - `grep -r "/opt/homebrew" dev/scripts/sbs/archive/gates.py` returns nothing
   - `python3 -c "from sbs.archive.entry import ArchiveEntry; e = ArchiveEntry.__dataclass_fields__; assert 'added_at' in e"`
3. **Issue closure:** Close #7, #10, #11, #12, #15, #16, #18, #22, #23, #24, #25, #26, #32, #33, #45 (15 issues)
4. **PR merge** via `sbs_pr_merge`
5. **Invoke `/update-and-archive`**

---

## Summary

| Metric | Value |
|--------|-------|
| Issues resolved | 15 |
| Waves | 3 |
| Files modified | ~12 |
| New MCP tools | 4 |
| New models | 6 |
| Gate metric | pytest evergreen: all_pass |
| New tests | ~5-7 (mostly dev tier) |
