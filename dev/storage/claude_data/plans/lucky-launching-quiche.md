# Plan: Rigidly Couple Skills to Archive System

## Goal

Update `/task` and `/update-and-archive` skills to enforce archive-based state tracking with hard gates that prevent completion until metrics pass.

---

## Alignment Summary

| Question | Decision |
|----------|----------|
| A) Archive calls required? | **Yes, 100% mandatory** |
| B) Metric gates? | **Flexible, defined in plan** |
| C) Recovery contract? | **Conservative resume from substate start** |
| D) Failure mode? | **Pause for approval** |

---

## Current Problems

1. **State tracking is aspirational** - Skill describes substates but doesn't enforce archive calls
2. **No metric gates** - Nothing prevents completion if tests fail
3. **Recovery is undefined** - No protocol for resuming after compaction
4. **Tags unused for control flow** - Tags exist but don't gate transitions

---

## Design: Mandatory Archive Protocol

### Phase Transitions MUST Use Archive

Every phase transition requires:
```bash
sbs archive upload --trigger skill \
  --global-state '{"skill":"task","substate":"<new_substate>"}' \
  --state-transition phase_start
```

**Violation = skill contract breach.** The skill file will state this explicitly.

### Recovery Protocol

On any `/task` invocation (fresh or resumed):

```
1. Call sbs_archive_state()
2. If global_state is null:
   → Fresh start, begin alignment phase
3. If global_state.skill == "task":
   → Resume from start of global_state.substate
   → For "execution": check wave completion via commits/artifacts
4. If global_state.skill != "task":
   → Error: another skill owns the state
```

### Metric Gates

The plan file defines success criteria. Before finalization:

```
1. Run validators specified in plan
2. Compare results to thresholds
3. If ANY gate fails:
   → Pause, report findings
   → User approves to continue OR abort
4. All gates pass → proceed to finalization
```

**Gate definition example (in plan):**
```yaml
gates:
  tests: all_pass           # All tests must pass
  quality: T5 >= 0.8        # Status color match ≥ 80%
  regression: delta >= 0    # No quality regression
```

---

## Critical Files

| File | Changes |
|------|---------|
| `.claude/skills/task/SKILL.md` | Rewrite with enforcement language |
| `.claude/skills/update-and-archive/SKILL.md` | Add archive protocol |

---

## Changes to `/task` Skill

### Section: Mandatory Archive Protocol (NEW)

```markdown
## Mandatory Archive Protocol

**This is not optional. Violations break the skill contract.**

### First Action on Invocation

Before doing ANYTHING else:

1. Call `sbs_archive_state()` via MCP
2. Check `global_state` field:
   - `null` → Fresh task, proceed to alignment
   - `{skill: "task", substate: X}` → Resume from substate X
   - `{skill: "other", ...}` → Error: state conflict

### Phase Transitions

Every phase change MUST execute:

\`\`\`bash
sbs archive upload --trigger skill \
  --global-state '{"skill":"task","substate":"<phase>"}' \
  --state-transition phase_start
\`\`\`

Phases: `alignment` → `planning` → `execution` → `finalization`

### Ending the Task

Final archive call:
\`\`\`bash
sbs archive upload --trigger skill \
  --state-transition phase_end
\`\`\`

This clears `global_state` to `null`, returning system to idle.
```

### Section: Metric Gates (NEW)

```markdown
## Metric Gates

### Definition

Each plan MUST define gates in YAML format:

\`\`\`yaml
gates:
  tests: all_pass | <threshold>    # Test requirements
  quality:                          # Quality score requirements
    T5: >= 0.8
    T6: >= 0.9
  regression: >= 0                  # No regression allowed
\`\`\`

### Enforcement

Before transitioning to finalization:

1. Run `sbs_validate_project` with specified validators
2. Run `sbs_run_tests` with specified filters
3. Compare results to gate thresholds
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
```

### Section: Recovery Semantics (NEW)

```markdown
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
- Report error and wait for user resolution
```

---

## Changes to `/update-and-archive` Skill

### Section: Mandatory Archive Protocol (ADD)

```markdown
## Mandatory Archive Protocol

### First Action

Before any work:
\`\`\`bash
sbs archive upload --trigger skill \
  --global-state '{"skill":"update-and-archive","substate":"readme-wave"}' \
  --state-transition phase_start
\`\`\`

### Substate Transitions

Each part transition:
- Part 0→1: `--global-state '{"skill":"update-and-archive","substate":"readme-wave"}'`
- Part 1→2: `--global-state '{"skill":"update-and-archive","substate":"oracle-regen"}'`
- Part 2→3: `--global-state '{"skill":"update-and-archive","substate":"porcelain"}'`
- Part 3→4: `--global-state '{"skill":"update-and-archive","substate":"archive-upload"}'`

### Final Action

Close epoch and clear state:
\`\`\`bash
sbs archive upload --trigger skill \
  --state-transition phase_end
\`\`\`
```

---

## Execution Plan

### Wave 1: Update `/task` Skill

1. Add "Mandatory Archive Protocol" section
2. Add "Metric Gates" section
3. Add "Recovery Semantics" section
4. Update phase descriptions with archive requirements
5. Add gate definition template to planning phase

### Wave 2: Update `/update-and-archive` Skill

1. Add "Mandatory Archive Protocol" section
2. Update part descriptions with archive calls
3. Clarify epoch close semantics

### Wave 3: Verification

1. Test archive state tracking manually
2. Verify `sbs_archive_state()` returns correct data
3. Test gate failure pause behavior (simulate)

---

## Success Criteria

1. Both skill files have "Mandatory Archive Protocol" sections
2. `/task` has "Metric Gates" section with YAML template
3. `/task` has "Recovery Semantics" section
4. Archive calls are REQUIRED, not suggested
5. Gate failures MUST pause (not continue automatically)
6. Recovery protocol explicitly defined

---

## Verification

After implementation:

1. Read updated skill files
2. Invoke `/task` and verify it calls `sbs_archive_state()` first
3. Check that `global_state` is set during execution
4. Verify `/update-and-archive` clears state at end

