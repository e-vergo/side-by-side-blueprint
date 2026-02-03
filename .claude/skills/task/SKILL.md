---
name: task
description: General-purpose agentic task execution with validation
disable-model-invocation: true
version: 3.0.0
---

# /task - Agentic Task Workflow

## Invocation

| Pattern | Behavior |
|---------|----------|
| `/task` | Lists open issues, offers choice OR freeform description |
| `/task #42` | Loads issue #42 as task context |
| `/task <description>` | Uses description as task (no issue linkage) |

### Issue-Driven Invocation

When invoked with an issue number (`/task #42`):
1. Call `sbs_issue_get` MCP tool to fetch issue details
2. Use issue title and body as task context
3. Track `issue_refs: [42]` throughout execution

When invoked without arguments (`/task`):
1. Call `sbs_issue_list` MCP tool to get open issues
2. Present list to user with AskUserQuestion:
   - Option for each open issue (up to 5 most recent)
   - "Describe a new task" option for freeform
3. If user selects an issue, proceed as issue-driven
4. If user describes new task, proceed without issue linkage

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
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill \
  --global-state '{"skill":"task","substate":"<phase>"}' \
  --state-transition phase_start \
  --issue-refs <comma-separated-issue-numbers>  # If issue-driven
  --pr-number <pr-number>  # If PR-based (after plan approval)
```

Phases: `alignment` → `planning` → `execution` → `finalization`

**Planning is MANDATORY.** The MCP server enforces this -- transitions from alignment directly to execution are rejected. Every task must go through planning before execution begins.

**Issue Tracking:** If the task is issue-driven, include `--issue-refs` with the linked issue number(s) in every archive upload during this task.

### Ending the Task

Final archive call clears state:

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill \
  --state-transition phase_end
```

This sets `global_state` to `null`, returning system to idle.

---

## Phase 1: Alignment (Q&A)


**DO NOT CHANGE**
```
This is your chance to interact with, understand and brainstorm with the user.  They watched you design all the tools and know exactly what needs to happen in that phase in order for us to move on. let them guide and pull you. Even though you may not know where thay are pulliny you towards, know that you will end up where you need to be. Open with a greeting and gentle probe about what the task is. Use a professional, but casual and inviting tone.

Do not, under any circumstance, modify files before aligning with the user, discussing and agreeing on metrics, and have a shared understanding that the conditions to pass through the gate to the next phase have been met. If this does not happen you will lose sight of the fact that we need to work in a structured way that will allow use to use the archival and approval process properly. doing this right will make your job easier in the future.
```

Phase topics
- Task scope, boundaries, methods brainstorming
- Success criteria
- Validation requirements
- Affected repositories

**REQUIRED:** After completing alignment, transition to planning:

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill \
  --global-state '{"skill":"task","substate":"planning"}' \
  --state-transition phase_start
```

---

## Phase 2: Planning

**Plan mode entry:** Either the user enters plan mode manually, or Claude calls `EnterPlanMode`. Both are valid - use whichever occurs first.

Claude presents:
1. Task breakdown into waves/agents
2. Validator specifications per wave
3. Success criteria mapped to ledger checks
4. Estimated scope (files, repos, complexity)

### Gate Definition (REQUIRED)

Every plan MUST include a `gates:` section in YAML format:

```yaml
gates:
  tests: all_pass | <threshold>    # Test requirements
  test_tier: evergreen             # Optional: evergreen, dev, interactive, all (default: evergreen)
  quality:                          # Quality score requirements
    T5: >= 0.8
    T6: >= 0.9
  regression: >= 0                  # No regression allowed
```

Plans without gates are incomplete. Define appropriate gates based on task scope.

**Test Tiers:**
- `evergreen`: Tests marked with `@pytest.mark.evergreen` - fast, reliable, always run
- `dev`: Development tests - may be slower or require specific setup
- `interactive`: Tests requiring interactive validation
- `all`: Run all tests regardless of tier

**Change-based Validator Selection:** The system automatically determines which T1-T8 validators to run based on which repos have changed. For example, CSS changes trigger T5/T6/T7/T8 validators.

**REQUIRED:** After plan approval, transition to execution:

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill \
  --global-state '{"skill":"task","substate":"execution"}' \
  --state-transition phase_start
```

---

## PR Creation (After Plan Approval)

**When plan is approved and before transitioning to execution:**

1. **Create feature branch:**
   ```bash
   git checkout main && git pull
   git checkout -b task/<issue-or-id>-<slug>
   git commit --allow-empty -m "chore: initialize task branch"
   # Direct git push denied by hooks - push via Python subprocess:
   python3 -c "import subprocess; subprocess.run(['git', 'push', '--set-upstream', 'origin', 'task/<issue-or-id>-<slug>'], check=True)"
   ```

2. **Create PR via MCP:**
   ```
   sbs_pr_create(
       title="<task title>",
       body="## Summary\n<brief description>\n\n## Plan\nSee plan file in branch.\n\n## Test Plan\n- [ ] Validators pass\n- [ ] Tests pass",
       base="main",
       draft=False
   )
   ```

   The PR will automatically include:
   - `ai-authored` label
   - Attribution footer

