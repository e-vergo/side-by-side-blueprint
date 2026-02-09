# Runway Output Analysis and Fix Plan

## Executive Summary

**Blocking Issue**: Node lookup failure - all nodes show "not found" errors. Root cause is label format mismatch: LaTeX uses `def:is-positive` (colons), but HashMap keys use `def-is-positive` (hyphens). **One-line fix** in Theme.lean line ~1006.

**Quick Wins**:
1. Node lookup fix (Theme.lean) - unblocks entire output
2. Path resolution fix (Main.lean) - allows relative paths in runway.json
3. Chapter title format (Theme.lean) - cosmetic

**Larger Changes**:
4. Hierarchical sidebar with expandable sections
5. Theorem numbering (Definition 4.1.1 format)

---

## Current State vs Goal Comparison

### Current Output (Screenshot 2026-01-25 at 4.24.49 PM.png)

The current output shows:
- **Header**: "SBS-Test: Blueprint Feature Demonstration" with blue gradient - GOOD
- **Sidebar**: Simple flat list with chapter titles numbered (1. Introduction, 2. Basic Definitions and Lemmas, etc.) - PARTIAL
- **Content Area**: Chapter 2 is displayed with:
  - Chapter title "Chapter 2: Basic Definitions and Lemmas"
  - Chapter intro prose
  - Section headings (2.1 Definitions, 2.2 Basic Results)
  - **CRITICAL ISSUE**: "Node 'def:is-positive' not found" errors for ALL nodes
  - Prev/next navigation at bottom

### Goal Output (goal2.png)

The Python leanblueprint goal shows:
- **Header**: "Crystallographic Restriction Theorem" with blue gradient
- **Sidebar**: Hierarchical navigation with:
  - Numbered chapters (1. The Psi Function, 2. Companion Matrices, etc.)
  - Expandable sections under chapters (4.1 Definition and Basic Properties, 4.2 Crystallographic...)
  - Indented subsection-level items visible when chapter expanded
- **Content Area**:
  - Chapter title "4 Companion Matrices" (note: no "Chapter" prefix, just number)
  - Intro prose paragraph
  - Section "4.1 Definition and Basic Properties"
  - **FULL SIDE-BY-SIDE RENDERING**:
    - Left column: LaTeX theorem statement with matrix notation
    - Right column: Lean code with syntax highlighting
  - Proof section with toggle ("Proof" with triangle)
  - Numbered definitions/theorems (Definition 4.1.1, Theorem 4.1.2)
  - More prose between theorems

---

## Fundamental Issues Identified

### Issue 1: Node Lookup Failure (CRITICAL)
**Problem**: All nodes show "Node 'def:is-positive' not found" errors.

**Root Cause**: CONFIRMED - Label format mismatch between LaTeX and internal storage.
- LaTeX uses: `\inputleannode{def:is-positive}` (colons)
- Dress artifacts stored in directories like: `nodes/def-is-positive/` (hyphens)
- Artifact HashMap keys use: `def-is-positive` (colons replaced with hyphens via line 325 in Traverse.lean)
- NodeInfo.label is set to: `node.id` which is `def-is-positive`
- Placeholder lookup searches for: `def:is-positive` (raw from LaTeX)

**Evidence**:
```
Artifacts directory: .lake/build/dressed/nodes/def-is-positive/
decl.tex contains: \label{def:is-positive}
Traverse.lean line 325: let key := artifact.label.replace ":" "-"
```

**Location**:
- `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/Theme.lean` lines 1006 (nodeLookup[label]?)
- `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/Traverse.lean` line 325 (key normalization)

---

### Issue 2: Path Resolution (Config file relative paths)
**Problem**: `blueprintTexPath` in `runway.json` requires absolute path workaround.

