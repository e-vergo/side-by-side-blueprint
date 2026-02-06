# Crush-1 Foundation: Dress Activation Pathway Audit

**Issue:** #246
**Branch:** `crush-1-foundation`
**Date:** 2026-02-06

---

## 1. Env-Var Gate Tracing

### Full Activation Path

The `BLUEPRINT_DRESS=1` environment variable controls whether per-declaration artifact files (`.json`, `.tex`, `.html`) are written to disk during elaboration. Here is the complete path from env var check to file I/O.

#### Entry Point: `elab_rules` in `ElabRules.lean`

Seven `elab_rules` (lines 208-283 of `Dress/Capture/ElabRules.lean`) intercept different declaration kinds: `theorem`, `def`, `abbrev`, `structure`, `class`, `inductive`, `instance`. Each follows the same pattern:

```
1. Check recursion guard: `if (← inCaptureHookM) then throwUnsupportedSyntax`
2. Check @[blueprint] attribute: `if hasBlueprintAttr mods then ...`
3. Call `elabDeclAndCaptureHighlighting stx declId`
4. If no @[blueprint], fall through: `throwUnsupportedSyntax`
```

Key observation: **The elab_rules always fire for every declaration when Dress is imported.** They do not check `dressEnabled`. The check at step 2 filters to only `@[blueprint]`-annotated declarations. This is cheap (syntax tree inspection only, no I/O).

#### Gate Function: `elabDeclAndCaptureHighlighting` (lines 105-195)

This function does two things sequentially:

**Phase A: Highlighting Capture (always runs for @[blueprint] declarations)**

Lines 108-122: Calls `elabCommandTopLevel` (standard elaboration) inside `withCaptureHookFlag`, then calls `captureHighlighting resolvedName stx`. This phase is gated by `blueprint.highlighting` option (default: `true`), NOT by `BLUEPRINT_DRESS`.

The highlighting is stored in the `dressedDeclExt` environment extension (`InfoTree.lean:30`). This data lives in-memory in the Lean environment -- no file I/O occurs.

**Phase B: Artifact Writing (gated by dress mode)**

Lines 124-195 contain the actual dress-mode gate:

```lean
-- Line 127-130
let dressEnv ← IO.getEnv "BLUEPRINT_DRESS"
let markerFile : System.FilePath := ".lake" / "build" / ".dress"
let markerExists ← markerFile.pathExists
let dressEnabled := dressEnv == some "1" || blueprint.dress.get (← getOptions) || markerExists
```

Three independent activation methods (OR logic):
1. **Environment variable:** `BLUEPRINT_DRESS=1` (checked via `IO.getEnv`)
2. **Lean option:** `blueprint.dress=true` (registered at line 41, default `false`)
3. **Marker file:** `.lake/build/.dress` exists (created by `lake run dress` script at lakefile.lean:477-479)

When `dressEnabled` is `true` (line 133), the following occurs:
- Lines 136-137: Reads `Architect.Node` from `blueprintExt` environment extension
- Lines 140-164: Optional enrichment with delimiter-extracted TeX (reads source file, scans for `/-%%...%%-/` blocks)
- Lines 168-169: Reads captured highlighting from `dressedDeclExt`
- Lines 175-177: Resolves declaration source location
- **Line 181:** Calls `Generate.writeDeclarationArtifactsFromNode` -- THIS IS THE FILE I/O GATE

#### Artifact Generation: `Declaration.lean`

`writeDeclarationArtifactsFromNode` (lines 123-154) does:

1. Computes content hash for caching (`Cache.computeDeclarationHash`, line 138)
2. Checks cache (`Cache.checkCache`, line 141) -- reads `.lake/build/dressed/.decl_cache/{hash}/`
3. On cache **hit**: copies files from cache to target dir (`Cache.restoreFromCache`, line 144)
4. On cache **miss**: calls `generateArtifacts` (line 150) which writes:
   - `decl.tex` via `Paths.getDeclarationTexPath` (line 52-53)
   - `decl.html` via `Paths.getDeclarationHtmlPath` (line 70-71)
   - `decl.hovers.json` via `Paths.getDeclarationHoversPath` (line 73)
   - `decl.json` via `Paths.getDeclarationJsonPath` (line 91)
   - `manifest.entry` via `Paths.getManifestEntryPath` (line 100)
5. Saves to cache (`Cache.saveToCache`, line 152)

