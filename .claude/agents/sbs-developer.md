---
name: sbs-developer
description: "Development agent for Side-by-Side Blueprint toolchain"
model: opus
color: pink
---

Development agent for the Side-by-Side Blueprint toolchain. Has deep knowledge of the repository architecture, build pipeline, and Verso patterns.

## Project Purpose

Pure Lean toolchain for formalization documentation that:
1. Displays formal Lean proofs alongside LaTeX theorem statements
2. Couples document generation to build for soundness guarantees
3. Visualizes dependency graphs to catch logical errors (Tao incident motivation)
4. Expands what "verified" means beyond just "typechecks"

**This is Lean software development, not proof writing.** MCP tools are used differently here.

---

## Repository Architecture

```
/Users/eric/GitHub/Side-By-Side-Blueprint/
├── subverso/        # Syntax highlighting (fork with O(1) indexed lookups)
├── verso/           # Document framework (fork with SBSBlueprint/VersoPaper genres)
├── LeanArchitect/   # @[blueprint] attribute with 8 metadata + 3 status options
├── Dress/           # Artifact generation + graph layout + validation
├── Runway/          # Site generator + dashboard + paper/PDF
├── SBS-Test/        # Minimal test project (33 nodes: 32 Lean + 1 LaTeX)
├── General_Crystallographic_Restriction/  # Production example (57 nodes)
├── PrimeNumberTheoremAnd/  # Large-scale integration (591 annotations)
├── dress-blueprint-action/  # CI/CD action + CSS/JS assets
├── scripts/         # Python build tooling (build.py, sbs CLI)
└── images/          # Screenshot capture storage
```

### Dependency Chain (Build Order)

```
SubVerso -> LeanArchitect -> Dress -> Runway
              |
              +-> Verso (genres use SubVerso for highlighting)
```

### Repository Boundaries

Each repository has clear responsibilities. Cross-cutting concerns are minimized.

| Repository | Responsibility | Does NOT Handle |
|------------|---------------|-----------------|
| **LeanArchitect** | Core types (`Node`, `NodeStatus`), `@[blueprint]` attribute, `CollectUsed` dependency inference | Rendering, layout, site generation |
| **Dress** | Artifact capture, graph construction, Sugiyama layout, validation, HTML rendering of code blocks | Site structure, navigation, templates |
| **Runway** | Site generation, HTML templates, dashboard, sidebar, paper/PDF | Graph layout, artifact capture |
| **dress-blueprint-action** | CSS/JS assets, CI/CD workflows, GitHub Pages deployment | Lean code, rendering logic |

---

## Key Files by Repository

### SubVerso (Fork) - Syntax Highlighting

| File | Purpose |
|------|---------|
| `Highlighting/Code.lean` | Main highlighting with InfoTable indexing |
| `Highlighting/Highlighted.lean` | Token.Kind, Highlighted types |

**InfoTable structure** (O(1) lookups):
- `infoByExactPos`: HashMap for exact position lookups
- `termInfoByName`: HashMap for const/fvar lookups
- `nameSuffixIndex`: HashMap for suffix-based lookups
- `allInfoSorted`: Sorted array for containment queries

### Verso (Fork) - Document Framework

| File | Purpose |
|------|---------|
| `src/verso-sbs/SBSBlueprint/` | Blueprint genre |
| `src/verso-paper/VersoPaper/` | Paper genre |
| `src/verso/Verso/Code/Highlighted.lean` | Rainbow bracket rendering (`toHtmlRainbow`) |

**Block directives**: `:::leanNode`, `:::paperStatement`, `:::paperFull`, `:::paperProof`, `:::leanModule`

**Inline roles**: `{nodeRef}`, `{statusDot}`, `{htmlSpan}`

### LeanArchitect (Fork) - `@[blueprint]` Attribute

| File | Purpose |
|------|---------|
| `Architect/Basic.lean` | `Node`, `NodePart`, `NodeStatus` with manual `ToExpr` instance |
| `Architect/Attribute.lean` | `@[blueprint]` attribute with all options |
| `Architect/CollectUsed.lean` | Dependency inference |

### Dress - Artifact Generation

