# PNT Blueprint Comment Migration (#306)

## Status

Phases 1-4 **COMPLETE**. Migration script written, executed (137 migrated, 55 narrative-skipped, 6 orphan), agent-reviewed (all PASS after Lcm.lean fix), user-reviewed. `-- MIGRATED:` lines remain in 31 files pending deletion.

**Current work: Phase 6 (CI fix + rendering verification) before Phase 5 (cleanup + push).**

---

## Phase 6: Fix PNT CI + Verify Rendering

### Context

The most recent PNT blueprint build on `e-vergo/PrimeNumberTheoremAnd` (run 21813027908, Feb 9) failed with **exit code 139 (SIGSEGV)** during the `dress` graph generation step. GCR and SBS-Test CI are green.

**Two independent issues discovered:**

1. **Version drift in CI action**: `dress-blueprint-action/action.yml` hardcodes `ref: main` for all 5 toolchain checkouts. PNT's `lake-manifest.json` locks Dress at `663b965` and LeanArchitect at `4f8cbdf`, but both repos' `main` branches have advanced (Dress to `031504d`, 3 commits ahead; LA to `30931d7`, 2 commits ahead). The toolchain cache key only depends on `lean-toolchain` hash, so cache hits serve stale binaries while source diverges. On cache miss, the freshly-built Dress binary may be built against a different LeanArchitect than PNT was compiled with, causing deserialization crashes when loading PNT's environment.

2. **Dangling submodule in LeanArchitect**: Git tree has a `160000` entry for `wallpaper_groups` with no `.gitmodules` file. Produces `fatal: No url found for submodule path 'wallpaper_groups'` during CI. Can break `lake build LeanArchitect` on cache miss.

### Step 1: Diagnose locally (orchestrator, ~5 min)

Run the exact dress graph command CI uses:
```bash
cd Side-By-Side-Blueprint/showcase/PrimeNumberTheoremAnd
lake env ../../toolchain/Dress/.lake/build/bin/extract_blueprint graph \
  --build .lake/build PrimeNumberTheoremAnd
```
If succeeds → CI-specific issue (resource limits or version mismatch). If crashes → Dress bug.

### Step 2: Fix LeanArchitect — Remove `wallpaper_groups` (1 agent)

```bash
cd Side-By-Side-Blueprint/forks/LeanArchitect
git rm --cached wallpaper_groups
# commit + push
```

**File:** `Side-By-Side-Blueprint/forks/LeanArchitect/` (git index only)

### Step 3: Fix `action.yml` — Auto-detect from manifest (1 agent)

**File:** `Side-By-Side-Blueprint/toolchain/dress-blueprint-action/action.yml`

**Implementation:**

Insert a new step between "Free disk space" and "Checkout SubVerso" (between current lines 55 and 57):

```yaml
# ========================================
# STEP 1.5: Extract toolchain versions from project manifest
# ========================================
- name: Extract toolchain versions
  id: toolchain-versions
  shell: bash
  working-directory: ${{ inputs.project-directory }}
  run: |
    MANIFEST="lake-manifest.json"
    if [ ! -f "$MANIFEST" ]; then
      echo "::warning::No lake-manifest.json, using main for all toolchain repos"
      for pkg in subverso LeanArchitect Dress Runway; do
        echo "${pkg,,}-ref=main" >> $GITHUB_OUTPUT
      done
      exit 0
    fi

    # Extract rev for a named package from the manifest
    extract_rev() {
      python3 -c "
import json, sys
with open('$MANIFEST') as f:
    m = json.load(f)
for p in m.get('packages', []):
    if p.get('name','').lower() == sys.argv[1].lower():
        print(p.get('rev', 'main')); sys.exit(0)
print('main')
" "$1"
    }

    for pkg in subverso LeanArchitect Dress Runway; do
      REF=$(extract_rev "$pkg")
      echo "${pkg,,}-ref=$REF" >> $GITHUB_OUTPUT
      echo "  $pkg: $REF"
    done
```

Then update each checkout step's `ref:` field:

