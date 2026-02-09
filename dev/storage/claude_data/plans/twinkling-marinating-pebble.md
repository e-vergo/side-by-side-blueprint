# Implementation Plan: 5-Issue Crush Session

**Issues:** #190 (tactic-mode proofs), #189/#188/#187 (paper bugs), #206 (skill restructuring)
**Strategy:** 3 sequential waves, 4 total agents, ~30min end-to-end

---

## Wave 1: Tactic-Mode Proofs (#190)

**Agent:** Single sbs-developer
**Complexity:** Trivial (~5min)

### Changes

**File:** `toolchain/SBS-Test/SBSTest/BracketDemo.lean`

Add 2 theorems with multi-tactic `by` blocks:

```lean
@[blueprint]
theorem nat_add_comm_tactic (n m : Nat) : n + m = m + n := by
  induction m with
  | zero => simp [Nat.add_zero, Nat.zero_add]
  | succ m ih => simp [Nat.add_succ, Nat.succ_add, ih]

@[blueprint]
theorem list_length_append_tactic {α : Type} (xs ys : List α) :
    (xs ++ ys).length = xs.length + ys.length := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
    simp [List.length_cons, List.cons_append]
    exact Nat.succ_add xs.length ys.length ▸ congrArg Nat.succ ih
```

### Validation

1. Build: `cd toolchain/SBS-Test && python ../../dev/scripts/build.py`
2. Capture: `cd dev/scripts && python3 -m sbs capture --project SBSTest --interactive`
3. Compliance: `python3 -m sbs compliance --project SBSTest`
4. Verify: `tactic_state_toggle` criterion passes

### Gates
- Change-based validators (likely none - pure Lean)
- Evergreen tests: `pytest sbs/tests/pytest -m evergreen --tb=short`
- Success: `tactic_state_toggle` passes

---

## Wave 2: Paper Bug Fix (#189, #188, #187)

**Agent:** Single sbs-developer
**Complexity:** Moderate (~15min)
**Root cause:** TeX paper rendering doesn't load artifacts

### Changes

**File:** `toolchain/Runway/Runway/Html/Render.lean`

**1. Add imports (top of file):**
```lean
import Runway.Paper
import Runway.Site
```

**2. Define RenderContext (before RenderState, ~line 40):**
```lean
structure RenderContext where
  artifacts : HashMap String NodeInfo
  baseUrl : String := ""
  deriving Inhabited
```

**3. Extend RenderM monad (~line 44):**
```lean
-- Current: abbrev RenderM := StateM RenderState
-- New:
abbrev RenderM := ReaderT RenderContext (StateM RenderState)
```

**4. Update render() entry point (~lines 291-294):**

Add artifacts parameter and thread context:
```lean
def render (doc : Latex.Document) (config : RenderConfig := {})
    (artifacts : HashMap String NodeInfo := {}) (baseUrl : String := "") : String :=
  let initialState : RenderState := {}
  let initialContext : RenderContext := { artifacts, baseUrl }
  let (html, _) := (Render.renderBlock config doc.root).run initialContext |>.run initialState
  Html.doctype ++ "\n" ++ html.asString
```

**5. Replace placeholder handlers (lines 265-278):**

```lean
| .paperStatement label => do
  let ctx ← read
  let normalizedLabel := label.replace ":" "-"
  match ctx.artifacts.get? normalizedLabel with
  | some node =>
    let _ ← registerLabel label
    let paperNode := Paper.toPaperNodeInfoExt node ctx.baseUrl
    return Paper.renderStatementSbs paperNode
  | none =>
    let _ ← registerLabel label
    return .tag "div" #[("id", labelToId label), ("class", "paper-statement error")]
      (Html.text true s!"[Statement not found: {label}]")

| .paperFull label => do
  let ctx ← read
  let normalizedLabel := label.replace ":" "-"
  match ctx.artifacts.get? normalizedLabel with
  | some node =>
    let _ ← registerLabel label
    let paperNode := Paper.toPaperNodeInfoExt node ctx.baseUrl
    return Paper.renderFullSbs paperNode
  | none =>
    let _ ← registerLabel label
    return .tag "div" #[("id", labelToId label), ("class", "paper-full error")]
      (Html.text true s!"[Full not found: {label}]")

| .paperProof label => do
  let ctx ← read
  let normalizedLabel := label.replace ":" "-"
  match ctx.artifacts.get? normalizedLabel with
  | some node =>
    let _ ← registerLabel label
    let paperNode := Paper.toPaperNodeInfoExt node ctx.baseUrl
    return Paper.renderProofOnly paperNode
  | none =>
    let _ ← registerLabel label
    return .tag "div" #[("id", labelToId label), ("class", "paper-proof error")]
      (Html.text true s!"[Proof not found: {label}]")
```

