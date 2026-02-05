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
| `/converge GCR` | Run convergence loop on GCR (all failures fixed in parallel per iteration) |
| `/converge SBSTest` | Run convergence loop on SBSTest |
| `/converge PNT` | Run convergence loop on PNT |
| `/converge GCR --max-iter 5` | Override max iterations (default: 3) |
| `/converge GCR --single` | Process failures one category at a time (sequential mode) |
| `/converge GCR --goal qa` | QA criteria evaluation (default behavior) |
| `/converge GCR --goal tests` | Pytest pass rate convergence |
| `/converge GCR --goal "T5 >= 0.9, T6 >= 0.95"` | Custom validator thresholds |
| `/converge hardcore GCR` | Hardcore mode -- no bail, tick-tock introspect |
| `/converge hardcore GCR --goal tests` | Hardcore with custom goal |
| `/converge hardcore GCR --single` | Hardcore in sequential mode |

**Default behavior is crush mode:** all QA failures in an iteration are addressed simultaneously, with fix agents grouped by category to avoid file conflicts. Use `--single` to revert to sequential one-category-at-a-time processing.

**Hardcore mode** (`hardcore` keyword before project name) also uses crush mode by default. It disables plateau detection and max-iteration caps, running indefinitely until 100% pass or build failure. Introspection follows a tick-tock cadence (every other iteration).

### Argument Parsing

- First argument is **required**: project name (`SBSTest`, `GCR`, or `PNT`)
- `--max-iter N` overrides the default max iteration count of 3
- `--single` enables sequential mode: process one failure category at a time instead of all in parallel (crush mode is the default)
- `--goal <target>` sets the convergence target (default: `qa`):
  - `qa` -- evaluate QA criteria via browser (current default behavior)
  - `tests` -- run `sbs_run_tests` and converge on pytest pass rate
  - `"T5 >= 0.9, T6 >= 0.95"` -- run `sbs_validate_project` with specified validators and check against custom thresholds (comma-separated `<validator> >= <threshold>` pairs)
- `hardcore` keyword (before project name) enables hardcore mode:
  - Disables plateau detection exit condition
  - Disables max_iterations exit condition (runs indefinitely)
  - Enables tick-tock introspection cadence (introspect on odd iterations only)
  - Uses crush (parallel) mode by default (overridable with `--single`)
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

### Goal Dispatch

Evaluation behavior depends on `--goal`:

- **`qa` (default):** Evaluate QA criteria via browser tools as described below. Pass rate = passed criteria / total criteria.
- **`tests`:** Run `sbs_run_tests(project="<name>")` and parse results. Pass rate = tests passed / tests total. Skip browser-based evaluation entirely.
- **Custom thresholds (e.g., `"T5 >= 0.9, T6 >= 0.95"`):** Run `sbs_validate_project(project="<name>", validators=["T5", "T6"])` and check each validator's score against its threshold. Pass rate = validators meeting threshold / total validators specified.

For `tests` and custom threshold goals, skip steps 1-3 below and jump directly to step 4 (write results) with the appropriate pass/fail data. The ledger format is the same; the `pages` field is replaced with `validators` or `tests` as appropriate.

### Actions (QA Goal)

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
   1. Pass rate = 100% -- **converged** (all modes)
   2. N > 1 AND current pass rate <= previous pass rate -- **plateau** (normal mode only; **DISABLED** in hardcore mode)
   3. N >= max_iterations -- **hard cap** (normal mode only; **DISABLED** in hardcore mode)
   4. Build failure -- **fatal** (all modes, handled separately in rebuild phase)

   In hardcore mode, only condition 1 (100% converged) triggers exit from the eval-fix loop. The loop runs indefinitely until full convergence or a build failure halts it.

7. If no exit condition met: transition to `fix-N`

### Transition

```
sbs_skill_transition(skill="converge", to_phase="fix-<N>")
# or
sbs_skill_transition(skill="converge", to_phase="report")
```

---

## Phase: Fix-N (Remediation, iteration N)

**Purpose:** Parse failures, categorize them, spawn agents to fix.

**No planning phase.** Fix scope is derived directly from failure analysis. Each failure maps to a known category with actionable remediation.

**Default: crush mode.** All failure categories are addressed in parallel within a single iteration (up to 4 concurrent agents, grouped by category to avoid file conflicts). With `--single`, categories are processed sequentially one at a time.

### Entry

```
sbs_skill_transition(skill="converge", to_phase="fix-<N>")
```

### Actions

0. **Load adaptation notes** from `dev/storage/<project>/adaptation_notes.json`. For N > 1, pass adaptation context (persistent failures, recommended strategies, what was tried before) to fix agents as additional context.

1. **Parse failure data** from the latest evaluation results.

2. **Determine fix strategy based on goal type:**

   **For `qa` goal (default):** Parse `qa_ledger.json` for failures (findings starting with `"FAIL:"`). Categorize each by criterion category:

   | QA Failure Category | Fix Strategy | Typical Files |
   |---------------------|-------------|---------------|
   | `color` | Edit CSS variables in common.css or Lean status colors | `dress-blueprint-action/assets/css/common.css`, `Dress/Graph/Svg.lean` |
   | `layout` | Edit CSS layout rules or template structure | `dress-blueprint-action/assets/css/common.css`, `Runway/Theme.lean` |
   | `interaction` | Edit JS event handlers or HTML attributes | `dress-blueprint-action/assets/js/*.js` |
   | `content` | Edit Lean templates or document generation | `Runway/Theme.lean`, `Dress/*.lean` |
   | `visual` | Edit CSS visual properties | `dress-blueprint-action/assets/css/common.css` |

   **For `tests` goal:** Parse test error output. Group failures by module/file. Fix strategy is driven by error messages and stack traces rather than predefined categories.

   **For custom validator thresholds:** Identify which validators fell below their threshold. Apply validator-specific remediation (e.g., T5 failures -> CSS color variable fixes, T6 failures -> replace hardcoded colors with CSS variables).

