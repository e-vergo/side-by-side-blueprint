---
name: update-and-archive
description: Documentation refresh and porcelain state
version: 3.1.0
---

# /update-and-archive

Update all documentation and achieve porcelain git state across all repos.

---

## Required Reading

Agents must read these before making changes:

```
/Users/eric/GitHub/Side-By-Side-Blueprint/dev/markdowns/permanent/ARCHITECTURE.md
/Users/eric/GitHub/Side-By-Side-Blueprint/dev/markdowns/permanent/Archive_Orchestration_and_Agent_Harmony.md
/Users/eric/GitHub/Side-By-Side-Blueprint/dev/markdowns/permanent/README.md
```

---

## Trigger Semantics

The `sbs archive upload` command accepts a `--trigger` flag for provenance tracking:

| Trigger | Source | Purpose |
|---------|--------|---------|
| `--trigger build` | Automatic from `build.py` | Marks entry as build-triggered |
| `--trigger skill` | This skill (Part 4) | Marks entry as skill-triggered |
| Manual (no flag) | User CLI invocation | Marks as manual |

**Key**: Trigger affects metadata only, not behavior. Archive upload always does the same thing regardless of trigger source.

---

## Mandatory Archive Protocol

**This is not optional. Violations break the skill contract.**

### First Action on Invocation

Before doing ANY work:

1. Call `sbs_archive_state()` via MCP
2. Check `global_state` field:
   - `null` → Fresh invocation, proceed (set state via phase_start)
   - `{skill: "update-and-archive", substate: X}` → Resume from substate X (may have been started via handoff from `/task`)
   - `{skill: "other", ...}` → Error: state conflict, do NOT proceed

**Handoff entry point:** When invoked at the end of `/task`, state is already set to `{skill: "update-and-archive", substate: "retrospective"}` via `sbs_skill_handoff`. No additional phase_start is needed -- proceed directly to Part -1 (Session Retrospective).

### Substate Transitions

Each part transition MUST execute the corresponding archive call:

| Transition | Command |
|------------|---------|
| Start | `python3 -m sbs archive upload --trigger skill --global-state '{"skill":"update-and-archive","substate":"retrospective"}' --state-transition phase_start` |
| Retro→Readme | `python3 -m sbs archive upload --trigger skill --global-state '{"skill":"update-and-archive","substate":"readme-wave"}' --state-transition phase_start` |
| Part 1→2 | `python3 -m sbs archive upload --trigger skill --global-state '{"skill":"update-and-archive","substate":"oracle-regen"}' --state-transition phase_start` |
| Part 2→3 | `python3 -m sbs archive upload --trigger skill --global-state '{"skill":"update-and-archive","substate":"porcelain"}' --state-transition phase_start` |
| Part 3→4 | `python3 -m sbs archive upload --trigger skill --global-state '{"skill":"update-and-archive","substate":"archive-upload"}' --state-transition phase_start` |

**Note:** All commands assume working directory is `/Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts`.

### Ending the Skill

