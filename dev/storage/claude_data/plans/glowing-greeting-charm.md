# Task #65: Dedicated MCP Self-Improvement Tools

## Summary

Add 5 purpose-built MCP tools for the `/self-improve` skill, replacing ad-hoc archive queries with structured endpoints. Each tool returns raw analytics by default, with an optional `as_findings` parameter for discovery-phase integration.

## Files Modified

| File | Changes |
|------|---------|
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_self_improve.py` | 5 impl functions + shared helpers (~300 lines) |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` | 10 new Pydantic models (2 per tool) |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` | 5 MCP tool registrations (after line 2394) |
| `dev/scripts/sbs/tests/pytest/test_self_improve.py` | ~12 new test methods |
| `.claude/skills/self-improve/SKILL.md` | Tool inventory update |

## Shared Infrastructure

Before any tool, implement shared helpers in `sbs_self_improve.py`:

```python
@dataclass
class SkillSession:
    skill: str
    entries: List[ArchiveEntry]
    first_entry_id: str
    last_entry_id: str
    phases_visited: List[str]
    completed: bool
    start_time: Optional[str]
    end_time: Optional[str]

SKILL_PHASE_ORDERS = {
    "task": ["alignment", "planning", "execution", "finalization"],
    "self-improve": ["discovery", "selection", "dialogue", "logging", "archive"],
}

CORRECTION_KEYWORDS = ["correction", "redo", "retry", "revert", "wrong", "mistake",
                        "back to", "restart", "redirected", "changed approach", "pivot"]

def _group_entries_by_skill_session(entries) -> List[SkillSession]: ...
def _compute_session_duration(session) -> Optional[float]: ...
def _detect_backward_transitions(session, expected_order) -> List[Tuple]: ...
def _detect_skipped_phases(session, expected_order) -> List[str]: ...
```

## 5 Tools

### 1. `sbs_skill_stats` (implement first — validates session grouping)
- **Purpose:** Per-skill lifecycle metrics
- **Output model:** `SkillStatsResult` containing `Dict[str, SkillStatEntry]`
- **Key fields:** invocation_count, completion_count, completion_rate, avg_duration_seconds, common_failure_substates, common_failure_tags
- **Logic:** Group sessions by skill, compute counts/rates/durations, identify failure modes from incomplete sessions

### 2. `sbs_phase_transition_health` (adds transition helpers)
- **Purpose:** Transition pattern analysis
- **Output model:** `PhaseTransitionHealthResult` containing `List[PhaseTransitionReport]`
- **Key fields:** expected_sequence, backward_transitions, backward_details, skipped_phases, time_in_phase
- **Logic:** Compare actual transition sequences against `SKILL_PHASE_ORDERS`, detect backward/skipped phases, compute time-in-phase from timestamp diffs

### 3. `sbs_interruption_analysis` (uses sessions + transitions + keywords)
- **Purpose:** Detect user corrections/redirections
- **Output model:** `InterruptionAnalysisResult` containing `List[InterruptionEvent]`
- **Key fields:** event_type (backward_transition|retry|correction_keyword|high_entry_count), from_phase, to_phase, context
- **Detection:** Backward transitions, multiple entries in same substate (>2), notes with correction keywords, sessions with entry_count > 2x phase_count

### 4. `sbs_gate_failures` (independent, simple filter)
- **Purpose:** Gate validation failure patterns
- **Output model:** `GateFailureReport` containing `List[GateFailureEntry]`
- **Key fields:** total_gate_checks, total_failures, failure_rate, override_count, common_findings
- **Logic:** Filter entries with `gate_validation != null`, detect overrides (gate failed but task continued)
- **Note:** `gate_validation` may be sparse — tool handles this gracefully

### 5. `sbs_tag_effectiveness` (synthesizes multiple analyses)
- **Purpose:** Auto-tag signal-to-noise ratio
- **Output model:** `TagEffectivenessResult` containing `List[TagEffectivenessEntry]`
- **Key fields:** frequency, frequency_pct, co_occurs_with_gate_failure, co_occurs_with_backward_transition, signal_score, classification (signal|noise|neutral)
- **Logic:** Cross-reference auto-tags with gate failures, backward transitions, error notes; classify noise (>80% frequency) vs signal (>0.3 correlation)

## MCP Registration Pattern

All 5 follow the existing pattern (inserted after line 2394 in `sbs_tools.py`):
- `readOnlyHint=True`, `idempotentHint=True`, `openWorldHint=False`
- Accept optional `as_findings: bool = False` parameter
- Return `str` via `.model_dump_json(indent=2)`
- Lazy import from `.sbs_self_improve` inside function body

## Execution Plan

**Single wave** — one `sbs-developer` agent implements all 5 tools sequentially in the order above, since each builds on shared infrastructure from the previous.

**Steps:**
1. Add shared helpers (`SkillSession`, grouping logic, transition detection)
2. Add all 10 Pydantic models to `sbs_models.py`
3. Implement 5 `_impl()` functions in `sbs_self_improve.py`
4. Register 5 tools in `sbs_tools.py`
5. Add tests to `test_self_improve.py`
6. Update self-improve SKILL.md tool inventory

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  regression: >= 0
```

## Risks

- **`gate_validation` sparsity:** Few entries may have this field. Tool returns "0 of N entries had gate validation data" gracefully.
- **Session boundary ambiguity:** Orphaned sessions (no `phase_end`) are handled by closing session on skill change or new `phase_start`.
- **`issue_refs` type inconsistency:** `ArchiveEntry` declares `list[str]` but tests pass integers. Implementations handle both.
