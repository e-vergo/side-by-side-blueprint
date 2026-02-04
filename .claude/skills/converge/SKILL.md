---
name: converge
description: Autonomous QA convergence loop — evaluates, fixes, rebuilds until pass
version: 1.0.0
---

# /converge - Autonomous QA Convergence Loop

Autonomous QA evaluation, fix, rebuild loop. Runs unattended until 100% QA pass rate or max iterations. User kicks this off and walks away.

The loop is: **build -> evaluate -> fix -> rebuild -> re-evaluate** until convergence (100% pass), plateau (no improvement), or iteration cap.

---

## Invocation

| Pattern | Behavior |
|---------|----------|
| `/converge GCR` | Run convergence loop on GCR |
| `/converge SBSTest` | Run convergence loop on SBSTest |
| `/converge PNT` | Run convergence loop on PNT |
| `/converge GCR --max-iter 5` | Override max iterations (default: 3) |

### Argument Parsing

- First argument is **required**: project name (`SBSTest`, `GCR`, or `PNT`)
- `--max-iter N` overrides the default max iteration count of 3
- No arguments -> error: project name required

---

## Mandatory Archive Protocol

**This is not optional. Violations break the skill contract.**

### First Action on Invocation

Before doing ANYTHING else:

1. Call `sbs_archive_state()` via MCP
2. Check `global_state` field:
   - `null` -> Fresh convergence run, proceed to setup
   - `{skill: "converge", substate: X}` -> Resume from substate X
   - `{skill: "other", ...}` -> Error: state conflict, do NOT proceed

### Phase Transitions

Every phase change MUST use the MCP skill lifecycle tools:

- **Start:** `sbs_skill_start(skill="converge", initial_substate="setup")`
- **Transition:** `sbs_skill_transition(skill="converge", to_phase="<next_phase>")`
- **End:** `sbs_skill_end(skill="converge")`
- **Failure:** `sbs_skill_fail(skill="converge", reason="<description>")`

### State Conflict

If `global_state.skill != "converge"` and `global_state` is not `null`:
- Another skill owns the state
- Do NOT proceed
- Report error: "State conflict: skill '<other_skill>' currently owns global state"
- Wait for user resolution

---

## Phase: Setup

**Purpose:** Build the project, start the dev server, initialize loop state.

### Entry

```
sbs_skill_start(skill="converge", initial_substate="setup")
```

### Actions

1. **Build project** via `sbs_build_project(project="<name>")`
   - If build fails: `sbs_skill_fail(skill="converge", reason="Build failed: <details>")` and stop
2. **Start dev server** via `sbs_serve_project(project="<name>", action="start")`
   - If server fails to start: `sbs_skill_fail(skill="converge", reason="Server failed to start")` and stop
3. **Initialize loop state:**
   - `iteration = 1`
   - `max_iterations = 3` (or override from `--max-iter`)
   - `pass_rates = []`

### Transition

```
sbs_skill_transition(skill="converge", to_phase="eval-1")
```

---

## Phase: Eval-N (QA Evaluation, iteration N)

**Purpose:** Systematically evaluate every QA criterion using browser tools.

### Entry

```
sbs_skill_transition(skill="converge", to_phase="eval-<N>")
```

### Actions

1. **Navigate to each page type:** `dashboard`, `dep_graph`, `paper_tex`, `pdf_tex`, `chapter`
   - Pages that return HTTP 404 are skipped without error

2. **Evaluate criteria from `dev/scripts/sbs/tests/compliance/criteria.py`** using browser MCP tools:
   - For criteria with `selector`: `browser_get_elements` to verify element presence
   - For criteria with `hex_color`: `browser_evaluate` to compute and compare styles
   - For layout criteria: `browser_evaluate` for overflow, dimensions, grid properties
   - For interactive criteria: `browser_click` + verify expected behavior

