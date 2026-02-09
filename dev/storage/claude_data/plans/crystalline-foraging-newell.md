# SubVerso Changes for Tactic Mode Support

## Summary

Enable hover tooltips AND proper syntax highlighting for terms inside tactic proof bodies (e.g., lemma names in `exact foo`, `rw [bar]`).

**File to Modify:** `/Users/eric/GitHub/subverso/src/SubVerso/Highlighting/Code.lean`

---

## Current Status

### Completed
- **Build script**: Updated to use `BLUEPRINT_DRESS=1` environment variable
- **Tippy.js hover system**: Ported from Verso to leanblueprint

### Current State

The SubVerso change to `identKind` was **reverted** when debugging build issues. The change needs to be re-applied and properly pushed to e-vergo/subverso.

**What's working now:**
- Hover for tactic keywords (simp, rw, exact)
- Hover for variables with direct TermInfo matches
- Syntax highlighting for the above

**What's NOT working:**
- Hover for lemma names inside brackets (`simp [psi]`, `rw [foo.bar]`)
- Syntax highlighting for the above (shows as "unknown token")

**Current HTML output** shows `"unknown token"` for lemma names inside tactic brackets:
```html
<span class="keyword token">simp</span> <span class="keyword token">only</span>
<span class="unknown token">[</span>
<span class="unknown token">psi</span>           <!-- Should be "const token" with hover -->
<span class="unknown token">]</span>
```

---

## The Fix (Same for Hover AND Syntax Highlighting)

The `identKind` function returns `Token.Kind` which controls BOTH:
1. **CSS class** (const, var, keyword, unknown)
2. **Hover data** (type signature, docs)

Adding `infoIncludingSyntax` fallback fixes both issues at once.

---

## Root Cause Analysis

### Why Tactic Arguments Don't Get Hover Info

1. **InfoTable only stores TacticInfo** (line 37-38):
   ```lean
   structure InfoTable where
     tacticInfo : Compat.HashMap Compat.Syntax.Range (Array (ContextInfo × TacticInfo)) := {}
   ```

2. **InfoTable.add discards all non-tactic info** (lines 45-53):
   ```lean
   def InfoTable.add (ctx : ContextInfo) (i : Info) (table : InfoTable) : InfoTable :=
     match i with
     | .ofTacticInfo ti => { table with tacticInfo := ... }
     | _ => table  -- TermInfo discarded here!
   ```

3. **`infoKind` returns `none` for TacticInfo** (line 392):
   ```lean
   | .ofTacticInfo _ => pure none  -- No hover data generated
   ```

### Key Finding

TermInfo nodes **DO exist** nested within TacticInfo in Lean's info tree. The function `infoForSyntax` (lines 93-98) already finds ALL nested info nodes. SubVerso **actively filters them out** - this is a design choice, not a technical limitation.

---

## Implementation Options

### Option 1: Extend InfoTable to Store TermInfo (Recommended)

**Pros:** Clean, maintains existing architecture
**Cons:** More invasive change

**Changes:**

1. **Modify InfoTable structure** (line 37):
   ```lean
   structure InfoTable where
     tacticInfo : Compat.HashMap Compat.Syntax.Range (Array (ContextInfo × TacticInfo)) := {}
     termInfo : Compat.HashMap Compat.Syntax.Range (Array (ContextInfo × TermInfo)) := {}  -- ADD
   ```

2. **Update InfoTable.add** (line 45):
   ```lean
   def InfoTable.add (ctx : ContextInfo) (i : Info) (table : InfoTable) : InfoTable :=
     match i with
     | .ofTermInfo ti =>
       if let some rng := ti.stx.getRange? (canonicalOnly := true) then
         { table with termInfo := table.termInfo.insert rng <|
           ((Compat.HashMap.get? table.termInfo rng).getD #[]).push (ctx, ti)
         }
       else table
     | .ofTacticInfo ti =>
       if let some rng := ti.stx.getRange? (canonicalOnly := true) then
         { table with tacticInfo := table.tacticInfo.insert rng <|
           ((Compat.HashMap.get? table.tacticInfo rng).getD #[]).push (ctx, ti)
         }
       else table
     | _ => table
   ```

3. **Add lookup function** for TermInfo similar to `findTactics`

### Option 2: Modify `identKind` Lookup (Minimal Change)

**Pros:** Smallest code change
**Cons:** May miss some cases

The `identKind` function (lines 399-409) already iterates through ALL info from `infoForSyntax`, which finds both TacticInfo and TermInfo. The issue is that when it calls `infoKind` on TermInfo, it works fine - the problem is that some tokens inside tactics don't have direct syntax matches.

**Change:** Use `infoIncludingSyntax` instead of `infoForSyntax` to find info nodes that *include* the given syntax:

```lean
def identKind ... := do
  let mut kind : Token.Kind := .unknown
  for t in trees do
    -- CHANGE: Use infoIncludingSyntax for broader search
    for (ci, info) in infoIncludingSyntax t stx do
      if let some seen ← infoKind ci info (allowUnknownTyped := allowUnknownTyped) then
        if seen.priority > kind.priority then kind := seen
  pure kind
```

### Option 3: Enable `pp.tagAppFns` Globally for Tactic Highlighting

**Pros:** Works for function applications
**Cons:** Only helps function applications, not all terms

Lines 1076-1082 show this option is enabled only for goal state rendering:
```lean
let ci' := { ci with options :=
    ci.options |>.set `pp.tagAppFns true |>.set `maxHeartbeats maxHeartbeats
  }
```

