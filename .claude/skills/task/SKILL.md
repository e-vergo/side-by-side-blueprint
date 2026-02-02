---
name: task
description: General-purpose agentic task execution with validation
disable-model-invocation: true
version: 3.0.0
---

# /task - Agentic Task Workflow

## Invocation

User triggers `/task` with a task description.

---

## Mandatory Archive Protocol

**This is not optional. Violations break the skill contract.**

### First Action on Invocation

Before doing ANYTHING else:

1. Call `sbs_archive_state()` via MCP
2. Check `global_state` field:
   - `null` → Fresh task, proceed to alignment
   - `{skill: "task", substate: X}` → Resume from substate X
   - `{skill: "other", ...}` → Error: state conflict, do NOT proceed

### Phase Transitions

Every phase change MUST execute:

```bash
sbs archive upload --trigger skill \
  --global-state '{"skill":"task","substate":"<phase>"}' \
  --state-transition phase_start
```

Phases: `alignment` → `planning` → `execution` → `finalization`

### Ending the Task

Final archive call clears state:

```bash
sbs archive upload --trigger skill \
  --state-transition phase_end
```

This sets `global_state` to `null`, returning system to idle.

---

## Phase 1: Alignment (Q&A)

Questions should cover:
- Task scope, boundaries, methods brainstorming
- Success criteria
- Validation requirements
- Affected repositories

**REQUIRED:** After completing alignment, transition to planning:

```bash
sbs archive upload --trigger skill \
  --global-state '{"skill":"task","substate":"planning"}' \
  --state-transition phase_start
```

---

## Phase 2: Planning

User moves chat to plan mode. Claude presents:
1. Task breakdown into waves/agents
2. Validator specifications per wave
3. Success criteria mapped to ledger checks
4. Estimated scope (files, repos, complexity)

### Gate Definition (REQUIRED)

Every plan MUST include a `gates:` section in YAML format:

```yaml
gates:
  tests: all_pass | <threshold>    # Test requirements
  quality:                          # Quality score requirements
    T5: >= 0.8
    T6: >= 0.9
  regression: >= 0                  # No regression allowed
```

Plans without gates are incomplete. Define appropriate gates based on task scope.

**REQUIRED:** After plan approval, transition to execution:

```bash
sbs archive upload --trigger skill \
  --global-state '{"skill":"task","substate":"execution"}' \
  --state-transition phase_start
```

---

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

**REQUIRED:** After all waves complete and gates pass, transition to finalization:

```bash
sbs archive upload --trigger skill \
  --global-state '{"skill":"task","substate":"finalization"}' \
  --state-transition phase_start
```

---

## Metric Gates

### Enforcement

Before transitioning to finalization:

1. Call `sbs_validate_project` MCP tool with validators specified in plan
2. Call `sbs_run_tests` MCP tool with specified filters
3. Compare results to gate thresholds defined in plan
4. **If ANY gate fails:**
   - Do NOT proceed to finalization
   - Report all findings with specific failures
   - Ask user: "Gate failed. Approve to continue anyway, or abort?"
   - Wait for explicit approval before continuing

### Gate Failure Response

On failure, report:
- Which gate(s) failed
- Expected vs actual values
- Specific test/validator failures
- Suggested remediation

User can:
- Approve continuation (override gate)
- Request retry (fix issues, re-validate)
- Abort task (clear state, return to idle)

**Gate failures MUST pause execution.** Automatic continuation is a skill contract violation.

---

## Phase 4: Finalization

1. Run full validation suite
2. Update unified ledger
3. Generate summary report
4. Commit final state

**REQUIRED:** After finalization completes, clear state:

```bash
sbs archive upload --trigger skill \
  --state-transition phase_end
```

---

## Phase 5: Documentation Cleanup (MANDATORY)

**Execution is NOT complete until this phase runs.**

Invoke `/update-and-archive` as the final step. This:
1. Refreshes all repository READMEs in parallel waves
2. Synchronizes core documentation (ARCHITECTURE.md, CLAUDE.md, GOALS.md, README.md)
3. Ensures documentation reflects the changes made during execution

This phase cannot be skipped. The `/task` skill is considered incomplete until `/update-and-archive` completes successfully.

---

## Recovery Semantics

### Compaction Survival

If context compacts mid-task:

1. New context queries `sbs_archive_state()`
2. Reads current `global_state.substate`
3. Resumes from **start** of that substate

### Substate Resume Behavior

| Substate | Resume Action |
|----------|---------------|
| `alignment` | Re-ask clarifying questions |
| `planning` | Read plan file, continue planning |
| `execution` | Check wave completion, resume incomplete waves |
| `finalization` | Re-run validators, re-check gates |

### Execution Wave Recovery

During `execution` substate, determine wave completion by checking BOTH:
1. **Commit evidence**: Check `repo_commits` field in archive entries for expected commits
2. **Artifact existence**: Verify expected output files exist (e.g., `_site/`, test reports)

A wave is only considered complete if BOTH checks pass. This belt-and-suspenders approach prevents:
- False positives from stale artifacts
- False positives from commits without successful builds

Only re-run waves that fail either check.

### State Conflict

If `global_state.skill != "task"`:
- Another skill owns the state
- Do NOT proceed
- Report error: "State conflict: skill '<other_skill>' currently owns global state"
- Wait for user resolution

---

## Substates

The task skill has four substates, tracked in the archive:

| Substate | Description | Transition |
|----------|-------------|------------|
| `alignment` | Q&A phase, clarifying requirements | → planning |
| `planning` | Designing implementation approach | → execution |
| `execution` | Agents running, validators checking | → finalization |
| `finalization` | Full validation, summary generation | → (triggers /update-and-archive) |

Each substate transition archives state with `state_transition: "phase_start"` for the incoming phase. Only the final transition uses `phase_end` to clear global state.

---

## Validators

Specify validators in plan:

```yaml
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

---

## Error Handling

- Agent failure: retry once, then pause
- Validation failure: pause for re-approval with findings
- Build failure: halt, report, wait for user
- Gate failure: pause for user approval (NEVER auto-continue)
- State conflict: halt, report, wait for user resolution

---

## Summary Report

After completion:
- Agents spawned: N
- Validation passes: X/Y
- Build metrics: timing, commits, diffs
- Failures: list with causes
- Gates: all pass/fail status with values

---

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