3. **Write results** to `dev/storage/<project>/qa_ledger.json` (same format as /qa):
   ```json
   {
     "version": "1.0",
     "project": "<project>",
     "run_id": "<ISO-timestamp>-<short-hash>",
     "timestamp": "<ISO-timestamp>",
     "iteration": N,
     "pages": {
       "<page_name>": {
         "status": "pass|fail|warn",
         "criteria_checked": 13,
         "criteria_passed": 12,
         "findings": ["PASS: ...", "FAIL: ..."],
         "screenshots": ["screenshot_filenames"],
         "interactions_tested": 3
       }
     },
     "summary": {
       "pages_reviewed": 5,
       "total_criteria": 61,
       "passed": 58,
       "failed": 3,
       "pass_rate": 0.95,
       "issues_logged": [142, 143]
     }
   }
   ```

4. **Calculate pass rate:** `passed / total_criteria`

5. **Append to `pass_rates` list**

6. **Check exit conditions** (any triggers transition to `report`):
   1. Pass rate = 100% -- **converged**
   2. N > 1 AND current pass rate <= previous pass rate -- **plateau** (not improving)
   3. N >= max_iterations -- **hard cap**

7. If no exit condition met: transition to `fix-N`

### Transition

```
sbs_skill_transition(skill="converge", to_phase="fix-<N>")
# or
sbs_skill_transition(skill="converge", to_phase="report")
```

---

## Phase: Fix-N (Remediation, iteration N)

**Purpose:** Parse QA failures, categorize them, spawn agents to fix, rebuild.

**No planning phase.** Fix scope is derived directly from QA failure analysis. Each failure maps to a criterion with known category, selector, and expected value.

### Entry

```
sbs_skill_transition(skill="converge", to_phase="fix-<N>")
```

### Actions

1. **Parse `qa_ledger.json`** for failures (findings starting with `"FAIL:"`)

2. **Categorize each failure** by its criterion category:

   | QA Failure Category | Fix Strategy | Typical Files |
   |---------------------|-------------|---------------|
   | `color` | Edit CSS variables in common.css or Lean status colors | `dress-blueprint-action/assets/css/common.css`, `Dress/Graph/Svg.lean` |
   | `layout` | Edit CSS layout rules or template structure | `dress-blueprint-action/assets/css/common.css`, `Runway/Theme.lean` |
   | `interaction` | Edit JS event handlers or HTML attributes | `dress-blueprint-action/assets/js/*.js` |
   | `content` | Edit Lean templates or document generation | `Runway/Theme.lean`, `Dress/*.lean` |
   | `visual` | Edit CSS visual properties | `dress-blueprint-action/assets/css/common.css` |

3. **For each failure category:**
   1. Query `ask_oracle` for affected files
   2. Spawn `sbs-developer` agent(s) with specific fix instructions (up to 4 concurrent, non-overlapping files)
   3. Each agent receives: criterion ID, expected value, actual value, affected file paths

4. **After all agents complete:**
   - Rebuild project via `sbs_build_project(project="<name>")`
   - If build fails: log error, `sbs_skill_fail(skill="converge", reason="Build failed after fix-<N>: <details>")` and stop

### Transition

```
sbs_skill_transition(skill="converge", to_phase="eval-<N+1>")
```

---

## Phase: Report

**Purpose:** Generate convergence summary, clean up resources.

### Entry

```
sbs_skill_transition(skill="converge", to_phase="report")
```

### Actions

1. **Generate convergence summary in dialogue:**
   - Iterations run: N
   - Pass rate per iteration (showing trend): e.g., `72% -> 89% -> 100%`
   - Exit reason: `converged` | `plateau` | `max iterations`
   - Remaining failures (if any): list with criterion IDs and descriptions
   - Issues logged across all iterations

2. **Stop dev server** via `sbs_serve_project(project="<name>", action="stop")`

3. **End skill:**
   ```
   sbs_skill_end(skill="converge")
   ```

---

## Safety Mechanisms

