# Plan: Issue #168 — Autonomous QA Convergence Loop

## Summary

Create a `/converge` skill that runs an unattended `/qa -> fix -> rebuild` loop until 100% QA pass rate or max 3 iterations. Also add `--auto` mode documentation to existing `/task` and `/qa` skills.

## Deliverables

| # | File | Action | Description |
|---|------|--------|-------------|
| 1 | `.claude/skills/converge/SKILL.md` | **Create** | New meta-skill for autonomous QA convergence |
| 2 | `.claude/skills/task/SKILL.md` | **Modify** | Add `--auto` mode section for unattended execution |
| 3 | `.claude/skills/qa/SKILL.md` | **Modify** | Add converge integration notes + machine-readable output docs |
| 4 | `CLAUDE.md` | **Modify** | Add `/converge` to Custom Skills section |

No Python code, no Lean code, no infrastructure changes. Pure skill definition work.

---

## Deliverable 1: `/converge` SKILL.md

### Invocation

| Pattern | Behavior |
|---------|----------|
| `/converge GCR` | Run convergence loop on GCR |
| `/converge SBSTest` | Run convergence loop on SBSTest |
| `/converge GCR --max-iter 5` | Override default max iterations (default: 3) |

### Skill Lifecycle

Stateful skill owning `global_state`. Substates encode iteration:

```
setup → eval-1 → fix-1 → eval-2 → fix-2 → eval-3 → report
```

Early exit at any `eval-N` if pass rate = 100% or no improvement over previous iteration (plateau detection as bonus, hard cap at 3 is primary).

### Phase Details

**Setup:**
- `sbs_skill_start(skill="converge", initial_substate="setup")`
- Build project via `sbs_build_project()`
- Start dev server via `sbs_serve_project(action="start")`
- Verify server is running
- Transition to `eval-1`

**Eval-N (QA Evaluation):**
- Navigate to each page type (dashboard, dep_graph, paper_tex, pdf_tex, chapter)
- Evaluate criteria from `criteria.py` using browser MCP tools
- Write results to `dev/storage/<project>/qa_ledger.json`
- Parse failures from ledger
- If 0 failures → transition to `report`
- If N > 1 and failure count >= previous iteration → transition to `report` (plateau)
- Otherwise → transition to `fix-N`

**Fix-N (Remediation):**
- Categorize failures by type (CSS, template, JS, content)
- For each failure category:
  - Query oracle for affected files
  - Spawn sbs-developer agent(s) with specific fix instructions (up to 4 concurrent, non-overlapping files)
- Rebuild project via `sbs_build_project()`
- Wait for build completion
- Transition to `eval-(N+1)`

**No planning phase.** Fix scope is derived directly from QA failure analysis. Each failure maps to a criterion with known category, selector, and expected value — this provides sufficient specification for targeted fixes.

**Report:**
- Generate convergence summary:
  - Iterations run
  - Pass rate per iteration (showing trend)
  - Remaining failures (if any)
  - Issues logged across all iterations
- Stop dev server
- Archive final state
- `sbs_skill_end(skill="converge")`

### Fix Categorization Logic

| QA Failure Category | Fix Strategy | Example |
|---------------------|-------------|---------|
| `color` | Edit CSS variables in `common.css` or status colors | Wrong status dot color |
| `layout` | Edit CSS layout rules or template structure | Missing sidebar, wrong grid |
| `interaction` | Edit JS event handlers or HTML attributes | Toggle not working |
| `content` | Edit Lean templates or document generation | Missing text, wrong labels |
| `visual` | Edit CSS visual properties | Font size, spacing, borders |

### Safety Mechanisms

1. **Hard iteration cap:** Max 3 iterations (configurable)
2. **Plateau detection:** Stop if no improvement between iterations
3. **Build failure:** Halt immediately, report, `sbs_skill_fail()`
4. **Agent failure:** Retry once, then skip that fix and continue (don't block entire iteration)
5. **No gate overrides:** Unlike /task, converge doesn't ask for gate override — it just reports and stops

### Recovery

On compaction, call `sbs_archive_state()`:
- Resume from start of current substate
- `eval-N`: re-run QA evaluation for iteration N
- `fix-N`: check which fixes were committed, re-run remaining
- `report`: re-generate report

### Archive Protocol

Each substate transition records:
```bash
python3 -m sbs archive upload --trigger skill \
  --global-state '{"skill":"converge","substate":"<phase>"}' \
  --state-transition phase_start
```

---

## Deliverable 2: `/task --auto` Mode

Add a new section to `/task` SKILL.md after the "Crush Mode" section:

### Auto Mode (`/task --auto`)

When invoked with `--auto` flag (or driven by `/converge`):

**Skipped phases:**
- Alignment: scope provided externally (QA ledger failures or explicit description)
- Planning: go directly to execution (scope is bounded and pre-analyzed)

**Modified behavior:**
- Gate passes → auto-continue (no confirmation)
- Gate failures → still pause and report (safety valve preserved)
- Issue closure → auto-close on success
- PR merge → auto-merge on gate pass

**Substates in auto mode:**
```
execution → finalization → handoff
```

**Restrictions:**
- Only valid when scope is bounded (QA failures, specific issue fixes)
- Cannot be used for open-ended feature work
- Gate failure still requires manual intervention

---

## Deliverable 3: `/qa` Converge Integration

Add a section to `/qa` SKILL.md documenting:

1. **Machine-readable output**: qa_ledger.json format is stable and consumable by other skills
2. **Converge mode note**: When driven by `/converge`, QA runs identically but results feed the convergence loop
3. **No behavioral changes**: /qa itself doesn't change — converge reuses its evaluation logic and output format

---

## Deliverable 4: CLAUDE.md Update

Add to Custom Skills section:

```markdown
### `/converge`

Autonomous QA convergence loop. Runs QA evaluation, fixes failures, rebuilds, and repeats until 100% pass rate or max iterations.

**Usage:** `/converge GCR`, `/converge SBSTest`

**Workflow:** Setup → [Eval → Fix → Rebuild]×N → Report

**Location:** `.claude/skills/converge/SKILL.md`
```

---

## Execution Plan

**Single wave** — all 4 files can be written in parallel by separate agents since they don't overlap:

| Agent | File | Action |
|-------|------|--------|
| A1 | `.claude/skills/converge/SKILL.md` | Create full skill definition |
| A2 | `.claude/skills/task/SKILL.md` | Add --auto mode section |
| A3 | `.claude/skills/qa/SKILL.md` | Add converge integration section |
| A4 | `CLAUDE.md` | Add /converge to Custom Skills |

---

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
```

Pure documentation changes — validation is that existing tests remain green.

## Verification

1. Run evergreen tests: `sbs_run_tests(tier="evergreen")`
2. Confirm new skill directory exists: `ls .claude/skills/converge/SKILL.md`
3. Confirm CLAUDE.md references `/converge`
4. Manual review: skill definitions are internally consistent and reference correct MCP tools