Final archive call closes the epoch and clears state:

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill --state-transition phase_end
```

This sets `global_state` to `null` and marks the epoch boundary.

---

## Recovery Semantics

If context compacts mid-skill:
1. Query `sbs_archive_state()`
2. Resume from start of current substate
3. Substates are designed to be idempotent (re-running is safe)

---

## Substates

The update-and-archive skill has five substates, tracked in the archive:

| Substate | Description | Transition |
|----------|-------------|------------|
| `retrospective` | Session retrospective analysis | → readme-wave |
| `readme-wave` | Updating repository READMEs | → oracle-regen |
| `oracle-regen` | Regenerating sbs-oracle.md | → porcelain |
| `porcelain` | Ensuring clean git state | → archive-upload |
| `archive-upload` | Creating archive entry | → (skill complete, epoch closed) |

---

## Epoch Semantics

This skill closes epochs. An epoch is the set of archive entries between two `/update-and-archive` invocations.

### Epoch Lifecycle

1. **Epoch opens**: Implicitly, when work begins after previous epoch close
2. **Entries accumulate**: Build entries (`trigger: "build"`), manual entries
3. **Epoch closes**: When `/update-and-archive` runs, creating a skill-triggered entry

### Epoch Summary

The closing entry includes `epoch_summary`:
```json
{
  "entries_in_epoch": 5,
  "builds_in_epoch": 4,
  "entry_ids": ["1234567890", "1234567891", ...]
}
```

### Why Epochs Matter

Epochs create natural boundaries for:
- Documentation synchronization (READMEs updated at epoch close)
- Data aggregation (trends computed per epoch)
- State demarcation (what happened since last sync)

---

## Agent Model

When `/update-and-archive` is invoked, it spawns a dedicated agent that runs autonomously to completion.

### Why a Dedicated Agent

This skill:
- Has a well-defined, deterministic workflow (retrospective → readme-wave → oracle-regen → porcelain → archive-upload)
- Requires no supervision or decision-making from higher levels
- Should not consume context from the orchestrating chat
- Can run completely autonomously once invoked

### Center Stage Execution

The update-and-archive agent:
- Becomes "center stage" for the duration of the skill
- Manages its own substates via archive entries
- Reports completion to the invoking context
- Closes the current epoch upon successful completion

### State Tracking

Each substate transition creates an archive entry with:
- `global_state`: `{skill: "update-and-archive", substate: <current_substate>}`
- `state_transition`: "phase_start" or "phase_end"

The final archive entry (substate: `archive-upload`) includes:
- `trigger: "skill"`
- `epoch_summary` with aggregated data from the epoch
- Marks the epoch boundary

### Invocation Contexts

| Context | Behavior |
|---------|----------|
| End of `/task` (Phase 5) | Task agent spawns u&a agent, waits for completion |
| Standalone invocation | Top-level spawns u&a agent directly |
| Manual by user | Same as standalone |

In all cases, the u&a agent runs autonomously - the invoking context does not orchestrate its internal steps.

---

## Part -1: Session Retrospective

**Timing:** Record start time. Include `timing: {phase: "retrospective", duration_s: <N>}` in archive entry notes for the transition.

**Invocation timing:** Runs FIRST in the update-and-archive workflow, while context is hottest. The orchestrator spawns the retrospective agent with a detailed prompt containing session observations.

**REQUIRED:** Before starting, record skill entry (skip if state already set via handoff):
```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill --global-state '{"skill":"update-and-archive","substate":"retrospective"}' --state-transition phase_start
```

### 5 Analysis Dimensions

1. **User Orchestration** -- How effectively did the user direct work? What patterns in their answers to questions? What questions did they have to answer repeatedly that could be pre-communicated?
2. **Claude Alignment** -- Where did Claude misunderstand intent? What could Claude have asked earlier? What assumptions proved wrong?
3. **System Design** -- What tooling friction was encountered? What MCP tools were missing or awkward? What automation should exist?
4. **Plan Execution** -- How closely did execution follow the plan? Where did the plan need mid-flight adjustment? What was underestimated?
5. **Meta-Observations** -- Observations about the archive system itself, the skill workflow, documentation quality, test coverage gaps.

### Output

- **Standalone markdown file:** `dev/storage/archive/retrospectives/<entry-id>.md` (L1 introspection)
- **Summary included in archive entry notes** (key findings, 3-5 bullet points)

**Introspection hierarchy role:** These retrospectives are **L1 introspections** -- per-session observations captured while context is hot. During `/self-improve`, all L1 documents since the last improvement cycle are read and synthesized into an **L2 introspection** (self-improvement summary at `dev/storage/archive/summaries/`). Write retrospectives with this consumer in mind: include specific examples, concrete data, and observations that automated analysis cannot reconstruct.

### Methodology

- The agent has access to the full conversation context at spawn time (compaction-immune)
- Reads recent archive entries via `sbs_search_entries` or `sbs_context` for quantitative data
- Examines user answer patterns, question frequency, correction patterns
- Captures specific examples, not just summaries -- `/self-improve` reads these as L1 inputs for L2 synthesis

### Transition

After retrospective completes, transition to readme-wave:
```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill --global-state '{"skill":"update-and-archive","substate":"readme-wave"}' --state-transition phase_start
```

---

## Part 0: README Staleness Check

**Timing:** Record start time. Include `timing: {phase: "readme-wave", duration_s: <N>}` in archive entry notes for the transition.

**REQUIRED:** Before starting, record skill entry (skip if already transitioned from retrospective):
```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill --global-state '{"skill":"update-and-archive","substate":"readme-wave"}' --state-transition phase_start
```

**Conditional skip:** If `sbs readme-check --json` shows 0 repos changed AND no code changes were made during this session, skip Parts 0-1 entirely and transition directly to oracle-regen.

Run the staleness check to determine which repos need documentation updates:

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs readme-check --json
```

**Interpret the JSON output:**
- `repos_with_changes` array lists repos with uncommitted/unpushed changes
- `changed_files` shows what was modified in each repo
- `clean_repos` array lists repos needing no updates

**Agent allocation based on `summary.needs_review`:**
- 0 repos changed → Skip Part 1 entirely
- 1-2 repos changed → Single agent for all README updates
- 3-5 repos changed → 2 agents (grouped by wave)
- 6+ repos changed → 3 agents (one per wave)

**Only update READMEs for repos appearing in `repos_with_changes`.**

---

## Part 1: README Updates

**Timing:** Record start time. Include `timing: {phase: "readme-updates", duration_s: <N>}` in archive entry notes for the transition.

