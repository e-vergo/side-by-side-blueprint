# Self-Improve Agent: Background Autonomous Introspection

## Objective

Add a dedicated `sbs-self-improve` agent that runs autonomously in the background after every task session. Slim down `sbs-end-epoch` by removing its retrospective and alignment phases. Eliminate user-facing time on introspection entirely.

## Architecture

```
Task completes → orchestrator spawns sbs-self-improve in background →
  agent calls sbs_self_improve() MCP tool →
  MCP tool computes level, assembles context (entries, session transcript, issues) →
  agent analyzes, logs issues via sbs_issue_log, writes findings →
  (if higher levels triggered: cascading L1→L0, L2→L1→L0, etc.)
```

### Hierarchical Levels

| Level | Trigger | Input | Output |
|-------|---------|-------|--------|
| L0 | Every task session | Session transcript + recent entries | Session findings + issue logs |
| L1 | Every 4 L0s | All L0 findings since last L1 | Pattern synthesis document |
| L2 | Every 16 tasks (4 L1s) | All L1 documents since last L2 | Meta-analysis document |
| L(N) | Every 4^N tasks | All L(N-1) documents | Higher-order synthesis |

**Cascading:** L1 runs L0 first, then synthesizes. L2 runs L1 (which runs L0), then synthesizes. Full tree traversal.

**Multiplier:** Default 4x, configurable. Stored as constant in `sbs_self_improve()` MCP tool.

### Level Computation

Tag-based queries in DuckDB. Each self-improve archive entry gets a `"level:L0"` / `"level:L1"` / etc. tag.

```python
def compute_self_improve_level(self) -> int:
    """Count L0 entries since last L1, L1 entries since last L2, etc."""
    # Count L0s since last L1 → if >= multiplier, level is at least 1
    # Count L1s since last L2 → if >= multiplier, level is at least 2
    # Continue until count < multiplier
```

This lives in `duckdb_layer.py` alongside existing `entries_since_self_improve()`.

### Trigger Mechanism

The orchestrator (CLAUDE.md protocol) spawns `sbs-self-improve` at the end of every `/task` session, immediately after the task's archive upload. The agent runs in the background — the orchestrator does not wait for it.

For the future VSCode extension: the extension observes task completion and spawns the self-improve agent automatically. The trigger lives in the orchestration layer, not in Python code.

---

## What Changes

### New Files
1. `.claude/agents/sbs-self-improve.md` — Agent definition
2. `SelfImproveContext` model in `sbs_models.py` — Context blob

### Modified Files
1. `skill_tools.py` — Add `sbs_self_improve()` context fetcher tool
2. `sbs_models.py` — Add `SelfImproveContext` model
3. `duckdb_layer.py` — Add `compute_self_improve_level()` method
4. `sbs-end-epoch.md` — Remove Phase 1 (retrospective) and Phase 2 (alignment dialogue), keep Phase 3 (doc refresh) only
5. `CLAUDE.md` — Add self-improve trigger protocol, update capability table
6. `SLS_EXTENSION.md` — Add self-improve as background auto-trigger
7. `Archive_Orchestration_and_Agent_Harmony.md` — Update agent roster

### Preserved (Unchanged)
- `sbs_introspect()` MCP tool — kept for manual deep analysis
- `entries_since_self_improve()` in DuckDB — still works, now feeds L0
- `improvement_review()` in DuckDB — still works
- Archive upload pipeline — unchanged
- All other agents and tools

---

## Implementation Waves

### Wave 1: MCP Layer (2 parallel agents)

**Agent 1** — `sbs_models.py` + `skill_tools.py`

Add `SelfImproveContext` model:
```python
class SelfImproveContext(BaseModel):
    level: int  # Computed level (0, 1, 2, ...)
    multiplier: int  # Current multiplier (default 4)
    session_transcript_path: Optional[str]  # Path to JSONL for L0
    entries_since_last_level: List[Dict]  # Entries at current level
    lower_level_findings: List[str]  # Paths to L(N-1) finding docs
    open_issues: List[Dict]  # Open GitHub issues for correlation
    improvement_captures: List[Dict]  # IO() captures since last run
    archive_state: Dict  # Current archive state
```

Add `sbs_self_improve()` tool in `skill_tools.py`:
- Calls `db.compute_self_improve_level()` to determine level
- For L0: locates latest session JSONL via extractor
- For L1+: locates L(N-1) finding documents in `dev/storage/archive/self-improve/`
- Fetches open issues for correlation
- Returns `SelfImproveContext`

**Agent 2** — `duckdb_layer.py`

Add `compute_self_improve_level()`:
- Query entries with `"self-improve"` trigger and `"level:LN"` tags
- Count L0s since last L1, L1s since last L2, etc.
- Return highest level where count >= multiplier
- Configurable multiplier parameter (default 4)

**Gate:** MCP tests pass (`sbs_run_tests(repo="mcp")`).

### Wave 2: Agent Definitions (2 parallel agents)

**Agent 1** — `.claude/agents/sbs-self-improve.md`

