# Semantic Highlighting via Lake Facet Caching

## Goal
Enable proper semantic highlighting using `subverso-extract-mod` with **Lake facet caching** so extraction only runs once per module change (not on every blueprint build).

## Current Problem
The current implementation calls `lake exe subverso-extract-mod` for every module during every blueprint extraction. This is extremely slow (minutes per module) because:
1. Each call re-elaborates the entire module from scratch
2. No caching - repeated builds re-extract everything
3. Environment setup overhead on each call

## Solution: Lake Facet Caching (Verso Pattern)
Verso solves this by defining a `module_facet highlighted` that:
- Depends on the module's `.olean` file
- Only rebuilds when the module changes
- Caches JSON output in `buildDir/highlighted/`
- Lake handles all dependency tracking automatically

---

## Architecture Overview

```
+-------------------- Lake Build System ---------------------+
|                                                             |
|   module_facet highlighted                                  |
|   ├── Depends on: mod.olean (compiled module)              |
|   ├── Depends on: subverso-extract-mod executable          |
|   ├── Runs: subverso-extract-mod ModuleName output.json    |
|   └── Output: buildDir/highlighted/Module/Name.json        |
|                                                             |
|   module_facet blueprint                                    |
|   ├── Depends on: mod.facet `highlighted (the JSON)        |
|   ├── Depends on: extract_blueprint executable             |
|   └── Runs: extract_blueprint --highlighted-json FILE      |
|                                                             |
+-------------------------------------------------------------+
```

**Cache Invalidation:** Lake automatically rebuilds `highlighted` when:
- Module source changes → `.olean` changes → facet rebuilds
- `subverso-extract-mod` executable changes
- First build (no cache exists)

---

## Files to Modify

| File | Change |
|------|--------|
| `LeanArchitect/lakefile.lean` | Add `highlighted` facet, update `buildModuleBlueprint` |
| `LeanArchitect/Main.lean` | Accept `--highlighted-json` flag |
| `LeanArchitect/Architect/Load.lean` | Read from JSON file instead of calling executable |
| `LeanArchitect/Architect/SubVersoExtract.lean` | Add `loadHighlightingFromFile` function |

---

## Implementation Steps

### Step 1: Add `highlighted` Module Facet to lakefile.lean

Add to `/Users/eric/GitHub/LeanArchitect/lakefile.lean`:

```lean
/-- Facet that extracts highlighted JSON for a module using subverso-extract-mod.
    Cached by Lake - only rebuilds when module's olean changes. -/
module_facet highlighted (mod : Module) : FilePath := do
  let ws ← getWorkspace
  let some extract ← findLeanExe? `«subverso-extract-mod»
    | error "subverso-extract-mod executable not found"

  let exeJob ← extract.exe.fetch
  let modJob ← mod.olean.fetch

  let buildDir := ws.root.buildDir
  let hlFile := mod.filePath (buildDir / "highlighted") "json"

  exeJob.bindM fun exeFile => do
    modJob.mapM fun _oleanFile => do
      buildFileUnlessUpToDate' hlFile do
        IO.FS.createDirAll (buildDir / "highlighted")
        proc {
          cmd := exeFile.toString
          args := #[mod.name.toString, hlFile.toString]
          env := ← getAugmentedEnv
        }
      pure hlFile
```

### Step 2: Update `buildModuleBlueprint` to Consume Facet

Modify the existing function to depend on the `highlighted` facet:

```lean
def buildModuleBlueprint (mod : Module) (ext : String) (extractArgs : Array String) : FetchM (Job Unit) := do
  let exeJob ← extract_blueprint.fetch
  let modJob ← mod.leanArts.fetch
  let hlJob ← fetch <| mod.facet `highlighted  -- NEW: get cached JSON
  let buildDir := (← getRootPackage).buildDir
  let mainFile := mod.filePath (buildDir / "blueprint" / "module") ext
  let leanOptions := Lean.toJson mod.leanOptions |>.compress

  exeJob.bindM fun exeFile => do
    hlJob.bindM fun hlFile => do  -- NEW: thread through highlighted JSON path
      modJob.mapM fun _ => do
        buildFileUnlessUpToDate' mainFile do
          proc {
            cmd := exeFile.toString
            args := #["single", "--build", buildDir.toString,
                      "--highlighted-json", hlFile.toString,  -- NEW
                      "--options", leanOptions, mod.name.toString] ++ extractArgs
            env := ← getAugmentedEnv
          }
