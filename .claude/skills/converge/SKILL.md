---
name: converge
description: Autonomous QA convergence loop — evaluates, fixes, rebuilds until pass
version: 2.0.0
---

# /converge - Autonomous QA Convergence Loop

Autonomous QA evaluation, fix, rebuild loop. Runs unattended until 100% QA pass rate or max iterations. User kicks this off and walks away.

The loop is: **build -> evaluate -> fix -> introspect -> rebuild -> re-evaluate** until convergence (100% pass), plateau (no improvement), or iteration cap.

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
4. **Clear adaptation notes:** Write empty `adaptation_notes.json` to `dev/storage/<project>/` (fresh run = fresh memory)

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

**Purpose:** Parse QA failures, categorize them, spawn agents to fix.

**No planning phase.** Fix scope is derived directly from QA failure analysis. Each failure maps to a criterion with known category, selector, and expected value.

### Entry

```
sbs_skill_transition(skill="converge", to_phase="fix-<N>")
```

### Actions

0. **Load adaptation notes** from `dev/storage/<project>/adaptation_notes.json`. For N > 1, pass adaptation context (persistent failures, recommended strategies, what was tried before) to fix agents as additional context.

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

### Transition

```
sbs_skill_transition(skill="converge", to_phase="introspect-<N>")
```

---

## Phase: Introspect-N (In-Loop Reflection, iteration N)

**Purpose:** Reflect on Fix-N outcomes, compare with prior iterations, produce adaptation notes for the next cycle. Fully autonomous -- no user interaction.

### Entry

```
sbs_skill_transition(skill="converge", to_phase="introspect-<N>")
```

### Actions

1. **Load context:**
   - Read `dev/storage/<project>/adaptation_notes.json` (empty on iteration 1)
   - Read current `qa_ledger.json` for Eval-N results
   - If N > 1, load Eval-(N-1) results for comparison

2. **Failure differential analysis** (N > 1 only; skip for N=1):
   - **Resolved:** Criteria that failed in Eval-(N-1) but passed in Eval-N -- record which fix strategy worked
   - **Persistent:** Criteria that failed in both evaluations -- flag for strategy change
   - **Regressions:** Criteria that passed in Eval-(N-1) but failed in Eval-N -- flag as high-priority

3. **Strategy assessment** (for persistent failures and regressions):
   - What fix strategy was used? Why might it have failed?
   - What alternative approach should Fix-(N+1) try?
   - What constraints should Fix-(N+1) observe to avoid regressions?

4. **Produce outputs:**

   a. **`sbs_improvement_capture()`** -- Call with a concise observation summarizing what this iteration revealed. Category: `"process"`. Examples:
      - "Converge iteration 2 on GCR: color fixes resolved 3/5 failures but layout criterion L-03 persists -- CSS grid approach insufficient, may need template-level fix"
      - "Converge iteration 1 on SBSTest: 8 failures identified, 5 are color category (CSS variable gaps), 3 are interaction (JS event handlers)"

   b. **`sbs_issue_log()`** -- Call ONLY when a clear, reproducible bug is discovered that transcends the current convergence run. Do NOT log ordinary QA failures -- those are the loop's job to fix. Examples of when to log:
      - A criterion that cannot be fixed due to an upstream tool limitation
      - A regression pattern suggesting an architectural problem

   c. **Write adaptation notes** -- Append iteration entry to `dev/storage/<project>/adaptation_notes.json`:
      ```json
      {
        "iteration": N,
        "timestamp": "<ISO>",
        "eval_pass_rate": 0.0,
        "resolved": ["<criterion_ids>"],
        "persistent": ["<criterion_ids>"],
        "regressions": ["<criterion_ids>"],
        "strategy_notes": [
          {
            "criterion_id": "<id>",
            "category": "<color|layout|interaction|content|visual>",
            "current_strategy": "<what was tried>",
            "observation": "<why it didn't work>",
            "recommended_next": "<what to try next>"
          }
        ],
        "improvement_captured": true,
        "issues_logged": []
      }
      ```

### Transition

```
sbs_skill_transition(skill="converge", to_phase="rebuild-<N>")
```

---

## Phase: Rebuild-N (Post-Fix Rebuild, iteration N)

**Purpose:** Rebuild the project after fixes and introspection, before next evaluation.

### Entry

```
sbs_skill_transition(skill="converge", to_phase="rebuild-<N>")
```

### Actions

1. **Rebuild project** via `sbs_build_project(project="<name>")`
   - If build fails: `sbs_skill_fail(skill="converge", reason="Build failed after fix-<N>: <details>")` and stop

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

