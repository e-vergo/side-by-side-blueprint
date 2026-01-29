# Side-by-Side Blueprint Architecture

> **Prototype Status**: Alpha software with known bugs, slow workflows, and incomplete features.

## Overview

Eight repositories work together to produce formalization documentation:

| Repository | Purpose |
|------------|---------|
| **SubVerso** | Syntax highlighting extraction from Lean info trees |
| **LeanArchitect** | `@[blueprint]` attribute with 8 metadata options + 5 status flags |
| **Dress** | Artifact generation + dependency graph layout + stats computation + validation checks |
| **Runway** | Site generator with dashboard + PDF/paper generation |
| **SBS-Test** | Minimal test project for iteration (11 nodes, all features) |
| **General_Crystallographic_Restriction** | Production example with full paper generation |
| **PrimeNumberTheoremAnd** | Large-scale integration (530 annotations, 33 files) |
| **dress-blueprint-action** | GitHub Action + external CSS/JS assets + Runway CI support |

**Dependency chain**: SubVerso -> LeanArchitect -> Dress -> Runway -> Consumer projects

**Toolchain**: All repos use `leanprover/lean4:v4.27.0`

## Build Pipeline

```
@[blueprint "label"] theorem foo ...
        |
        v
DRESS (during elaboration):
  - SubVerso extracts highlighting from info trees (800-6500ms, 93-99% of time)
  - Splits code into signature + proof body
  - Renders HTML with hover data via Verso
  - Writes: decl.tex, decl.html, decl.json, decl.hovers.json
        |
        v
LAKE FACETS (after compilation):
  - :blueprint aggregates module artifacts
  - :depGraph generates dep-graph.json + dep-graph.svg
  - Computes stats (StatusCounts) and extracts project metadata
  - Uses Node.inferUses for real Lean code dependency inference
  - Validates graph: connectivity check, cycle detection
  - Writes manifest.json with precomputed stats and validation results
        |
        v
RUNWAY (post-build):
  - Parses blueprint.tex for chapter/section structure
  - Loads artifacts from .lake/build/dressed/
  - Loads manifest.json (precomputed stats, no recomputation)
  - Copies assets from assetsDir to output
  - Generates dashboard homepage + multi-page static site
  - Optionally: paper.html + paper.pdf + pdf.html (viewer)
```

### Full Build Commands

```bash
# 1. Build dependency chain (SubVerso -> LeanArchitect -> Dress -> Runway)
# 2. Run artifact generation with environment variable or .dress file
BLUEPRINT_DRESS=1 lake build
# Or: echo "1" > .lake/build/.dress && lake build

# 3. Build blueprint facet
lake build :blueprint

# 4. Extract dependency graph from environment
lake exe extract_blueprint graph

# 5. Generate static site
lake exe runway build runway.json

# 6. (Optional) Generate paper if paperTexPath configured
lake exe runway paper runway.json
```

## Output Directories

### Dress Artifacts (.lake/build/dressed/)

```
.lake/build/dressed/
├── {Module/Path}/
│   └── {sanitized-label}/
│       ├── decl.tex          # LaTeX with base64 HTML
│       ├── decl.html         # Syntax-highlighted HTML
│       ├── decl.json         # Metadata + highlighting
│       └── decl.hovers.json  # Tooltip data
├── dep-graph.json            # D3.js graph data
├── dep-graph.svg             # Static Sugiyama layout
└── manifest.json             # Stats, validation, project metadata
```

### Runway Output (.lake/build/runway/)

```
.lake/build/runway/
├── index.html                # Dashboard homepage
├── dep_graph.html            # Full dependency graph with rich modals
├── chapter{N}.html           # Per-chapter pages
├── paper.html                # Paper with MathJax + Lean links (if configured)
├── paper.pdf                 # Compiled PDF (if LaTeX compiler available)
├── pdf.html                  # Embedded PDF viewer page
├── manifest.json             # Node index
└── assets/
    ├── blueprint.css         # From assetsDir
    ├── plastex.js            # LaTeX proof toggle
    └── verso-code.js         # Hovers, bindings, pan/zoom, modal init
```