| Step | Current | New |
|------|---------|-----|
| Checkout SubVerso (line 64) | `ref: main` | `ref: ${{ steps.toolchain-versions.outputs.subverso-ref }}` |
| Checkout LeanArchitect (line 71) | `ref: main` | `ref: ${{ steps.toolchain-versions.outputs.leanarchitect-ref }}` |
| Checkout Dress (line 78) | `ref: main` | `ref: ${{ steps.toolchain-versions.outputs.dress-ref }}` |
| Checkout Runway (line 85) | `ref: main` | `ref: ${{ steps.toolchain-versions.outputs.runway-ref }}` |
| Checkout assets (line 92) | `ref: main` | **Keep `main`** (assets aren't a Lake package) |

Also update the cache key (line 154) to include manifest hash:
```yaml
key: toolchain-${{ runner.os }}-${{ hashFiles(format('{0}/lean-toolchain', inputs.project-directory)) }}-${{ hashFiles(format('{0}/lake-manifest.json', inputs.project-directory)) }}
```

**Why this works:** PNT's `lake-manifest.json` already contains locked SHAs for all relevant packages:
- `Dress`: `663b965` (direct dependency)
- `LeanArchitect`: `4f8cbdf` (inherited via Dress)
- `subverso`: `160bb35` (inherited)
- `Runway`: not in manifest → falls back to `main`

This ensures the CI Dress binary is built from the exact same code that `lake build` resolved.

### Step 4: Verify rendering — Build + Serve + Visual (orchestrator + browser)

1. Run full `build.py` pipeline for PNT
2. Serve at localhost, open in browser
3. Check pages with migrated above/below content:
   - `MediumPNT` — prose `above` fields
   - `Lcm` — multiple grouped `above` fields
   - `ZetaAppendix` — `below` fields
4. Confirm `above` renders above theorem heading (`<div class="sbs-above-content">`)
5. Confirm `below` renders below proof section (`<div class="sbs-below-content">`)
6. CSS: `common.css` lines 408-438 — grid rows 1 and 5, with border separators

### Step 5: Delete `-- MIGRATED:` lines (1 agent)

1. Remove all `-- MIGRATED: blueprint_comment ...` lines (702 lines across 31 files)
2. Collapse 3+ consecutive blank lines to 2
3. `lean_diagnostic_messages` on all 35 files — zero new errors

### Step 6: Commit + Push + Deploy

Submodule commit chain (innermost first):
1. **LeanArchitect** → `fix: remove dangling wallpaper_groups submodule`
2. **dress-blueprint-action** → `feat: auto-detect toolchain versions from manifest`
3. **Dress** → update submodule pointer if LeanArchitect changed
4. **PNT** → `chore: migrate blueprint_comment to above/below fields (#306)` + delete MIGRATED lines
5. **SBS** → update submodule pointers
6. **SLS** → update SBS pointer

Push via `sbs archive upload`. Then trigger CI on all three repos.

### Files Modified

| Location | Changes |
|----------|---------|
| `forks/LeanArchitect/` | Remove `wallpaper_groups` submodule entry |
| `toolchain/dress-blueprint-action/action.yml` | New extraction step + dynamic refs + cache key update |
| `showcase/PrimeNumberTheoremAnd/PrimeNumberTheoremAnd/*.lean` (31 files) | Delete `-- MIGRATED:` lines |

### Execution Order

Steps 1-3 can partially overlap:
- Step 1 (diagnose) runs first — informs if there's a deeper bug
- Steps 2 + 3 (fixes) can run as parallel agents after diagnosis
- Step 4 (rendering) blocks on Step 1 completing
- Step 5 (cleanup) blocks on Step 4 confirming rendering is correct
- Step 6 (push) blocks on everything

### Verification

1. Local dress graph command succeeds without segfault
2. Full `build.py` pipeline completes
3. Visual inspection confirms above/below rendering with correct positioning
4. `lean_diagnostic_messages` on all 35 files — zero errors
5. CI passes on all three repos after push
