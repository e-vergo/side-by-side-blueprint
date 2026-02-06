# SubVerso Highlighting Pipeline Profile

**Date:** 2026-02-06
**Branch:** `crush-1-foundation`
**Goal:** Identify optimization targets for sub-200ms per-declaration highlighting (Crush 2 live infoview)

---

## Executive Summary

SubVerso highlighting accounts for 93-99% of SBS build time. For PNT (591 annotations), `build_project` takes ~1054s (~17.6 minutes). For SBS-Test (40 declarations), it takes ~58s. The highlighting pipeline has 6 distinct phases, each with different scaling characteristics. The dominant costs are:

1. **Goal/proof state rendering** (`highlightGoals` -> `ppCodeWithInfos`) -- MetaM pretty-printing of every hypothesis and conclusion for every tactic step
2. **InfoTable construction** (`InfoTable.ofInfoTrees`) -- O(N) tree traversal + O(N log N) sort, run once per declaration
3. **Suffix index construction** (`buildSuffixIndex`) -- scans entire `env.constants` for every declaration
4. **Module reference building** (`findModuleRefs`) -- traverses all info trees per declaration

The key insight: phases 2-4 are **per-declaration overhead that could be amortized** if highlighting were done per-module instead of per-declaration.

---

## Pipeline Architecture

### Call Chain (per declaration, during `BLUEPRINT_DRESS=1` elaboration)

```
Dress.Capture.captureHighlighting (InfoTree.lean:84)
  -> liftTermElabM (captureHighlightingFromInfoTrees)
    -> highlightIncludingUnparsed (Code.lean:1857)
      -> [1] Lean.Server.findModuleRefs        -- build reference table
      -> [2] InfoTable.ofInfoTrees              -- O(N) tree walk + O(N log N) sort
      -> [3] InfoTable.buildSuffixIndex         -- scan env.constants
      -> [4] HighlightState.ofMessages          -- filter/bundle messages
      -> [5] highlight' (recursive)             -- main syntax traversal
         -> identKind' (cached)                 -- O(1) token classification
         -> findTactics / findTactics'          -- tactic state lookup
         -> highlightGoals                      -- EXPENSIVE: MetaM rendering
            -> ppCodeWithInfos per hypothesis   -- ppExprTagged (pretty-printing)
            -> renderTagged / renderOrGet        -- with expression caching
         -> highlightSpecial                    -- arrow-like, projections, etc.
      -> [6] Highlighted.fromOutput             -- assemble final output
```

### Two Pipeline Modes

1. **Per-declaration (current SBS mode):** `captureHighlighting` in `ElabRules.lean` calls `highlightIncludingUnparsed` for each `@[blueprint]` declaration individually. Phases 1-3 repeat for every declaration.

2. **Per-module (`subverso-extract-mod` mode):** `highlightFrontendResult` in `Code.lean` runs phases 1-3 once, then iterates `highlight'` per command. This is more efficient but not currently used by SBS (no binary is built).

---

## Measured Data

### Build Timings (from unified ledger)

| Project | Declarations | `build_project` (s) | Per-decl avg (s) |
|---------|-------------|---------------------|-------------------|
| SBS-Test | 40 | 57-61 | 1.4-1.5 |
| PNT | 591 | 1054 | 1.78 |

Note: `build_project` includes Lean elaboration + highlighting. Highlighting is estimated at 93-99% based on SubVerso documentation. For SBS-Test, the cached (no Lean change) build shows `build_project: 0.005s`, confirming that virtually all time is in elaboration+highlighting, not site generation.

### Artifact Output Sizes

| Project | Total JSON | Avg JSON/decl | Max JSON/decl | Declarations |
|---------|-----------|--------------|---------------|-------------|
| SBS-Test | 345 KB | 8.6 KB | 18.7 KB | 40 |
| GCR | 2.15 MB | 35.3 KB | 97.7 KB | 61 |

**Top 5 largest GCR declarations by JSON output:**