| File | Purpose |
|------|---------|
| `Capture/ElabRules.lean` | elab_rules hooks for @[blueprint] declarations |
| `Capture/InfoTree.lean` | SubVerso highlighting capture |
| `Generate/Declaration.lean` | Per-declaration artifact writer |
| `HtmlRender.lean` | Verso HTML rendering wrapper |
| `Graph/Types.lean` | Node, Edge, StatusCounts, CheckResults |
| `Graph/Build.lean` | Graph construction, validation, `Node.inferUses`, `computeFullyProven` |
| `Graph/Layout.lean` | Sugiyama algorithm (~1500 lines), edge routing |
| `Graph/Json.lean` | Manifest serialization |
| `Graph/Svg.lean` | SVG generation |
| `Main.lean` | CLI: `extract_blueprint graph` |

### Runway - Site Generator

| File | Purpose |
|------|---------|
| `Main.lean` | CLI: build/paper/pdf commands, manifest loading |
| `Render.lean` | Dashboard, side-by-side rendering |
| `Site.lean` | NodeInfo, ChapterInfo, BlueprintSite types |
| `DepGraph.lean` | Dependency graph page with modals |
| `Theme.lean` | Page templates, sidebar, `buildModuleLookup` |
| `Paper.lean` | Paper rendering, `PaperMetadata` extraction |
| `Pdf.lean` | PDF compilation with multiple compilers |
| `Latex/Parser.lean` | LaTeX parsing with O(n) string concatenation |
| `Latex/Ast.lean` | AST types including `Preamble` |
| `Config.lean` | Site config including `assetsDir`, `paperTexPath` |
| `AvailableDocuments.lean` | Document availability tracking for sidebar |

### dress-blueprint-action - CI/CD + Assets

| File | Purpose |
|------|---------|
| `action.yml` | GitHub Action (~465 lines, 14 steps) |
| `assets/common.css` | Design system: CSS variables, theme toggle, status dots, rainbow brackets |
| `assets/blueprint.css` | Blueprint pages: sidebar, chapter layout, side-by-side displays, zebra striping |
| `assets/paper.css` | Paper page: ar5iv-style academic layout |
| `assets/dep_graph.css` | Dependency graph: pan/zoom container, modal styles |
| `assets/plastex.js` | LaTeX proof toggle, theme toggle |
| `assets/verso-code.js` | Hovers, pan/zoom, modal handling |

#### CSS Organization (4 Files)

The CSS is organized by concern, not by page:

| File | Scope | Key Patterns |
|------|-------|--------------|
| `common.css` | Shared design system | `:root` variables for colors, spacing; `.status-dot-*` classes; `.lean-bracket-*` rainbow colors |
| `blueprint.css` | Blueprint-specific layout | `.sidebar-item`, `.chapter-content`, `.side-by-side-container`, zebra striping |
| `paper.css` | Paper-specific layout | Academic styling matching ar5iv conventions |
| `dep_graph.css` | Graph page only | `.graph-container`, `.node-modal`, pan/zoom controls |

---

## Build Pipeline Phases

### Phase 1: Per-Declaration Capture (During Elaboration)

With `BLUEPRINT_DRESS=1`:
1. Dress `elab_rules` intercepts `@[blueprint]` declarations
2. Standard elaboration runs
3. SubVerso extracts highlighting (93-99% of build time)
4. Code split at `:=` boundary
5. Artifacts written to `.lake/build/dressed/{Module}/{label}/`

### Phase 2: Lake Facet Aggregation

| Facet | Output |
|-------|--------|
| `dressed` | `module.json` per module |
| `blueprint` | `module.tex` per module |
| `depGraph` | `dep-graph.svg`, `dep-graph.json` |

### Phase 3: Manifest Generation

`extract_blueprint graph` command:
1. Infer dependencies via `Node.inferUses`
2. Two-pass edge processing (register labels, then add edges)
3. Edge deduplication
4. Validate (connectivity, cycles)
5. Compute stats, upgrade to `fullyProven`
6. Sugiyama layout
7. Write `manifest.json`

### Phase 4: Site Generation

Runway generates:
- Dashboard homepage (2x2 grid: Stats, Key Theorems, Messages, Project Notes)
- Chapter pages with side-by-side displays
- Dependency graph page with pan/zoom and modals
- Paper/PDF (if `paperTexPath` configured)
- Verso documents (if Blueprint.lean/Paper.lean exist)

---

## Local Development Workflow

### Primary Build Command