## External Assets Architecture

CSS and JavaScript are maintained as real files in `dress-blueprint-action/assets/`, not embedded strings:

| File | Size | Purpose |
|------|------|---------|
| `blueprint.css` | ~35 KB | Full stylesheet including modal and graph styles |
| `plastex.js` | ~2 KB | LaTeX proof toggle (expand/collapse) |
| `verso-code.js` | ~20 KB | Hover tooltips, token binding, pan/zoom, modal MathJax/Tippy init |

**Configuration**: `runway.json` requires `assetsDir` field pointing to assets directory. Runway copies these to `output/assets/` during build.

```json
{
  "assetsDir": "/path/to/dress-blueprint-action/assets"
}
```

## manifest.json System

**Dress** generates `manifest.json` with precomputed statistics, validation results, and project metadata (soundness: stats computed at source):

```json
{
  "stats": {
    "notReady": 1, "stated": 0, "ready": 1, "hasSorry": 2,
    "proven": 24, "fullyProven": 1, "mathlibReady": 2, "inMathlib": 1,
    "total": 32
  },
  "checkResults": {
    "connected": true,
    "componentCount": 1,
    "componentSizes": [32],
    "cycles": []
  },
  "keyTheorems": ["thm:dashboard-key", "thm:dashboard-multi"],
  "messages": [
    {"id": "thm:dashboard-message", "label": "SBSTest.Chapter4.dashboard_message_test",
     "message": "Consider alternative proof approach"}
  ],
  "projectNotes": {
    "priority": [{"id": "thm:dashboard-priority-high", "label": "SBSTest.Chapter4.dashboard_priority_high"}],
    "blocked": [{"id": "thm:dashboard-blocked", "label": "...", "reason": "Waiting for upstream mathlib PR"}],
    "potentialIssues": [{"id": "lem:dashboard-issue", "label": "...", "issue": "May not generalize"}],
    "technicalDebt": [{"id": "def:dashboard-debt", "label": "...", "debt": "Refactor to use Finset API"}],
    "misc": [{"id": "thm:dashboard-misc", "label": "...", "note": "See discussion in issue #42"}]
  },
  "nodes": {
    "thm:main-result": "#thm:main-result",
    ...
  }
}
```

Used for:
- Dashboard homepage (stats panel, key theorems, project notes)
- Validation warnings (connectivity, cycles)
- Node lookup from dependency graph modals
- Cross-page linking

## Repository Details

### LeanArchitect

Lightweight metadata store. Only depends on `batteries`.

| File | Purpose |
|------|---------|
| `Architect/Basic.lean` | `Node`, `NodePart`, `NodeStatus` structures with manual `ToExpr` instance |
| `Architect/Attribute.lean` | `@[blueprint]` attribute with all options |
| `Architect/CollectUsed.lean` | Dependency inference |

**Manual ToExpr instance**: The `Node` structure uses a manual `ToExpr` instance instead of derived one. This is required because Lean's derived `ToExpr` for structures with default field values doesn't correctly serialize all fields - causing status flags to not persist through the environment extension.

**Attribute options (8 metadata + 5 status flags)**:

| Option | Type | Purpose |
|--------|------|---------|
| `title` | String | Custom node label in dependency graph (renamed from `displayName`) |
| `keyDeclaration` | Bool | Highlight in dashboard Key Theorems section (renamed from `keyTheorem`) |
| `message` | String | User notes (appears in Messages panel) |
| `priorityItem` | Bool | Flag for Attention column in dashboard |
| `blocked` | String | Reason for blockage (Attention column) |
| `potentialIssue` | String | Known concerns (Attention column) |
| `technicalDebt` | String | Cleanup notes (Attention column) |
| `misc` | String | Catch-all notes (Attention column) |
| `notReady` | Bool | Status: not ready (red/gray) |
| `ready` | Bool | Status: ready to formalize (orange) |
| `fullyProven` | Bool | Status: fully proven with all deps (dark green) |
| `mathlibReady` | Bool | Status: ready for mathlib (purple) |
| `mathlib` | Bool | Status: already in mathlib (dark blue) |