| Declaration | JSON (KB) | Hovers (KB) |
|-------------|----------|-------------|
| `lem-cyclotomic-divisors-lcm-eq` | 97.7 | 21.9 |
| `lem-sum-totient-ge-psi` | 93.6 | 23.3 |
| `lem-psi-le-totient` | 92.3 | 20.0 |
| `lem-factorization-split-lt` | 89.4 | -- |
| `thm-mem-integerMatrixOrders-psi` | 87.0 | 21.4 |

These large outputs strongly correlate with proof length (many tactic steps = many rendered proof states).

---

## Phase-by-Phase Analysis

### Phase 1: Module Reference Building (`findModuleRefs`)

**Location:** `Lean.Server.findModuleRefs` (Lean core)
**Input:** FileMap + all info trees
**Complexity:** O(T) where T = total info tree nodes
**Per-declaration cost:** Full traversal of ALL trees in the command state (not just the current declaration's trees)

**Impact estimate:** ~5% of highlighting time. The reference map (`HashMap Lsp.RefIdent Lsp.RefIdent`) is used by `Context.ids` for alias resolution. This is unavoidable but could be amortized.

### Phase 2: InfoTable Construction (`InfoTable.ofInfoTrees`)

**Location:** Code.lean:1871
**Structure:**
- `InfoTable.ofInfoTree` (partial, recursive): O(N) traversal of each InfoTree
- For each node: inserts into 4 HashMaps + appends to `allInfoSorted` array
- After all trees: `qsort` on `allInfoSorted` for containment queries

**Complexity:** O(N log N) due to the sort step
**Per-declaration cost:** Proportional to total info tree size for that command

**Cache structure built:**
- `tacticInfo: HashMap Range (Array (ContextInfo x TacticInfo))` -- O(1) tactic lookup
- `infoByExactPos: HashMap (Pos x Pos) (Array (ContextInfo x Info))` -- O(1) exact lookup
- `termInfoByName: HashMap Name (Array (ContextInfo x TermInfo))` -- O(1) name lookup
- `allInfoSorted: Array (Pos x Pos x ContextInfo x Info)` -- sorted for containment

**Impact estimate:** ~10% of highlighting time. The sort is the expensive part for large declarations.

### Phase 3: Suffix Index Construction (`buildSuffixIndex`)

**Location:** Code.lean:122-130
**Operation:** `env.constants.fold` -- iterates over EVERY constant in the environment
**Complexity:** O(E) where E = number of environment constants

**This is a major concern for large mathlib-dependent projects.** With mathlib, E can exceed 100K constants. This fold runs for every declaration, even though the environment barely changes between declarations in the same module.

**Impact estimate:** ~15-20% of highlighting time for mathlib-heavy projects. The suffix index maps final name components (`"add"`, `"mul"`, etc.) to full names for fuzzy identifier resolution.

### Phase 4: Message Filtering (`HighlightState.ofMessages`)

**Location:** Code.lean:797-818
**Complexity:** O(M) where M = total messages
**Impact estimate:** <1%. Cheap linear filter.

### Phase 5: Main Highlighting (`highlight'`, recursive)

**Location:** Code.lean:1688-1829
**Operation:** Recursive traversal of the syntax tree

This phase has several sub-costs:

#### 5a. `identKind'` (Token Classification)

**Location:** Code.lean:864-934
**Optimized with caching:** Results cached in `identKindCache: HashMap (Pos x Name) Token.Kind`
**Fallback chain:**
1. Cache hit -> O(1)
2. `lookupByExactPos` -> O(1) HashMap lookup
3. `lookupContaining` -> O(N) linear scan of sorted array (early termination possible)
4. `lookupTermInfoByName` -> O(1) HashMap lookup
5. Environment constant lookup + suffix index -> O(1) + potential `ppSignature` call

**`ppSignature` in Pass 4 is expensive** when triggered -- it involves pretty-printing the full type signature of a constant. Cached in `signatureCache`.

**Impact estimate:** ~5-10% depending on cache hit rate. For typical code, most identifiers are resolved in Pass 1 or 2.

#### 5b. `findTactics` / `findTactics'` (Tactic State Lookup)

**Location:** Code.lean:1374-1497
**Operation:** For each syntax node in tactic mode, look up tactic info
**Uses:** `InfoTable.tacticInfo?` (O(1) HashMap lookup) + `lookupContaining` (O(N) scan)
**Caching:** `hasTacticCache` and `childHasTacticCache` prevent redundant searches

**Impact estimate:** ~5%. The O(1) table lookups are fast; the cost is in `childHasTactics` which traverses syntax children.

#### 5c. `highlightGoals` (Proof State Rendering) -- **DOMINANT COST**

**Location:** Code.lean:1320-1360
**Operation:** For each tactic step with non-empty goals:
1. Iterate over all goals (MVarIds)
2. For each goal, iterate over local context declarations
3. For each hypothesis: `ppCodeWithInfos(type)` + `renderTagged` -> full MetaM pretty-printing
4. For conclusion: `ppCodeWithInfos(type)` + `renderTagged`

**`ppCodeWithInfos` (Code.lean:221-230):**
- Calls `instantiateMVars`
- Calls `ppExprTagged` (Lean's tagged pretty-printer, MetaM)
- Falls back to `ppExpr` on failure
- Each call involves MetaM context manipulation

**Caching:** `renderOrGet` caches rendered `Highlighted` by `Expr` key. `renderOrGetCodeWithInfos` caches `CodeWithInfos` by `Expr` key. `terms` and `ppTerms` HashMaps in HighlightState.

**But:** Caches are RESET between commands (`HighlightState.resetCache` at Code.lean:794, called in `highlightMany.go` and `highlightFrontendResult.go`). This means expression caches don't persist across declarations.

**Impact estimate:** ~50-60% of highlighting time. For a theorem with 20 tactic steps and 10 hypotheses per goal, that's ~200+ `ppCodeWithInfos` calls, each involving MetaM context setup and pretty-printing.

### Phase 6: Output Assembly (`Highlighted.fromOutput`)

**Location:** Code.lean:675-681
**Complexity:** O(output size)
**Impact estimate:** <1%. Simple list-to-tree conversion.

---

## Estimated Per-Phase Time Budget (1.5s typical SBS-Test declaration)

| Phase | Estimated % | Estimated ms | Notes |
|-------|------------|-------------|-------|
| findModuleRefs | 5% | 75 | Traverses all trees |
| InfoTable.ofInfoTrees | 10% | 150 | O(N log N) sort |
| buildSuffixIndex | 15% | 225 | O(E) env scan |
| ofMessages | <1% | 10 | Linear filter |
| highlight' traversal | 10% | 150 | Syntax recursion |
| identKind' calls | 8% | 120 | Mostly cached |
| findTactics lookups | 5% | 75 | O(1) table lookups |
| highlightGoals / ppCodeWithInfos | 55% | 825 | MetaM pretty-printing |
| Output assembly + JSON | 2% | 30 | Cheap |

For complex GCR declarations (~1.78s average), `highlightGoals` likely accounts for an even higher percentage due to more tactic steps and larger proof contexts.

---

## Cache Effectiveness Analysis

### HighlightState Caches

| Cache | Key Type | Hit Pattern | Cross-decl? |
|-------|----------|------------|-------------|
| `identKindCache` | `(Pos, Name)` | High within declaration | No (new HighlightState per decl) |
| `signatureCache` | `Name` | High for repeated constants | No |
| `hasTacticCache` | `Syntax.Range` | High for nested tactics | No |
| `childHasTacticCache` | `Syntax.Range` | High for nested tactics | No |
| `terms` | `Expr` | Medium (shared subexprs) | No (explicitly reset) |
| `ppTerms` | `Expr` | Medium (shared subexprs) | No (explicitly reset) |

**Critical finding:** ALL caches are per-declaration. They are created fresh for each declaration and discarded after. This means:

1. `signatureCache` -- The same constant's signature is pretty-printed independently in every declaration
2. `terms/ppTerms` -- The same expression type (e.g., `Nat`, `List Nat`) is re-rendered in every declaration
3. `buildSuffixIndex` -- The same environment scan runs for every declaration

### Unique Identity Counts (estimated)

For a typical SBS-Test declaration (10 tactic lines):
- Unique `(Pos, Name)` pairs in `identKindCache`: ~30-50
- Unique names in `signatureCache`: ~10-20
- Unique expressions in `terms/ppTerms`: ~20-40

For a complex GCR declaration (50+ tactic lines):
- Unique `(Pos, Name)` pairs: ~100-200
- Unique names in `signatureCache`: ~30-60
- Unique expressions in `terms/ppTerms`: ~80-150

---

## Top 10 Optimization Targets (Ranked by Expected Impact)

### 1. Cross-Declaration Expression Cache (HIGH impact, MEDIUM effort)
**Current:** `terms` and `ppTerms` caches reset between declarations.
**Proposed:** Persist expression rendering cache across declarations in the same module.
**Expected savings:** 20-30% of `highlightGoals` cost = ~10-15% total.
**Rationale:** Many hypotheses share the same types across tactic steps (e.g., `n : Nat` appears in every goal). Currently re-rendered each time.

### 2. Module-Level Suffix Index (HIGH impact, LOW effort)
**Current:** `buildSuffixIndex` scans all env constants for every declaration.
**Proposed:** Build once per module, pass as parameter.
**Expected savings:** 15-20% total for mathlib-heavy projects.
**Rationale:** The environment changes minimally between declarations in the same module.

### 3. Module-Level InfoTable + ModuleRefs (MEDIUM impact, MEDIUM effort)
**Current:** `InfoTable.ofInfoTrees` and `findModuleRefs` run per-declaration.
**Proposed:** Use `highlightFrontendResult` pattern: build once, iterate per command.
**Expected savings:** 10-15% total.
**Rationale:** Amortizes O(N log N) sort and full tree traversal.

### 4. Lazy Goal Rendering (HIGH impact, HIGH effort)
**Current:** ALL goals for ALL tactic steps are rendered eagerly during highlighting.
**Proposed:** For Crush 2 live infoview, render only the goals for the cursor position. Store goal MVarIds + ContextInfo, defer rendering.
**Expected savings:** 50-60% of highlighting time (eliminates ~90% of `ppCodeWithInfos` calls).
**Rationale:** For a 50-line proof, user views 1-2 goal states at a time, not all 50.
**Caveat:** This changes the output format -- requires downstream changes.

### 5. Incremental InfoTable Update (MEDIUM impact, HIGH effort)
**Current:** InfoTable rebuilt from scratch for each declaration.
**Proposed:** For single-declaration changes, incrementally update the table (add new entries, re-sort affected region).
**Expected savings:** 5-10% total.
**Rationale:** Most of the table is unchanged between declarations.

### 6. Parallel Goal Rendering (MEDIUM impact, MEDIUM effort)
**Current:** Goals rendered sequentially in `highlightGoals`.
**Proposed:** Render independent goals in parallel using `IO.mapTasks` or similar.
**Expected savings:** Variable -- depends on CPU cores and goal independence.
**Rationale:** Each goal's rendering is independent; MetaM contexts are separate.

### 7. Signature Cache Persistence (LOW-MEDIUM impact, LOW effort)
**Current:** `signatureCache` is per-declaration.
**Proposed:** Persist across declarations in module scope.
**Expected savings:** 2-5% total.
**Rationale:** The same constants (e.g., `Nat.add`, `List.length`) appear across many declarations.

### 8. `lookupContaining` Optimization (LOW impact, LOW effort)
**Current:** Linear scan of sorted array with early termination.
**Proposed:** Binary search for start position, then linear scan.
**Expected savings:** 1-2% total.
**Rationale:** For large info tables, the linear scan prefix before the relevant region wastes time.

### 9. `ppExprTagged` Caching in Lean Core (HIGH impact, IMPOSSIBLE without Lean changes)
**Current:** `ppExprTagged` runs full pretty-printing each time.
**Proposed:** Cache at the Lean level by expression + local context hash.
**Expected savings:** 30-40% of `highlightGoals` cost.
**Rationale:** Would eliminate redundant pretty-printing across all callers.

### 10. JSON Serialization Optimization (LOW impact, LOW effort)
**Current:** JSON serialized via `ToJson` instances.
**Proposed:** Use streaming JSON writer for large outputs.
**Expected savings:** <2% total.
**Rationale:** Serialization is fast compared to rendering.

---

## Baseline Numbers for Future Comparison

### SBS-Test Baseline (40 declarations)
- **Total build_project:** 57-61s (with full Lean elaboration + highlighting)
- **Average per declaration:** 1.4-1.5s
- **Average JSON output:** 8.6 KB/declaration
- **Largest output:** 18.7 KB (`bracket-list_length_append_tactic`)

### GCR Baseline (61 declarations)
- **Average JSON output:** 35.3 KB/declaration
- **Largest output:** 97.7 KB (`lem-cyclotomic-divisors-lcm-eq`)
- **Total JSON output:** 2.15 MB

### PNT Baseline (591 annotations)
- **Total build_project:** 1054s (17.6 minutes)
- **Average per declaration:** ~1.78s

### Target for Crush 2
- **Sub-200ms per declaration** for live infoview
- Current average: 1400-1780ms
- **Required speedup: 7-9x**

---

## Methodology Notes

### What Was Measured
- Build phase timings from `unified_ledger.json` (Python `build.py` instrumentation)
- Artifact output sizes via `wc -c` on `.lake/build/dressed/*/decl.json`
- Code structure analysis by reading SubVerso source (~1962 lines of Code.lean)

### What Could Not Be Measured (requires instrumentation)
- Per-phase breakdown within `highlightIncludingUnparsed` (need internal timers)
- `ppCodeWithInfos` call count per declaration
- Cache hit rates for `identKindCache`, `terms`, `ppTerms`
- InfoTable construction time vs highlight traversal time
- `buildSuffixIndex` time in isolation

### Recommended Instrumentation for Follow-Up
1. Add `IO.monoMsNow` timing around each phase in `highlightIncludingUnparsed`
2. Add counters for `ppCodeWithInfos` calls in `highlightGoals`
3. Add cache hit/miss counters in `identKind'` and `renderOrGet`
4. Measure `buildSuffixIndex` time with a simple wrapper
5. Profile `InfoTable.ofInfoTree` separately from the sort step

These would require temporary modifications to SubVerso (acceptable for profiling, revert before merging).

---

## Architectural Observations for Crush 2

### Per-Module vs Per-Declaration
The current SBS pipeline highlights per-declaration (via `captureHighlighting` in ElabRules). SubVerso's `highlightFrontendResult` already supports per-module highlighting with amortized setup costs. Switching to per-module would eliminate repeated `buildSuffixIndex`, `InfoTable` construction, and `findModuleRefs` calls.

### Lazy vs Eager Goal Rendering
For live infoview (Crush 2), eager rendering of all proof states is unnecessary. A lazy approach that stores goal MVarIds and renders on-demand would dramatically reduce per-declaration cost. This is the single highest-impact optimization for achieving sub-200ms.

### Cache Reset Between Declarations
The `HighlightState.resetCache` call (Code.lean:794) in `highlightMany.go` and `highlightFrontendResult.go` explicitly clears expression caches between commands. This was presumably done to avoid stale cache entries, but for a module where the environment grows monotonically, cached renderings remain valid. Removing or relaxing this reset could yield significant gains.

### Environment Constants Scale
For mathlib-dependent projects, `env.constants` can contain 100K+ entries. The `buildSuffixIndex` fold is O(E) per declaration. For PNT with 591 declarations, this means ~591 * O(100K) = O(59M) iterations just for suffix indexing. This is a clear candidate for one-time computation.