Create the agent definition:
- **L0 workflow:** Read session transcript → extract patterns (errors, retries, misunderstandings, friction) → correlate with open issues → correlate with recent archive entries → log issues via `sbs_issue_log` → write L0 finding to `dev/storage/archive/self-improve/L0-<entry-id>.md` → archive upload
- **L1 workflow:** Run L0 first → read all L0 findings since last L1 → synthesize patterns across sessions → identify recurring themes → write L1 finding → archive upload
- **L2+ workflow:** Run L(N-1) first (which cascades) → read all L(N-1) findings → meta-analyze → write L(N) finding → archive upload
- **Autonomous:** No `AskUserQuestion`. No user interaction. Logs issues directly.
- **Background-safe:** Designed to run without orchestrator attention. Failure is silent (logged but doesn't block anything).

**Agent 2** — `.claude/agents/sbs-end-epoch.md`

Slim down:
- Remove Phase 1 (Deep Retrospective) entirely — now handled by L0/L1 self-improve
- Remove Phase 2 (Alignment Dialogue) entirely — user doesn't want to burn time on this
- Phase 3 (Documentation Refresh) becomes the entire workflow
- Remove "Four Pillars Framework" section — moved to self-improve agent
- Remove "L3+ Meta-Analysis" section — moved to self-improve agent
- Keep: README staleness check, README updates, core doc sync, oracle regen, stale file detection, git porcelain, archive upload

**Gate:** No references to retrospective or alignment dialogue in `sbs-end-epoch.md`. Self-improve agent has complete hierarchy description. Grep for orphaned references.

### Wave 3: Documentation (2 parallel agents)

**Agent 1** — `CLAUDE.md`

- Add `sbs_self_improve` to capability tools table
- Add `sbs-self-improve` to agent table
- Add trigger protocol: "After every `/task` session completes (success or failure), the orchestrator spawns `sbs-self-improve` in the background. Do not wait for completion."
- Update `sbs_end_epoch` / `/end-epoch` description: remove retrospective/alignment references
- Remove `sbs_introspect` / `/introspect` from primary workflow (keep as manual tool)

**Agent 2** — `SLS_EXTENSION.md` + `Archive_Orchestration_and_Agent_Harmony.md`

- `SLS_EXTENSION.md`: Add self-improve as auto-triggered background agent (no button — runs automatically). Update End Epoch button description (no retrospective). Note: extension observes task completion event and auto-triggers.
- `Archive_Orchestration_and_Agent_Harmony.md`: Update agent roster, remove retrospective from end-epoch workflow diagram, add self-improve agent description.

**Gate:** Grep for orphaned introspect/retrospective references in living docs.

---

## Key Files

| File | Path | Role |
|------|------|------|
| skill_tools.py | `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/skill_tools.py` | New `sbs_self_improve()` tool (~line 911) |
| sbs_models.py | `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` | New `SelfImproveContext` model |
| duckdb_layer.py | `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/duckdb_layer.py` | New `compute_self_improve_level()` (~line 892) |
| sbs-self-improve.md | `.claude/agents/sbs-self-improve.md` | New agent definition |
| sbs-end-epoch.md | `.claude/agents/sbs-end-epoch.md` | Slim down (remove phases 1+2) |
| CLAUDE.md | `CLAUDE.md` | Trigger protocol, capability table |
| SLS_EXTENSION.md | `dev/markdowns/permanent/SLS_EXTENSION.md` | Auto-trigger spec |
| Archive_Orchestration | `dev/markdowns/permanent/Archive_Orchestration_and_Agent_Harmony.md` | Agent roster update |

## Reusable Code

- `entries_since_self_improve()` at [duckdb_layer.py:823](forks/sbs-lsp-mcp/src/sbs_lsp_mcp/duckdb_layer.py#L823) — feeds L0 context
- `improvement_review()` at [duckdb_layer.py:893](forks/sbs-lsp-mcp/src/sbs_lsp_mcp/duckdb_layer.py#L893) — surfaces IO captures
- `_get_archive_state_dict()` in skill_tools.py — reusable context helper
- `_fetch_github_issues()` in skill_tools.py — reusable issue fetcher
- `get_sbs_project_dirs()` at [extractor.py:32](dev/scripts/sbs/archive/extractor.py#L32) — session JSONL location
- Existing `IntrospectContext` model — structural reference for `SelfImproveContext`

---

## Verification

1. **MCP tests pass:** `sbs_run_tests(repo="mcp")` — 208+ tests
2. **Evergreen tests pass:** `sbs_run_tests(tier="evergreen")` — 715+ pass, 4 known failures
3. **New tool callable:** `sbs_self_improve()` returns valid `SelfImproveContext` with computed level
4. **Level computation correct:** With 0 prior L0s → level 0. With 4 L0s and 0 L1s → level 1. Etc.
5. **End-epoch slimmed:** `sbs-end-epoch.md` has no retrospective or alignment dialogue
6. **Self-improve complete:** Agent def has L0/L1/L2+ workflows, autonomous issue logging, no user interaction
7. **No orphaned refs:** Grep for "retrospective" in end-epoch, "sbs_introspect" as primary workflow in CLAUDE.md
8. **Findings directory exists:** `dev/storage/archive/self-improve/` created (or documented as auto-created by agent)