Could be enabled when highlighting tactic syntax in `highlight'`.

---

## Known Limitations

**Numeric literals in tactics will NOT get hover info** regardless of fix approach. This is a Lean core limitation - the elaborator doesn't produce TermInfo for numeric literals inside tactics. Example:

```
stx=[anonymous] found 1 info nodes: 0 TermInfo, 1 TacticInfo → kind=unknown
```

This would require changes to Lean's tactic elaborator, which is out of scope.

---

## Recommended Implementation Plan

### Step 1: Diagnostic Verification
Add tracing to `identKind` to confirm TermInfo exists for tactic arguments:
```lean
for (ci, info) in infoForSyntax t stx do
  dbg_trace s!"stx={stx.raw.getKind} found info: {info.isOfTermInfo}"
```

### Step 2: Try Option 2 First (Minimal Change)
Replace `infoForSyntax` with `infoIncludingSyntax` in `identKind` to see if broader search finds TermInfo.

### Step 3: If Step 2 Fails, Implement Option 1
Extend InfoTable to store both TacticInfo and TermInfo.

### Step 4: Test
- Build SubVerso
- Build Dress against modified SubVerso
- Build Crystallographic blueprint
- Verify hovers appear on tactic arguments

---

## Files Summary

| File | Location | Change |
|------|----------|--------|
| `Code.lean` | `/Users/eric/GitHub/subverso/src/SubVerso/Highlighting/Code.lean` | Main implementation |

### Key Line Numbers in Code.lean

| Line | Function | Purpose |
|------|----------|---------|
| 37-38 | `InfoTable` | Structure definition - add termInfo field |
| 45-53 | `InfoTable.add` | Add TermInfo storage |
| 93-98 | `infoForSyntax` | Already finds all nested info |
| 382-397 | `infoKind` | Returns none for TacticInfo |
| 399-409 | `identKind` | Main entry point for identifier highlighting |
| 1076-1082 | `highlightGoals` | pp.tagAppFns setting |

---

## Verification

1. Build SubVerso: `cd /Users/eric/GitHub/subverso && lake build`
2. Update Dress lakefile to use local SubVerso
3. Build Dress: `cd /Users/eric/GitHub/Dress && lake build`
4. Rebuild Crystallographic: `lake build :blueprint`
5. Test: Hover over lemma names in proof bodies should show type signatures

---

---

## Implementation Plan (Agent Orchestration)

**Approach**: Single general-purpose agent executes all steps sequentially with full permissions, reporting back after each major step.

### Agent Task Sequence

The agent will execute these steps in order:

**1. Apply SubVerso Change**
- Edit `/Users/eric/GitHub/subverso/src/SubVerso/Highlighting/Code.lean`
- Add `infoIncludingSyntax` fallback to `identKind` (lines 399-409)
- Build SubVerso to verify: `cd /Users/eric/GitHub/subverso && lake build`

**2. Commit and Push SubVerso**
- Create/switch to `tactic-hover-support` branch
- Commit with message: "feat: Enable hover/highlighting for tactic arguments"
- Push to origin (e-vergo/subverso)

**3. Update Dress**
- Edit `/Users/eric/GitHub/Dress/lakefile.lean` to use `tactic-hover-support` branch
- Clean and update: `rm -rf .lake/packages/subverso && lake update subverso`
- Build: `lake build`

**4. Update Crystallographic**
- Update packages: `lake update Dress`
- Run build script: `./scripts/build_blueprint.sh`

**5. Verify Changes**
- Check HTML output for lemma names in tactic brackets
- Confirm `class="const token"` (not "unknown token")
- Confirm `data-verso-hover` attribute present
- Report success/failure

### Code Change Details

**File**: `/Users/eric/GitHub/subverso/src/SubVerso/Highlighting/Code.lean`
**Location**: Lines 399-409, `identKind` function

**Before**:
```lean
def identKind ... := do
  let mut kind : Token.Kind := .unknown
  for t in trees do
    for (ci, info) in infoForSyntax t stx do
      if let some seen ← infoKind ci info ... then
        if seen.priority > kind.priority then kind := seen
  pure kind
```

**After**:
```lean
def identKind ... := do
  let mut kind : Token.Kind := .unknown
  -- First try exact syntax match
  for t in trees do
    for (ci, info) in infoForSyntax t stx do
      if let some seen ← infoKind ci info ... then
        if seen.priority > kind.priority then kind := seen
  -- Fallback: broader search for enclosing info nodes
  if kind == .unknown then
    for t in trees do
      for (ci, info) in infoIncludingSyntax t stx do
        if let some seen ← infoKind ci info ... then
          if seen.priority > kind.priority then kind := seen
  pure kind
```

### Success Criteria

After completion, check `blueprint/web/sect0002.html`:
- Lemma names in `simp [psi]` should have `class="const token"`
- Lemma names should have `data-verso-hover` with valid hover ID
- Hovering shows type signature in browser

---

## Completed Work (Reference)

The following work was completed in previous sessions:

1. **Hover ID collision fix** - Dress now uses stateful rendering to ensure unique hover IDs across signature and proof body
2. **Tippy.js hover system** - Ported Verso's interactive hover system to leanblueprint with Popper.js and Tippy.js
3. **z-index fix** - Fixed invisible tooltips with CSS z-index override
4. **Build script** - Updated to use `BLUEPRINT_DRESS=1` environment variable