**Current Code** (`Main.lean` lines 168-177):
```lean
def loadBlueprintChapters (config : Config) (allNodes : Array NodeInfo) : IO (Array ChapterInfo) := do
  match config.blueprintTexPath with
  | none => return #[]
  | some texPath =>
    let path : FilePath := texPath  -- <-- Uses path as-is, not relative to config
    if !(← path.pathExists) then
      IO.eprintln s!"Warning: Blueprint tex file not found at {texPath}"
      return #[]
```

**Fix**: When loading the config, resolve `blueprintTexPath` relative to the config file's directory if it's a relative path.

**Location**: `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Main.lean` around line 102-111 (`loadConfig`)

**Proposed Change**:
1. Accept the config file path as a parameter to track its location
2. After parsing config, if `blueprintTexPath` is relative, resolve it against the config file's parent directory
3. Or: Store config file directory in Config struct and resolve later

---

### Issue 3: Sidebar Missing Hierarchical Structure
**Problem**: Sidebar shows flat chapter list, not expandable chapter/section hierarchy.

**Goal**: Sidebar should show chapters with expandable sections underneath (like goal2.png).

**Current Code**: `renderSidebar` in Theme.lean (lines 675-695) only renders chapters as flat list items.

**Location**: `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/Theme.lean` lines 675-695