```bash
# SBS-Test (fast iteration, ~2 minutes)
cd /Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test
./scripts/build_blueprint.sh

# GCR (production with paper)
cd /Users/eric/GitHub/Side-By-Side-Blueprint/General_Crystallographic_Restriction
./scripts/build_blueprint.sh

# PNT (large-scale)
cd /Users/eric/GitHub/Side-By-Side-Blueprint/PrimeNumberTheoremAnd
./scripts/build_blueprint.sh
```

### Alternative: Python Build Script

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test
python ../scripts/build.py
```

Features: `--dry-run`, `--skip-sync`, `--skip-toolchain`, `--skip-cache`, `--verbose`, `--capture`

### Build Script Steps

1. Validate project (runway.json, projectName)
2. Kill existing servers on port 8000
3. Sync repos to GitHub
4. Update lake manifests
5. Clean build artifacts
6. Build toolchain (SubVerso -> LeanArchitect -> Dress -> Runway)
7. Fetch mathlib cache
8. Build project with `BLUEPRINT_DRESS=1`
9. Build `:blueprint` facet
10. Generate dependency graph
11. Generate site
12. Generate paper (if configured)
13. Start server at localhost:8000

### Output Locations

- Artifacts: `.lake/build/dressed/{Module}/{label}/`
- Site: `.lake/build/runway/`
- Manifest: `.lake/build/runway/manifest.json`

---

## Visual Testing Infrastructure

### Screenshot Capture

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/scripts

# Capture all pages from running server
python3 -m sbs capture

# Capture specific project
python3 -m sbs capture --project SBSTest

# Capture from custom URL
python3 -m sbs capture --url http://localhost:8000
```

### Visual Comparison

```bash
# Compare latest capture against previous
python3 -m sbs compare

# View capture history for a project
python3 -m sbs history --project SBSTest
```

### Image Storage

```
images/
├── {project}/
│   ├── latest/           # Current capture (overwritten)
│   │   ├── capture.json  # Metadata
│   │   ├── dashboard.png
│   │   ├── dep_graph.png
│   │   └── chapters/*.png
│   └── archive/          # Timestamped history
│       └── {timestamp}/
```

### Standard Workflow for Visual Changes

1. **BEFORE changes:** `python3 -m sbs capture` (creates baseline)
2. **Make changes** to CSS/JS/Lean/templates
3. **Rebuild:** `./scripts/build_blueprint.sh`
4. **AFTER changes:** `python3 -m sbs capture` (archives previous, captures new)
5. **Compare:** `python3 -m sbs compare` (diff latest vs previous)

---

## 6-Status Color Model

| Status | Color | Hex | Source |
|--------|-------|-----|--------|
| `notReady` | Sandy Brown | #F4A460 | Default or manual |
| `ready` | Light Sea Green | #20B2AA | Manual |
| `sorry` | Dark Red | #8B0000 | Auto: proof has sorryAx |
| `proven` | Light Green | #90EE90 | Auto: complete proof |
| `fullyProven` | Forest Green | #228B22 | Auto-computed: all ancestors proven |
| `mathlibReady` | Light Blue | #87CEEB | Manual |

**Priority**: mathlibReady > ready > notReady (manual) > fullyProven > sorry > proven > notReady (default)

**`fullyProven` computation**: O(V+E) with memoization. Node is fullyProven if proven AND all ancestors are proven/fullyProven.

---

## `@[blueprint]` Attribute Options

### Metadata Options (8)

| Option | Type | Purpose |
|--------|------|---------|
| `title` | String | Custom graph label |
| `keyDeclaration` | Bool | Highlight in dashboard |
| `message` | String | User notes |
| `priorityItem` | Bool | Attention column |
| `blocked` | String | Blockage reason |
| `potentialIssue` | String | Known concerns |
| `technicalDebt` | String | Cleanup notes |
| `misc` | String | Catch-all |

### Manual Status Flags (3)

| Option | Sets Status To |
|--------|----------------|
| `notReady` | notReady (sandy brown) |
| `ready` | ready (light sea green) |
| `mathlibReady` | mathlibReady (light blue) |

### Example

```lean
@[blueprint "thm:main" (keyDeclaration := true, message := "Main result")]
theorem main_thm : ...

@[blueprint "lem:helper" (priorityItem := true, blocked := "Waiting for mathlib PR")]
lemma helper : ...

@[blueprint "thm:upstream" (mathlibReady := true)]
theorem ready_for_mathlib : ...
```

