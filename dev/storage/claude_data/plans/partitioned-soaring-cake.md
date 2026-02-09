# Fix #57: Verso Paper Content Not Loading

## Problem

`paper_verso.html` shows a placeholder documentation page instead of rendered Paper.lean content. Three independent failures:

1. **Orchestrator gap**: `orchestrator.py` never runs `lake exe generate-paper-verso`
2. **SBS-Test outputDir collision**: `GeneratePaper.lean` writes to `.lake/build/runway/` -- Runway overwrites this with its placeholder. Must write to `.lake/build/verso/`
3. **GCR missing generator**: `Crystallographic/Paper.lean` (415 lines) exists but no executable to build it

## Wave 1: Fix SBS-Test output directory

**Files**: `toolchain/SBS-Test/GeneratePaper.lean`, `toolchain/SBS-Test/GenerateBlueprint.lean`

Change `outputDir` from `.lake/build/runway` to `.lake/build/verso` in both files. This routes output where Runway's `detectVersoDocuments` expects it (via `versOutputLocations`), avoiding the circular overwrite.

## Wave 2: Create GCR generator

**New file**: `showcase/General_Crystallographic_Restriction/GeneratePaper.lean`
- Follow SBS-Test pattern: import `Crystallographic.Paper`, call `sbsBlueprintMain` with `outputDir := ".lake/build/verso"`

**Edit**: `showcase/General_Crystallographic_Restriction/lakefile.toml`
- Add `[[lean_exe]]` entry: `name = "generate-paper-verso"`, `root = "GeneratePaper"`

## Wave 3: Add orchestrator build step

**File**: `dev/scripts/sbs/build/orchestrator.py`

Add `generate_verso_documents()` method that runs `lake exe generate-paper-verso` and `lake exe generate-blueprint-verso`, handling missing executables gracefully (not all projects have them).

Insert between `build_blueprint` and `build_dep_graph` phases (after `:blueprint` facet produces manifest.json, before Runway site generation detects the output).

## Wave 4: Validation

1. Build SBS-Test -- confirm `.lake/build/verso/paper_verso.html` has real content, copied to `runway/`
2. Build GCR -- confirm same
3. Evergreen tests pass

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  regression: >= 0
```

## Files Modified

| File | Action |
|------|--------|
| `toolchain/SBS-Test/GeneratePaper.lean` | Fix outputDir |
| `toolchain/SBS-Test/GenerateBlueprint.lean` | Fix outputDir |
| `showcase/General_Crystallographic_Restriction/GeneratePaper.lean` | Create |
| `showcase/General_Crystallographic_Restriction/lakefile.toml` | Add exe entry |
| `dev/scripts/sbs/build/orchestrator.py` | Add generate_verso phase |

## Out of Scope (follow-up)

- Runway template integration (sidebar, theme, MathJax) for Verso pages
- blueprint_verso content loading (same pattern, separate issue)