**REQUIRED:** After completing Part 0 analysis, if READMEs need updates, this part executes. Upon completion of all README updates, transition to Part 2:
```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill --global-state '{"skill":"update-and-archive","substate":"oracle-regen"}' --state-transition phase_start
```

### Wave Dependencies

Updates must respect this order (earlier waves inform later ones):

1. **Forks** - Explain diffs from upstream
   - `forks/verso` (upstream: leanprover/verso)
   - `forks/subverso` (upstream: leanprover/subverso)
   - `forks/LeanArchitect` (upstream: hanwenzhu/LeanArchitect)

2. **Showcase** - Real project style with build instructions
   - `showcase/General_Crystallographic_Restriction`
   - `showcase/PrimeNumberTheoremAnd` (note: fork of original PNT+)

3. **Toolchain** - Comprehensive documentation
   - `toolchain/SBS-Test`
   - `toolchain/Runway`
   - `toolchain/Dress`
   - `toolchain/dress-blueprint-action`

### Agent Strategy

The orchestrator decides agent count based on git state:
- Check `git diff` and `git status` across all repos
- Few changes → fewer agents (possibly one for all)
- Many changes → more agents (grouped by wave)
- Small code changes may still require many doc updates

---

## Part 2: Core Documentation

**Timing:** Record start time. Include `timing: {phase: "core-docs", duration_s: <N>}` in archive entry notes for the transition.

**REQUIRED:** After completing core documentation sync, transition to Part 3:
```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill --global-state '{"skill":"update-and-archive","substate":"porcelain"}' --state-transition phase_start
```

After READMEs are updated, synchronize:

| Document | Focus |
|----------|-------|
| `dev/.refs/ARCHITECTURE.md` | Technical reference |
| `dev/markdowns/ARCHITECTURE.md` | Public architecture |
| `CLAUDE.md` | Claude Code instructions |
| `dev/markdowns/GOALS.md` | Project vision |
| `dev/markdowns/README.md` | Public overview |

**Exclusion:** Do not modify this skill file.

---

## Part 3: Oracle Regeneration

**Timing:** Record start time. Include `timing: {phase: "oracle-regen", duration_s: <N>}` in archive entry notes for the transition.

**Conditional skip:** If `dev/storage/sbs-oracle.md` modification timestamp is more recent than the latest code change in any repo, skip oracle regeneration.

**REQUIRED:** After completing oracle regeneration, transition to Part 4:
```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill --global-state '{"skill":"update-and-archive","substate":"archive-upload"}' --state-transition phase_start
```

**Timing**: Oracle regeneration happens AFTER all README waves complete in Part 1, and AFTER core documentation sync in Part 2. This ensures the Oracle captures the final state of all documentation.

Regenerate the Oracle:

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs oracle compile
```

This extracts content from all READMEs and CLAUDE.md into `.claude/agents/sbs-oracle.md`.

**Validation:**
- Oracle must have all sections populated
- File paths must be valid

---

## Part 4: Finalization

**Timing:** Record start time. Include `timing: {phase: "finalization", duration_s: <N>}` in archive entry notes for the transition.

**REQUIRED:** After achieving porcelain state and completing all work, close the epoch:
```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill --state-transition phase_end
```

This clears `global_state` to `null` and marks the epoch boundary.

**Epoch data:** Use the `sbs_epoch_summary` MCP tool to retrieve aggregated epoch data before closing if needed for reporting.

### Stale Detection

Read `dev/storage/migrations.json`:
- Delete files listed in `migrations[].from` if they exist (confirm with user)
- Replace patterns in `path_references` automatically

### Archive Integration

Archive upload runs automatically during builds. If this skill is invoked after a build, session data has already been archived. For standalone documentation refreshes, run:

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill
```

### Git Porcelain

For each repo (main + 10 submodules):

```
Main: /Users/eric/GitHub/Side-By-Side-Blueprint
Submodules:
  - forks/verso, forks/subverso, forks/LeanArchitect
  - toolchain/Dress, toolchain/Runway, toolchain/SBS-Test, toolchain/dress-blueprint-action
  - showcase/General_Crystallographic_Restriction, showcase/PrimeNumberTheoremAnd
  - dev/storage
```

1. Stage and commit changes: `"docs: update-and-archive refresh"`
2. Request user confirmation before pushing
3. Verify: `git status` clean, no commits ahead of origin

**Push mechanism:** `ensure_porcelain()` (called by `sbs archive upload`) handles the actual `git push` via Python's `subprocess.run()`. This bypasses Claude Code's hook restriction on direct Bash `git push`, which denies pushes by design to enforce archival-first workflow. For new branches without upstream tracking, the initial push must be done separately via Python subprocess with `--set-upstream` before `ensure_porcelain()` can push subsequent commits.

---

## Success Criteria

- Documentation reflects codebase state
- All repos committed and pushed
- `git status` clean in all 11 repos