```

### Step 3: Add `--highlighted-json` Flag to Main.lean

Modify `/Users/eric/GitHub/LeanArchitect/Main.lean`:

```lean
def singleCmd := `[Cli|
  single VIA runSingleCmd;
  "Extract blueprint for a single module."

  FLAGS:
    j, json; "Output JSON instead of LaTeX."
    h, highlight; "No-op (backward compatibility)."
    b, build : String; "Build directory."
    o, options : String; "LeanOptions in JSON."
    highlightedJson : String; "Path to pre-computed highlighted JSON from facet."  -- NEW

  ARGS:
    module : String; "The module to extract."
]
```

Update `runSingleCmd` to use the JSON file:

```lean
def runSingleCmd (p : Parsed) : IO UInt32 := do
  -- ... existing setup ...

  let highlightedJsonPath := p.flag? "highlightedJson" |>.map (·.as! String)

  if isJson then
    let json ← jsonOfImportModule module options.toOptions highlightedJsonPath
    outputJsonResults baseDir module json
  else
    let latexOutput ← latexOutputOfImportModule module options.toOptions highlightedJsonPath
    discard <| outputLatexResults baseDir module latexOutput
  return 0
```

### Step 4: Update Load.lean to Accept JSON Path

Modify `/Users/eric/GitHub/LeanArchitect/Architect/Load.lean`:

```lean
def latexOutputOfImportModule (module : Name) (options : Options)
    (highlightedJsonPath? : Option String := none) : IO LatexOutput := do
  let highlightingMap ← match highlightedJsonPath? with
    | some path => SubVersoExtract.loadHighlightingFromFile path
    | none => SubVersoExtract.extractHighlightingMap module  -- fallback for direct CLI use
  runEnvOfImports #[module] options (moduleToLatexOutput module highlightingMap)
```

### Step 5: Add File Loading to SubVersoExtract.lean

Add to `/Users/eric/GitHub/LeanArchitect/Architect/SubVersoExtract.lean`:

```lean
/-- Load highlighting from a pre-computed JSON file (from Lake facet cache). -/
def loadHighlightingFromFile (path : String) : IO (NameMap Highlighted) := do
  let contents ← IO.FS.readFile path
  match Json.parse contents with
  | .error e =>
    IO.eprintln s!"Warning: Failed to parse highlighted JSON: {e}"
    return {}
  | .ok json =>
    match Module.fromJson? json with
    | .error e =>
      IO.eprintln s!"Warning: Failed to parse Module from JSON: {e}"
      return {}
    | .ok mod =>
      return buildHighlightingMap mod.items
```

---

## Key Files Reference

### Verso's Facet Implementation
`/Users/eric/GitHub/General_Crystallographic_Restriction/.lake/packages/subverso/lakefile.lean` (lines 153-212)

### Current LeanArchitect Facets
`/Users/eric/GitHub/General_Crystallographic_Restriction/.lake/packages/LeanArchitect/lakefile.lean` (lines 33-92)

---

## Fallback Behavior

If `--highlighted-json` is not provided (direct CLI usage):
1. Falls back to calling `lake exe subverso-extract-mod` directly
2. This maintains backward compatibility
3. Just slower than using the cached facet

---

## Verification

After implementation:

1. **Build LeanArchitect:**
   ```bash
   cd /Users/eric/GitHub/LeanArchitect && lake build
   ```

2. **Build GCR with facets:**
   ```bash
   cd /Users/eric/GitHub/General_Crystallographic_Restriction
   lake build Crystallographic:highlighted  # Should create JSON cache
   lake build Crystallographic:blueprint    # Should use cached JSON
   ```

3. **Verify caching works:**
   ```bash
   # Second build should be instant (no "Exporting highlighted..." messages)
   lake build Crystallographic:blueprint
   ```

4. **Check output has highlighting:**
   ```bash
   grep -l 'leansource' .lake/build/blueprint/module/Crystallographic/**/*.tex
   ```

---

## Performance Expectations

| Scenario | Before (no cache) | After (with facet) |
|----------|-------------------|-------------------|
| First build | ~minutes/module | ~minutes/module (same) |
| Subsequent builds | ~minutes/module | ~instant (cached) |
| Module changed | N/A | ~minutes for that module only |

---

## Orchestration

Execute steps sequentially:
1. Modify lakefile.lean (add facet + update buildModuleBlueprint)
2. Modify Main.lean (add flag)
3. Modify Load.lean (accept path parameter)
4. Modify SubVersoExtract.lean (add file loading)
5. Build and test