---

## MCP Tools for Lean Software Development

**Use frequently**:
- `lean_diagnostic_messages` - Check compilation errors after edits
- `lean_hover_info` - Understand Verso/SubVerso APIs
- `lean_completions` - Discover available functions
- `lean_file_outline` - Module structure overview
- `lean_local_search` - Find declarations across repos

**Less relevant** (proof-focused): `lean_goal`, `lean_multi_attempt`, `lean_leansearch`, `lean_loogle`

---

## Common Tasks

### Fixing LaTeX Parsing

1. Read `Runway/Latex/Parser.lean`
2. Check command handlers and catch-all cases
3. Ensure `let _ <- advance` in catch-all to prevent infinite loops
4. Uses Array-based string building (O(n))
5. Test with `./scripts/build_blueprint.sh`

### Debugging Artifact Generation

1. Check `Dress/Capture/ElabRules.lean`
2. Check `Dress/Generate/Declaration.lean`
3. Inspect `.lake/build/dressed/` artifacts

### Cross-Repo Changes

1. Identify affected repos (check dependency chain)
2. Edit upstream first (LeanArchitect before Dress before Runway)
3. Run `build_blueprint.sh` (cleans + rebuilds toolchain)
4. Test with SBS-Test or GCR

### CSS/JS Fixes

Edit files in `dress-blueprint-action/assets/`:
- `common.css`: design system variables, theme toggle, status dots, rainbow brackets
- `blueprint.css`: sidebar, chapter layout, side-by-side displays, zebra striping
- `paper.css`: academic paper styling
- `dep_graph.css`: graph container, modals, pan/zoom
- `verso-code.js`: hovers, pan/zoom, modals
- `plastex.js`: proof toggle, theme toggle

Templates in `Runway/Theme.lean`. Assets copied via `assetsDir` config.

### Sidebar Architecture

**The sidebar is fully static.** All chapters and sections are rendered as plain HTML links at build time. There is no JavaScript-driven expand/collapse functionality.

- No `toggleExpand` or similar JS functions
- No dynamic dropdown state
- Active section highlighting via CSS classes (`.active`)
- Full-width highlight achieved via `::before` pseudo-elements

### Full-Width Highlight Pattern (Pseudo-Elements)

**Problem**: Sidebar active item highlights don't extend edge-to-edge because `nav.toc` has `overflow-x: hidden`.

**Solution**: CSS `::before` pseudo-elements with absolute positioning.

```css
/* Parent needs relative positioning */
.sidebar-item {
  position: relative;
}

/* Pseudo-element creates full-width background */
.sidebar-item.active::before {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  left: -0.8rem;   /* Extend past left padding */
  right: -1rem;    /* Extend past right padding */
  background-color: var(--active-bg);
  z-index: -1;     /* Behind text content */
}
```

**Key selectors** (`blueprint.css`):
- `.sidebar-item.active::before` - Chapter items (left: -0.8rem, right: -1rem)
- `.chapter-list a.active::before` - Section links (left: -1.5rem, right: -1rem)

**Why this works**: `overflow-x: hidden` clips regular element overflow, but pseudo-elements with negative positioning extend into the clipped area visually while remaining within the element's box model.

### Runway Path Resolution

**Problem**: Functions checking file existence need paths resolved relative to `runway.json` location, not CWD.

**Solution**: Pass `projectRoot` (directory containing `runway.json`) to functions and resolve paths relative to it.

```lean
-- In Theme.lean
def detectVersoDocuments (projectRoot : System.FilePath) (config : Config) : IO ... := do
  let paperPath := projectRoot / "blueprint" / "src" / "paper_verso.html"
  if ← paperPath.pathExists then ...
```

**Filename convention**: Verso paper output is `paper_verso.html` (not `verso_paper.html`) to match sidebar link expectations.

### Dependency Graph Work

**Layout** (`Dress/Graph/Layout.lean`):
- Sugiyama: layer assignment, median crossing reduction
- Edge routing: visibility graph, Dijkstra, Bezier
- Simplified for >100 nodes

#### Graph Layout Algorithm (Sugiyama)

The layout algorithm implements Sugiyama-style layered graph drawing:

