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
| `/task crush` | Batch issue resolution — loads all open issues, proposes triage plan |
| `/task crush #1 #5` | Same, scoped to specified issues only |

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

### Crush Mode (Batch Issue Resolution)

When invoked as `/task crush` (with or without issue numbers):

**Argument parsing:** The `crush` keyword is detected before the description fallthrough. Remaining args after `crush` are parsed for `#N` issue references.
- `/task crush` → operates on all open issues
- `/task crush #1 #5 #12` → scoped to issues 1, 5, and 12 only

**Workflow:**

1. **Pre-load issues:**
   - Call `sbs_issue_summary()` MCP tool to get all open issues with metadata (type, area, labels, age)
   - If specific issue numbers follow `crush`, filter results to those issues
   - Otherwise, operate on all open issues

2. **Gather oracle context (parallel):**
   - Spawn up to 4 read-only Explore agents, each taking a batch of issues
   - Each agent calls `sbs_oracle_query` for its batch and reads relevant files
   - Each reports back per issue: affected files, estimated complexity (trivial/moderate/significant), recommended wave type (direct/fix/docs/code)

3. **Propose triage plan:**
   - Present issues grouped by recommended wave type:
     - **Wave 0 (direct):** Issues closable via MCP queries alone (duplicates, already-fixed, informational)
     - **Wave 1 (fix):** Bug fixes with known root causes
     - **Wave 2 (docs):** Documentation or guidance changes
     - **Wave 3 (code):** Moderate-scope implementation work
   - For each issue show: `#number - title (age, complexity, wave)`
   - Use AskUserQuestion with multi-select to let user include/exclude issues
   - Ask user to approve the proposed wave grouping

4. **On approval:** Transition to normal `/task` planning phase with all selected issues as `issue_refs`. The existing Triage Wave Structure (in the Execution section) applies for organizing execution waves.

**Archive tracking:** Crush mode uses the same archive protocol as normal `/task` — all phase transitions are recorded. The `issue_refs` field tracks all selected issues throughout the session.

**Gate validation:** Same gates apply as normal `/task`. All selected issues must pass their respective validation before closure.

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

**Runtime state checks:** Before asking the user about system state during alignment, agents must first query MCP tools (`sbs_archive_state`, `sbs_skill_status`, `sbs_serve_project`) to gather facts. Questions should be reserved for requirements ambiguity and preference decisions, not discoverable state.

**For tasks producing artifacts (builds, screenshots, CSS, templates):**
- Probe for quantitative success criteria: "What score/threshold defines success?"
- Map criteria to specific gate definitions (T1-T8, test counts, regression bounds)
- If user doesn't specify, propose defaults based on affected repos

**Agent concurrency:** Up to 4 `sbs-developer` agents may run in parallel during alignment when independent exploration tasks are needed (e.g., reading different repos simultaneously). All agents are read-only during alignment — no file modifications before plan approval.

**Exploration differentiation:** When spawning multiple exploration agents, each must target a **distinct investigation dimension**. Examples of distinct dimensions: "check if CSS exists" vs "trace the call chain from entry point to output" vs "check test coverage for feature X". Single-question explorations ("does X exist?") should use 1 agent, not N. Redundant confirmation of the same fact across multiple agents is wasted work.

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

**Pre-flight checklist (REQUIRED before finalizing plan):**
- Read CLAUDE.md "Known Limitations" section — verify plan doesn't conflict with documented limitations
- Check open issues (`sbs_issue_list`) for related/duplicate work

**Agent concurrency:** Up to 4 `sbs-developer` agents may run in parallel during planning for independent analysis tasks (e.g., exploring affected repos, prototyping approaches in separate files).

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

