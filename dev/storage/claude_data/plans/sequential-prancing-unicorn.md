# Plan: In-Loop Introspection for /converge (#176)

## Summary

Add autonomous introspection inside the convergence loop and L3 meta-analysis after report. The loop transforms from `Eval → Fix → Rebuild` to `Eval → Fix → Introspect → Rebuild`, giving the loop memory across iterations.

## Files Modified

| File | Change |
|------|--------|
| [SKILL.md](.claude/skills/converge/SKILL.md) | Major: restructure loop, add 2 new phases, update all reference sections |
| [CLAUDE.md](CLAUDE.md:293-301) | Minor: update workflow line |

Single `sbs-developer` agent — this is markdown editing only.

## Changes

### 1. Header (line 11)

`build -> evaluate -> fix -> rebuild -> re-evaluate` becomes `build -> evaluate -> fix -> introspect -> rebuild -> re-evaluate`

### 2. Setup Phase (line 84)

Add initialization of adaptation notes: clear/create `dev/storage/<project>/adaptation_notes.json`

### 3. Fix-N Phase (lines 165-204)

- **Remove rebuild** (step 4, lines 196-198) — moves to new Rebuild-N phase
- **Add step 0**: Load adaptation notes from prior iterations. For N > 1, pass adaptation context (persistent failures, recommended strategies) to fix agents
- **Change transition** from `eval-(N+1)` to `introspect-N`

### 4. NEW: Introspect-N Phase (insert after Fix-N)

Fully autonomous, no user interaction.

**Actions:**
1. Load `adaptation_notes.json` + `qa_ledger.json` for current and prior iterations
2. **Failure differential** (N > 1): resolved, persistent, new regressions
3. **Strategy assessment**: Why persistent failures resist fixes, what to try next
4. **Produce outputs**:
   - `sbs_improvement_capture()` — concise observation of iteration
   - `sbs_issue_log()` — ONLY for bugs transcending the convergence run
   - Write adaptation notes to `dev/storage/<project>/adaptation_notes.json`

**Transition:** `introspect-N` → `rebuild-N`

### 5. NEW: Rebuild-N Phase (insert after Introspect-N)

Extracted from Fix-N. Rebuild via `sbs_build_project`. Build failure → `sbs_skill_fail`.

**Transition:** `rebuild-N` → `eval-(N+1)`

### 6. Report Phase (lines 208-233)

Replace `sbs_skill_end` with conditional L3 handoff:
- Glob `dev/storage/archive/summaries/*.md`
- If 2+ L2 docs: `sbs_skill_handoff(from="converge", to="introspect", substate="ingestion")` → run L3 phases → `sbs_skill_end(skill="introspect")`
- If < 2 L2 docs: report skip, `sbs_skill_end(skill="converge")`

### 7. Updated Substates Table (lines 268-280)

```
setup → eval-1 → fix-1 → introspect-1 → rebuild-1 → eval-2 → fix-2 → introspect-2 → rebuild-2 → eval-3 → report → (L3 handoff or end)
```

### 8. Recovery Semantics (lines 247-265)

Add entries for `introspect-N` (re-read adaptation_notes + qa_ledger, regenerate outputs) and `rebuild-N` (re-run build, idempotent).

### 9. Error Handling (lines 296-307)

Add: adaptation notes corrupt (delete + regenerate), introspection tool failures (non-fatal, continue), rebuild failure (sbs_skill_fail), L3 handoff failure (graceful fallback), L3 insufficient data (skip, not failure).

### 10. Safety Mechanisms (lines 236-243)

Add: introspection is non-blocking — tool failures never halt the loop.

### 11. Tool Reference + Anti-Patterns

Add `sbs_improvement_capture`, `sbs_skill_handoff` to tool table. Add anti-patterns: don't log every failure as issue, don't block on introspection failures, don't ignore adaptation notes.

### 12. CLAUDE.md (line 299)

`Setup → [Eval → Fix → Rebuild]×N → Report` becomes `Setup → [Eval → Fix → Introspect → Rebuild]×N → Report → L3`

## Adaptation Notes Schema

File: `dev/storage/<project>/adaptation_notes.json`

```json
{
  "version": "1.0",
  "project": "<project>",
  "iterations": [
    {
      "iteration": 1,
      "timestamp": "<ISO>",
      "eval_pass_rate": 0.72,
      "resolved": [],
      "persistent": [],
      "regressions": [],
      "strategy_notes": [
        {
          "criterion_id": "C-05",
          "category": "color",
          "current_strategy": "CSS variable update",
          "observation": "First attempt",
          "recommended_next": null
        }
      ],
      "improvement_captured": true,
      "issues_logged": []
    }
  ]
}
```

Append-only per run. Cleared at start of new `/converge` run. Survives compaction.

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  structural:
    - All substates in table match phase definitions
    - All transitions are consistent (no dangling references)
    - Recovery semantics cover every substate
    - Error handling covers every new failure mode
```

## Verification

1. Read both files end-to-end after edits — verify structural consistency
2. Run evergreen tests: `sbs_run_tests(tier="evergreen")`
3. Spot-check: grep for old transition targets (`eval-(N+1)` in Fix-N) to confirm removal