**Fix**:
1. Modify `renderSidebar` to include nested `<ul>` for sections within each chapter
2. Add CSS for nested navigation indentation
3. Add JavaScript for expand/collapse functionality
4. Track which chapter is currently expanded (current page's chapter)

---

### Issue 4: Chapter Title Format
**Problem**: Current shows "Chapter 2: Basic Definitions and Lemmas"
**Goal**: Shows "4 Companion Matrices" (just number + title, no "Chapter:" prefix)

**Location**: `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/Theme.lean` lines 1029-1033

**Fix**: Change the title format from `Chapter {number}: {title}` to `{number} {title}`

---

### Issue 5: Missing Numbered Theorem Labels
**Problem**: Theorems/definitions aren't numbered (should be "Definition 4.1.1", "Theorem 4.1.2")

**Goal**: Each theorem environment should have a numbered label based on chapter.section.item

**Current State**: The node rendering likely just shows the environment type without numbering.

**Location**:
- `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/Render.lean` (node rendering)
- `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/Theme.lean` (chapter content rendering)

**Fix**:
1. Track theorem counters per section in ChapterInfo/SectionInfo
2. Pass counter context when rendering nodes
3. Display "Definition {chapter}.{section}.{count}" format

---

### Issue 6: Proof Toggle Synchronization
**Problem**: The current output shows placeholders, so we can't verify proof toggles work.

**Goal**: Clicking "Proof" triangle should:
1. Expand/collapse the LaTeX proof text
2. Simultaneously show/hide the Lean proof body

**Location**:
- JavaScript in `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/Assets.lean`
- HTML structure in node rendering

**Status**: Need to verify once nodes render correctly.

---

### Issue 7: Side-by-Side Layout Not Visible
**Problem**: Current output shows "not found" errors, so no side-by-side layout.

**Goal**: Two-column layout with:
- Left (75ch fixed): LaTeX theorem statement + proof
- Right (flexible): Lean signature + proof body

**Status**: May already be implemented but blocked by node lookup failure.

---

## Prioritized Fix Plan

### Priority 1: Fix Node Lookup (Unblocks everything else)

**Root cause confirmed**: The placeholder label from LaTeX (`def:is-positive`) doesn't match the normalized key (`def-is-positive`) used in the nodeLookup HashMap.

**Solution**: Normalize the label in `replacePlaceholders` before lookup.

**Step 1.1**: Modify `replacePlaceholders` in Theme.lean
```lean
-- At line 1006, before looking up:
let normalizedLabel := label.replace ":" "-"
match nodeLookup[normalizedLabel]? with
```

This is a one-line fix that normalizes the LaTeX label to match the HashMap key format.

**Alternative**: Store artifacts with original labels (colons), but this would require changes in multiple places and break consistency with filesystem paths.

**Files to modify**:
- `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/Theme.lean` line ~1006 (add label normalization)

---

### Priority 2: Fix Path Resolution

**Current code** (`Main.lean` lines 101-111):
```lean
def loadConfig (path : FilePath) : IO Config := do
  if ← path.pathExists then
    let content ← IO.FS.readFile path
    match Lean.Json.parse content >>= Lean.FromJson.fromJson? with
    | .ok config => return config  -- <-- Returns config as-is
    | .error e => throw <| IO.userError s!"Failed to parse config: {e}"
  else
    -- ...
```

**Step 2.1**: Modify `loadConfig` to resolve relative paths
```lean
def loadConfig (configPath : FilePath) : IO Config := do
  let configDir := configPath.parent.getD "."
  if ← configPath.pathExists then
    let content ← IO.FS.readFile configPath
    match Lean.Json.parse content >>= Lean.FromJson.fromJson? with
    | .ok config =>
      -- Resolve blueprintTexPath relative to config file directory
      let resolved := match config.blueprintTexPath with
        | some texPath =>
          if texPath.startsWith "/" then config  -- Already absolute
          else { config with blueprintTexPath := some ((configDir / texPath).toString) }
        | none => config
      return resolved
    | .error e => throw <| IO.userError s!"Failed to parse config: {e}"
  else
    -- ...
```

**Expected runway.json after fix**:
```json
{
  "blueprintTexPath": "blueprint/src/blueprint.tex"  // Relative path works!
}
```

**Files to modify**:
- `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Main.lean` (loadConfig function, lines 101-111)

---

### Priority 3: Hierarchical Sidebar

**Step 3.1**: Update `renderSidebar` to include section nesting
```lean
def renderSidebar (chapters : Array ChapterInfo) (currentSlug : Option String) (toRoot : String) : Html :=
  -- For each chapter, render a <li> containing:
  --   <a> chapter link
  --   <ul> nested list of sections (if chapter is current)
```

**Step 3.2**: Add CSS for nested navigation
- Indentation for section items
- Collapse/expand styles

**Step 3.3**: Add JavaScript for expand/collapse

**Files to modify**:
- `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/Theme.lean` (renderSidebar)
- `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/Assets.lean` (CSS/JS)

---

### Priority 4: Theorem Numbering

**Step 4.1**: Add counter tracking to SectionInfo
```lean
structure SectionInfo where
  -- existing fields...
  theoremCounters : Std.HashMap String Nat := {}  -- envType -> count
```

**Step 4.2**: Modify node rendering to accept and display numbers
- Pass chapter number, section number, and item counter
- Format as "Definition {c}.{s}.{n}"

**Files to modify**:
- `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/Site.lean` (SectionInfo)
- `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/Theme.lean` (node rendering in chapter content)

---

### Priority 5: Chapter Title Format

**Step 5.1**: Change title rendering
- From: `Chapter {number}: {title}`
- To: `{number} {title}`

**Files to modify**:
- `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/Theme.lean` line 1030-1032

---

## Summary of Files to Modify

| File | Changes |
|------|---------|
| `Runway/Main.lean` | Fix path resolution, debug node loading |
| `Runway/Runway/Theme.lean` | Hierarchical sidebar, title format, theorem numbering |
| `Runway/Runway/Assets.lean` | CSS for nested nav, JS for expand/collapse |
| `Runway/Runway/Site.lean` | Counter tracking (if needed) |
| `Dress/Dress/Paths.lean` | Verify label sanitization (if mismatch) |

---

## Verification Steps

After each fix:
1. Run `./scripts/build_blueprint.sh` in SBS-Test
2. Open `localhost:8000` and navigate to chapters
3. Compare against goal2.png for structural match
4. Verify:
   - Nodes render with side-by-side layout
   - Sidebar shows expandable sections
   - Theorems are numbered
   - Proof toggles work
   - Hover tooltips appear on Lean code
