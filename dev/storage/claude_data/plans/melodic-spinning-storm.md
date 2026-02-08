# Crush Plan: 9 Issues (8 resolve + 1 investigate)

**Issues:** #156, #153, #154, #152, #150, #142, #146, #143, #148
**Deferred:** #99 (architectural), #149 (exploratory docs)

---

## Wave 0: Investigation (no agents)

**#148 — Tactic toggle absent from chapter pages**
- Spawn 1 Explore agent to trace the rendering pipeline:
  - Check if SBS-Test theorems have tactic-mode proofs in Lean source
  - Check if Dress artifact generation emits tactic state data
  - Check if Runway Theme.lean renders `input.tactic-toggle` elements
  - Check built HTML in `_site/` for toggle presence
- Log findings as comment on #148; do NOT close — fix deferred

---

## Wave 1: Parallel Fixes (2 agents)

**#156 — Remove top bar from all pages**
- Files: `toolchain/dress-blueprint-action/assets/blueprint.css`
- Action: Hide/remove `body>header` rule (line 117) and related selectors (`#toc-toggle`, `h1#doc_title`, `#doc_title a`)
- Verification: Build SBSTest, capture screenshots, confirm header absent on dashboard + chapter pages
- Close #156

**#153 — sbs_serve_project unhelpful errors**
- Files: `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` (sbs_serve_project, ~line 860)
- Action: Add descriptive error messages to `ServeResult` returns for each failure case:
  - Unknown project name → "Unknown project '<name>'. Valid: SBSTest, GCR, PNT"
  - Missing `_site/` dir → "Site directory not found at <path>. Run build first."
  - Port already in use → "Port <N> already in use"
  - Process start failure → include subprocess stderr
- Verification: Run existing MCP tests; manually test with invalid project name
- Close #153

---

## Wave 2: Parallel Docs (2 agents)

**#154 — Add metric verification step to /task finalization**
- Files: `.claude/skills/task/SKILL.md`
- Action: Strengthen Phase 4 (Finalization) to explicitly reference the Metric Gates section. Add a checklist step: "Verify gate results are recorded in archive entry with pass/fail values." Currently the finalization section says "Run full validation suite" but doesn't mandate recording results or cross-referencing the gate definitions from the plan.
- Close #154

**#152 — Codify explore-before-ask principle**
- Files: `.claude/skills/task/SKILL.md` (alignment phase), `.claude/agents/sbs-developer.md` (Information Gathering Protocol section)
- Action: Add explicit "explore-before-ask" guidance for runtime/configuration state. The agent already has oracle-first for codebase questions; this extends to system state: check `sbs_archive_state`, `sbs_skill_status`, server status, build caches, etc. before asking user. Add 2-3 concrete examples.
- Close #152

---

## Wave 3: Parallel Trivial Code (2 agents)

**#150 — Add crush:ignore label to taxonomy**
- Files: `dev/storage/labels/taxonomy.yaml`
- Action: Add `crush:ignore` to the `standalone` section (after `ai-authored`). Description: "Issue excluded from /task crush batch processing"
- Post-edit: Run `python3 -m sbs labels sync` to push to GitHub
- Verification: `pytest sbs/tests/pytest/test_taxonomy.py -v`
- Close #150

**#142 — E2E MCP test for sbs_improvement_capture**
- Files: `forks/sbs-lsp-mcp/tests/test_skill_tools.py` (append new test class)
- Action: Add `TestImprovementCapture` class following existing patterns:
  - Test successful capture with explicit category
  - Test successful capture with default category
  - Test invalid category returns error
  - Test capture records correct tags (`improvement:<category>`, `trigger:improvement`)
- Pattern: Mock `load_archive_index` + `_run_archive_upload`, assert `ImprovementCaptureResult` fields
- Verification: Run the new tests
- Close #142

---

## Wave 4: Parallel Moderate Code (2 agents)

**#146 — IO/IO(msg) shorthand for improvement tagging**
- Files: `CLAUDE.md` (User Preferences section)
- Action: Add behavioral instruction recognizing `IO` and `IO(message)` patterns in user messages. When detected, invoke `sbs_improvement_capture` MCP tool. For bare `IO`, infer observation from recent conversation context. For `IO(message)`, use the message directly. This is a CLAUDE.md instruction, not code — the existing MCP tool handles the actual capture.
- Close #146

**#143 — Integrate validators into build.py pipeline**
- Files: `dev/scripts/sbs/build/orchestrator.py`
- Action: Add a new phase after compliance_checks that runs deterministic validators (T1, T2, T5, T6) via the existing `run_validators` function from `sbs.tests.validators.runner`. Follow the compliance_checks pattern: `_start_phase` / run / `_end_phase`. Failures should be warnings (non-blocking) since validators are informational during builds. Results update the quality ledger automatically (`update_ledger=True`).
- Import: `from sbs.tests.validators.runner import run_validators`
- Verification: Run `python3 dev/scripts/build.py --dry-run` to verify import chain; run SBSTest build to verify integration
- Close #143

---

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  taxonomy: pytest sbs/tests/pytest/test_taxonomy.py -v  # For #150
  mcp_tests: pytest forks/sbs-lsp-mcp/tests/test_skill_tools.py -v  # For #142
  regression: >= 0
```

---

## Execution Order

```
Wave 0 (#148 investigation)     → 1 explore agent
Wave 1 (#156 + #153)            → 2 sbs-developer agents in parallel
Wave 2 (#154 + #152)            → 2 sbs-developer agents in parallel
Wave 3 (#150 + #142)            → 2 sbs-developer agents in parallel
Wave 4 (#146 + #143)            → 2 sbs-developer agents in parallel
Gate validation                  → evergreen tests + taxonomy + MCP tests
Finalization                     → close issues, merge PR
```

Waves are sequential. Agents within a wave are parallel.

## Verification

1. Evergreen tests pass: `sbs_run_tests(tier="evergreen")`
2. Taxonomy tests pass: `sbs_run_tests(filter="test_taxonomy")`
3. MCP skill tests pass (for #142)
4. SBSTest build succeeds with validator integration (#143)
5. Screenshots confirm top bar removal (#156)
