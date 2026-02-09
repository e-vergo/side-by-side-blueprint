# Plan: Fix Blueprint Artifacts - Read from blueprintExt

## Three Separate Issues

1. **Proof dropdowns don't appear** - `\begin{proof}` blocks not generated correctly
2. **Second run doesn't generate artifacts** - Lake caching prevents re-elaboration
3. **Dependency graph missing nodes** - `\uses{...}` commands not emitted

## Root Cause: Dress Re-parses Instead of Reading blueprintExt

**Current Problem:**
- Dress's `Capture.Config.lean` re-parses @[blueprint] attribute syntax
- Line 182 explicitly SKIPS `uses`/`proofUses`: "uses, proofUses require name resolution"
- Result: `config.usesLabels` is empty → no `\uses{...}` → broken dependency graph

**Key Finding: Timing Works**

After `elabCommandTopLevel stx` returns in ElabRules.lean, `blueprintExt.find? env resolvedName` is immediately available with the full Node data. LeanArchitect's attribute runs `.afterCompilation` which executes synchronously during command elaboration.

This means Dress CAN read from `blueprintExt` during elaboration - no need for complex facet-based deferred generation.

## Solution: Read from blueprintExt Instead of Re-parsing

### Step 1: Modify ElabRules.lean

**File:** `/Users/eric/GitHub/Dress/Dress/Capture/ElabRules.lean`

After `elabCommandTopLevel stx` (line ~131), replace `parseBlueprintConfig` call with:
```lean
let some node := Architect.blueprintExt.find? (← getEnv) resolvedName
  | throwError "blueprintExt not populated for {resolvedName}"
-- Use node.latexLabel, node.statement, node.proof, etc.
```

### Step 2: Update generateDeclarationTex

**File:** `/Users/eric/GitHub/Dress/Dress/Generate/Latex.lean`

Add overload that accepts `Architect.Node` instead of `BlueprintConfig`:
```lean
def generateDeclarationTexFromNode (name : Name) (node : Architect.Node)
    (highlighting : Option Highlighted) (file : Option System.FilePath)
    (location : Option DeclarationRange) : CommandElabM String := do
  -- Use node.latexLabel instead of config.latexLabel
  -- Use node.statement.text instead of config.statement
  -- Use node.proof.map (·.text) instead of config.proof
  -- Use node.statement.usesLabels instead of config.usesLabels
  -- etc.
```

### Step 3: Simplify or Remove Config.lean

**File:** `/Users/eric/GitHub/Dress/Dress/Capture/Config.lean`

Either:
- Remove entirely (if no longer needed)
- Or simplify to only extract the label for artifact paths (minimal parsing)

### Step 4: Fix Second-Run Caching

**File:** `/Users/eric/GitHub/General_Crystallographic_Restriction/scripts/build_blueprint.sh`

Add trace file cleaning:
```bash
rm -rf "$PROJECT_ROOT/.lake/build/lib/Crystallographic"
rm -rf "$PROJECT_ROOT/.lake/build/Crystallographic"  # trace files
```

## Files to Modify

| File | Change |
|------|--------|
| `Dress/Dress/Capture/ElabRules.lean` | Replace `parseBlueprintConfig` with `blueprintExt.find?` |
| `Dress/Dress/Generate/Latex.lean` | Add `generateDeclarationTexFromNode` using `Architect.Node` |
| `Dress/Dress/Capture/Config.lean` | Remove or simplify (no longer needed for full config) |
| `scripts/build_blueprint.sh` | Add `rm -rf "$PROJECT_ROOT/.lake/build/Crystallographic"` |

## Why This Fixes All Three Issues

1. **Proof dropdowns**: `Node.proof : Option NodePart` has full proof text → proper `\begin{proof}` blocks
2. **Second run**: Clean trace files forces re-elaboration
3. **Dependencies**: `Node.statement.usesLabels` is populated by LeanArchitect → correct `\uses{...}`

## Verification

```bash
# 1. Build twice
./scripts/build_blueprint.sh
./scripts/build_blueprint.sh

# 2. Check artifacts exist
find .lake/build/dressed -name "decl.json" | wc -l  # > 0

# 3. Check dependencies
grep -r "\\\\uses{" .lake/build/dressed/  # Should show matches

# 4. Check proof blocks
grep -r "begin{proof}" .lake/build/dressed/  # Should show matches

# 5. Verify in browser at http://localhost:8000
# - Proof dropdowns should be collapsible
# - Dependency graph should show all nodes with edges
```