1. **Hard iteration cap:** Max 3 iterations (configurable via `--max-iter`)
2. **Plateau detection:** Stop if pass rate does not improve between iterations
3. **Build failure:** Halt immediately, report, `sbs_skill_fail()`
4. **Agent failure:** Retry once, then skip that fix and continue (do not block entire iteration)
5. **No gate overrides:** Unlike /task, converge does not ask for gate override -- it reports and stops
6. **No user interaction during loop:** The entire loop runs without AskUserQuestion calls

---

## Recovery Semantics

### Compaction Survival

On compaction, call `sbs_archive_state()`:

- Resume from start of current substate
- `setup`: Check server status via `sbs_serve_project(action="status")`, rebuild if needed
- `eval-N`: Re-run QA evaluation for iteration N
- `fix-N`: Check which fixes were committed (via git log), re-run remaining
- `report`: Re-generate report from latest `qa_ledger.json`

### State Conflict

If `global_state.skill != "converge"` and `global_state` is not `null`:
- Another skill owns the state
- Do NOT proceed
- Report error and wait for user resolution

---

## Substates

| Substate | Description | Transition |
|----------|-------------|------------|
| `setup` | Build, start server, initialize | -> eval-1 |
| `eval-1` | First QA evaluation | -> fix-1 or report |
| `fix-1` | First remediation pass | -> eval-2 |
| `eval-2` | Second QA evaluation | -> fix-2 or report |
| `fix-2` | Second remediation pass | -> eval-3 |
| `eval-3` | Third QA evaluation | -> report (always, max reached) |
| `report` | Convergence summary, cleanup | -> (end) |

Each substate transition is recorded via `sbs_skill_transition`. The final `sbs_skill_end` clears `global_state` to `null`.

---

## Archive Protocol Detail

Each substate transition records:

```
sbs_skill_transition(skill="converge", to_phase="<substate>")
```

The final `sbs_skill_end` clears `global_state` to `null`.

---

## Error Handling

| Error | Response |
|-------|----------|
| Build failure | `sbs_skill_fail(skill="converge", reason="Build failed: <details>")` |
| Server won't start | `sbs_skill_fail(skill="converge", reason="Server failed to start")` |
| Browser tool failure | Retry once. If still fails, skip criterion and record in findings |
| Page returns 404 | Skip page, not a convergence blocker |
| All agents fail in fix phase | Skip iteration's fixes, proceed to next eval (will likely plateau) |
| State conflict on resume | Report error, wait for user resolution |

All errors are surfaced in dialogue. Nothing is silently ignored.

---

## Tool Reference

### Browser Tools

| Tool | Use For |
|------|---------|
| `browser_navigate` | Navigate to page URL |
| `browser_screenshot` | Capture page state per iteration |
| `browser_click` | Test interactive elements |
| `browser_get_elements` | Verify element presence |
| `browser_evaluate` | Check computed styles, dimensions |

### SBS MCP Tools

| Tool | Use For |
|------|---------|
| `sbs_build_project` | Build project before eval and after fixes |
| `sbs_serve_project` | Start/stop/check dev server |
| `sbs_skill_start` | Begin converge session |
| `sbs_skill_transition` | Move between phases |
| `sbs_skill_end` | Complete converge and clear state |
| `sbs_skill_fail` | Record failure and release state |
| `ask_oracle` | Find affected files for fixes |
| `sbs_issue_log` | Log bugs discovered during eval |

### File Tools

| Tool | Use For |
|------|---------|
| `Read` | Load criteria.py, read qa_ledger.json |
| `Write` | Write qa_ledger.json |

---

## Anti-Patterns

- **Asking user questions during loop**: This skill is fully autonomous -- no AskUserQuestion calls
- **Skipping browser verification**: Do not mark criteria as passed without actually checking via browser tools
- **Fixing without oracle context**: Always query oracle for affected files before spawning fix agents
- **Continuing after build failure**: Build failures are fatal -- halt immediately
- **Ignoring plateau**: If pass rate stops improving, continuing wastes resources
- **Overlapping agent files**: Parallel fix agents must target non-overlapping files
