# Side-by-Side Blueprint Architecture

> **Prototype Status**: Alpha software with known bugs, slow workflows, and incomplete features.

## Overview

Eight repositories work together to produce formalization documentation:

| Repository | Purpose |
|------------|---------|
| **SubVerso** | Syntax highlighting extraction from Lean info trees |
| **LeanArchitect** | `@[blueprint]` attribute with 8 metadata options + 3 manual status flags |
| **Dress** | Artifact generation + dependency graph layout + stats computation + validation checks |
| **Runway** | Site generator with dashboard + PDF/paper generation + module reference support |
| **SBS-Test** | Minimal test project for iteration (16 nodes, all 6 status colors) |
| **General_Crystallographic_Restriction** | Production example with full paper generation |
| **PrimeNumberTheoremAnd** | Large-scale integration (530 annotations, 33 files) |
| **dress-blueprint-action** | Complete CI solution (~465 lines) + external CSS/JS assets |

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
  - Two-pass edge processing for proper back-edge handling
  - Writes manifest.json with precomputed stats and validation results
        |
        v
RUNWAY (post-build):
  - Parses blueprint.tex for chapter/section structure
  - Loads artifacts from .lake/build/dressed/
  - Loads manifest.json (precomputed stats, no recomputation)
  - Expands `\inputleanmodule{ModuleName}` placeholders
  - Copies assets from assetsDir to output
  - Generates dashboard homepage + multi-page static site
  - Optionally: paper.html + paper.pdf + pdf.html (viewer)
    - Paper metadata (title, authors, abstract) extracted from paper.tex
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
├── paper.pdf                 # Compiled PDF (requires LaTeX compiler)
├── pdf.html                  # Embedded PDF viewer page
├── manifest.json             # Node index
└── assets/
    ├── common.css            # Theme toggle, base styles
    ├── blueprint.css         # Full stylesheet including modal and graph styles
    ├── plastex.js            # LaTeX proof toggle
    └── verso-code.js         # Hovers, bindings, pan/zoom, modal init
```

## External Assets Architecture

CSS and JavaScript are maintained as real files in `dress-blueprint-action/assets/`, not embedded strings:

| File | Size | Purpose |
|------|------|---------|
| `common.css` | ~3 KB | Theme toggle (dark/light mode), base styles |
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
    "notReady": 1, "ready": 1, "hasSorry": 2,
    "proven": 24, "fullyProven": 1, "mathlibReady": 2,
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

**Attribute options (8 metadata + 3 manual status flags)**:

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
| `notReady` | Bool | Status: not ready (sandy brown) |
| `ready` | Bool | Status: ready to formalize (light sea green) |
| `mathlibReady` | Bool | Status: ready for mathlib (light blue) |

**Removed flags** (previously 5, now 3):
- `fullyProven` - now auto-computed via graph traversal
- `mathlib` - redundant with `mathlibReady`

**Example usage**:
```lean
@[blueprint (keyDeclaration := true, message := "Main result of paper")]
theorem main_theorem : ...

@[blueprint (priorityItem := true, blocked := "Waiting for upstream PR")]
lemma helper_lemma : ...

@[blueprint (title := "Square Non-negative")]
theorem square_nonneg : ...

@[blueprint (mathlibReady := true)]
theorem ready_for_mathlib : ...
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
| `Graph/Build.lean` | Graph construction + stats + validation + `Node.inferUses` + two-pass edge processing |
| `Graph/Json.lean` | Manifest serialization with stats/metadata/validation |
| `Graph/Layout.lean` | Sugiyama algorithm, visibility graph edge routing (simplified for >100 nodes) |
| `Graph/Render.lean` | SVG generation with Bezier curves |
| `Paths.lean` | Centralized path management |
| `Main.lean` | Writes manifest.json with precomputed stats |

**Dependency inference**: `Node.inferUses` traces actual Lean code dependencies by examining the expression tree, rather than using manually-specified `\uses{}` annotations. This produces edges that reflect real proof dependencies.