**Taxonomy changes:** Plans modifying `dev/storage/labels/taxonomy.yaml` or tag dimensions MUST include taxonomy tests in gates (`pytest sbs/tests/pytest/test_taxonomy.py -v`).

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
1. **Up to 4 `sbs-developer` agents may run concurrently** within a wave during ANY phase (alignment, planning, execution, finalization). The approved plan determines which waves are parallel vs sequential.
2. **All commits go to the feature branch** -- commits are pushed to remote automatically by `sbs archive upload` during phase transitions. Agents never need direct `git push`.
3. **Parallel wave spawning:** Spawn all agents in a parallel wave in a SINGLE message with multiple Task tool calls. Collision avoidance is the plan's responsibility -- parallel waves must target non-overlapping files/repos.
4. **Validators run after all agents in a wave complete** -- not after individual agents.
5. If validation fails:
   - Retry failed agent once
   - If retry fails, pause for re-approval
6. Continue until all waves complete
7. **Autonomous bug logging:** When agents discover bugs during execution, they should log them immediately via `sbs_issue_log` MCP tool without pausing work. This preserves discovery context and keeps the backlog current.

### Triage Wave Structure

For batch-closure tasks (multiple issues in one session), organize execution waves by **operation type**, not by issue number:

1. **Wave 0 (direct operations):** Quick closures, investigations that need only MCP queries -- no agents needed
2. **Wave 1 (uniform fixes):** Bug fixes with known root causes -- parallel agents where files don't overlap
3. **Wave 2 (documentation):** Guidance additions, prose changes -- parallel agents on separate files
4. **Wave 3 (code changes):** Moderate-scope implementation work -- sequential if files overlap

Uniform-complexity waves complete more predictably than mixed-complexity waves. When triaging, group issues by what kind of work they require, not by their issue number or priority.

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

1. Run full validation suite (per plan's `gates:` section)
2. **Verify gate results against plan:**
   - Cross-reference each gate defined in the plan with actual results
   - Record pass/fail status and actual values for each gate in the archive entry
   - If any plan-specified validator was not run, flag it as a gap
3. Update unified ledger
4. Generate summary report (include gate results table)
5. **If gates pass:**
   - Merge PR via `sbs_pr_merge` MCP tool (squash strategy)
   - Feature branch is automatically deleted
6. Commit final state

**Agent concurrency:** Up to 4 `sbs-developer` agents may run in parallel during finalization for independent validation tasks (e.g., running validators on different projects, checking different repos).

**PR Merge:**
```
sbs_pr_merge(
    number=<pr_number>,
    strategy="squash",
    delete_branch=True
)
```

### Compressed Confirmation

For straightforward closures where all conditions are unambiguous (all gates pass, PR approved, issues clearly linked), use a single compressed confirmation rather than step-by-step walkthrough:

"Closing #X, #Y, merging PR #Z, pushing -- proceed?"

Reserve step-by-step confirmation for cases with ambiguity: partial gate failures, overridden gates, unclear issue linkage, or user-requested granularity.

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

**Available validators:** Discover registered validators at runtime via `discover_validators()` from `dev/scripts/sbs/tests/validators/`. Each validator file uses `@register_validator` -- grep the directory for the full current list. Do not hardcode validator names here; the registry is the source of truth.

**T1-T8 validator details:** See `dev/storage/README.md` for the canonical T1-T8 mapping (categories, types, weights, descriptions). The mapping is also documented in `CLAUDE.md` under "Quality Validation Framework".

### Hybrid Compliance Pattern

The compliance validation uses a bidirectional agent-script pattern:

1. Agent runs `sbs compliance --project <name>`
2. Script computes which pages need validation, generates prompts with screenshot paths
3. Agent reads screenshots using vision capabilities, provides JSON validation response
4. Script updates `compliance_ledger.json` with results

**Why this pattern**: Scripts never call AI APIs. Agents never bypass scripts for state changes. This pattern satisfies both constraints while enabling AI-powered validation.

### Test Cleanup on Feature Removal

When a plan includes removing a feature, capability, or surface area, the plan **must** include a cleanup step:

1. Grep the test suite for references to the removed feature (function names, page types, CSS classes, etc.)
2. Update or remove test assertions that reference the removed feature
3. Verify no tests pass vacuously (testing something that no longer exists)

This step is mandatory in the plan -- not a post-hoc fix during execution. Feature removal consistently causes test failures from stale assertions when this step is omitted.

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
