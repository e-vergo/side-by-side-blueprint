# Fix sbs_skill_stats Inaccurate Completion Rates (#76)

## Problem

`_group_entries_by_skill_session()` in `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_self_improve.py:71-148` has two bugs:

1. **`phase_end` entries have `global_state: null`** -- they hit the "no skill" branch (line 87) which closes sessions WITHOUT setting `completed = True`. Completion detection on line 120 is unreachable.

2. **Regular entries with `global_state: null` during active sessions** -- 85 such entries fragment 33 real task sessions into ~47, inflating invocation counts.

Result: 0% completion rate reported vs actual ~73%.

## Fix: Rewrite `_group_entries_by_skill_session()`

### File
`forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_self_improve.py`

### New Algorithm

```
for each entry (sorted by entry_id):
    1. Check state_transition FIRST (before global_state)
       - "phase_end" → mark current session completed, close it

    2. Extract skill from global_state
       - If no skill AND no state_transition → skip (don't fragment session)

    3. If "phase_start":
       - Same skill as current session → track phase, continue session
       - Different skill or no session → close current, start new session

    4. If entry has skill matching current session → add to session

    5. If entry has different skill (no phase_start) → close current, start new
```

Key changes from current logic:
- `phase_end` checked BEFORE `global_state.skill` extraction
- Null-state entries during active sessions are absorbed, not session-ending
- `SkillSession` gets a `last_substate: str` field for failure location tracking

### Model Change

Add to `SkillSession` dataclass (line 46-56):
```python
last_substate: str = ""  # Where incomplete sessions stopped
```

### Consumers (no changes needed)

All 6 callers use `_group_entries_by_skill_session()` identically -- they iterate sessions and check `.completed`. The fix is transparent:
- `sbs_skill_stats_impl` (line 247) -- already uses `common_failure_substates`
- `sbs_phase_transition_health_impl` (line 334)
- `sbs_interruption_analysis_impl` (line 446)
- `sbs_gate_failures_impl` (line 555)
- `sbs_tag_effectiveness_impl` (line 674)

### `sbs_skill_stats_impl` Enhancement

Update failure mode tracking (lines 278-288) to use `last_substate` from the session directly, rather than parsing the last entry's global_state (which is often null for incomplete sessions).

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  regression: >= 0
```

## Verification

1. After fix, call `sbs_skill_stats(as_findings=True)` via MCP
2. Verify task completion rate is ~73% (not 0%)
3. Verify session counts match: ~33 task, ~27 update-and-archive, ~6 self-improve
4. Verify incomplete sessions report their failure substate
5. Run evergreen tests: `pytest sbs/tests/pytest -m evergreen`