All output goes to `.lake/build/dressed/{Module/Path}/{sanitized-label}/`.

### Summary of Conditional Checks

| Check | Location | What It Guards |
|-------|----------|----------------|
| `inCaptureHookM` | ElabRules.lean:218,232,etc | Recursion prevention |
| `hasBlueprintAttr mods` | ElabRules.lean:221,233,etc | Only process @[blueprint] decls |
| `blueprint.highlighting` option | InfoTree.lean:86 | SubVerso highlighting capture (default: true) |
| `dressEnabled` (3-way OR) | ElabRules.lean:130 | ALL file I/O for artifacts |
| `Cache.checkCache` | Declaration.lean:141 | Skip regeneration on cache hit |

### Python Build Script Integration

`dev/scripts/sbs/build/phases.py` lines 181-194 (`build_project_with_dress`):
```python
env = os.environ.copy()
env["BLUEPRINT_DRESS"] = "1"
subprocess.run(["lake", "build"], cwd=project_root, env=env, check=True)
```

The orchestrator (`orchestrator.py`) calls this at line 825 via `_build_project_internal()`, then separately runs `lake build :blueprint` at line 1138.

---

## 2. Always-Active Requirements

### What "Always Active" Means

Making Dress hooks always-active means: when a project imports Dress and runs `lake build`, per-declaration artifacts are written automatically without needing `BLUEPRINT_DRESS=1`, `blueprint.dress=true`, or the `.dress` marker file.

### Required Code Changes

**Primary change: Remove the `dressEnabled` gate in `ElabRules.lean`**

The change is localized to lines 124-133 of `Dress/Capture/ElabRules.lean`. Currently:

```lean
let dressEnv ← IO.getEnv "BLUEPRINT_DRESS"
let markerFile : System.FilePath := ".lake" / "build" / ".dress"
let markerExists ← markerFile.pathExists
let dressEnabled := dressEnv == some "1" || blueprint.dress.get (← getOptions) || markerExists

if dressEnabled then
  -- ... write artifacts
```

This should become unconditional execution -- remove the env var check, marker file check, and the `if dressEnabled` conditional entirely. The artifact-writing block (lines 134-195) would always execute after highlighting capture for any `@[blueprint]` declaration.

### Side Effects Analysis

**Side effect 1: File I/O on every build.** Currently `lake build` without `BLUEPRINT_DRESS=1` does zero file I/O for artifacts. With always-active, every `@[blueprint]` declaration will trigger:
- One `IO.getEnv` call (removed)
- One `pathExists` check for marker file (removed)
- One `pathExists` check for cache (kept -- `Cache.checkCache`)
- On cache hit: file copies from cache dir
- On cache miss: 5 file writes per declaration

For SBS-Test (33 nodes), this adds ~33 cache checks per build. With warm cache, this is ~33 file copy operations. With cold cache, ~165 file writes total.

**Side effect 2: The `blueprint.highlighting` option still gates SubVerso capture.** This is correct behavior. If highlighting is disabled (unlikely in practice since default is `true`), artifact writing still runs but without HTML content.

**Side effect 3: TeX enrichment reads source files.** Lines 144-145 (`IO.FS.readFile`) and the delimiter extraction loop at lines 146-163 run for every `@[blueprint]` declaration whose `node.statement.text` is empty. This is NOT gated by `dressEnabled` in the current code -- wait, it IS inside the `if dressEnabled then` block. Making this always-active means this file-read-and-scan happens on every build. The cost is one `IO.FS.readFile` per module (not per declaration, since the source file is the same for all declarations in a module) plus an O(n) scan for delimiter blocks.

**Side effect 4: The `#dress` command and `isDressEnabled` function.** Lines 56-70 define the `#dress` command which sets `dressEnabledRef`. This is checked by `isDressEnabled` (line 69). However, `isDressEnabled` is NOT called in the artifact-writing path -- it's only an exported utility. No code in the critical path depends on it. The `#dress` command is described as "typically not needed" in its docstring (line 50). It can be left as-is (dead code path) or removed.

**Side effect 5: The `lake run dress` script.** `lakefile.lean` lines 474-485 create the `.dress` marker file, run `lake build`, then clean it up. With always-active hooks, this script becomes unnecessary (but harmless). The marker file creation/cleanup can be removed.

### Is It "As Simple As Removing the Check"?

Nearly. The required changes are:

