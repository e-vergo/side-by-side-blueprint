# Task: Batch Issue Crush (10 issues)

**Branch:** `task/batch-devtools-fixes`
**Issues:** #129, #126, #123, #121, #127, #125, #124, #122, #114, #111

## Wave Structure

| Wave | Agents | Issues | Files |
|------|--------|--------|-------|
| 0 | 1 | #129, #126 | `sbs_self_improve.py`, `test_self_improve.py` |
| 1 | 1 | #123 | `registry.py` |
| 2 | 2 parallel | #127, #125, #122, #124 | A: `SKILL.md`, B: `sbs-developer.md` |
| 3 | 1 | #121 | `session_profiler.py` |
| 4 | 2 parallel | #114, #111 | A: `upload.py`, B: `runner.py` |

**Total:** 5 waves, 7 agent invocations, max 2 concurrent.

---

## Wave 0: DateTime Bugs (#129, #126)

**Agent:** 1 `sbs-developer`
**Files:**
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_self_improve.py`
- `dev/scripts/sbs/tests/pytest/test_self_improve.py`

**Changes:**
1. Add `_parse_timestamp(s: str) -> datetime` helper that normalizes any ISO string to timezone-aware UTC (appends `+00:00` when no tzinfo present)
2. In `_build_skill_intervals()` (~line 1400) and `_correlate_with_archive()` (~line 1455): use `_parse_timestamp` instead of raw `fromisoformat`
3. In `sbs_question_analysis_impl()` (~line 1499) and `sbs_question_stats_impl()` (~line 1569): convert `since`/`until` to aware datetimes at function entry, compare as datetimes not strings
4. Fix `test_tag_effectiveness_classifies_noise` test data: verify entry_id/created_at consistency and monkeypatch ordering

**Validation:** `sbs_run_tests(filter="test_self_improve")`

---

## Wave 1: Module Caching (#123)

**Agent:** 1 `sbs-developer`
**File:** `dev/scripts/sbs/tests/validators/registry.py`

**Changes:**
1. Add `clear()` method to `ValidatorRegistry`
2. Add `force_reload: bool = False` param to `discover_validators()`
3. When `force_reload=True`: call `registry.clear()`, then `importlib.reload()` on any module already in `sys.modules` before importing

**Validation:** `sbs_run_tests(filter="test_validator")`

---

## Wave 2: Guidance Prose (#127, #125, #124, #122)

**Agent A** (SKILL.md): #127, #125, #122
**Agent B** (sbs-developer.md): #124, #122

**Agent A changes to `.claude/skills/task/SKILL.md`:**
1. **#127** -- After Phase 3 agent concurrency note (~line 204): add "Triage Wave Structure" subsection. Group by operation type (investigate -> docs -> code), not issue number. Uniform-complexity waves complete more predictably.
2. **#125** -- After Validators section (~line 452): add "Test Cleanup on Feature Removal" subsection. When a plan removes a feature, automatically include a step to grep tests for references and update/remove stale assertions.
3. **#122** -- Expand Phase 1 agent concurrency note (~line 98): when spawning multiple exploration agents, each must have a distinct investigation dimension. Single-question explorations use 1 agent. No redundant confirmation of the same fact.

**Agent B changes to `.claude/agents/sbs-developer.md`:**
1. **#124** -- After Info Gathering Protocol (~line 48): add "Call-Chain Tracing" subsection. When investigating feature correctness, trace from entry point to output. Verifying function existence is necessary but not sufficient -- verify it's reachable.
2. **#122** -- In Info Gathering Protocol: distinguish "orientation exploration" (oracle, outline -- cheap, do first) from "deep exploration" (read, grep, hover -- targeted based on orientation results).

**Validation:** Manual review (prose only).

---

## Wave 3: Auto-Tagger Discrimination (#121)

**Agent:** 1 `sbs-developer`
**File:** `dev/storage/tagging/hooks/session_profiler.py`

**Changes:**
1. **Session-type tags** (lines ~122-130): Make mutually exclusive. Compute ratios for exploration/edit/creation, emit only the dominant one via `max()`.
2. **Tool-dominance tags** (lines ~131-164): Make mutually exclusive. Among bash-heavy/mcp-heavy/search-heavy/delegation-heavy, emit only the winner.
3. Keep orthogonal dimension tags (session length, interactivity) non-exclusive -- these describe independent features.

**Validation:** `sbs_run_tests(filter="test_auto_tag or test_session")`

---

## Wave 4: Silent Failure Hardening (#114, #111)

**Agent A** -- `dev/scripts/sbs/archive/upload.py`
**Agent B** -- `dev/scripts/sbs/tests/validators/runner.py`

**Agent A changes:**
1. `_load_quality_scores()` (~line 304): When `ledger.scores` is empty, log warning and return empty dict `{}` instead of `None` so consumers distinguish "no scores" from "never attempted"
2. `should_validate` (~line 451): Also validate on finalization transitions (`state_transition == "phase_start"` and `substate == "finalization"`)
3. Gate validation (~line 526): Ensure archive entry is saved even on gate failure (currently returns early without saving)

**Agent B changes:**
1. Heuristic skip (~line 284): Add skipped validators to `runner_result.warnings` list for traceability
2. Validator exceptions (~line 298): Create a `ValidatorResult(passed=False, score=0)` and add to results dict so exceptions produce score entries, not gaps
3. Add `warnings: list[str]` field to `RunnerResult` if not present

**Validation:** `sbs_run_tests(tier="evergreen")`

---

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  regression: >= 0
```

Per-wave validation runs after each wave. Final gate runs full evergreen suite.

---

## Issue Closure Plan

| Issue | Closes When |
|-------|-------------|
| #129 | All 3 test_self_improve tests pass |
| #126 | `sbs_question_stats()` returns without TypeError |
| #123 | `discover_validators(force_reload=True)` reloads edited modules |
| #121 | Session profiler emits mutually exclusive tags |
| #127 | Triage wave prose in SKILL.md |
| #125 | Feature removal prose in SKILL.md |
| #124 | Call-chain tracing prose in sbs-developer.md |
| #122 | Exploration differentiation prose in both files |
| #114 | Gate failures produce archive entries; finalization errors are visible |
| #111 | Validator exceptions produce score entries; finalization triggers validation |

---

## Verification

1. `sbs_run_tests(tier="evergreen")` -- 100% pass
2. `sbs_question_stats()` via MCP -- no datetime error
3. Manual check: session_profiler.py produces at most 1 session-type tag and 1 tool-dominance tag per entry
4. Manual check: SKILL.md and sbs-developer.md have new guidance sections
