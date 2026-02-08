# Task Crush: 7 Issues

**Issues:** #172, #173, #174, #175, #178, #179, #180
**Branch:** `task/crush-7-issues`

---

## Wave 0: Direct Closures (no agents)

### #179 — Multiagent in skill phases beyond /introspect
**Already addressed.** CLAUDE.md documents multiagent (up to 4 concurrent `sbs-developer` agents) during ALL `/task` phases (alignment, planning, execution, finalization) and during `/introspect`. The "Multiagent Behavior Definition" section explicitly lists allowed/disallowed contexts.
**Action:** Close with comment noting it's already implemented.

### #180 — SBS-Test should display all 6 status colors
**Already addressed.** `toolchain/SBS-Test/SBSTest/StatusDemo.lean` contains 15 blueprint declarations covering all 6 statuses: notReady (`foundation`), ready (`ready_to_prove`, `another_ready`), sorry (`has_sorry`, `also_sorry`), proven (`proven_leaf`, `proven_mid`, `proven_chain`), fullyProven (`fully_chain_1..3`), mathlibReady (`mathlib_theorem`).
**Action:** Close with comment noting StatusDemo.lean covers all 6.

---

## Wave 1: Converge Skill Docs (1 agent, sequential edits)

### #178 — /converge should use crush mode by default
**File:** `.claude/skills/converge/SKILL.md`
**Change:** Add `/converge crush <project>` invocation pattern. Make crush the default behavior — `/converge GCR` triggers crush mode (build+eval+fix loop on all QA failures, not just first). Add `--single` flag for old behavior (one failure at a time).

### #173 — Generalize /converge to accept arbitrary goals/thresholds
**File:** `.claude/skills/converge/SKILL.md`
**Change:** Add goal specification to invocation:
- `/converge GCR --goal "T5 >= 0.9, T6 >= 0.95"` — custom thresholds
- `/converge GCR --goal qa` — default QA criteria (current behavior)
- `/converge GCR --goal tests` — pytest pass rate convergence
- Eval-N phase reads goal spec to determine what to evaluate
- Fix-N phase derives fixes from goal-specific failure analysis

Both edits target the same file so 1 agent handles them sequentially.

---

## Wave 2: Visual/Theme Fixes (3 parallel agents)

### Agent A: #175 — Proof toggle one-line gap
**Files:**
- `toolchain/dress-blueprint-action/assets/plastex.js` (lines 82-98)
- `toolchain/dress-blueprint-action/assets/verso-code.js` (lines 186-211)

**Root cause:** jQuery `slideDown()` sets `display: block` on `<code class="lean-proof-body">`. Combined with leading `\n` in proof body content inside `<pre>`, this creates a visible blank line.

**Fix:** Add CSS rule `.lean-proof-body { display: none; }` is already present. The fix is to strip leading whitespace when slideDown completes, or better: add a CSS callback. Simplest approach: add `.lean-proof-body { white-space: pre; }` override on slideDown to trim the visual gap. Specifically:
1. In `plastex.js`: Change `slideDown()` to `slideDown(300, function() { $(this).css('display', 'inline'); })` — force inline display after animation
2. In `verso-code.js`: Same pattern for the slideDown call
3. Or simpler: add CSS `.lean-proof-body.visible { display: inline !important; }` and toggle class instead of relying on slideDown's default block behavior

**Agent decides best approach** from these options.

### Agent B: #172 — Remove prefers-color-scheme auto-detect
**Files:**
- `toolchain/dress-blueprint-action/assets/common.css` (lines 318-329) — remove `@media (prefers-color-scheme: dark)` block
- `toolchain/dress-blueprint-action/assets/plastex.js` (lines 4-13, 35-42) — remove system preference check from `getPreferredTheme()`, remove `matchMedia` listener

**Fix:**
1. Delete CSS media query block (lines 318-329)
2. Simplify `getPreferredTheme()` to only check localStorage, default to `'light'`
3. Remove the `matchMedia` event listener (lines 35-42)

### Agent C: #174 — GCR rainbow bracket regression
**Files:**
- `showcase/GCR/lake-manifest.json` — update verso commit from `b17723e` to current HEAD (`7ecb0b7`)
- Also update any other stale dependency pins (Dress, SubVerso, LeanArchitect) to match SBS-Test's versions

**Fix:** Update the verso (and related) entries in GCR's lake-manifest.json to match current HEAD commits. Then GCR needs a rebuild (handled in rebuild phase).

---

## Wave 3: Removed

#180 moved to Wave 0. No Wave 3 needed.

---

## Rebuild Phase

After Wave 2 completes:
1. **Rebuild SBS-Test** — validates #175, #172 changes in dress-blueprint-action assets
2. **Rebuild GCR** — validates #174 manifest update + picks up #175/#172 asset changes

---

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  quality:
    T5: >= 0.8
    T6: >= 0.8
  regression: >= 0
```

---

## Verification

1. Evergreen tests pass: `sbs_run_tests(tier="evergreen")`
2. SBS-Test validators: `sbs_validate_project(project="SBSTest", validators=["T5", "T6"])`
3. GCR validators: `sbs_validate_project(project="GCR", validators=["T5", "T6"])`
4. Visual spot-check: proof toggle on SBS-Test shows no gap, theme starts as light (no auto-detect)
5. GCR dep_graph: rainbow brackets display correct nesting colors