**6. Find and update all callers of render()** in Runway repo (likely TexPaper.lean or similar)

### Validation

1. Build GCR: `cd showcase/GCR && python ../../dev/scripts/build.py`
2. Capture: `cd dev/scripts && python3 -m sbs capture --project GCR --pages paper_tex`
3. Visual inspection: Open `dev/storage/qa/screenshots/GCR/paper_tex_*.png`
   - Verify SBS layout renders (no placeholder text)
   - Confirm side-by-side blocks appear
4. Compliance: `python3 -m sbs compliance --project GCR`

### Gates
- Change-based validators (Runway → likely T5/T6)
- Evergreen tests
- Success: Visual inspection shows rendered SBS blocks

---

## Wave 3: Skill Restructuring (#206)

**Agents:** 2 sbs-developers (parallel, non-overlapping files)
**Complexity:** Moderate (~10min)

### Agent 3: Skill Files + CLAUDE.md

**1. Rename directory:**
```bash
git mv .claude/skills/update-and-archive .claude/skills/end-epoch
```

**2. File: `.claude/skills/end-epoch/SKILL.md`**
- Line 2: `name: update-and-archive` → `name: end-epoch`
- Line 7: `# /update-and-archive` → `# /end-epoch`
- All examples with `"update-and-archive"` → `"end-epoch"`
- Update description to mention "epoch closing"

**3. File: `.claude/skills/task/SKILL.md`**
- Lines 393-404: Handoff examples
  ```lean
  sbs_skill_handoff(
      from_skill="task",
      to_skill="end-epoch",  // was "update-and-archive"
      to_substate="retrospective"
  )
  ```

**4. File: `.claude/skills/introspect/SKILL.md`**
- Renumber ALL levels: L2→L1, L3→L2, L4+→L3+
- Update parameter validation: `level >= 2` → `level >= 1`
- Update workflow references to new numbering (~30 occurrences)

**5. File: `CLAUDE.md`**
- Section "Custom Skills" → update `/update-and-archive` header and references
- Update workflow diagrams showing skill transitions

### Agent 4: sbs-lsp-mcp Submodule

**1. File: `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py`**

**CRITICAL: VALID_TRANSITIONS dictionary (~line 3136-3141):**
```python
# Change key:
"end-epoch": {  # was "update-and-archive"
    "retrospective": {"readme-wave"},
    "readme-wave": {"oracle-regen"},
    "oracle-regen": {"porcelain"},
    "porcelain": {"archive-upload"},
}
```

**Update docstrings:**
- All examples with "update-and-archive" → "end-epoch"
- All skill name lists in descriptions

**2. File: `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py`**
- Field descriptions: "task, update-and-archive, log" → "task, end-epoch, log"

### Validation

**Grep verification (Agent 3):**
```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint
grep -r "update-and-archive" .claude/  # expect 0 results
grep -r "update-and-archive" CLAUDE.md  # expect 0 results
```

**Grep verification (Agent 4):**
```bash
cd forks/sbs-lsp-mcp
grep -r "update-and-archive" src/  # expect 0 results (except comments)
python3 -m py_compile src/sbs_lsp_mcp/sbs_tools.py
python3 -m py_compile src/sbs_lsp_mcp/sbs_models.py
```

**Live integration test (both agents complete):**
1. Restart MCP server (reload submodule)
2. User invokes: `/end-epoch` with observation
3. Verify:
   - Skill starts without errors
   - Archive records `skill: "end-epoch"`
   - Workflow completes normally

### Gates
- Change-based validators (likely none - refactoring only)
- Evergreen tests
- Success: Live integration test passes, grep checks return 0 results

---

## Critical Files Reference

| Wave | Files |
|------|-------|
| 1 | `toolchain/SBS-Test/SBSTest/BracketDemo.lean` |
| 2 | `toolchain/Runway/Runway/Html/Render.lean` (primary)<br>`toolchain/Runway/Runway/Paper.lean` (reference)<br>Callers of `render()` in Runway |
| 3 | `.claude/skills/end-epoch/SKILL.md`<br>`.claude/skills/task/SKILL.md`<br>`.claude/skills/introspect/SKILL.md`<br>`CLAUDE.md`<br>`forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py`<br>`forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` |

---

## Final Gate (All Waves)

After all 3 waves complete:
- All evergreen tests pass
- All compliance checks pass (SBSTest, GCR)
- Live integration test passes
- Visual inspection confirms paper rendering works

---

## Execution Notes

- **Wave order:** Sequential (1 → 2 → 3) for increasing complexity
- **Wave 3 parallelization:** Agents 3 and 4 run concurrently (non-overlapping files)
- **MCP restart:** Required after Wave 3 Agent 4 completes (submodule changes)
- **User participation:** Live integration test in Wave 3 (observing /end-epoch invocation)