**Two-pass edge processing** (`Graph/Build.lean`):
- PASS 1: Register all labels and create nodes (so all labels exist in the builder state)
- PASS 2: Add all edges (now back-edges work because targets are registered)
- Edge deduplication: keeps first occurrence of each from/to pair

**Transitive reduction performance**: `Graph.transitiveReduction` in `Graph/Types.lean` uses Floyd-Warshall algorithm which is O(n^3). For large graphs like PNT (530 nodes), this would be 530^3 = 149 million iterations causing multi-hour hangs. **Fix**: Skip transitive reduction for graphs with >100 nodes. Trade-off: some redundant edges appear but layout still works.

**Layout performance** (`Graph/Layout.lean`):
- Simplified edge routing for large graphs (>100 nodes)
- Visibility graph computation optimized
- Bezier curve fitting uses direct paths when routing fails

**Validation checks** (`Graph/Build.lean`):
- `findComponents`: Detects disconnected subgraphs (warns about unreachable nodes)
- `detectCycles`: Finds circular dependencies via DFS (errors on cycles)
- Results stored in `CheckResults` and written to manifest.json

**`computeFullyProven` algorithm** (`Graph/Build.lean`):
- O(V+E) complexity with memoization
- A node is `fullyProven` if: it is `proven` AND all ancestors are `proven` or `fullyProven`
- Automatically upgrades `proven` nodes whose entire dependency chain is complete
- Runs as post-processing step in `buildGraph` after initial status assignment

### Runway

Pure Lean site generator using Verso patterns.

| File | Purpose |
|------|---------|
| `Main.lean` | CLI entry point with `build`, `paper`, `pdf` commands; `assignPagePaths` for declaration-specific links |
| `Render.lean` | Side-by-side node rendering, dashboard, modal content |
| `Theme.lean` | Page templates, sidebar, `buildModuleLookup`, `replaceModulePlaceholders` |
| `DepGraph.lean` | Dependency graph page with sidebar + modal wrappers |
| `Site.lean` | `NodeInfo` structure with `title`, `pagePath`, `moduleName` fields; `fullUrl` helper |
| `Pdf.lean` | PDF compilation with multiple LaTeX compilers |
| `Paper.lean` | Paper rendering + `PaperMetadata` extraction from paper.tex |
| `Latex/Parser.lean` | LaTeX parsing (with infinite loop fixes for large documents) |
| `Latex/Ast.lean` | AST types including `Preamble` with `abstract` field |
| `Latex/ToHtml.lean` | LaTeX to HTML |
| `Config.lean` | Site config including `assetsDir`, `paperTexPath` |
| `Assets.lean` | Asset copying |

**Module reference support** (`Theme.lean`):
- `buildModuleLookup`: Creates map from module name to nodes in that module
- `replaceModulePlaceholders`: Finds `<div class="lean-module-placeholder" data-module="X">` and replaces with rendered nodes from module X
- Registers nodes under full module name (e.g., `PrimeNumberTheoremAnd.Wiener`)
- Allows `\inputleanmodule{ModuleName}` in LaTeX to expand to all nodes from that module

**Declaration-specific links**: The `pagePath` field in `NodeInfo` tracks which chapter page each node belongs to. The `assignPagePaths` function in `Main.lean` populates this during site generation. Paper links use `fullUrl` to generate correct URLs like `basic-definitions.html#thm-main` instead of just `#thm-main`.

**Dashboard rendering** (`Render.lean`):
- `renderDashboard`: Main 2x2 grid layout
- `renderProgress`: Stats panel with Completion/Attention columns
- `renderKeyTheorems`: Key theorems with side-by-side preview and status dots
- `renderMessages`: User notes section
- `renderProjectNotes`: Blocked/Issues/Debt/Misc sections
- Static tile heights (320px for stats and checks boxes)
- Project Notes aligned with Key Declarations column