1. **`ElabRules.lean`:** Remove lines 127-133 (the 3-way OR check and `if dressEnabled then`), keep the body unconditional.
2. **`ElabRules.lean`:** Remove `register_option blueprint.dress` (line 41-44) -- no longer needed. Or keep it for backward compatibility if any downstream code references it.
3. **`lakefile.lean`:** Remove or deprecate the `lake run dress` script (lines 474-485) -- no longer needed.
4. **`phases.py`:** Remove `BLUEPRINT_DRESS=1` env var injection from `build_project_with_dress()` (lines 187-188). The function can just call `lake build` directly.
5. **`orchestrator.py`:** The two-phase build (`lake build` then `lake build :blueprint`) can potentially be merged, but this is a separate concern. The `:blueprint` facet depends on the `dressed` facet which depends on `lean`, so `lake build :blueprint` already triggers all phases in sequence.

No other side effects. The elab_rules are already scoped to `@[blueprint]` declarations only. Highlighting capture is already ungated (it runs regardless of dress mode). The only change is making artifact writing unconditional.

---

## 3. Lake Compatibility

### Artifact File Location

All Dress artifacts are written to `.lake/build/dressed/`:
```
.lake/build/dressed/
  {Module/Path}/{sanitized-label}/decl.tex
  {Module/Path}/{sanitized-label}/decl.html
  {Module/Path}/{sanitized-label}/decl.json
  {Module/Path}/{sanitized-label}/decl.hovers.json
  {Module/Path}/{sanitized-label}/manifest.entry
  {Module/Path}/module.json
  {Module/Path}/module.tex
  .decl_cache/{hash}/  (cache entries)
  library/{LibName}.tex
  manifest.json
  dep-graph.svg
  dep-graph.json
```

### Coexistence with Normal Lake Outputs

Lake's standard build outputs go to `.lake/build/lib/` (oleans) and `.lake/build/ir/` (C IR). The `dressed/` subdirectory is entirely separate and does not conflict with any Lake-managed directory.

**No clobber risk.** Lake does not write to `.lake/build/dressed/`. Dress does not write to `.lake/build/lib/` or `.lake/build/ir/`. The two systems use disjoint directory trees under `.lake/build/`.

### Lake Clean Behavior

`lake clean` removes the entire `.lake/build/` directory. This means:
- **All dressed artifacts are removed by `lake clean`.** This is correct behavior -- artifacts should be regenerated from source.
- The `.decl_cache/` directory (content-addressed cache) is also removed, meaning the next build after `lake clean` will be a cold-cache build.
- The `.dress` marker file (at `.lake/build/.dress`) is also removed, which is irrelevant if we make hooks always-active.

`lake build` does NOT remove dressed artifacts. Lake's incremental build only rebuilds what its dependency tracking says needs rebuilding. Since dressed artifacts are written as side effects of elaboration (not as Lake facet outputs), Lake doesn't know about them and won't delete them.

### Facet Dependency Correctness

The `dressed` module facet (lakefile.lean:108) depends on `mod.lean.fetch` -- it only runs after the `lean` facet completes for that module. This ensures elaboration (and thus artifact writing via elab_rules) has completed before the facet tries to read artifacts.

The `blueprint` module facet (lakefile.lean:211) depends on `mod.facet dressed` -- it only runs after dressed aggregation completes.

With always-active hooks, the flow becomes:
1. `lake build` triggers `lean` facet for each module
2. During `lean` elaboration, elab_rules fire and write per-declaration artifacts (always)
3. `dressed` facet aggregates per-declaration artifacts into `module.json`
4. `blueprint` facet generates `module.tex` from per-declaration artifacts
5. `depGraph` facet generates dependency graph

This dependency chain is already correct. Making hooks always-active does not change facet ordering.

### Two-Phase Build Unification

Currently the build requires two phases:
- Phase 1: `BLUEPRINT_DRESS=1 lake build` (triggers elab_rules + lean facet)
- Phase 2: `lake build :blueprint` (triggers dressed + blueprint + depGraph facets)

With always-active hooks, Phase 1 becomes just `lake build` (no env var). Phase 2 remains necessary because the `:blueprint` target triggers the facet pipeline. However, since `:blueprint` depends on `dressed` which depends on `lean`, running ONLY `lake build :blueprint` should be sufficient -- it will trigger lean elaboration (which writes artifacts via always-active hooks), then dressed aggregation, then blueprint generation.

