# SBS First-Class Experience: Technical Specification

**Status:** Living document — single source of truth for Crushes 1-3
**Epic:** [#224](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/224)
**Last updated:** 2026-02-06

---

## 1. Vision

SBS transforms from a batch-oriented prototype into a live development tool where:

1. **Dress artifacts generate during normal Lake type-checking** — no separate build pass.
2. **SubVerso highlights in under 200ms** — enabling live infoview use.
3. **A forked Lean infoview displays blueprint data** — status, rendered LaTeX statements, dependency navigation — directly in VSCode.
4. **The browser site regenerates incrementally** via watch mode with live reload.

```
Edit .lean
  → Lake incremental recompile (Dress hooks always active)
    → SubVerso highlights in <200ms
    → Artifacts generated live (.json, .tex, .html, .hovers.json)
    → Infoview shows SBS panel (status, statement, deps)
  → Runway incrementally regenerates affected pages
  → Dev server live-reloads browser
```

The caching strategy is Lake-native incrementality. Unchanged files are not recompiled, so their artifacts are not regenerated. Custom caching is reserved for global operations (graph layout, manifest aggregation, site generation), which Waves 1-2 already addressed.

---

## 2. Current Architecture (Baseline)

### 2.1 Build Pipeline Phases

The current `build.py` orchestrator runs these phases sequentially:

1. **validation** — pre-flight structure checks
2. **sync_repos** — git pull all repos
3. **update_manifests** — update `lake-manifest.json` (conditional on Lean changes)
4. **build_toolchain** — build upstream: SubVerso → LeanArchitect → Dress → Runway
5. **fetch_mathlib_cache** — get mathlib cache
6. **build_project** — `BLUEPRINT_DRESS=1 lake build` (the costly separate pass)
7. **build_blueprint** — `lake build :blueprint` facet
8. **build_dep_graph** — generate dependency graph SVG
9. **generate_site** — run Runway site generation
10. **capture** — screenshot capture (optional)

**The problem:** Phase 6 is a full second compilation pass. Lake cannot share incremental state between the two passes because the env var changes the elaboration behavior.

### 2.2 Dress Activation (Three Gates)

`toolchain/Dress/Dress/Capture/ElabRules.lean:127-130`:

```lean
let dressEnv ← IO.getEnv "BLUEPRINT_DRESS"
let markerFile : System.FilePath := ".lake" / "build" / ".dress"
let markerExists ← markerFile.pathExists
let dressEnabled := dressEnv == some "1" || blueprint.dress.get (← getOptions) || markerExists
```

Dress activates when ANY of these are true:
- `BLUEPRINT_DRESS=1` environment variable
- `blueprint.dress` Lean option is set
- `.lake/build/.dress` marker file exists

### 2.3 Per-Declaration Artifact Structure

Each `@[blueprint]` declaration produces artifacts in `.lake/build/dressed/{Module/Path}/{label}/`:

| File | Content | Size (typical) |
|------|---------|----------------|
| `decl.tex` | LaTeX statement text | 0.2-2 KB |
| `decl.html` | Rendered HTML with syntax highlighting | 2-20 KB |
| `decl.hovers.json` | Hover ID → HTML content mapping | 1-10 KB |
| `decl.json` | Full metadata: name, label, highlighting, status | 5-50 KB |
| `manifest.entry` | Label + module path for manifest aggregation | 0.1 KB |

### 2.4 Content-Addressed Cache

`toolchain/Dress/Dress/Cache.lean` implements per-declaration caching:

**Cache location:** `.lake/build/dressed/.decl_cache/{hash}/`

**Hash components:**
1. Declaration fully qualified name
2. Node JSON (all `@[blueprint]` fields serialized)
3. Highlighting JSON (SubVerso `Highlighted` structure)
4. Source file path
5. Location range (`line:col-line:col`)

**Result:** 16-character hex string (UInt64 hash). On cache hit, all 5 artifact files are restored from cache instead of regenerated.

### 2.5 SubVerso InfoTable

`forks/subverso/src/SubVerso/Highlighting/Code.lean:37-47`:

```lean
structure InfoTable where
  tacticInfo : HashMap Syntax.Range (Array (ContextInfo × TacticInfo))
  infoByExactPos : HashMap (String.Pos.Raw × String.Pos.Raw) (Array (ContextInfo × Info))
  termInfoByName : HashMap Name (Array (ContextInfo × TermInfo))
  nameSuffixIndex : HashMap String (Array Name)
  allInfoSorted : Array (String.Pos.Raw × String.Pos.Raw × ContextInfo × Info)
```

**Performance profile:** 800-6500ms per declaration (93-99% of build time). The info tree is traversed once and indexed into HashMaps for O(1) lookups by position, name, and suffix. Containment queries use binary search on `allInfoSorted`.

**In-memory caches:** `identKindCache`, `signatureCache`, `hasTacticCache`, `childHasTacticCache` — all session-scoped, not persisted.

### 2.6 @[blueprint] Node Structure

`forks/LeanArchitect/Architect/Basic.lean:93-123`:

```lean
structure Node where
  name : Name
  latexLabel : String
  statement : NodePart        -- LaTeX text + dependency refs
  proof : Option NodePart     -- Optional proof
  status : NodeStatus         -- Auto-computed from proof state
  discussion : Option Nat     -- GitHub issue number
  title : Option String
  keyDeclaration : Bool       -- Dashboard highlight flag
  message : Option String     -- User notes
  priorityItem : Bool         -- Dashboard priority flag
  blocked : Option String
  potentialIssue : Option String
  technicalDebt : Option String
  misc : Option String
```

```lean
structure NodePart where
  text : String               -- LaTeX content
  uses : Array Name           -- Lean name references
  excludes : Array Name
  usesLabels : Array String   -- Label references (cross-declaration)
  excludesLabels : Array String
  latexEnv : String           -- e.g., "theorem", "lemma", "definition"
```

### 2.7 6-Status Color Model

Source of truth: `toolchain/Dress/Dress/Graph/Svg.lean:19-25`

| Status | Color | Hex | Determination |
|--------|-------|-----|---------------|
| `notReady` | Sandy Brown | `#F4A460` | Manual: `notReady := true` |
| `ready` | Light Sea Green | `#20B2AA` | Manual: `ready := true` |
| `sorry` | Dark Red | `#8B0000` | Auto: proof contains `sorry` |
| `proven` | Light Green | `#90EE90` | Auto: proof exists, no `sorry` |
| `fullyProven` | Forest Green | `#228B22` | Auto: proven + all dependencies proven |
| `mathlibReady` | Light Blue | `#87CEEB` | Manual: `mathlibReady := true` |

CSS variables in `dress-blueprint-action/assets/common.css` must match these hex values exactly.

### 2.8 runway.json Configuration

```json
{
  "title": "SBS-Test: Blueprint Feature Demonstration",
  "projectName": "SBSTest",
  "githubUrl": "https://github.com/e-vergo/SBS-Test",
  "baseUrl": "/SBS-Test/",
  "docgen4Url": null,
  "runwayDir": "runway",
  "assetsDir": "../dress-blueprint-action/assets",
  "statementSource": "both"
}
```

### 2.9 Manifest Structure

Aggregated from per-declaration `manifest.entry` files:

```json
{
  "stats": {
    "total": 40, "ready": 2, "proven": 4, "notReady": 0,
    "mathlibReady": 1, "hasSorry": 2, "fullyProven": 31
  },
  "projectNotes": {
    "technicalDebt": [], "priority": [],
    "potentialIssues": [], "misc": [], "blocked": []
  },
  "nodes": { "label": "#label", ... },
  "messages": [],
  "keyDeclarations": [],
  "checks": {
    "numComponents": 26, "isConnected": false,
    "cycles": [], "componentSizes": []
  }
}
```

---

## 3. Target Architecture

### 3.1 Single-Pass Build

**Before:** Two Lake builds. The first compiles Lean. The second (with `BLUEPRINT_DRESS=1`) re-compiles with artifact generation.

**After:** One Lake build. Dress hooks fire during normal compilation. The `blueprint.dress` Lean option is set in `lakefile.lean` (not via env var), making it part of Lake's option hash — so Lake knows that Dress-enabled builds and non-Dress builds are distinct configurations, and can cache both.

**Impact on `build.py`:** Phases 6 and 7 merge into a single `lake build`. The separate Dress pass disappears. The CSS-only fast path remains but is joined by a "Lean-only" fast path that rebuilds only changed declarations.

### 3.2 Live Infoview Panel

A forked Lean infoview adds a "Blueprint" tab. When the cursor is on a `@[blueprint]` declaration:

```
┌─────────────────────────────────────┐
│ Goals │ Messages │ Blueprint         │
├─────────────────────────────────────┤
│                                     │
│  ● fullyProven   Schur's Lemma      │
│                                     │
│  ┌─ Statement ──────────────────┐   │
│  │  Let V be a finite-dim...    │   │
│  │  [rendered LaTeX via KaTeX]  │   │
│  └──────────────────────────────┘   │
│                                     │
│  Dependencies (3):                  │
│    ● fullyProven  irreducible_rep   │
│    ● fullyProven  schur_orthogonal  │
│    ● proven       group_algebra     │
│                                     │
│  Dependents (1):                    │
│    ● ready        burnside_thm      │
│                                     │
│  ▸ Proof (click to expand)          │
│  ▸ Notes: "Needs cleanup"          │
│                                     │
└─────────────────────────────────────┘
```

**Data flow:** Cursor position → Lean RPC → query environment for nearest `@[blueprint]` `Node` → return structured data → React renders with KaTeX.

### 3.3 SubVerso Performance Target

| Metric | Current | Target |
|--------|---------|--------|
| Median per-declaration | 800-2000ms | < 200ms |
| P95 per-declaration | 2000-4000ms | < 500ms |
| Max (PNT outliers) | 6500ms | < 1500ms |
| Initial response (basic syntax) | N/A | < 50ms |
| Hover computation (on-demand) | Upfront, bundled | < 10ms per event |

Achieved through: critical path optimization, lazy hover computation, shared type info pool, progressive refinement.

### 3.4 Live Development Server

```bash
sbs dev --project SBSTest
# Equivalent to: watch + incremental rebuild + serve + live reload
```

| Change Type | Action | Latency Target |
|-------------|--------|----------------|
| `.lean` source | Lake recompile (incremental) + page regen | Depends on Lake |
| Artifact change (post-Lake) | Regenerate affected pages only | < 2s |
| CSS/JS change | Asset copy only | < 1s |
| Status-only change | Recolor graph nodes (no re-layout) | < 500ms |
| Graph topology change | Re-layout graph | < 2s |
| Template change | Full page regen | < 5s |

---

## 4. Track Specifications

### Track 1: Dress Upstream Integration

**Goal:** Eliminate the separate `BLUEPRINT_DRESS=1` build pass. Lake handles incrementality natively.

#### T1-A: Audit Dress Activation Pathway ([#246](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/246))

Deliverable: Written assessment covering:
1. Which code paths in `ElabRules.lean` are gated by `dressEnabled`
2. What happens if hooks fire on non-`@[blueprint]` declarations (must be zero-cost)
3. Whether artifact files conflict with Lake's own `.lake/build/` outputs
4. Recommended approach: `blueprint.dress` Lean option in `lakefile.lean` vs. always-active

#### T1-B: Integration ([#247](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/247))

Implementation:
1. Set `blueprint.dress` option in `lakefile.lean` for SBS projects
2. Remove env-var gating path from `ElabRules.lean` (keep option-based gate)
3. Update `build.py` to drop phase 6 (separate Dress pass)
4. Verify: `lake build` produces identical artifacts to current two-pass approach

#### T1-C: Incremental Validation ([#248](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/248))

Test matrix:

| Scenario | Expected Artifact Behavior |
|----------|---------------------------|
| No-op rebuild | Zero artifacts touched |
| Single declaration change | Only that declaration's 5 files regenerated |
| New declaration added | New artifacts only, existing untouched |
| Declaration deleted | Stale artifacts detected/cleaned |
| Statement-only change | Scoped regeneration |
| Non-blueprint file change | Zero artifact work |
| Dependency chain change | Correct propagation |

---

### Track 2: SubVerso Live Performance

**Goal:** Sub-200ms per-declaration highlighting for live infoview use.

#### T2-A: Profile Pipeline ([#245](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/245))

Instrument and measure each phase of `Highlighted` construction:

```
Info tree traversal → InfoTable construction → Token classification → Hover extraction → Serialization
```

Benchmark across all three projects. Deliverable: profiling report with per-phase breakdown, top 10 slowest declarations, ranked optimization targets.

#### T2-B: Optimize Critical Paths ([#250](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/250))

Probable optimization targets (to be confirmed by profiling):
- **Containment queries:** `allInfoSorted` uses linear scan. Interval tree or binary search on sorted spans could reduce to O(log n).
- **Hover extraction:** Currently computed for every token upfront. Batch or defer.
- **String concatenation:** Lean string concat is O(n^2). Use builder pattern.
- **Redundant classification:** Stdlib types (Nat, List, Prop) classified identically every time.

#### T2-C: Lazy/Incremental Highlighting ([#251](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/251))

Architectural shift from eager to lazy:

| Strategy | Impact | Complexity |
|----------|--------|------------|
| Lazy hover computation | Skip upfront hover work; compute on demand | Low |
| Shared type info pool | Reuse stdlib classification across declarations | Medium |
| Progressive refinement | Basic syntax < 50ms; semantic tokens async | Medium |
| Partial re-highlighting | Only re-process changed syntax nodes | High |

---

### Track 3: Lean Infoview Fork

**Goal:** SBS panel in VSCode showing status, rendered LaTeX, dependency navigation.

#### T3-A: Fork Setup + Minimal Panel ([#252](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/252))

**Decision gate:** Before forking, evaluate whether Lean's [user widgets](https://lean-lang.org/lean4/doc/examples/widgets.html) can achieve the same result. User widgets allow custom React components in the infoview without forking. If widgets suffice, the "fork" is actually a Lean library + npm package — dramatically simpler to maintain.

**If fork is needed:**
- Fork `lean4` (server-side RPC) and `lean4-infoview` (React frontend)
- Add "Blueprint" tab alongside Goals/Messages
- Placeholder content from nearest `@[blueprint]` declaration
- Document all modified files for upstream rebase tracking

**Fork maintenance rule:** Minimize diff. Every changed line must be justified. Track upstream releases.

#### T3-B: Wire Data via RPC ([#253](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/253))

**RPC endpoint definition:**

```
Method: $/sbs/blueprintAtPosition
Params: { textDocument: TextDocumentIdentifier, position: Position }
Result: BlueprintData | null
```

**`BlueprintData` schema:**

```typescript
interface BlueprintData {
  label: string;
  name: string;
  status: "notReady" | "ready" | "sorry" | "proven" | "fullyProven" | "mathlibReady";
  statusColor: string;          // Hex from 6-status model
  title: string | null;
  statement: {
    latex: string;              // Raw LaTeX for KaTeX rendering
    latexEnv: string;           // "theorem", "lemma", "definition", etc.
  };
  proof: {
    exists: boolean;
    hasSorry: boolean;
    text: string | null;        // Proof source (for collapsible display)
  };
  dependencies: Array<{
    label: string;
    name: string;
    status: string;
    statusColor: string;
    sourceLocation: Location;   // For click-to-navigate
  }>;
  dependents: Array<{
    label: string;
    name: string;
    status: string;
    statusColor: string;
    sourceLocation: Location;
  }>;
  metadata: {
    discussion: number | null;  // GitHub issue number
    message: string | null;
    keyDeclaration: boolean;
    priorityItem: boolean;
    blocked: string | null;
    potentialIssue: string | null;
    technicalDebt: string | null;
  };
  sourceLocation: Location;     // Declaration source for this node
}
```

**Implementation path:** During elaboration, `Dress/Load.lean` already reconstructs `Node` data from the environment. The RPC handler:
1. Finds the enclosing declaration at cursor position
2. Queries the environment for its `@[blueprint]` `Node`
3. Resolves `uses`/`usesLabels` to dependency info
4. Returns structured `BlueprintData`

#### T3-C: LaTeX Rendering ([#255](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/255))

**Technology:** KaTeX (lightweight, ~300KB, fast client-side rendering).

**React component:**
```tsx
<LaTeXStatement latex={data.statement.latex} env={data.statement.latexEnv} />
```

**Requirements:**
- Render the LaTeX subset used in `@[blueprint]` statements
- Support custom macros from project preambles (via configurable macro injection)
- Graceful fallback: malformed LaTeX → raw text + warning indicator
- Rendering latency < 20ms per statement

#### T3-D: Interactive Navigation ([#256](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/256))

**Features:**
1. Status color indicators using the 6-status hex values
2. Clickable dependency list → navigate to source location
3. Mini dependency DAG (current node + immediate neighbors)
4. Collapsible proof display with SubVerso highlighting
5. Metadata panel (discussion link, notes, project flags)

**Mini graph library:** Evaluate `dagre` (layout) + lightweight SVG rendering. Must render in < 100ms for typical neighborhoods (< 20 nodes).

---

### Track 4: Statement Validation

**Goal:** Catch drift between LaTeX statements and Lean declarations at elaboration time.

#### T4-A: Completeness + Basic LaTeX ([#249](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/249))

Fires during elaboration as Lean diagnostics:

| Check | Severity | Suppressible |
|-------|----------|-------------|
| Empty `statement` field | Warning | `skipValidation := true` |
| Unbalanced `{}` in statement | Warning | No |
| Unbalanced math delimiters | Warning | No |
| Non-UTF8 characters | Warning | No |

**Zero noise requirement:** All three existing projects (SBS-Test, GCR, PNT) must produce zero spurious warnings.

#### T4-B: Heuristic Cross-Referencing ([#254](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/254))

**Not full semantic equivalence.** A smoke test that catches obvious drift.

**Matching strategy:**
1. Extract Lean signature: quantified variables, hypothesis types, conclusion type, key identifiers
2. Extract LaTeX: mathematical symbols, quantifier phrases, structural elements
3. Cross-reference: key types in Lean should have plausible LaTeX counterparts; quantifier counts should roughly match

**Quality bar:** < 5% false positive rate on existing projects. Suppressible per-declaration via `skipCrossRef := true`.

---

### Track 5: Live Development Experience

**Goal:** `sbs dev` command for edit-save-see workflow.

#### T5-A: Watch Mode + Incremental Site Regen ([#257](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/257))

**Watch targets:**
- `.lake/build/dressed/` — artifact changes (post-Lake recompile)
- `dress-blueprint-action/assets/` — CSS/JS changes
- Runway templates — template changes

**Change classification:**

```python
def classify_change(path: Path) -> Action:
    if path.suffix in ('.css', '.js'):
        return Action.ASSET_COPY
    if path.name == 'manifest.entry':
        return Action.MANIFEST_REGEN
    if is_graph_topology_change(path):
        return Action.GRAPH_RELAYOUT
    if is_status_only_change(path):
        return Action.GRAPH_RECOLOR
    if is_template(path):
        return Action.FULL_PAGE_REGEN
    return Action.PAGE_REGEN  # default: regen affected page
```

**Graph intelligence:** Compare previous and current `dep-graph.json` edge sets. If edges changed → re-layout. If only node statuses changed → recolor SVG in-place (no layout recalc).

#### T5-B: Dev Server + Live Reload ([#258](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/258))

**Architecture:**

```
┌──────────────┐     ┌────────────────┐     ┌─────────────┐
│ File Watcher │────→│ Change Handler │────→│ Site Regen   │
│ (watchdog)   │     │ (classifier)   │     │ (incremental)│
└──────────────┘     └────────────────┘     └──────┬──────┘
                                                   │
                                            ┌──────▼──────┐
                                            │  WebSocket   │
                                            │  Broadcast   │
                                            └──────┬──────┘
                                                   │
                                            ┌──────▼──────┐
                                            │  Browser(s)  │
                                            │  auto-reload │
                                            └─────────────┘
```

**Implementation:**
- Python `http.server` + `websockets` library
- Injected `<script>` connects to `/ws`, reloads on message
- CSS-only changes → hot-reload stylesheets (no full page refresh)
- 50ms debounce to prevent reload storms

---

## 5. Crush Sessions

### Crush 1: Foundation

**Tracks active:** T1 (full), T2-A, T4-A
**Parallelism:** T1-A and T2-A and T4-A can run concurrently. T1-B depends on T1-A. T1-C depends on T1-B.

| Order | Issue | Title |
|-------|-------|-------|
| 1a | [#246](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/246) | Audit Dress activation pathway |
| 1b | [#245](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/245) | Profile SubVerso highlighting pipeline |
| 1c | [#249](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/249) | Statement completeness validator |
| 2 | [#247](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/247) | Integrate Dress into normal Lake build |
| 3 | [#248](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/248) | Validate Lake-native incremental behavior |

**Exit criteria:** Single-pass `lake build` produces all artifacts. SubVerso profiling data available. Basic statement validation active.

### Crush 2: Performance + Infoview

**Tracks active:** T2-B/C, T3-A/B, T4-B
**Parallelism:** T2-B and T3-A and T4-B can run concurrently. T2-C depends on T2-B. T3-B depends on T3-A.

| Order | Issue | Title |
|-------|-------|-------|
| 1a | [#250](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/250) | Optimize SubVerso critical paths |
| 1b | [#252](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/252) | Fork Lean infoview: setup + minimal panel |
| 1c | [#254](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/254) | Heuristic statement cross-referencing |
| 2a | [#251](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/251) | Lazy/incremental SubVerso highlighting |
| 2b | [#253](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/253) | Wire SBS data to infoview via RPC |

**Exit criteria:** SubVerso < 200ms median. Infoview shows real blueprint data. Cross-referencing catches obvious drift.

### Crush 3: Polish + Live Dev

**Tracks active:** T3-C/D, T5
**Parallelism:** T3-C and T5-A can run concurrently. T3-D depends on T3-C. T5-B depends on T5-A.

| Order | Issue | Title |
|-------|-------|-------|
| 1a | [#255](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/255) | LaTeX rendering in infoview |
| 1b | [#257](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/257) | Watch mode + incremental site regen |
| 2a | [#256](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/256) | Interactive navigation in infoview |
| 2b | [#258](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/258) | Dev server with live reload |

**Exit criteria:** LaTeX renders in infoview. Click-to-navigate works. `sbs dev` provides full live workflow.

---

## 6. Data Contracts

### 6.1 Dress → Infoview (RPC)

The RPC endpoint `$/sbs/blueprintAtPosition` returns `BlueprintData` as defined in Section 4 (Track 3-B). This is the primary data contract between the build system and the IDE.

### 6.2 Dress → Runway (Artifacts)

Per-declaration artifacts in `.lake/build/dressed/{Module/Path}/{label}/`:
- `decl.tex`, `decl.html`, `decl.hovers.json`, `decl.json`, `manifest.entry`

Manifest aggregation: `manifest.json` at project root (schema in Section 2.9).

### 6.3 Watcher → Site Generator (Change Events)

```python
@dataclass
class ChangeEvent:
    path: Path
    action: Action  # ASSET_COPY | MANIFEST_REGEN | GRAPH_RELAYOUT | GRAPH_RECOLOR | PAGE_REGEN | FULL_PAGE_REGEN
    affected_labels: list[str]  # For PAGE_REGEN: which declarations changed
```

### 6.4 Site Generator → Browser (WebSocket)

```json
{ "type": "reload" }
{ "type": "css-update", "path": "common.css" }
```

---

## 7. Risk Register

| Risk | Impact | Mitigation |
|------|--------|-----------|
| User widgets sufficient (no fork needed) | Crush 2 scope shrinks significantly | T3-A explicitly evaluates widgets first |
| SubVerso optimization hits diminishing returns | Live infoview feels sluggish on large declarations | Progressive refinement (basic syntax fast, semantic async) |
| Lake option hash incompatibility | Dress-enabled builds invalidate non-Dress caches | T1-A audit will surface this; may need Lake upstream discussion |
| KaTeX doesn't support project-specific macros | LaTeX rendering incomplete | Macro injection from project preamble; fallback to raw text |
| Fork maintenance burden | Upstream Lean changes break fork | Minimize diff; document every change; track upstream releases |
| Heuristic validation false positives | Developers disable validation entirely | Conservative matching; per-declaration suppression; < 5% FP rate |

---

## 8. Success Metrics

### Quantitative

| Metric | Current | Target |
|--------|---------|--------|
| Build passes for artifacts | 2 | 1 |
| No-op rebuild time | ~13s (cached) | < 1s |
| SubVerso median latency | 800-2000ms | < 200ms |
| Infoview RPC latency | N/A | < 50ms |
| Site regen (artifact change) | Full rebuild | < 2s |
| CSS change → browser update | Manual refresh | < 1s |

### Qualitative

- Yaël: blueprint data visible in VSCode without browser context-switch
- Alex: PNT+ delimiter workflow works natively
- New users: start with `paper.tex`, migrate to Lean-first seamlessly
- All contributors: statement/declaration drift caught automatically

---

## 9. File Reference Index

Key files referenced throughout this spec, organized by component:

**Dress (artifact generation):**
- `toolchain/Dress/Dress/Capture/ElabRules.lean` — elaboration hooks, env-var gating
- `toolchain/Dress/Dress/Generate/Declaration.lean` — per-declaration artifact writing
- `toolchain/Dress/Dress/Cache.lean` — content-addressed caching
- `toolchain/Dress/Dress/Load.lean` — environment queries for node data
- `toolchain/Dress/Dress/Graph/Svg.lean` — 6-status color model
- `toolchain/Dress/Dress/SubVersoExtract.lean` — SubVerso integration

**LeanArchitect (attribute system):**
- `forks/LeanArchitect/Architect/Basic.lean` — `Node`, `NodePart`, `NodeStatus` types
- `forks/LeanArchitect/Architect/Attribute.lean` — `@[blueprint]` attribute processing

**SubVerso (highlighting):**
- `forks/subverso/src/SubVerso/Highlighting/Code.lean` — `InfoTable`, highlighting pipeline

**Runway (site generation):**
- `toolchain/Runway/` — site generator, dashboard, paper/PDF

**Build tooling:**
- `dev/scripts/build.py` — build orchestrator
- `dev/scripts/sbs/build/orchestrator.py` — phase definitions
- `dev/scripts/sbs/build/caching.py` — Python-side caching

**Assets:**
- `toolchain/dress-blueprint-action/assets/common.css` — CSS variables (must match color model)
- `toolchain/dress-blueprint-action/assets/` — all CSS/JS

**Configuration:**
- `toolchain/SBS-Test/runway.json` — project configuration
- `toolchain/SBS-Test/lakefile.lean` — Lake build configuration