**Example usage**:
```lean
@[blueprint (keyDeclaration := true, message := "Main result of paper")]
theorem main_theorem : ...

@[blueprint (priorityItem := true, blocked := "Waiting for upstream PR")]
lemma helper_lemma : ...

@[blueprint (title := "Square Non-negative")]
theorem square_nonneg : ...

@[blueprint (fullyProven := true)]
theorem complete_with_all_deps : ...
```

### Dress

Two-phase: per-declaration during elaboration, library-level via Lake facets.

| File | Purpose |
|------|---------|
| `Capture/ElabRules.lean` | elab_rules hooks |
| `Capture/InfoTree.lean` | SubVerso highlighting capture |
| `Generate/Declaration.lean` | Per-declaration artifact writer |
| `HtmlRender.lean` | Verso HTML rendering |
| `Graph/Types.lean` | `Node`, `Edge`, `StatusCounts`, `CheckResults` types; `transitiveReduction` with O(n^3) skip |
| `Graph/Build.lean` | Graph construction + stats + validation + `Node.inferUses` |
| `Graph/Json.lean` | Manifest serialization with stats/metadata/validation |
| `Graph/Layout.lean` | Sugiyama algorithm, visibility graph edge routing |
| `Graph/Render.lean` | SVG generation with Bezier curves |
| `Paths.lean` | Centralized path management |
| `Main.lean` | Writes manifest.json with precomputed stats |

**Dependency inference**: `Node.inferUses` traces actual Lean code dependencies by examining the expression tree, rather than using manually-specified `\uses{}` annotations. This produces edges that reflect real proof dependencies.

**Transitive reduction performance**: `Graph.transitiveReduction` in `Graph/Types.lean` uses Floyd-Warshall algorithm which is O(n^3). For large graphs like PNT (530 nodes), this would be 530^3 = 149 million iterations causing multi-hour hangs. **Fix**: Skip transitive reduction for graphs with >100 nodes. Trade-off: some redundant edges appear but layout still works.

**Validation checks** (`Graph/Build.lean`):
- `findComponents`: Detects disconnected subgraphs (warns about unreachable nodes)
- `detectCycles`: Finds circular dependencies via DFS (errors on cycles)
- Results stored in `CheckResults` and written to manifest.json

### Runway

Pure Lean site generator using Verso patterns.

| File | Purpose |
|------|---------|
| `Main.lean` | CLI entry point with `build`, `paper`, `pdf` commands; `assignPagePaths` for declaration-specific links |
| `Render.lean` | Side-by-side node rendering, dashboard, modal content |
| `Theme.lean` | Page templates, sidebar |
| `DepGraph.lean` | Dependency graph page with sidebar + modal wrappers |
| `Site.lean` | `NodeInfo` structure with `title` and `pagePath` fields; `fullUrl` helper |
| `Pdf.lean` | PDF compilation with multiple LaTeX compilers |
| `Latex/Parser.lean` | LaTeX parsing (with infinite loop fixes for large documents) |
| `Latex/ToHtml.lean` | LaTeX to HTML |
| `Config.lean` | Site config including `assetsDir`, `paperTexPath`, paper metadata |
| `Assets.lean` | Asset copying |

**Declaration-specific links**: The `pagePath` field in `NodeInfo` tracks which chapter page each node belongs to. The `assignPagePaths` function in `Main.lean` populates this during site generation. Paper links use `fullUrl` to generate correct URLs like `basic-definitions.html#thm-main` instead of just `#thm-main`.