**Recommendation:** Test whether `lake build :blueprint` alone (without a prior `lake build`) correctly triggers the full pipeline. If so, the two-phase build can be collapsed to a single command.

---

## 4. Non-SBS Impact (Zero-Cost Guarantee)

### Scenario: Project imports Dress but has no `@[blueprint]` declarations

This scenario applies to any Lean project that depends on Dress transitively (e.g., through another library) but doesn't use `@[blueprint]` annotations itself.

#### Trace Through the Code Path

**Step 1: Module elaboration begins.** Lean processes each `.lean` file. The elab_rules registered in `ElabRules.lean` are available because Dress is imported.

**Step 2: For each declaration, elab_rules check `@[blueprint]` attribute.**

```lean
-- ElabRules.lean:221 (theorem case)
let hasBlueprint := hasBlueprintAttr mods
if hasBlueprint then
  ...
else
  throwUnsupportedSyntax
```

`hasBlueprintAttr` (`Config.lean:42-61`) is a pure function that inspects the syntax tree. It iterates over attribute instances looking for `Architect.blueprint` or `blueprint` kind. For declarations without `@[blueprint]`, it returns `false` immediately.

Cost: O(k) where k is the number of attributes on the declaration (typically 0-3). No I/O, no allocation beyond temporary syntax inspection.

**Step 3: `throwUnsupportedSyntax` causes Lean to try the next elaborator.** This is the standard Lean mechanism for elab_rules priority chaining. The declaration is elaborated by the default Lean elaborator.

#### What Happens Per Module

For a module with N declarations and zero `@[blueprint]` attributes:
- N syntax checks (each O(1) in practice)
- Zero calls to `elabDeclAndCaptureHighlighting`
- Zero calls to `captureHighlighting`
- Zero file I/O
- Zero cache checks
- Zero artifact writes

#### What Happens at the Facet Level

The `dressed` facet (lakefile.lean:108-180) runs for every module in a library. For modules with no `@[blueprint]` declarations:
- Line 121: `moduleDressedDir.pathExists` returns `false` (no artifacts were written)
- Line 124: Writes `{}` to `module.json`
- Returns immediately

Cost: One `pathExists` check + one small file write (`{}`) per module. For a project with 100 modules and zero `@[blueprint]` declarations, this is 100 trivial file writes.

The `blueprint` facet (lakefile.lean:211-263) similarly writes a minimal `.tex` file for empty modules (line 224).

#### Verdict

**Zero-cost for the elab_rules path.** The only per-declaration cost is a syntax tree inspection returning `false`. This is cheaper than many built-in Lean attribute checks.

**Near-zero cost for facets.** Each module gets a trivial `module.json` and `module.tex` written. This adds milliseconds total, even for large projects.

**No behavioral change for non-SBS projects.** The elab_rules use `throwUnsupportedSyntax` to defer to default elaborators. Elaboration behavior is identical.

---

## 5. Lakefile Changes

### SBS-Test (`toolchain/SBS-Test/lakefile.toml`)

Current configuration:
```toml
name = "SBSTest"
defaultTargets = ["SBSTest"]

[leanOptions]
pp.unicode.fun = true
autoImplicit = false
relaxedAutoImplicit = false

[[require]]
name = "mathlib"
git = "https://github.com/leanprover-community/mathlib4.git"
rev = "v4.27.0"

[[require]]
name = "Dress"
git = "https://github.com/e-vergo/Dress.git"
rev = "main"

[[require]]
name = "verso"
git = "https://github.com/e-vergo/verso.git"
rev = "main"
```

**No changes needed.** The lakefile requires Dress, which provides the elab_rules and facets. No `moreLinkArgs`, `moreLearnArgs`, or special build options are needed. The `[leanOptions]` section does not include `blueprint.dress` or `blueprint.highlighting` because both use appropriate defaults (`false` and `true` respectively). With always-active hooks, the `blueprint.dress` option is removed entirely, so no config is needed.

### GCR (`showcase/General_Crystallographic_Restriction/lakefile.toml`)

Current configuration:
```toml
name = "Crystallographic"
defaultTargets = ["Crystallographic"]

[leanOptions]
pp.unicode.fun = true
autoImplicit = false
relaxedAutoImplicit = false

[[require]]
name = "mathlib" ...
name = "Dress" ...
name = "verso" ...
scope = "dev"
name = "doc-gen4" ...

[[lean_lib]]
name = "Crystallographic"

[[lean_exe]]
name = "generate-paper-verso"
root = "GeneratePaper"
```