3. **Attempt L3 meta-analysis handoff:**

   Check if sufficient L2 data exists for L3 analysis:
   - Glob `dev/storage/archive/summaries/*.md` (excluding `.gitkeep`)
   - If 2+ L2 documents exist:
     ```
     sbs_skill_handoff(
         from_skill="converge",
         to_skill="introspect",
         to_substate="ingestion"
     )
     ```
     Execute L3+ phases (ingestion -> synthesis -> archive) as defined in `/introspect` SKILL.md, fully automated.
     After L3 completes: `sbs_skill_end(skill="introspect")`

   - If fewer than 2 L2 documents:
     Report: "L3 meta-analysis skipped: insufficient L2 summaries (found N, need 2+)"
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
7. **Introspection is non-blocking:** If `sbs_improvement_capture` or `sbs_issue_log` fails, log the error and continue. Introspection tool failures must never halt the convergence loop.

---

## Recovery Semantics

### Compaction Survival

On compaction, call `sbs_archive_state()`:

- Resume from start of current substate
- `setup`: Check server status via `sbs_serve_project(action="status")`, rebuild if needed
- `eval-N`: Re-run QA evaluation for iteration N
- `fix-N`: Check which fixes were committed (via git log), re-run remaining
- `introspect-N`: Re-read `adaptation_notes.json` and `qa_ledger.json`, regenerate outputs. `sbs_improvement_capture` creates new entries (acceptable). Check existing issues before `sbs_issue_log` to avoid duplicates.
- `rebuild-N`: Re-run build (idempotent operation)
- `report`: Re-generate report from latest `qa_ledger.json`. If L3 handoff was initiated, check `sbs_archive_state()` for introspect skill ownership and resume L3 accordingly.

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
| `fix-1` | First remediation pass | -> introspect-1 |
| `introspect-1` | Reflect on iteration 1, produce adaptation notes | -> rebuild-1 |
| `rebuild-1` | Rebuild after fix-1 | -> eval-2 |
| `eval-2` | Second QA evaluation | -> fix-2 or report |
| `fix-2` | Second remediation pass | -> introspect-2 |
| `introspect-2` | Reflect on iteration 2, produce adaptation notes | -> rebuild-2 |
| `rebuild-2` | Rebuild after fix-2 | -> eval-3 |
| `eval-3` | Third QA evaluation | -> report (always, max reached) |
| `report` | Convergence summary, cleanup | -> handoff to introspect L3 or end |

Each substate transition is recorded via `sbs_skill_transition`. The final `sbs_skill_end` (or `sbs_skill_handoff` for L3) clears `global_state` to `null`.

---

## Archive Protocol Detail

Each substate transition records:

```
sbs_skill_transition(skill="converge", to_phase="<substate>")
```

The final `sbs_skill_end` clears `global_state` to `null`. When sufficient L2 data exists, `sbs_skill_handoff` may replace `sbs_skill_end` to atomically transition from converge to introspect L3.

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
| Adaptation notes file corrupt | Delete and regenerate from qa_ledger.json history |
| Introspect-N improvement_capture fails | Log warning, continue (non-fatal) |
| Introspect-N issue_log fails | Log warning, continue (non-fatal) |
| Rebuild-N build failure | `sbs_skill_fail()` -- same as existing build failure semantics |
| L3 handoff fails | Log warning, `sbs_skill_end(skill="converge")` (graceful fallback) |
| L3 insufficient data | Report and `sbs_skill_end(skill="converge")` (not a failure) |

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
| `sbs_improvement_capture` | Log improvement observations from introspection |
| `sbs_skill_handoff` | Atomic converge -> introspect L3 transition |

### File Tools

| Tool | Use For |
|------|---------|
| `Read` | Load criteria.py, read qa_ledger.json |
| `Write` | Write qa_ledger.json, adaptation_notes.json |

---

## Anti-Patterns

- **Asking user questions during loop**: This skill is fully autonomous -- no AskUserQuestion calls
- **Skipping browser verification**: Do not mark criteria as passed without actually checking via browser tools
- **Fixing without oracle context**: Always query oracle for affected files before spawning fix agents
- **Continuing after build failure**: Build failures are fatal -- halt immediately
- **Ignoring plateau**: If pass rate stops improving, continuing wastes resources
- **Overlapping agent files**: Parallel fix agents must target non-overlapping files
- **Logging every failure as an issue**: Only log issues for bugs that transcend the convergence run. Normal QA failures are the loop's responsibility.
- **Blocking on introspection failures**: `sbs_improvement_capture` and `sbs_issue_log` failures are non-fatal. The loop must continue.
- **Ignoring adaptation notes**: Fix-(N+1) agents MUST receive adaptation notes as context. Without this, the loop has no memory.