**Dashboard rendering** (`Render.lean`):
- `renderDashboard`: Main 2x2 grid layout
- `renderProgress`: Stats panel with Completion/Attention columns
- `renderKeyTheorems`: Key theorems with side-by-side preview
- `renderMessages`: User notes section
- `renderProjectNotes`: Blocked/Issues/Debt/Misc sections

**Parser fixes**: The LaTeX parser includes `let _ <- advance` in catch-all cases in `parseBlocks`, `parseBody`, `parseSectionBody`, and `parseItems` to prevent infinite loops when parsing large documents (e.g., GCR's 3989-token blueprint.tex).

### SubVerso

Fork of leanprover/subverso with optimizations.

| File | Purpose |
|------|---------|
| `Highlighting/Highlighted.lean` | Token.Kind, Highlighted types |
| `Highlighting/Code.lean` | Main highlighting logic |

## PDF/Paper Generation Pipeline

Runway supports generating academic papers alongside blueprints:

### Commands

- `lake exe runway paper runway.json` - Generate paper.html + paper.pdf
- `lake exe runway pdf runway.json` - Generate just the PDF
- `lake exe runway build runway.json` - Generates paper if `paperTexPath` configured

### Paper TeX Format

Paper documents use custom hooks to reference Lean formalizations:

```latex
\documentclass{article}
\begin{document}

\section{Main Result}
The crystallographic restriction theorem states:
\paperstatement{thm:main}  % Inserts LaTeX statement, links to Lean

\section{Full Proof}
\paperfull{thm:main}       % Inserts full side-by-side display

\end{document}
```

### Configuration

```json
{
  "paperTexPath": "blueprint/src/paper.tex",
  "paperTitle": "The Crystallographic Restriction Theorem",
  "paperAuthors": ["J. Kuzmanovich", "A. Pavlichenkov", "E. Vergo"],
  "paperAbstract": "We present a complete formalization..."
}
```

### Supported LaTeX Compilers

`Pdf.lean` supports multiple compilers with auto-detection:

| Compiler | Priority | Notes |
|----------|----------|-------|
| `tectonic` | 1 (preferred) | Modern, self-contained, handles passes automatically |
| `pdflatex` | 2 | Most common, requires TeX distribution |
| `xelatex` | 3 | Better Unicode support |
| `lualatex` | 4 | Lua scripting support |

### Output Files

| File | Purpose |
|------|---------|
| `paper.html` | MathJax-rendered paper with links to Lean code |
| `paper.pdf` | Compiled PDF (requires LaTeX compiler) |
| `pdf.html` | Embedded PDF viewer page |

## Dependency Graph Architecture

### Layout Algorithm (Dress/Graph/Layout.lean)

Sugiyama-style hierarchical layout:
1. **Layer assignment**: Top-to-bottom, respecting edge directions
2. **Crossing reduction**: Median heuristic for node ordering within layers
3. **Position refinement**: Iterative adjustment for better spacing
4. **Edge routing**: Visibility graph + Dijkstra shortest path + Bezier fitting

### Node Rendering

| Shape | Used For |
|-------|----------|
| Ellipse | Theorems, lemmas, propositions |
| Box (rect) | Definitions |

**8-status color model**:

| Status | Color | Source |
|--------|-------|--------|
| notReady | Red/Gray | Manual: `(notReady := true)` |
| stated | Light Blue | Default (LaTeX statement exists, no Lean code) |
| ready | Orange | Manual: `(ready := true)` |
| sorry | Yellow | Derived: proof contains sorry |
| proven | Light Green | Derived: complete proof exists |
| fullyProven | Dark Green | Manual: `(fullyProven := true)` |
| mathlibReady | Purple | Manual: `(mathlibReady := true)` |
| inMathlib | Dark Blue | Manual: `(mathlib := true)` |

Dark backgrounds use white text.

### Edge Rendering

- **Solid lines**: Proof dependencies (from `Node.inferUses` proofUses)
- **Dashed lines**: Statement dependencies (from `Node.inferUses` statementUses)
- **Bezier curves**: Control points calculated via visibility graph to route around nodes
- **Arrow heads**: Point at target node boundary (clipped to shape)

### Modal System

Modals display rich side-by-side content when nodes are clicked:

**Generation flow**:
1. `Runway/Render.lean`: `renderNodeModal` wraps existing `renderNode` output in modal structure
2. `Runway/DepGraph.lean`: `wrapInModal` creates modal container with close button
3. `verso-code.js`: `onModalOpen()` initializes MathJax and Tippy.js on modal content

**ID normalization**: Node IDs containing colons (e.g., `thm:main`) must be converted to hyphens (`thm-main`) in modal element IDs because CSS selectors don't handle colons well.

**Proof toggles**:
- LaTeX proofs: `plastex.js` handles expand/collapse
- Lean proofs: CSS checkbox pattern (pure CSS, no JS)

### Pan/Zoom (verso-code.js)

D3-style behavior implemented manually (no D3 dependency):
- **Wheel**: Zoom centered on cursor position
- **Drag**: Pan with pointer capture
- **Fit button**: Scales and centers graph using content bounds (getBBox) for proper X/Y centering

**Fit algorithm fix**: Uses `getBBox()` to get actual content bounds, then centers on `contentCenterX/Y` rather than SVG declared dimensions. This fixes X-axis bias when SVG has asymmetric padding.

## Validation Checks

Graph integrity validation is implemented in `Dress/Graph/Build.lean`:

### Connectivity Check

`findComponents` uses BFS to detect disconnected subgraphs. Reports:
- `connected`: Boolean (true if single component)
- `componentCount`: Number of disconnected components
- `componentSizes`: Array of component sizes

**Purpose**: Catch "Tao-style" errors where final theorems are disconnected from their lemmas.

### Cycle Detection

`detectCycles` uses DFS with gray/black node coloring to find back-edges. Returns array of cycles.

**Purpose**: Prevent circular dependencies that indicate logical errors.

### Integration

Results are stored in `CheckResults` structure and serialized to `manifest.json`. CI workflows can check these values and fail on validation errors.

## CI/CD Architecture

### Workflow Structure (~340 lines for full workflow)

GCR and PNT use similar `full-build-deploy.yml` workflows:

```yaml
jobs:
  build:
    steps:
      # SETUP: Free disk space, checkout 6 repos
      - Checkout project, SubVerso, LeanArchitect, Dress, Runway, dress-blueprint-action

      # TOOLCHAIN: Direct elan installation (not lean-action)
      - Install elan, Lean toolchain, LaTeX

      # CACHE: Restore/save toolchain and mathlib caches
      - Toolchain cache (subverso, LeanArchitect, Dress, Runway .lake dirs)
      - Mathlib cache (from server or GitHub Actions cache)

      # BUILD: Toolchain in dependency order
      - Build SubVerso -> LeanArchitect -> Dress -> Runway

      # BUILD: Project with dressed artifacts
      - Create .dress file, lake build, lake build :blueprint
      - Generate dependency graph with extract_blueprint

      # DOCGEN4: Download pre-built docs (docs-static branch pattern)
      - git fetch docs-static branch (~4,700 files in seconds vs ~1 hour)

      # SITE: Generate with Runway
      - Create runway-ci.json with absolute paths
      - lake exe runway build + paper (if configured)

      # VERIFY: Check key files exist
      - index.html, dep_graph.html, paper.html, paper.pdf, pdf.html

      # CACHE: Save for future builds
      # UPLOAD: Pages artifact

  deploy:
    - Deploy to GitHub Pages
```

### Key Patterns

**Direct elan installation**: lean-action failed in CI; direct elan-init.sh works reliably.

**Toolchain cache disabled**: CI workflows in PNT, SBS-Test, and GCR have toolchain caching disabled. The cache was restoring old compiled binaries and ignoring code fixes, causing CI to use stale code. Mathlib cache is still enabled (separate concern).

**runway-ci.json**: CI-specific config with `$WORKSPACE` placeholder replaced by `${{ github.workspace }}`:

```json
{
  "blueprintTexPath": "$WORKSPACE/GCR/blueprint/src/blueprint.tex",
  "assetsDir": "$WORKSPACE/dress-blueprint-action/assets",
  "paperTexPath": "$WORKSPACE/GCR/blueprint/src/paper.tex"
}
```

**docs-static branch pattern**: Pre-generated DocGen4 documentation stored in orphan branch, downloaded in CI instead of regenerating.

**Verification step**: Checks for expected output files before deployment.

### CI Differences by Project

| Feature | GCR | PNT | SBS-Test |
|---------|-----|-----|----------|
| DocGen4 | Yes (docs-static) | No | No |
| Paper generation | Yes | No | Optional |
| PDF output | Yes | No | Optional |
| Mathlib | Yes | Yes | Minimal |
| Toolchain | v4.27.0 | v4.27.0 | v4.27.0 |

## PrimeNumberTheoremAnd Integration

Successfully integrated the PNT project as a large-scale test case:

### Integration Details

- **530 `@[blueprint]` annotations** across 33 files
- **Zero changes to Lean proof code** - annotations added non-invasively
- **Toolchain downgrade**: v4.28.0-rc1 -> v4.27.0 (to match toolchain)
- **Mathlib pinned**: to v4.27.0

### Key Theorems Tagged

```lean
@[blueprint (keyTheorem := true)]
theorem WeakPNT : ...

@[blueprint (keyTheorem := true)]
theorem MediumPNT : ...

@[blueprint (keyTheorem := true)]
theorem WeakPNT_AP : ...
```

### lakefile.toml

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

## CSS Layout

**Content layout**: Non-declaration content (paragraphs, prose) should stay in the left column matching LaTeX width. The selectors `.chapter-page > p` and `section.section > p` target these elements.

**Side-by-side container**: Uses flexbox with two 100ch columns plus gap.

**Dashboard grid**: 2x2 layout with Stats, Key Theorems, Messages, Project Notes panels.

## Performance Analysis

**SubVerso optimization completed** (Phase 1): Indexing, caching, and containment query optimizations implemented.

**Measured performance breakdown**:

| Operation | Time | Percentage |
|-----------|------|------------|
| SubVerso highlighting | 800-6500ms | 93-99% |
| TeX/HTML generation | <30ms | <1% |

**Key finding**: SubVerso highlighting dominates build time due to goal pretty-printing in info trees. This cannot be deferred because info trees are ephemeral (only exist during elaboration).

**Deferred generation (Phase 2) skipped**: Analysis showed no benefit since the bottleneck (SubVerso) must run during elaboration anyway.

## Configuration

### runway.json

```json
{
  "title": "Project Title",
  "projectName": "ProjectName",
  "githubUrl": "https://github.com/...",
  "baseUrl": "/",
  "docgen4Url": null,
  "blueprintTexPath": "blueprint/src/blueprint.tex",
  "paperTexPath": "paper/paper.tex",
  "paperTitle": "Paper Title",
  "paperAuthors": ["Author One", "Author Two"],
  "paperAbstract": "Abstract text...",
  "assetsDir": "/path/to/dress-blueprint-action/assets"
}
```

| Field | Required | Purpose |
|-------|----------|---------|
| `blueprintTexPath` | Yes | LaTeX source defining structure |
| `paperTexPath` | No | Paper TeX for paper generation |
| `paperTitle` | No | Title for paper.html |
| `paperAuthors` | No | Author list for paper.html |
| `paperAbstract` | No | Abstract for paper.html |
| `assetsDir` | Yes | Directory with CSS/JS assets |
| `docgen4Url` | No | Relative path to docgen4 docs (e.g., "docs/") |

### lakefile.toml

```toml
[[require]]
name = "Dress"
git = "https://github.com/e-vergo/Dress"
rev = "main"

# Optional: doc-gen4 as dev dependency
[[require]]
scope = "dev"
name = "doc-gen4"
git = "https://github.com/leanprover/doc-gen4.git"
rev = "01e1433"  # v4.27.0 compatible
```

## Build Scripts

### build_blueprint.sh Pattern

Local development scripts in `scripts/build_blueprint.sh`:

```
Step 0:  Sync repos to GitHub (auto-commit/push changes)
Step 0b: Update lake manifests in dependency order
Step 1:  Build local forks (SubVerso -> LeanArchitect -> Dress -> Runway)
Step 2:  Fetch mathlib cache
Step 3:  Build with BLUEPRINT_DRESS=1
Step 4:  Build :blueprint facet
Step 5:  Generate dependency graph
Step 6:  Generate site with Runway
Step 7:  Generate paper (if paperTexPath configured)
Step 8:  Serve at localhost:8000
```

### SBS-Test (development)

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test
./scripts/build_blueprint.sh
```

### GCR (production example)

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/General_Crystallographic_Restriction
./scripts/build_blueprint.sh
```

### Manual steps

```bash
rm -rf .lake/build/dressed .lake/build/lib/YourProject
BLUEPRINT_DRESS=1 lake build
lake build :blueprint
lake exe extract_blueprint graph
lake exe runway build runway.json
lake exe runway paper runway.json  # if paperTexPath configured
python3 -m http.server -d .lake/build/runway 8000
```

## docs-static Branch Pattern

For projects with pre-generated documentation (like docgen4 output that takes ~1 hour to generate):

1. Generate docs locally: `lake -R -Kenv=dev build Module:docs`
2. Create orphan branch: `git checkout --orphan docs-static`
3. Add and commit docs to branch root
4. Push: `git push origin docs-static`
5. CI downloads from branch instead of regenerating (~4,700 HTML files in seconds vs. ~1 hour)

**CI usage** (GCR workflow):
```yaml
- name: Download pre-generated DocGen4 documentation
  run: |
    mkdir -p GCR/.lake/build/doc
    cd GCR/.lake/build/doc
    git init
    git remote add origin https://github.com/e-vergo/General_Crystallographic_Restriction.git
    git fetch origin docs-static --depth=1
    git checkout FETCH_HEAD
    rm -rf .git
```

## Feature Status

### Complete (through Phase 7 + Dashboard + Paper Phases)

**Blueprint Core**:
- Side-by-side display with proof toggle sync
- Hierarchical sidebar navigation
- Numbered theorems (4.1.1 format)
- Multi-page chapter generation
- Hover tooltips with type signatures
- Token binding highlights
- External CSS/JS assets
- Parser fixes for large documents (3989+ tokens)
- Declaration-specific links (paper links navigate to correct chapter pages)

**Dashboard Homepage**:
- 2x2 grid layout: Stats / Key Theorems / Messages / Project Notes
- Stats panel with Completion column (proven, fullyProven, mathlibReady, inMathlib)
- Stats panel with Attention column (notReady, stated, ready, hasSorry)
- Key Theorems section with side-by-side preview and status dots
- Messages panel showing user notes from `message` attribute
- Project Notes: blocked/potentialIssues/technicalDebt/misc sections
- All stats computed upstream in Dress (soundness guarantee)
- `title` propagation for cleaner labels (renamed from `displayName`)

**Dependency Graph**:
- Sugiyama layout algorithm (top-to-bottom, median heuristic)
- Node shapes: Ellipse (theorems) / Box (definitions)
- Edge styles: Solid (proof deps) / Dashed (statement deps) with Bezier curves
- 8-status color model with appropriate text contrast (see Node Status Types)
- Static legend embedded in SVG
- D3-style pan/zoom (cursor-centered, no D3 dependency)
- Edge routing: Visibility graph + Dijkstra + Bezier fitting
- Node hover border thickening
- Combined Fit button with corrected X-axis centering
- **Sidebar navigation** (chapters, Blueprint Home, Dependency Graph, Paper, GitHub links)
- **Real dependency inference** via `Node.inferUses` (traces actual Lean code)
- **O(n^3) transitive reduction skip** for graphs >100 nodes (PNT fix)

**Rich Modals (Verso Integration)**:
- Click node to open modal with full side-by-side content
- Reuses `renderNode` for consistent display
- MathJax rendering in modal content
- Tippy.js hover tooltips in modals
- LaTeX proof toggle (plastex.js)
- Lean proof toggle (CSS checkbox pattern)
- "View in Blueprint" link

**`@[blueprint]` Attribute Options** (8 metadata + 5 status flags):
- `title`: Custom graph labels (renamed from `displayName`)
- `keyDeclaration`: Dashboard highlighting (renamed from `keyTheorem`)
- `message`: User notes
- `priorityItem`: Attention flagging
- `blocked`, `potentialIssue`, `technicalDebt`, `misc`: Project notes
- `notReady`, `ready`, `fullyProven`, `mathlibReady`, `mathlib`: Manual status overrides

**Node Status Types (8 total)**:
| Status | Color | Source |
|--------|-------|--------|
| notReady | Red/Gray | Manual: `(notReady := true)` |
| stated | Light Blue | Default (no Lean code) |
| ready | Orange | Manual: `(ready := true)` |
| sorry | Yellow | Derived: proof contains sorry |
| proven | Light Green | Derived: complete proof |
| fullyProven | Dark Green | Manual: `(fullyProven := true)` |
| mathlibReady | Purple | Manual: `(mathlibReady := true)` |
| inMathlib | Dark Blue | Manual: `(mathlib := true)` |

**Validation Checks**:
- Connectivity check: warns about disconnected components
- Cycle detection: finds circular dependencies
- Results in manifest.json for CI integration
- SBS-Test includes disconnected cycle (cycleA <-> cycleB) for testing

**PDF/Paper Generation**:
- `\paperstatement{label}` and `\paperfull{label}` hooks
- MathJax-rendered paper.html with links to Lean code
- Declaration-specific links navigate to correct chapter pages (e.g., `basic-definitions.html#thm-main`)
- Multiple LaTeX compilers: tectonic, pdflatex, xelatex, lualatex
- Embedded PDF viewer (pdf.html)
- Auto-detection of available compiler

**CI/CD**:
- `dress-blueprint-action` supports Runway via `use-runway` input
- Multi-repo CI workflow (checks out 6 repos)
- Direct elan installation (lean-action unreliable)
- Toolchain cache disabled (was causing stale code issues)
- Mathlib cache enabled separately
- GitHub Pages deployment
- Build script auto-exits after 5 minutes (SBS-Test) or runs indefinitely (GCR)
- docs-static branch pattern for pre-generated documentation
- Consolidated workflow: `full-build-deploy.yml`

**Large-Scale Integration**:
- PrimeNumberTheoremAnd: 530 annotations, 33 files, zero proof code changes
- GCR: Full production example with paper generation

**Bug Fixes (This Session)**:
- `displayName` -> `title` migration (aligned with PNT's hanwenzhu/LeanArchitect usage)
- Manual `ToExpr` instance for `Node` (status persistence through environment extension)
- O(n^3) transitive reduction skip for graphs >100 nodes (PNT 3+ hour hang fix)
- Paper links 404 fix (files at root level, not `chapters/` subdirectory)
- CI toolchain cache disabled (was ignoring code fixes)

### Future

- Tactic state expansion
- doc-gen4 cross-linking improvements
- Additional soundness checks (no sorry enforcement in CI)