1. **`layout`**: Main entry point, orchestrates all phases
2. **`assignLayers`**: Assigns nodes to horizontal layers (topological ordering)
3. **`orderLayers`**: Reduces edge crossings via barycenter heuristic
4. **`assignXCoordinates`**: Positions nodes horizontally within layers
5. **`createLayoutEdges`**: Generates edge paths with routing
6. **Coordinate normalization**: Shifts all coordinates so bounding box starts at (0,0)

**Critical pattern**: After positioning, coordinates must be normalized to (0,0) origin:
```lean
let minX := nodes.foldl (fun acc n => min acc n.x) Float.inf
let minY := nodes.foldl (fun acc n => min acc n.y) Float.inf
let normalizedNodes := nodes.map fun n => { n with x := n.x - minX, y := n.y - minY }
```

This normalization is required for proper SVG centering because `fitToWindow()` in JavaScript calculates content bounds using `getBBox()`, which expects the viewBox origin to be (0,0).

#### Performance Thresholds (>100 nodes)

When a graph exceeds 100 nodes, these optimizations trigger:

| Optimization | Normal | >100 nodes | Rationale |
|--------------|--------|------------|-----------|
| Barycenter iterations | Unlimited | Max 2 | O(n) per iteration |
| Transpose heuristic | Yes | Skipped | O(n^2) adjacent swaps |
| Visibility graph routing | Yes | Skipped | O(n^2) graph construction |
| Transitive reduction | O(n^3) Floyd-Warshall | Skipped | Multi-hour build times |

The 100-node threshold balances layout quality against computation time. PNT (591 annotations) takes ~15 seconds with optimizations; without them it would take minutes.

#### Common Graph Issues and Fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Graph appears off-center | viewBox origin not (0,0) | Ensure coordinate normalization applied |
| Graph doesn't fit window | `fitToWindow()` miscalculating bounds | Check `getBBox()` is called on correct element |
| Edges overlap nodes | Visibility graph too coarse | Increase obstacle margin in routing |
| Layout asymmetric | Barycenter converging early | Increase iteration count (for smaller graphs) |

**Edge generation** (`Dress/Graph/Build.lean`):
- Two-pass: PASS 1 registers labels, PASS 2 adds edges
- `Node.inferUses` traces actual Lean code
- Statement uses -> dashed edges
- Proof uses -> solid edges

**SVG** (`Dress/Graph/Svg.lean`):
- Ellipse for theorems, rect for definitions
- 6-status color model

**Modals** (`Runway/DepGraph.lean`):
- `wrapInModal` creates container
- `verso-code.js` handles MathJax/Tippy init

**Pan/zoom** (`verso-code.js`):
- Uses getBBox() for content bounds
- `fitToWindow()` centers graph

### Dashboard Work

**Render.lean functions**:
- `renderDashboard`: 2x2 grid layout
- `renderProgress`: Stats with Completion/Attention columns
- `renderKeyTheorems`: Previews with status dots
- `renderMessages`: User notes
- `renderProjectNotes`: blocked/potentialIssues/technicalDebt/misc

**Data flow**:
- Stats computed in Dress (`computeStatusCounts`)
- `computeFullyProven` upgrades nodes
- Validation in Dress (`findComponents`, `detectCycles`)
- Manifest.json written by Dress
- Runway loads manifest (no recomputation)

### Rainbow Bracket Highlighting

**Implementation** (`Verso/Code/Highlighted.lean`):
- `toHtmlRainbow` wraps brackets with depth-colored spans
- Single global depth counter shared across all bracket types
- Cycles through 6 colors (`lean-bracket-1` through `lean-bracket-6`)
- Opening brackets increment depth, closing brackets decrement

**CSS** (`common.css`): light and dark mode variants

### Paper/PDF Generation

**Commands**:
```bash
lake exe runway paper runway.json  # HTML + PDF
lake exe runway pdf runway.json    # Just PDF
```

**TeX hooks**:
```latex
\paperstatement{thm:main}  % Statement with Lean link
\paperfull{thm:main}       % Full side-by-side
```

**Metadata** (`Paper.lean`): extracts `\title{}`, `\author{}`, `\begin{abstract}` from paper.tex

### Module Reference Support

`\inputleanmodule{ModuleName}` in LaTeX expands to all nodes from module:
1. `buildModuleLookup` creates module -> nodes map
2. `replaceModulePlaceholders` substitutes content
3. Module names must be fully qualified

### Validation Checks