**Status indicator dots** appear throughout the UI:
| Location | File | Description |
|----------|------|-------------|
| Dashboard Key Declarations | `Render.lean` | Dots next to each key declaration |
| Dashboard Project Notes | `Render.lean` | Dots in all note sections |
| Blueprint Theorem Headers | `Dress/Render/SideBySide.lean` | Dot in thm_header_extras |
| Blueprint Index/TOC | `Render.lean` | Dots in sidebar node list |
| Dependency Graph Modals | `DepGraph.lean` | Dot in modal header bar |
| Paper Theorem Headers | `Dress/Render/SideBySide.lean` | Dot + status text in verification badge |

**CSS consolidation** - Status dot styles are in `common.css` (not scattered):
- Base `.status-dot` (8px)
- `.header-status-dot` (10px for blueprint headers)
- `.paper-status-dot` (10px for paper headers)
- `.modal-status-dot` (12px for dependency graph modals)
- `.node-list-item` (sidebar/TOC)
- `.note-item-with-dot` (dashboard notes)
- `.dep-modal-header-bar` (modal layout)

**Parser fixes**: The LaTeX parser includes `let _ <- advance` in catch-all cases in `parseBlocks`, `parseBody`, `parseSectionBody`, and `parseItems` to prevent infinite loops when parsing large documents (e.g., GCR's 3989-token blueprint.tex).

**Paper metadata extraction** (`Paper.lean`):
- `PaperMetadata` struct holds title, authors array, and optional abstract
- `extractMetadata` function pulls data from parsed document's `Preamble`
- `\title{...}` → paper title (fallback to config.title)
- `\author{...}` → split on `\and` to get authors array (`Preamble.authors`)
- `\begin{abstract}...\end{abstract}` → abstract text
- No need for `paperTitle`, `paperAuthors`, `paperAbstract` in runway.json

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
\title{The Crystallographic Restriction Theorem}
\author{J. Kuzmanovich \and A. Pavlichenkov \and E. Vergo}
\begin{document}

\begin{abstract}
We present a complete formalization of the crystallographic restriction theorem...
\end{abstract}

\section{Main Result}
The crystallographic restriction theorem states:
\paperstatement{thm:main}  % Inserts LaTeX statement, links to Lean

\section{Full Proof}
\paperfull{thm:main}       % Inserts full side-by-side display

\end{document}
```

### Configuration

Paper metadata is extracted automatically from `paper.tex`:

```json
{
  "paperTexPath": "blueprint/src/paper.tex"
}
```

The following are extracted from `paper.tex` (no longer in runway.json):
- `\title{...}` → paper title
- `\author{...}` split on `\and` → authors array
- `\begin{abstract}...\end{abstract}` → abstract

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
4. **Edge routing**: Visibility graph + Dijkstra shortest path + Bezier fitting (simplified for large graphs)

### Node Rendering

| Shape | Used For |
|-------|----------|
| Ellipse | Theorems, lemmas, propositions |
| Box (rect) | Definitions |

**6-status color model** (reduced from 8):

| Status | Color | Hex | Source |
|--------|-------|-----|--------|
| notReady | Sandy Brown | #F4A460 | Default + Manual: `(notReady := true)` |
| ready | Light Sea Green | #20B2AA | Manual: `(ready := true)` |
| sorry | Dark Red | #8B0000 | Auto: proof contains sorryAx |
| proven | Light Green | #90EE90 | Auto: complete proof |
| fullyProven | Forest Green | #228B22 | Auto-computed: proven + all ancestors proven/fullyProven |
| mathlibReady | Light Blue | #87CEEB | Manual: `(mathlibReady := true)` |

**Removed statuses**:
- `stated` (Gold #FFD700) - consolidated into `notReady`
- `inMathlib` (Midnight Blue #191970) - redundant with `mathlibReady`

**Priority order** (manual always wins):
1. `mathlibReady` (manual) - highest
2. `ready` (manual)
3. `notReady` (manual, if explicitly set)
4. `fullyProven` (auto-computed from graph)
5. `sorry` (auto-detected via sorryAx)
6. `proven` (auto-detected, has Lean without sorry)
7. `notReady` (default, no Lean code)

Dark backgrounds use white text.

### Edge Rendering

- **Solid lines**: Proof dependencies (from `Node.inferUses` proofUses)
- **Dashed lines**: Statement dependencies (from `Node.inferUses` statementUses)
- **Bezier curves**: Control points calculated via visibility graph to route around nodes
- **Arrow heads**: Point at target node boundary (clipped to shape)
- **Deduplication**: First occurrence of each from/to pair kept; duplicates removed

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
- **Wheel**: Zoom centered on cursor position (4x reduced sensitivity)
- **Drag**: Pan with pointer capture
- **Fit button**: Scales and centers graph using content bounds (getBBox) for proper X/Y centering

**Fit algorithm**: Uses `getBBox()` to get actual SVG content bounds, calculates `contentCenterX/Y` from bbox, then translates to center content in viewport. This fixes X-axis bias when SVG has asymmetric padding.

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

### Dashboard Display

Checks panel on dashboard shows:
- Connectivity status with component count
- Cycle warnings if any detected
- Placeholder checks: Kernel Verification, Soundness Checks (future features)
- Static tile height (320px) for consistent layout

### Integration

Results are stored in `CheckResults` structure and serialized to `manifest.json`. CI workflows can check these values and fail on validation errors.

## CI/CD Architecture

### Design Philosophy

The CI system is designed for **user control**:
- Workflows only trigger on `workflow_dispatch` (manual) - no automatic deploys
- Users decide when to deploy
- Simplified per-project workflows (~30 lines) that call the reusable action
- All complexity centralized in `dress-blueprint-action` (~465 lines, 14 steps)

### Per-Project Workflow (~30 lines)

SBS-Test, GCR, and PNT all use minimal workflows:

```yaml
name: Full Blueprint Build and Deploy

on:
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: e-vergo/dress-blueprint-action@main

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/deploy-pages@v4
        id: deployment
```

### dress-blueprint-action (~465 lines, 14 steps)

Complete CI solution that handles everything:

```
Step 1:  Free disk space
Step 2:  Checkout toolchain repos to _sbs_toolchain/
Step 3:  Install elan
Step 4:  Install Lean toolchain (from lean-toolchain or override)
Step 5:  Install LaTeX
Step 6:  Fetch mathlib cache from server (lake exe cache get)
Step 7:  Build SubVerso
Step 8:  Build LeanArchitect
Step 9:  Build Dress
Step 10: Build Runway
Step 11: Build project with Dress artifacts (.dress file)
Step 12: Build :blueprint facet
Step 13: Generate dependency graph (extract_blueprint graph)
Step 14: Generate site with Runway
Step 15: Generate paper (if paperTexPath configured)
Step 16: Handle DocGen4 (based on mode: skip, docs-static, generate)
Step 17: Verify site structure
Step 18: Upload Pages artifact
```

### Action Inputs (4)

| Input | Default | Purpose |
|-------|---------|---------|
| `project-directory` | `.` | Directory containing lakefile.toml and runway.json |
| `lean-version` | (auto) | Override Lean version (auto-detected from lean-toolchain) |
| `docgen4-mode` | `skip` | DocGen4 mode: `skip`, `docs-static`, or `generate` |
| `deploy-pages` | `true` | Upload artifact for GitHub Pages deployment |

### Mathlib Cache Strategy

**No GitHub Actions cache layer** - relies solely on mathlib server:
- `lake exe cache get` fetches pre-compiled oleans from mathlib's servers
- This is faster and more reliable than GitHub Actions cache for mathlib
- Oleans are already highly compressed and served efficiently

### DocGen4 Modes

| Mode | Behavior |
|------|----------|
| `skip` | No DocGen4 (fastest, default) |
| `docs-static` | Download from `docs-static` branch (~4,700 files in seconds) |
| `generate` | Run `lake -R -Kenv=dev build +:docs` (slow, ~1 hour) |

### Paper Generation

Auto-detected from `runway.json`:
- If `paperTexPath` field exists (and is not null), paper generation runs
- Paper metadata (title, authors, abstract) extracted from paper.tex
- Produces `paper.html`, `paper.pdf`, `pdf.html`

### Key Patterns

**Direct elan installation**: lean-action failed in CI; direct elan-init.sh works reliably.

**runway-ci.json**: CI creates a modified config with absolute paths:
- Replaces relative `assetsDir` with absolute `$WORKSPACE/_sbs_toolchain/dress-blueprint-action/assets`
- Converts relative TeX paths to absolute

**docs-static branch pattern**: Pre-generated DocGen4 documentation stored in orphan branch, downloaded in CI instead of regenerating.

**Verification step**: Checks for expected output files (index.html, dep_graph.html) before deployment.

## Local Build Scripts

### Shared Script Architecture

A single shared script at `/Users/eric/GitHub/Side-By-Side-Blueprint/scripts/build_blueprint.sh` (~245 lines) handles all local builds:

**Each project has a 3-line wrapper**:
```bash
#!/bin/bash
# Wrapper for shared build_blueprint.sh
exec /Users/eric/GitHub/Side-By-Side-Blueprint/scripts/build_blueprint.sh "$(dirname "$0")/.."
```

### Build Script Steps

```
Step 0:  Validate project (check runway.json exists)
         Auto-detect projectName from runway.json
Step 0a: Kill existing servers on port 8000
Step 0b: Sync all repos to GitHub (auto-commit/push with Claude co-author)
Step 0c: Update lake manifests in dependency order
Step 1:  Clean all build artifacts (toolchain + project)
Step 2:  Build toolchain (SubVerso -> LeanArchitect -> Dress -> Runway)
Step 3:  Fetch mathlib cache (lake exe cache get)
Step 4:  Build project with BLUEPRINT_DRESS=1
Step 5:  Build :blueprint facet
Step 6:  Generate dependency graph (extract_blueprint graph)
Step 7:  Generate site with Runway
Step 8:  Generate paper (if paperTexPath configured)
Step 9:  Start server and open browser (localhost:8000)
```

### Clean Build Strategy

**Always cleans** all toolchain and project build artifacts to eliminate stale caches:

```bash
# Toolchain repos (all build artifacts)
rm -rf "$SUBVERSO_PATH/.lake/build"
rm -rf "$LEAN_ARCHITECT_PATH/.lake/build"
rm -rf "$DRESS_PATH/.lake/build"
rm -rf "$RUNWAY_PATH/.lake/build"

# Project (module-specific + dressed artifacts)
rm -rf "$PROJECT_ROOT/.lake/build/lib/$MODULE_NAME"
rm -rf "$PROJECT_ROOT/.lake/build/ir/$MODULE_NAME"
rm -rf "$PROJECT_ROOT/.lake/build/dressed"
rm -rf "$PROJECT_ROOT/.lake/build/runway"
```

This eliminates the common issue of stale compiled binaries ignoring code fixes.

### Usage Examples

```bash
# Fast iteration with test project
cd /Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test
./scripts/build_blueprint.sh

# Production example with paper
cd /Users/eric/GitHub/Side-By-Side-Blueprint/General_Crystallographic_Restriction
./scripts/build_blueprint.sh

# Large-scale integration
cd /Users/eric/GitHub/Side-By-Side-Blueprint/PrimeNumberTheoremAnd
./scripts/build_blueprint.sh
```

### Warm Cache Script

Pre-fetch mathlib cache for all projects:

```bash
./scripts/warm_cache.sh
```

This fetches pre-compiled mathlib oleans (v4.27.0) for SBS-Test, GCR, and PNT, avoiding long compile times on first build.

## Mathlib Version Pinning

**All repos pinned to v4.27.0** for consistency:

| Repo | Has mathlib? | Version |
|------|--------------|---------|
| SubVerso | No | N/A |
| LeanArchitect | No | N/A |
| Dress | Yes | v4.27.0 |
| Runway | No | N/A |
| SBS-Test | Yes | v4.27.0 |
| GCR | Yes | v4.27.0 |
| PNT | Yes | v4.27.0 |

## PrimeNumberTheoremAnd Integration

Successfully integrated the PNT project as a large-scale test case:

### Integration Details

- **530 `@[blueprint]` annotations** across 33 files
- **Zero changes to Lean proof code** - annotations added non-invasively
- **Toolchain downgrade**: v4.28.0-rc1 -> v4.27.0 (to match toolchain)
- **Mathlib pinned**: to v4.27.0
- **Module reference support**: `\inputleanmodule{PrimeNumberTheoremAnd.Wiener}` expands to all nodes from that module

### Key Theorems Tagged

```lean
@[blueprint (keyDeclaration := true)]
theorem WeakPNT : ...

@[blueprint (keyDeclaration := true)]
theorem MediumPNT : ...

@[blueprint (keyDeclaration := true)]
theorem WeakPNT_AP : ...
```

## CSS Layout

**Content layout**: Non-declaration content (paragraphs, prose) should stay in the left column matching LaTeX width. The selectors `.chapter-page > p` and `section.section > p` target these elements.

**Side-by-side container**: Uses flexbox with two 100ch columns plus gap.

**Dashboard grid**: 2x2 layout with Stats, Key Theorems, Messages, Project Notes panels. Static tile heights (320px) for stats and checks boxes. Project Notes aligned with Key Declarations column.

## Performance Analysis

**SubVerso optimization completed** (Phase 1): Indexing, caching, and containment query optimizations implemented.

**Measured performance breakdown**:

| Operation | Time | Percentage |
|-----------|------|------------|
| SubVerso highlighting | 800-6500ms | 93-99% |
| TeX/HTML generation | <30ms | <1% |

**Key finding**: SubVerso highlighting dominates build time due to goal pretty-printing in info trees. This cannot be deferred because info trees are ephemeral (only exist during elaboration).

**Deferred generation (Phase 2) skipped**: Analysis showed no benefit since the bottleneck (SubVerso) must run during elaboration anyway.

**Large graph optimizations**:
- O(n^3) transitive reduction skipped for graphs >100 nodes
- Simplified edge routing for large graphs in Layout.lean
- Edge deduplication in Build.lean

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
  "assetsDir": "/path/to/dress-blueprint-action/assets"
}
```

| Field | Required | Purpose |
|-------|----------|---------|
| `projectName` | Yes | Module name for Lean (auto-detected by build script) |
| `blueprintTexPath` | Yes | LaTeX source defining structure |
| `assetsDir` | Yes | Directory with CSS/JS assets |
| `paperTexPath` | No | Paper TeX for paper generation (auto-detected by CI) |
| `docgen4Url` | No | Relative path to docgen4 docs (e.g., "docs/") |

**Note**: Paper metadata (`paperTitle`, `paperAuthors`, `paperAbstract`) is no longer configured in runway.json. These values are automatically extracted from `paper.tex`:
- `\title{...}` → paper title
- `\author{...}` split on `\and` → authors array
- `\begin{abstract}...\end{abstract}` → abstract

### lakefile.toml

```toml
[[require]]
name = "Dress"
git = "https://github.com/e-vergo/Dress"
rev = "main"

# Optional: mathlib (pin to v4.27.0)
[[require]]
name = "mathlib"
git = "https://github.com/leanprover-community/mathlib4.git"
rev = "v4.27.0"

# Optional: doc-gen4 as dev dependency
[[require]]
scope = "dev"
name = "doc-gen4"
git = "https://github.com/leanprover/doc-gen4.git"
rev = "01e1433"  # v4.27.0 compatible
```

## docs-static Branch Pattern

For projects with pre-generated documentation (like docgen4 output that takes ~1 hour to generate):

1. Generate docs locally: `lake -R -Kenv=dev build Module:docs`
2. Create orphan branch: `git checkout --orphan docs-static`
3. Add and commit docs to branch root
4. Push: `git push origin docs-static`
5. CI downloads from branch instead of regenerating (~4,700 HTML files in seconds vs. ~1 hour)

**CI usage** (dress-blueprint-action with `docgen4-mode: docs-static`):
```yaml
- uses: e-vergo/dress-blueprint-action@main
  with:
    docgen4-mode: docs-static
```

## Feature Status

### Complete (through Phase 7 + Dashboard + Paper + Module Reference Phases)

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
- Module reference support (`\inputleanmodule{}` expansion)

**Dashboard Homepage**:
- 2x2 grid layout: Stats / Key Theorems / Messages / Project Notes
- Stats panel with Completion column (proven, fullyProven, mathlibReady)
- Stats panel with Attention column (notReady, ready, hasSorry)
- Checks panel with connectivity/cycle info + placeholder future checks
- Key Theorems section with side-by-side preview and status dots
- Messages panel showing user notes from `message` attribute
- Project Notes: blocked/potentialIssues/technicalDebt/misc sections
- All stats computed upstream in Dress (soundness guarantee)
- `title` propagation for cleaner labels (renamed from `displayName`)
- Static tile heights (320px for stats and checks boxes)
- Project Notes aligned with Key Declarations column

**Dependency Graph**:
- Sugiyama layout algorithm (top-to-bottom, median heuristic)
- Node shapes: Ellipse (theorems) / Box (definitions)
- Edge styles: Solid (proof deps) / Dashed (statement deps) with Bezier curves
- 6-status color model (reduced from 8) with appropriate text contrast
- Static legend embedded in SVG (6 items instead of 8)
- D3-style pan/zoom (cursor-centered, no D3 dependency)
- Edge routing: Visibility graph + Dijkstra + Bezier fitting
- Node hover border thickening
- Combined Fit button with corrected X-axis centering (uses getBBox)
- **Sidebar navigation** (chapters, Blueprint Home, Dependency Graph, Paper, GitHub links)
- **Real dependency inference** via `Node.inferUses` (traces actual Lean code)
- **Two-pass edge processing** for proper back-edge handling
- **Edge deduplication** (keeps first occurrence of each from/to pair)
- **O(n^3) transitive reduction skip** for graphs >100 nodes (PNT fix)
- **Simplified edge routing** for large graphs

**Rich Modals (Verso Integration)**:
- Click node to open modal with full side-by-side content
- Reuses `renderNode` for consistent display
- MathJax rendering in modal content
- Tippy.js hover tooltips in modals
- LaTeX proof toggle (plastex.js)
- Lean proof toggle (CSS checkbox pattern)
- "View in Blueprint" link

**`@[blueprint]` Attribute Options** (8 metadata + 3 manual status flags):
- `title`: Custom graph labels (renamed from `displayName`)
- `keyDeclaration`: Dashboard highlighting (renamed from `keyTheorem`)
- `message`: User notes
- `priorityItem`: Attention flagging
- `blocked`, `potentialIssue`, `technicalDebt`, `misc`: Project notes
- `notReady`, `ready`, `mathlibReady`: Manual status overrides
- Removed: `fullyProven` (now auto-computed), `mathlib` (use `mathlibReady`)

**Validation Checks**:
- Connectivity check: warns about disconnected components
- Cycle detection: finds circular dependencies
- Results in manifest.json for CI integration
- SBS-Test includes disconnected cycle (cycleA <-> cycleB) for testing

**PDF/Paper Generation**:
- `\paperstatement{label}` and `\paperfull{label}` hooks
- MathJax-rendered paper.html with links to Lean code
- Declaration-specific links navigate to correct chapter pages
- Multiple LaTeX compilers: tectonic, pdflatex, xelatex, lualatex
- Embedded PDF viewer (pdf.html)
- Auto-detection of available compiler
- **Paper metadata extracted from paper.tex** (title, authors, abstract)
- No longer requires `paperTitle`/`paperAuthors`/`paperAbstract` in runway.json

**Module Reference Support**:
- `\inputleanmodule{ModuleName}` LaTeX command
- `moduleName` field added to Dress nodes for proper module tracking
- `buildModuleLookup` creates map from module name to nodes
- `replaceModulePlaceholders` expands placeholder divs to rendered nodes
- Full module name registration (e.g., `PrimeNumberTheoremAnd.Wiener`)

**CI/CD**:
- `dress-blueprint-action` is complete CI solution (~465 lines)
- Per-project workflows reduced to ~30 lines
- Manual trigger only (`workflow_dispatch`) - user controls deployments
- 4 inputs: `project-directory`, `lean-version`, `docgen4-mode`, `deploy-pages`
- Paper generation auto-detected from runway.json
- DocGen4 modes: skip, docs-static, generate
- Mathlib cache from server (no GitHub Actions cache layer)
- GitHub Pages deployment

**Local Build Scripts**:
- Single shared script (~245 lines) at `scripts/build_blueprint.sh`
- Per-project 3-line wrappers
- Auto-detects projectName from runway.json
- Always cleans toolchain build artifacts (eliminates stale cache issues)
- Consistent commit message format with Claude co-author
- Syncs all repos to GitHub before building
- `scripts/warm_cache.sh` to pre-fetch mathlib cache

**Large-Scale Integration**:
- PrimeNumberTheoremAnd: 530 annotations, 33 files, zero proof code changes
- GCR: Full production example with paper generation
- SBS-Test: 16 nodes demonstrating all 6 status colors

**SBS-Test node inventory** (16 nodes):
- `foundation` (notReady, manual flag)
- `ready_to_prove`, `another_ready` (ready)
- `has_sorry`, `also_sorry` (sorry)
- `proven_leaf`, `proven_mid`, `proven_chain` (proven)
- `fully_chain_1`, `fully_chain_2`, `fully_chain_3` (fullyProven, auto-computed)
- `mathlib_theorem` (mathlibReady)
- `cycle_a`, `cycle_b` (disconnected cycle for validation testing)
- `mod:first`, `mod:second` (module reference tests)

**Bug Fixes**:
- `displayName` -> `title` migration (aligned with PNT's hanwenzhu/LeanArchitect usage)
- Manual `ToExpr` instance for `Node` (status persistence through environment extension)
- O(n^3) transitive reduction skip for graphs >100 nodes (PNT 3+ hour hang fix)
- 6-status model refactoring (removed `stated`, `inMathlib`; `fullyProven` auto-computed)
- Status indicator dots throughout UI (dashboard, blueprint headers, TOC, modals)
- CSS consolidation of status dot styles in `common.css`

**Backwards compatibility** for JSON parsing:
- `"stated"` maps to `.notReady`
- `"inMathlib"` maps to `.mathlibReady`
- Paper links 404 fix (files at root level, not `chapters/` subdirectory)
- Dependency graph fit/centering fixed (proper getBBox handling for X/Y centering)
- Edge deduplication and two-pass processing in Build.lean
- Module name mismatch fix (registers full module names)
- Paper metadata extraction from paper.tex (removes config redundancy)

### Future

- Tactic state expansion
- doc-gen4 cross-linking improvements
- Additional soundness checks (no sorry enforcement in CI)
- Kernel Verification, Soundness Checks (placeholder in dashboard)
