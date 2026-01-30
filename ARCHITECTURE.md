# Side-by-Side Blueprint Architecture

![Lean](https://img.shields.io/badge/Lean-v4.27.0-blue)
![License](https://img.shields.io/badge/License-Apache%202.0-green)

> **Prototype Status**: Alpha software with known bugs, slow workflows, and incomplete features.

## Table of Contents

- [Overview](#overview)
- [Build Pipeline](#build-pipeline)
- [Output Directories](#output-directories)
- [External Assets Architecture](#external-assets-architecture)
- [manifest.json System](#manifestjson-system)
- [Repository Details](#repository-details)
- [Dependency Graph Architecture](#dependency-graph-architecture)
- [PDF/Paper Generation Pipeline](#pdfpaper-generation-pipeline)
- [CI/CD Architecture](#cicd-architecture)
- [Local Build Scripts](#local-build-scripts)
- [Performance](#performance)
- [Configuration](#configuration)

## Overview

Eight repositories work together to produce formalization documentation:

| Repository | Purpose |
|------------|---------|
| **SubVerso** | Syntax highlighting extraction from Lean info trees with O(1) indexed lookups |
| **LeanArchitect** | `@[blueprint]` attribute with 8 metadata options + 3 manual status flags |
| **Dress** | Artifact generation + rainbow brackets + dependency graph layout + stats computation + validation checks |
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
  - Applies rainbow bracket highlighting (wrapBracketsWithDepth)
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
│       ├── decl.html         # Syntax-highlighted HTML with rainbow brackets
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
    ├── common.css            # Theme toggle, base styles, status dots, rainbow brackets
    ├── blueprint.css         # Full stylesheet including modal and graph styles
    ├── plastex.js            # LaTeX proof toggle
    └── verso-code.js         # Hovers, bindings, pan/zoom, modal init, [blueprint] link positioning
```

## External Assets Architecture

CSS and JavaScript are maintained as real files in `dress-blueprint-action/assets/`:

| File | Size | Purpose |
|------|------|---------|
| `common.css` | ~3 KB | Theme toggle, status dots, rainbow brackets (6 depth colors, light/dark) |
| `blueprint.css` | ~35 KB | Full stylesheet including modal and graph styles |
| `plastex.js` | ~2 KB | LaTeX proof toggle (expand/collapse) |
| `verso-code.js` | ~20 KB | Hover tooltips, token binding, pan/zoom, modal MathJax/Tippy init, [blueprint] link positioning |

**Configuration**: `runway.json` requires `assetsDir` field pointing to assets directory.

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
  "messages": [...],
  "projectNotes": { "priority": [...], "blocked": [...], ... },
  "nodes": { "thm:main-result": "#thm:main-result", ... }
}
```

## Repository Details

### LeanArchitect

Lightweight metadata store. Only depends on `batteries`.

| File | Purpose |
|------|---------|
| `Architect/Basic.lean` | `Node`, `NodePart`, `NodeStatus` structures with manual `ToExpr` instance |
| `Architect/Attribute.lean` | `@[blueprint]` attribute with all options |
| `Architect/CollectUsed.lean` | Dependency inference |

**Attribute options (8 metadata + 3 manual status flags)**:

| Option | Type | Purpose |
|--------|------|---------|
| `title` | String | Custom node label in dependency graph |
| `keyDeclaration` | Bool | Highlight in dashboard Key Theorems section |
| `message` | String | User notes (appears in Messages panel) |
| `priorityItem` | Bool | Flag for Attention column in dashboard |
| `blocked` | String | Reason for blockage (Attention column) |
| `potentialIssue` | String | Known concerns (Attention column) |
| `technicalDebt` | String | Cleanup notes (Attention column) |
| `misc` | String | Catch-all notes (Attention column) |
| `notReady` | Bool | Status: not ready (sandy brown) |
| `ready` | Bool | Status: ready to formalize (light sea green) |
| `mathlibReady` | Bool | Status: ready for mathlib (light blue) |

### Dress

Two-phase: per-declaration during elaboration, library-level via Lake facets.

| File | Purpose |
|------|---------|
| `Capture/ElabRules.lean` | elab_rules hooks |
| `Capture/InfoTree.lean` | SubVerso highlighting capture |
| `Generate/Declaration.lean` | Per-declaration artifact writer |
| `HtmlRender.lean` | Verso HTML rendering + `wrapBracketsWithDepth` for rainbow brackets |
| `Graph/Types.lean` | `Node`, `Edge`, `StatusCounts`, `CheckResults` types; `transitiveReduction` with O(n^3) skip |
| `Graph/Build.lean` | Graph construction + stats + validation + `Node.inferUses` + two-pass edge processing |
| `Graph/Json.lean` | Manifest serialization with stats/metadata/validation |
| `Graph/Layout.lean` | Sugiyama algorithm, visibility graph edge routing (simplified for >100 nodes) |
| `Graph/Render.lean` | SVG generation with Bezier curves |
| `Paths.lean` | Centralized path management |
| `Main.lean` | Writes manifest.json with precomputed stats |

**Rainbow bracket highlighting** (`HtmlRender.lean`):
- `wrapBracketsWithDepth`: Wraps `(`, `)`, `[`, `]`, `{`, `}` with depth-colored spans
- Cycles through 6 colors (`lean-bracket-1` through `lean-bracket-6`)
- Skips brackets inside HTML tags (detects `<` to avoid breaking structure)
- CSS in `common.css` with light and dark mode variants

**Dependency inference**: `Node.inferUses` traces actual Lean code dependencies by examining the expression tree, rather than using manually-specified `\uses{}` annotations.

**Two-pass edge processing** (`Graph/Build.lean`):
- PASS 1: Register all labels and create nodes (so all labels exist in the builder state)
- PASS 2: Add all edges (now back-edges work because targets are registered)
- Edge deduplication: keeps first occurrence of each from/to pair

**Transitive reduction performance**: `Graph.transitiveReduction` uses Floyd-Warshall algorithm which is O(n^3). For large graphs like PNT (530 nodes), this is skipped for graphs with >100 nodes.

**Validation checks** (`Graph/Build.lean`):
- `findComponents`: Detects disconnected subgraphs (warns about unreachable nodes)
- `detectCycles`: Finds circular dependencies via DFS (errors on cycles)
- Results stored in `CheckResults` and written to manifest.json

**`computeFullyProven` algorithm** (`Graph/Build.lean`):
- O(V+E) complexity with memoization
- A node is `fullyProven` if: it is `proven` AND all ancestors are `proven` or `fullyProven`
- Automatically upgrades `proven` nodes whose entire dependency chain is complete

### Runway

Pure Lean site generator using Verso patterns.

| File | Purpose |
|------|---------|
| `Main.lean` | CLI entry point with `build`, `paper`, `pdf` commands; `assignPagePaths` for links |
| `Render.lean` | Side-by-side node rendering, dashboard, modal content |
| `Theme.lean` | Page templates, sidebar, `buildModuleLookup`, `replaceModulePlaceholders` |
| `DepGraph.lean` | Dependency graph page with sidebar + modal wrappers |
| `Site.lean` | `NodeInfo` structure with `title`, `pagePath`, `moduleName` fields; `fullUrl` helper |
| `Pdf.lean` | PDF compilation with multiple LaTeX compilers |
| `Paper.lean` | Paper rendering + `PaperMetadata` extraction from paper.tex |
| `Latex/Parser.lean` | LaTeX parsing with O(n) string concatenation and infinite loop protection |
| `Latex/Ast.lean` | AST types including `Preamble` with `abstract` field |
| `Latex/ToHtml.lean` | LaTeX to HTML |
| `Config.lean` | Site config including `assetsDir`, `paperTexPath` |
| `Assets.lean` | Asset copying |

**Parser implementation** (`Latex/Parser.lean`):
- Uses Array-based string building for O(n) concatenation (collects parts via `Array.push`, joins with `"".intercalate` at end)
- Includes `let _ <- advance` in catch-all cases to prevent infinite loops
- Handles large documents (3989+ tokens) without issues

**Module reference support** (`Theme.lean`):
- `buildModuleLookup`: Creates map from module name to nodes in that module
- `replaceModulePlaceholders`: Finds placeholder divs and replaces with rendered nodes
- Supports `\inputleanmodule{ModuleName}` LaTeX command

**Status indicator dots** appear throughout the UI:

| Location | File | Description |
|----------|------|-------------|
| Dashboard Key Declarations | `Render.lean` | Dots next to each key declaration |
| Dashboard Project Notes | `Render.lean` | Dots in all note sections |
| Blueprint Theorem Headers | `Dress/Render/SideBySide.lean` | Dot in thm_header_extras |
| Blueprint Index/TOC | `Render.lean` | Dots in sidebar node list |
| Dependency Graph Modals | `DepGraph.lean` | Dot in modal header bar + [blueprint] link inline with theorem header |
| Paper Theorem Headers | `Dress/Render/SideBySide.lean` | Dot + status text in verification badge |

**CSS consolidation** - All status dot and rainbow bracket styles are in `common.css`:
- Base `.status-dot` (8px)
- `.header-status-dot` (10px for blueprint headers)
- `.paper-status-dot` (10px for paper headers)
- `.modal-status-dot` (12px for dependency graph modals)
- `.node-list-item` (sidebar/TOC)
- `.note-item-with-dot` (dashboard notes)
- `.dep-modal-header-bar` (modal layout)
- `.lean-bracket-1` through `.lean-bracket-6` (rainbow brackets, light/dark variants)

### SubVerso

Fork of leanprover/subverso with optimizations.

| File | Purpose |
|------|---------|
| `Highlighting/Code.lean` | Main highlighting logic with InfoTable indexing |
| `Highlighting/Highlighted.lean` | Token.Kind, Highlighted types |

**InfoTable optimizations** (O(1) lookups instead of O(n) tree traversal):
- `infoByExactPos`: HashMap for exact position lookups
- `termInfoByName`: HashMap for const/fvar lookups
- `nameSuffixIndex`: HashMap for suffix-based lookups
- `allInfoSorted`: Sorted array for containment queries with early exit
- `lookupByExactPos`, `lookupTermInfoByName`, `lookupBySuffix`, `lookupContaining`

**Error handling**: Uses `throw <| IO.userError` for graceful error handling instead of panics.

## Dependency Graph Architecture

### Layout Algorithm (Dress/Graph/Layout.lean)

Sugiyama-style hierarchical layout:
1. **Layer assignment**: Top-to-bottom, respecting edge directions
2. **Crossing reduction**: Median heuristic for node ordering within layers
3. **Position refinement**: Iterative adjustment for better spacing
4. **Edge routing**: Visibility graph + Dijkstra shortest path + Bezier fitting (simplified for large graphs)

### Node Status Model (6 statuses)

| Status | Color | Hex | Source |
|--------|-------|-----|--------|
| notReady | Sandy Brown | #F4A460 | Default + Manual: `(notReady := true)` |
| ready | Light Sea Green | #20B2AA | Manual: `(ready := true)` |
| sorry | Dark Red | #8B0000 | Auto: proof contains sorryAx |
| proven | Light Green | #90EE90 | Auto: complete proof |
| fullyProven | Forest Green | #228B22 | Auto-computed: proven + all ancestors proven/fullyProven |
| mathlibReady | Light Blue | #87CEEB | Manual: `(mathlibReady := true)` |

**Priority order** (manual always wins):
1. `mathlibReady` (manual) - highest
2. `ready` (manual)
3. `notReady` (manual, if explicitly set)
4. `fullyProven` (auto-computed from graph)
5. `sorry` (auto-detected via sorryAx)
6. `proven` (auto-detected, has Lean without sorry)
7. `notReady` (default, no Lean code)

### Edge Rendering

- **Solid lines**: Proof dependencies (from `Node.inferUses` proofUses)
- **Dashed lines**: Statement dependencies (from `Node.inferUses` statementUses)
- **Bezier curves**: Control points calculated via visibility graph
- **Arrow heads**: Point at target node boundary (clipped to shape)
- **Deduplication**: First occurrence of each from/to pair kept

### Modal System

**Generation flow**:
1. `Runway/Render.lean`: `renderNodeModal` wraps existing `renderNode` output
2. `Runway/DepGraph.lean`: `wrapInModal` creates modal container with close button and [blueprint] link
3. `verso-code.js`: `onModalOpen()` moves [blueprint] link inline with theorem header via DOM manipulation, initializes MathJax and Tippy.js

**ID normalization**: Node IDs containing colons (`thm:main`) are converted to hyphens (`thm-main`) for modal element IDs and CSS selectors.

**Proof toggles**:
- LaTeX proofs: `plastex.js` handles expand/collapse
- Lean proofs: CSS checkbox pattern (pure CSS, no JS)

### Pan/Zoom (verso-code.js)

D3-style behavior implemented manually (no D3 dependency):
- **Wheel**: Zoom centered on cursor position (4x reduced sensitivity)
- **Drag**: Pan with pointer capture
- **Fit button**: Scales and centers graph using `getBBox()` for content bounds

## PDF/Paper Generation Pipeline

### Commands

- `lake exe runway paper runway.json` - Generate paper.html + paper.pdf
- `lake exe runway pdf runway.json` - Generate just the PDF
- `lake exe runway build runway.json` - Generates paper if `paperTexPath` configured

### Paper TeX Format

```latex
\documentclass{article}
\title{The Crystallographic Restriction Theorem}
\author{J. Kuzmanovich \and A. Pavlichenkov \and E. Vergo}
\begin{document}

\begin{abstract}
We present a complete formalization...
\end{abstract}

\paperstatement{thm:main}  % Insert LaTeX statement, link to Lean
\paperfull{thm:main}       % Insert full side-by-side display

\end{document}
```

### Supported LaTeX Compilers

| Compiler | Priority | Notes |
|----------|----------|-------|
| `tectonic` | 1 (preferred) | Modern, self-contained |
| `pdflatex` | 2 | Most common |
| `xelatex` | 3 | Better Unicode support |
| `lualatex` | 4 | Lua scripting support |

## CI/CD Architecture

### Design Philosophy

- **Manual triggers only**: `workflow_dispatch` - user controls deployments
- **Simplified workflows**: ~30 lines per project
- **Centralized complexity**: `dress-blueprint-action` (~465 lines, 14 steps)
- **No GitHub Actions mathlib cache**: relies on mathlib server (`lake exe cache get`)

### Per-Project Workflow (~30 lines)

```yaml
name: Full Blueprint Build and Deploy

on:
  workflow_dispatch:

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
    steps:
      - uses: actions/deploy-pages@v4
```

### Action Inputs (4)

| Input | Default | Purpose |
|-------|---------|---------|
| `project-directory` | `.` | Directory containing lakefile.toml and runway.json |
| `lean-version` | (auto) | Override Lean version (auto-detected from lean-toolchain) |
| `docgen4-mode` | `skip` | DocGen4 mode: `skip`, `docs-static`, or `generate` |
| `deploy-pages` | `true` | Upload artifact for GitHub Pages deployment |

### DocGen4 Modes

| Mode | Behavior |
|------|----------|
| `skip` | No DocGen4 (fastest, default) |
| `docs-static` | Download from `docs-static` branch (~4,700 files in seconds) |
| `generate` | Run `lake -R -Kenv=dev build +:docs` (slow, ~1 hour) |

## Local Build Scripts

A single shared script at `scripts/build_blueprint.sh` (~245 lines) handles all local builds. Each project has a 3-line wrapper.

### Build Script Steps

```
Step 0:  Validate project (check runway.json, auto-detect projectName)
Step 0a: Kill existing servers on port 8000
Step 0b: Sync all repos to GitHub (auto-commit/push with Claude co-author)
Step 0c: Update lake manifests in dependency order
Step 1:  Clean all build artifacts (toolchain + project) - eliminates stale caches
Step 2:  Build toolchain (SubVerso -> LeanArchitect -> Dress -> Runway)
Step 3:  Fetch mathlib cache (lake exe cache get)
Step 4:  Build project with BLUEPRINT_DRESS=1
Step 5:  Build :blueprint facet
Step 6:  Generate dependency graph (extract_blueprint graph)
Step 7:  Generate site with Runway
Step 8:  Generate paper (if paperTexPath configured)
Step 9:  Start server and open browser (localhost:8000)
```

## Performance

**SubVerso optimization complete**: O(1) indexed lookups via InfoTable.

| Operation | Time | Percentage |
|-----------|------|------------|
| SubVerso highlighting | 800-6500ms | 93-99% |
| TeX/HTML generation | <30ms | <1% |

**Large graph optimizations**:
- O(n^3) transitive reduction skipped for graphs >100 nodes
- Simplified edge routing for large graphs in Layout.lean
- Edge deduplication in Build.lean

**String concatenation**: Parser.lean uses Array-based building (O(n)) instead of repeated `++` (O(n^2)).

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

Paper metadata (title, authors, abstract) is extracted from `paper.tex` using `\title{}`, `\author{}` (split on `\and`), and `\begin{abstract}...\end{abstract}`.

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
```

## SBS-Test Node Inventory (16 nodes)

Demonstrates all 6 status colors:
- `foundation` (notReady, manual flag)
- `ready_to_prove`, `another_ready` (ready)
- `has_sorry`, `also_sorry` (sorry)
- `proven_leaf`, `proven_mid`, `proven_chain` (proven)
- `fully_chain_1`, `fully_chain_2`, `fully_chain_3` (fullyProven, auto-computed)
- `mathlib_theorem` (mathlibReady)
- `cycle_a`, `cycle_b` (disconnected cycle for validation testing)
- `mod:first`, `mod:second` (module reference tests)

## Backwards Compatibility

JSON parsing handles legacy status values:
- `"stated"` maps to `.notReady`
- `"inMathlib"` maps to `.mathlibReady`

## Related Documents

- [README.md](README.md) - Project overview and getting started
- [GOALS.md](GOALS.md) - Project vision and design goals