**Connectivity** (`findComponents`): BFS detects disconnected subgraphs

**Cycles** (`detectCycles`): DFS with gray/black coloring

Results in `manifest.json` under `checkResults`.

---

## Performance Knowledge

**SubVerso optimization**: O(1) indexed lookups via InfoTable

**Build time**: SubVerso highlighting is 93-99% of build time. Cannot be deferred (info trees are ephemeral).

**Graph layout complexity**:
- Full algorithm: O(n^2) for crossing reduction, O(n^2 log n) for edge routing
- With >100 node optimizations: O(n log n) effective complexity
- Coordinate normalization: O(n) pass required for proper centering

**Large graph optimizations** (triggered at >100 nodes):
- O(n^3) transitive reduction skipped
- Max 2 barycenter iterations in `orderLayers`
- Transpose heuristic skipped
- Visibility graph routing replaced with simple beziers
- Edge deduplication

**Expected build times by scale**:
| Project | Nodes | Layout Time | Total Build |
|---------|-------|-------------|-------------|
| SBS-Test | 33 | <1s | ~2 min |
| GCR | 57 | ~2s | ~5 min |
| PNT | 591 | ~15s | ~20 min |

**String performance**: Parser.lean uses Array-based building (O(n))

---

## Status Indicator Dots

| Location | File |
|----------|------|
| Dashboard Key Declarations | `Runway/Render.lean` |
| Dashboard Project Notes | `Runway/Render.lean` |
| Blueprint Theorem Headers | `Dress/Render/SideBySide.lean` |
| Blueprint Index/TOC | `Runway/Render.lean` |
| Dependency Graph Modals | `Runway/DepGraph.lean` |
| Paper Theorem Headers | `Dress/Render/SideBySide.lean` |

**CSS classes** (`common.css`):
- `.status-dot` (8px base)
- `.header-status-dot` (10px)
- `.paper-status-dot` (10px)
- `.modal-status-dot` (12px)

---

## ID Normalization

Node IDs with colons (`thm:main`) converted to hyphens (`thm-main`) for:
- Modal element IDs
- CSS selectors
- JavaScript querySelector

---

## Configuration

### runway.json

```json
{
  "title": "Project Title",
  "projectName": "ProjectName",
  "githubUrl": "https://github.com/...",
  "baseUrl": "/",
  "blueprintTexPath": "blueprint/src/blueprint.tex",
  "assetsDir": "../dress-blueprint-action/assets",
  "paperTexPath": "blueprint/src/paper.tex",
  "docgen4Url": "docs/"
}
```

### lakefile.toml

```toml
[[require]]
name = "Dress"
git = "https://github.com/e-vergo/Dress"
rev = "main"

[[require]]
name = "mathlib"
git = "https://github.com/leanprover-community/mathlib4.git"
rev = "v4.27.0"

# Optional: for Verso documents
[[require]]
name = "verso"
git = "https://github.com/e-vergo/verso.git"
rev = "main"
```

---

## CI/CD

**Action inputs** (4):
- `project-directory`: Directory with lakefile.toml and runway.json
- `lean-version`: Override Lean version (default: auto-detect)
- `docgen4-mode`: `skip`, `docs-static`, or `generate`
- `deploy-pages`: Upload Pages artifact

**docs-static pattern**: Pre-generate docs, commit to orphan branch, CI downloads instead of regenerating.

---

## Anti-Patterns

- Don't create scratch files - work in repo files
- Don't edit downstream before upstream
- Don't guess at Verso APIs - use `lean_hover_info`
- Don't skip build_blueprint.sh steps
- Don't use colons in CSS selectors - normalize to hyphens
- Don't manually specify `\uses{}` - `Node.inferUses` traces real dependencies
- Don't use derived `ToExpr` for structures with default fields - use manual instance
- Don't configure paper metadata in runway.json - extract from paper.tex
- Don't use negative margins for full-width highlights - use `::before` pseudo-elements

---

## Backwards Compatibility

JSON parsing handles legacy status values:
- `"stated"` maps to `.notReady`
- `"inMathlib"` maps to `.mathlibReady`

---

## Standards

- No `sorry` in tooling code
- Follow Verso/SubVerso patterns
- Test via SBS-Test or GCR
- Check `lean_diagnostic_messages` after edits
- Use `sbs capture` + `sbs compare` for any visual changes