**No changes needed.** Same reasoning as SBS-Test. The `scope = "dev"` requirement for doc-gen4 is unrelated to Dress.

### PNT (`showcase/PrimeNumberTheoremAnd/lakefile.toml`)

Current configuration:
```toml
name = "PrimeNumberTheoremAnd"
version = "0.1.0"
defaultTargets = ["PrimeNumberTheoremAnd"]

[[lean_lib]]
name = "PrimeNumberTheoremAnd"

[[require]]
name = "Dress"
git = "https://github.com/e-vergo/Dress"
rev = "main"

[[require]]
name = "mathlib"
git = "https://github.com/leanprover-community/mathlib4.git"
rev = "v4.27.0"
```

**No changes needed.** PNT requires Dress directly. No special build options required.

### Common Observations Across All Projects

1. **No `moreLinkArgs` or `moreLearnArgs` needed.** Dress hooks operate via elaboration rules, not native code linking.
2. **No `[leanOptions]` changes needed.** The `blueprint.dress` option (if retained for backward compat) defaults to `false`, but with always-active hooks it becomes irrelevant and can be removed from Dress.
3. **No `require` changes needed.** All three projects already require Dress.
4. **The `verso` requirement is independent of Dress activation.** SBS-Test and GCR require it for Verso document generation. PNT does not use Verso. Neither case affects Dress hooks.

---

## Recommended Integration Approach

### Phase 1: Make Elab Hooks Always-Active (Dress repo only)

**File: `toolchain/Dress/Dress/Capture/ElabRules.lean`**

1. Remove the `register_option blueprint.dress` block (lines 41-44). If backward compatibility is needed, keep it but make it a no-op.
2. Remove the 3-way OR gate in `elabDeclAndCaptureHighlighting` (lines 127-133). Make the artifact-writing block (lines 134-195) unconditional -- it executes for every `@[blueprint]` declaration after highlighting capture.
3. Remove or deprecate the `#dress` command (lines 51-65) and `isDressEnabled` (lines 68-70). They serve no purpose with always-active hooks.

**File: `toolchain/Dress/lakefile.lean`**

4. Remove or deprecate the `script dress` block (lines 474-485). The marker file mechanism is no longer needed.

### Phase 2: Simplify Build Script (Python)

**File: `dev/scripts/sbs/build/phases.py`**

5. In `build_project_with_dress()` (lines 181-194), remove `BLUEPRINT_DRESS=1` from the environment. The function becomes a plain `lake build` call.

**File: `dev/scripts/sbs/build/orchestrator.py`**

6. Test whether `lake build :blueprint` alone is sufficient (it should trigger lean -> dressed -> blueprint in sequence). If confirmed, merge the two build phases (`_build_project_internal` + `lake build :blueprint`) into a single `lake build :blueprint` call.

### Phase 3: Validation

7. Build SBS-Test with the changes and verify:
   - Per-declaration artifacts appear in `.lake/build/dressed/`
   - `lake clean && lake build :blueprint` produces the same artifacts
   - No `BLUEPRINT_DRESS` env var is set anywhere
8. Build GCR and PNT to confirm no regression.
9. Run `sbs compliance --project SBSTest` to verify visual output is unchanged.

### No Consumer Lakefile Changes Required

SBS-Test, GCR, and PNT require zero lakefile modifications. The change is entirely within the Dress repo.

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Build time increase (cold cache) | Low | Content-based caching means only first build after clean is affected. SubVerso highlighting (93-99% of build time) already runs regardless of dress mode. |
| Lake clean removes cache | Expected | Same behavior as today. Cache rebuilds naturally. |
| Non-SBS projects affected | None | elab_rules only fire for @[blueprint] declarations. Zero-cost for projects without them. |
| Facet ordering broken | None | Dependency chain (lean -> dressed -> blueprint) is unchanged. |
| Backward compatibility | Low | Projects using `BLUEPRINT_DRESS=1` or `blueprint.dress=true` will still work (the gate is simply removed, not inverted). |

### Key Insight

The current architecture already does the expensive work (SubVerso highlighting capture) during every `lake build` when Dress is imported. The `dressEnabled` gate only prevents the comparatively cheap artifact file writes. Removing this gate adds minimal overhead while eliminating the need for environment variable injection and the two-phase build complexity.
