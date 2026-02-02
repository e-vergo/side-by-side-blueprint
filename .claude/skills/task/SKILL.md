---
name: task
description: General-purpose agentic task execution with validation
disable-model-invocation: true
version: 2.0.0
---

# /task - Agentic Task Workflow

## Invocation

User triggers `/task` with a task description.

## Phase 1: Alignment (Q&A)

Questions should cover:
- Task scope, boundaries, methods brainstorming
- Success criteria
- Validation requirements
- Affected repositories

## Phase 2: Planning

User moves chat to plan mode. Claude presents:
1. Task breakdown into waves/agents
2. Validator specifications per wave
3. Success criteria mapped to ledger checks
4. Estimated scope (files, repos, complexity)

## Phase 3: Execution

Fully autonomous:
1. Execute agents sequentially (one at a time) for code changes
2. **Exception: Documentation-only waves** - Agents can run in parallel when:
   - No code is being modified (only README/docs)
   - No collision risk between agents
   - Spawn all wave agents in a SINGLE message with multiple Task tool calls
3. After each agent/wave, run specified validators
4. If validation fails:
   - Retry failed agent once
   - If retry fails, pause for re-approval
5. Continue until all agents complete

## Phase 4: Finalization

1. Run full validation suite
2. Update unified ledger
3. Generate summary report
4. Commit final state

## Phase 5: Documentation Cleanup (MANDATORY)

**Execution is NOT complete until this phase runs.**

Invoke `/update-and-archive` as the final step. This:
1. Refreshes all repository READMEs in parallel waves
2. Synchronizes core documentation (ARCHITECTURE.md, CLAUDE.md, GOALS.md, README.md)
3. Ensures documentation reflects the changes made during execution

This phase cannot be skipped. The `/task` skill is considered incomplete until `/update-and-archive` completes successfully.

## Validators

Specify validators in plan:

```
validators:
  - visual: [dashboard, dep_graph, chapter]
  - timing: true
  - git_metrics: true
  - code_stats: [loc, file_counts]
```

Available validators:
- `visual-compliance` - AI vision validation of screenshots (category: visual)
- `timing` - Build phase timing metrics (category: timing)
- `git-metrics` - Commit/diff tracking (category: git)
- `code-stats` - LOC and file counts (category: code)

### Validator to T1-T8 Mapping

| Tests | Category | Type | Description |
|-------|----------|------|-------------|
| T1-T2 | CLI | Deterministic | CLI execution, ledger population |
| T3-T4 | Dashboard | AI Vision | Dashboard clarity, toggle discoverability |
| T5-T6 | Design | Deterministic | Status color match, CSS variable coverage |
| T7-T8 | Polish | AI Vision | Jarring-free check, professional score |

### Hybrid Compliance Pattern

The compliance validation uses a bidirectional agent-script pattern:

1. Agent runs `sbs compliance --project <name>`
2. Script computes which pages need validation, generates prompts with screenshot paths
3. Agent reads screenshots using vision capabilities, provides JSON validation response
4. Script updates `compliance_ledger.json` with results

**Why this pattern**: Scripts never call AI APIs. Agents never bypass scripts for state changes. This pattern satisfies both constraints while enabling AI-powered validation.

## Error Handling

- Agent failure: retry once, then pause
- Validation failure: pause for re-approval with findings
- Build failure: halt, report, wait for user

## Summary Report

After completion:
- Agents spawned: N
- Validation passes: X/Y
- Build metrics: timing, commits, diffs
- Failures: list with causes

## Implementation Notes

All builds must go through `python build.py` (never skip commits/pushes). The unified ledger at `dev/storage/unified_ledger.json` tracks all metrics across builds.

**Combined validation command:**
```bash
# Run combined compliance + quality check
sbs validate-all --project SBSTest
```

**Quality score ledger:**
- Location: `dev/storage/{project}/quality_ledger.json`
- Intelligent invalidation: repo changes mark affected scores stale
- Tracks T1-T8 metrics with pass/fail status and weights

To run validators programmatically:
```python
from sbs.validators import discover_validators, registry, ValidationContext

discover_validators()
validator = registry.get('visual-compliance')
result = validator.validate(context)
```

---

## Task Agent Model

When `/task` is invoked, the orchestration follows a specific model designed for comprehensive data collection and compaction survival.

### Center Stage Architecture

The `/task` invocation spawns a dedicated task agent that becomes "center stage":

- **Direct subordination**: The task agent is directly beneath the top-level chat, not a nested subagent
- **Single-agent constraint**: Only one task agent runs at a time (architectural invariant)
- **Compaction survival**: The agent reconstructs state from archive on context reset
- **Full awareness**: The agent knows it's being tracked by the archive system it's helping build

### State Tracking

Each phase transition creates an archive entry with:
- `global_state`: `{skill: "task", substate: <current_phase>}`
- `state_transition`: "phase_start" or "phase_end"

This enables:
1. Recovery after compaction (query archive for current state)
2. Comprehensive data collection for self-improvement
3. Clear audit trail of all development work

### Why This Model

All development work in this repository should go through `/task` because:
1. Comprehensive tracking in archival format
2. Structured phases ensure thorough execution
3. Validation gates catch issues early
4. Data enables recursive self-improvement of the tooling itself

---

## Substates

The task skill has four substates, tracked in the archive:

| Substate | Description | Transition |
|----------|-------------|------------|
| `alignment` | Q&A phase, clarifying requirements | → planning |
| `planning` | Designing implementation approach | → execution |
| `execution` | Agents running, validators checking | → finalization |
| `finalization` | Full validation, summary generation | → (triggers /update-and-archive) |

Each substate transition archives state with `state_transition: "phase_end"` for the outgoing phase and `state_transition: "phase_start"` for the incoming phase.