3. **Record PR number in archive transition:**
   ```bash
   python3 -m sbs archive upload --trigger skill \
     --global-state '{"skill":"task","substate":"execution"}' \
     --state-transition phase_start \
     --pr-number <pr_number>
   ```

**Branch naming convention:**
- Issue-driven: `task/<issue>-<slug>` (e.g., `task/1-verso-pdf-fix`)
- Freeform: `task/<slug>` (e.g., `task/pr-workflow-integration`)

---

## Phase 3: Execution

**All work happens on the feature branch, not main.**

Fully autonomous:
1. **Up to 4 `sbs-developer` agents may run concurrently** within a wave. The approved plan determines which waves are parallel vs sequential.
2. **All commits go to the feature branch** -- commits are pushed to remote automatically by `sbs archive upload` during phase transitions. Agents never need direct `git push`.
3. **Parallel wave spawning:** Spawn all agents in a parallel wave in a SINGLE message with multiple Task tool calls. Collision avoidance is the plan's responsibility -- parallel waves must target non-overlapping files/repos.
4. **Validators run after all agents in a wave complete** -- not after individual agents.
5. If validation fails:
   - Retry failed agent once
   - If retry fails, pause for re-approval
6. Continue until all waves complete

**REQUIRED:** After all waves complete and gates pass, transition to finalization:

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs archive upload --trigger skill \
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
4. **If gates pass:**
   - Merge PR via `sbs_pr_merge` MCP tool (squash strategy)
   - Feature branch is automatically deleted
5. Commit final state

**PR Merge:**
```
sbs_pr_merge(
    number=<pr_number>,
    strategy="squash",
    delete_branch=True
)
```

**REQUIRED:** After finalization completes, hand off to update-and-archive:

Use the `sbs_skill_handoff` MCP tool to atomically end the task skill and start update-and-archive:
```
sbs_skill_handoff(
    from_skill="task",
    to_skill="update-and-archive",
    to_substate="retrospective"
)
```

This creates a single archive entry that simultaneously ends `/task` and starts `/update-and-archive`, preventing orphaned skill sessions. The retrospective runs first while context is hot, then readmes, oracle, porcelain. The old pattern of separate `phase_end` + `skill_start` calls is still supported but is not recommended.

---

## Issue Closure (If Issue-Driven)

If this task was linked to GitHub issue(s):

1. **After gate validation passes**, prompt user:
   ```
   Task linked to issue #42: "<issue title>"
   Close this issue? [Yes/No]
   ```

2. Use AskUserQuestion with options:
   - "Yes, close it" → Call `sbs_issue_close` MCP tool
   - "No, keep open" → Continue without closing
   - "Close with comment" → Ask for comment, then call `sbs_issue_close` with comment

3. Report closure result before proceeding to Phase 5

**Important:** Only prompt for closure if all gates passed. If gates failed and user overrode, still prompt but note that gates were overridden.

---

## Phase 5: Documentation Cleanup (MANDATORY)

**Execution is NOT complete until this phase runs.**

Invoke `/update-and-archive` as the final step. The handoff in Phase 4 already started this skill atomically via `sbs_skill_handoff` with substate `"retrospective"`. The update-and-archive agent:
1. Runs session retrospective while context is hot (5 analysis dimensions)
2. Refreshes all repository READMEs in parallel waves
3. Synchronizes core documentation (ARCHITECTURE.md, CLAUDE.md, GOALS.md, README.md)
4. Ensures documentation reflects the changes made during execution

This phase cannot be skipped. The `/task` skill is considered incomplete until `/update-and-archive` completes successfully.

---

## Repo Strategy

Not all repos use PRs. The strategy depends on repo type:

| Category | Strategy | Repos |
|----------|----------|-------|
| Main | PR required | Side-By-Side-Blueprint |
| Toolchain | PR required | Dress, Runway, SBS-Test, dress-blueprint-action |
| Showcase | PR required | GCR, PNT |
| Forks | Direct commits | verso, subverso, LeanArchitect, sbs-lsp-mcp |
| Storage | Direct commits | dev/storage |

**Multi-repo changes:** Submodule changes are committed directly to their repos. The main repo PR captures the submodule pointer bumps.

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
| `alignment` | Re-ask clarifying questions, **re-fetch issue if issue-driven** |
| `planning` | Read plan file, continue planning |
| `execution` | Check wave completion, resume incomplete waves |
| `finalization` | Re-run validators, re-check gates |

### Issue Linkage Recovery

The `issue_refs` field in archive entries persists the issue linkage. On recovery:
1. Query recent archive entries for this task
2. Extract `issue_refs` from entries
3. Continue tracking the same issue(s)

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
| `finalization` | Full validation, summary generation | → (handoff to /update-and-archive) |

Each substate transition archives state with `state_transition: "phase_start"` for the incoming phase. The final transition uses `state_transition: "handoff"` via `sbs_skill_handoff` to atomically end the task and start update-and-archive.

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
- **Concurrency constraint**: One agent at a time by default; up to 4 concurrent agents during execution phase per the approved plan
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