3. **Spawn fix agents:**

   **Crush mode (default):** Group all failures by category (for `qa`) or by target file (for `tests`/validators). Spawn up to 4 concurrent `sbs-developer` agents, one per non-overlapping file group. All categories are addressed within the same iteration.

   **Sequential mode (`--single`):** Process one failure category at a time. Spawn agent(s) for the first category, wait for completion, then proceed to the next.

   For each agent:
   1. Query `ask_oracle` for affected files
   2. Provide specific fix instructions (criterion ID, expected value, actual value, affected file paths)
   3. Include adaptation notes for N > 1

### Transition

```
# Normal mode (always introspect):
sbs_skill_transition(skill="converge", to_phase="introspect-<N>")

# Hardcore mode, even iteration (skip introspect):
sbs_skill_transition(skill="converge", to_phase="rebuild-<N>")

# Hardcore mode, odd iteration (introspect):
sbs_skill_transition(skill="converge", to_phase="introspect-<N>")
```

---

## Phase: Introspect-N (In-Loop Reflection, iteration N)

**Purpose:** Reflect on Fix-N outcomes, compare with prior iterations, produce adaptation notes for the next cycle. Fully autonomous -- no user interaction.

### Tick-Tock Cadence (Hardcore Mode)

In **normal mode**, introspect runs every iteration (unchanged).

In **hardcore mode**, introspect follows a tick-tock cadence:
- **Odd iterations (1, 3, 5, ...):** Full introspect phase runs (tick)
- **Even iterations (2, 4, 6, ...):** Skip introspect entirely (tock). Transition directly from `fix-N` to `rebuild-N`. Fix agents on even iterations still receive adaptation notes from the most recent odd-iteration introspect.

When skipping introspect on even iterations, the phase transition is:
```
fix-N -> rebuild-N  (skip introspect-N)
```

### Entry

```
sbs_skill_transition(skill="converge", to_phase="introspect-<N>")
```

(Only reached on odd iterations in hardcore mode, or every iteration in normal mode.)

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

### Recursive Tick-Tock (Hardcore Mode)

In hardcore mode, introspection levels above L2 also follow a tick-tock cadence:

- **L2** runs on odd converge iterations (1, 3, 5, ...) as described in the Introspect-N phase
- **L3** runs every other L2 completion (i.e., every 4th converge iteration: 1, 5, 9, ...)
- **L(N+1)** runs every other L(N) completion

To determine whether L3 should run, query the archive for previous `converge` entries with `hardcore` context:
```
sbs_search_entries(tags=["converge-hardcore-l2-complete"], limit=10)
```
Count completions since the last L3 run. If the count is even (0, 2, 4, ...), run L3. If odd, skip.

The pattern generalizes: each level N+1 fires every other level N, producing a geometric decay in introspection frequency. This prevents introspection overhead from dominating long-running hardcore sessions.

---

## Safety Mechanisms

1. **Hard iteration cap:** Max 3 iterations (configurable via `--max-iter`). **DISABLED** in hardcore mode.
2. **Plateau detection:** Stop if pass rate does not improve between iterations. **DISABLED** in hardcore mode.
3. **Build failure:** Halt immediately, report, `sbs_skill_fail()`. Active in ALL modes.
4. **Agent failure:** Retry once, then skip that fix and continue (do not block entire iteration)
5. **No gate overrides:** Unlike /task, converge does not ask for gate override -- it reports and stops
6. **No user interaction during loop:** The entire loop runs without AskUserQuestion calls
7. **Introspection is non-blocking:** If `sbs_improvement_capture` or `sbs_issue_log` fails, log the error and continue. Introspection tool failures must never halt the convergence loop.
8. **Hardcore stagnation warning:** In hardcore mode, if 3 consecutive iterations show no improvement in pass rate, log a warning via `sbs_improvement_capture(observation="Hardcore converge: 3 consecutive iterations with no improvement (iterations N-2 through N). Pass rate stalled at X%. Consider manual intervention.", category="process")`. The loop continues running -- this is a soft warning, not an exit condition. The warning repeats every 3 stagnant iterations.
9. **Hardcore mode monitoring:** Hardcore mode has no iteration cap and runs indefinitely. Users should monitor long-running sessions periodically. The tick-tock introspection cadence and stagnation warnings provide visibility into progress.

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
| `fix-2` | Second remediation pass | -> introspect-2 (normal) or rebuild-2 (hardcore) |
| `introspect-2` | Reflect on iteration 2 (normal mode only) | -> rebuild-2 |
| `rebuild-2` | Rebuild after fix-2 | -> eval-3 |
| `eval-3` | Third QA evaluation | -> report (normal: max reached) or fix-3 (hardcore: continues) |
| `report` | Convergence summary, cleanup | -> handoff to introspect L3 or end |

In **normal mode**, iteration count is bounded by `max_iterations` (default 3) and the table above shows the typical full run.

In **hardcore mode**, the iteration count is unbounded. The pattern continues as `eval-N -> fix-N -> [introspect-N] -> rebuild-N -> eval-(N+1)` indefinitely, where `introspect-N` phases only appear on odd N (tick-tock cadence). The loop exits only on 100% pass rate or build failure.

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
- **Running introspect on even iterations in hardcore mode**: Tick-tock cadence means even iterations skip introspect. Transition directly from fix-N to rebuild-N.
- **Bailing on plateau in hardcore mode**: Hardcore mode disables plateau exit. Only 100% pass or build failure can stop the loop.
