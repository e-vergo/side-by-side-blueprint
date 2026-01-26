# Side-by-Side Lean Code Display Architecture

> **Prototype Status**: This is alpha software with known bugs, slow workflows, and incomplete features. Not yet production-ready.

This document describes the architecture for displaying Lean source code side-by-side with LaTeX theorem statements in blueprint HTML output.

## Overview

The feature involves seven repositories (local forks for faster development):

1. **LeanArchitect** (`/Users/eric/GitHub/Side-By-Side-Blueprint/LeanArchitect`) - Lightweight Lean 4 library providing the `@[blueprint]` attribute and metadata storage
2. **Dress** (`/Users/eric/GitHub/Side-By-Side-Blueprint/Dress`) - Lean 4 tool generating syntax-highlighted artifacts during compilation
3. **Runway** (`/Users/eric/GitHub/Side-By-Side-Blueprint/Runway`) - Pure Lean site generator replacing Python leanblueprint, built on Verso patterns
4. **SubVerso** (`/Users/eric/GitHub/Side-By-Side-Blueprint/subverso`) - Syntax highlighting library for Lean 4 that extracts semantic info from elaboration
5. **dress-blueprint-action** (`/Users/eric/GitHub/Side-By-Side-Blueprint/dress-blueprint-action`) - GitHub Action automating the full build pipeline
6. **General_Crystallographic_Restriction** (`/Users/eric/GitHub/Side-By-Side-Blueprint/General_Crystallographic_Restriction`) - Example consumer project demonstrating ecosystem usage
7. **SBS-Test** (`/Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test`) - Minimal test project for CI validation of the full feature suite

**Toolchain**: All repositories use `leanprover/lean4:v4.27.0-rc1` for olean compatibility.

## Migration: Python leanblueprint -> Pure Lean Runway

### Why Migrate?

The original leanblueprint uses Python/plasTeX to consume Dress artifacts and produce HTML. This has several pain points:

- **Two build systems** - Lake for Lean, pip/texlive for Python
- **CI overhead** - texlive container adds ~10 minutes to builds
- **No incremental builds** - Full rebuild on any change
- **Stringly-typed templates** - Jinja2 templates lack type safety
- **Ecosystem misalignment** - Can't leverage Lean tooling improvements

### The New Stack

**Runway** is a pure Lean site generator that:
- Consumes Dress artifacts directly (no Python intermediary)
- Uses Verso's `Html` type and rendering patterns
- Integrates with Lake for incremental builds
- Provides type-safe HTML generation
- Aligns with the Lean reference manual's architecture

```
OLD STACK (3 languages):
@[blueprint] -> Dress (Lean) -> .tex artifacts -> leanblueprint (Python) -> HTML

NEW STACK (100% Lean):
@[blueprint] -> Dress (Lean) -> .html/.json artifacts -> Runway (Lean) -> HTML
```

## Repository Responsibilities

| Repository | Role | Dependencies |
|------------|------|--------------|
| **LeanArchitect** | Metadata storage | batteries |
| **Dress** | Type-checked artifact generation | LeanArchitect, SubVerso, Verso |
| **Runway** | Site assembly and HTML rendering | Dress, Verso |
| **SubVerso** | Syntax highlighting extraction | Lean core |

### Why This Split?

- **LeanArchitect** is minimal - just data structures and environment extensions. Could be upstreamed independently.
- **Dress** does heavy lifting during `lake build` - everything needing type info happens here.
- **Runway** is a pure site generator - could run on CI without rebuilding Lean. Mirrors how the reference manual separates SubVerso (highlighting) from Verso (rendering).

## Architecture

```
+-------------------------------------------------------------------------+
|                         LEAN PROJECT                                    |
|  import Dress                                                           |
|  @[blueprint "thm:foo"] theorem foo : P -> Q := ...                     |
+-------------------------------------------------------------------------+
                              |
                              | BLUEPRINT_DRESS=1 lake build
                              v
+-------------------------------------------------------------------------+
|                           DRESS                                         |
|                                                                         |
|  Phase 1: Elaboration-time (per @[blueprint] declaration)               |
|  +-- SubVerso captures semantic highlighting from info trees            |
|  +-- Verso renders HTML with hover tooltips (data-verso-hover)          |
|  +-- Writes per-declaration artifacts immediately:                      |
|      .lake/build/dressed/{Module/Path}/{label}/                         |
|          decl.tex, decl.html, decl.json                                 |
|                                                                         |
|  Phase 2: Lake facet (library-level, after compilation)                 |
|  +-- :blueprint facet aggregates module artifacts                       |
|  +-- :depGraph facet generates dep-graph.json + dep-graph.svg           |
+-------------------------------------------------------------------------+
                              |
                              | lake exe runway build
                              v
+-------------------------------------------------------------------------+
|                          RUNWAY                                         |
|                                                                         |
|  Pure Lean site generator (replaces Python leanblueprint):              |
|  +-- Loads Dress artifacts from .lake/build/dressed/                    |
|  +-- Parses blueprint.tex for chapter/section structure                 |
|  +-- Loads dependency graph (JSON + SVG)                                |
|  +-- Renders HTML using Verso patterns                                  |
|  +-- Generates multi-page output with chapter navigation                |
|  +-- Outputs static site to .lake/build/runway/                         |
|                                                                         |
|  Key components:                                                        |
|  +-- Theme.lean - plasTeX-compatible HTML templates with sidebar        |
|  +-- Render.lean - Side-by-side node rendering with proof toggle sync   |
|  +-- Latex/Parser.lean - LaTeX chapter/section parsing                  |
|  +-- Latex/ToHtml.lean - LaTeX prose to HTML conversion                 |
|  +-- Assets.lean - CSS/JS (migrated from leanblueprint)                 |
|  +-- Main.lean - CLI entry point                                        |
+-------------------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------------------+
|                        HTML OUTPUT                                      |
|                                                                         |
|  .sbs-container (CSS grid):                                             |
|  +-- .sbs-latex-column (75ch fixed) - LaTeX theorem                     |
|  +-- .sbs-lean-column (flexible) - Lean code with highlighting          |
|       +-- .lean-signature - Highlighted signature                       |
|       +-- .lean-proof-body - Collapsible proof (synced with LaTeX)      |
|                                                                         |
|  Interactive features (verso-code.js):                                  |
|  +-- Tippy.js hover tooltips with type signatures                       |
|  +-- Token binding highlights (hover variable -> all occurrences)       |
|  +-- Tactic state expansion on click                                    |
|  +-- Synchronized proof toggle (both columns animate together)          |
+-------------------------------------------------------------------------+
```

## Output Directory Structure

### Dress Artifacts (.lake/build/dressed/)

```text
.lake/build/dressed/
+-- {Module/Path}/                    # Per-module directory
|   +-- {sanitized-label}/            # Per-declaration subdirectory
|       +-- decl.tex                  # LaTeX with base64 data (legacy)
|       +-- decl.html                 # Syntax-highlighted HTML
|       +-- decl.json                 # Metadata + highlighting JSON
|
+-- dep-graph.json                    # Dependency graph for D3.js
+-- dep-graph.svg                     # Static SVG (Sugiyama layout)
```

### Runway Output (.lake/build/runway/)

```text
.lake/build/runway/
+-- index.html                        # Homepage with stats + chapter list
+-- dep-graph.html                    # Full dependency graph page
+-- chapter1.html                     # Per-chapter pages
+-- chapter2.html
+-- chapter3.html
+-- ...
+-- manifest.json                     # Node index (replaces nodes/ directory)
+-- assets/
    +-- blueprint.css                 # Copied from assetsDir
    +-- plastex.js                    # Proof toggle functionality
    +-- verso-code.js                 # Hover tooltips + binding highlight
```

## Key Files

### LeanArchitect

Lightweight metadata store with no artifact generation. Only depends on `batteries`.

| File | Purpose |
|------|---------|
| `Architect/Basic.lean` | `Node`, `NodePart`, `NodeWithPos` structures; environment extensions |
| `Architect/Attribute.lean` | `@[blueprint]` attribute syntax and elaboration |
| `Architect/CollectUsed.lean` | Automatic dependency inference from constant usage |

**Environment Extensions:**
- `blueprintExt : NameMapExtension Node` - All registered blueprint nodes
- `latexLabelToLeanNamesExt` - Reverse index: LaTeX label -> Lean names

### Dress

Two-phase architecture: per-declaration artifacts during elaboration, library-level aggregation via Lake facets.

| File | Purpose |
|------|---------|
| `Dress/Capture/ElabRules.lean` | `elab_rules` hooks for theorem/def/etc. |
| `Dress/Generate/Declaration.lean` | Per-declaration artifact writer (tex, html, json) |
| `Dress/HtmlRender.lean` | Verso HTML rendering wrapper |
| `Dress/Paths.lean` | Centralized path management |
| `Dress/Graph/` | Dependency graph generation (Types, Build, Layout, Svg, Json) |
| `lakefile.lean` | Lake facets (`dressed`, `blueprint`, `depGraph`) |

### Runway (replaces leanblueprint)

Pure Lean website generator built on Verso patterns.

| File | Purpose |
|------|---------|
| `Runway/Config.lean` | Site configuration (title, URLs, `blueprintTexPath`, `assetsDir`) |
| `Runway/Site.lean` | `NodeInfo`, `BlueprintSite`, `ChapterInfo`, `SectionInfo` structures |
| `Runway/Traverse.lean` | Artifact loading from Dress output |
| `Runway/Render.lean` | Side-by-side node HTML rendering with homepage stats |
| `Runway/Theme.lean` | plasTeX-compatible page templates with sidebar navigation |
| `Runway/Assets.lean` | Asset copying logic (minimal - assets are external files) |
| `Runway/DepGraph.lean` | Graph embedding in HTML |
| `Runway/Latex/Parser.lean` | LaTeX chapter/section/node parsing |
| `Runway/Latex/ToHtml.lean` | LaTeX prose to HTML conversion |
| `Main.lean` | CLI entry point (`runway build/serve/check`) |

### External Assets (dress-blueprint-action/assets/)

CSS and JavaScript are maintained as real files, not embedded strings.

| File | Purpose |
|------|---------|
| `blueprint.css` | Full stylesheet (plasTeX-compatible, side-by-side layout) |
| `plastex.js` | Proof toggle functionality |
| `verso-code.js` | Hover tooltips, token binding highlights |

### SubVerso

Semantic syntax highlighting library maintained by Lean FRO.

| File | Purpose |
|------|---------|
| `Highlighting/Highlighted.lean` | Core data structures: `Token.Kind`, `Highlighted` |
| `Highlighting/Code.lean` | Main highlighting logic from info trees |

## Feature Details

### Proof Toggle Synchronization

When the user clicks to expand/collapse a LaTeX proof, both columns animate together:

- **Left column**: LaTeX proof content slides open/closed
- **Right column**: Lean proof body (`.lean-proof-body`) slides in sync

The Lean code is split into two elements:
- `<code class="lean-signature">` - Always visible signature
- `<code class="lean-proof-body">` - Collapsible proof body

JavaScript in `plastex.js` handles the synchronized animation using jQuery's `slideToggle`.

### Multi-Page Chapter Generation

Runway parses `blueprint.tex` (or custom path via `blueprintTexPath` config) to extract:

- `\chapter{Title}` - Creates separate HTML pages
- `\section{Title}` - Subsections within chapters
- `\inputleanmodule{Module.Name}` - Include all nodes from a module
- `\inputleannode{label}` - Include specific node by label
- Prose text between commands - Rendered as HTML with MathJax

Output includes:
- **Sidebar navigation** - Chapter list with current page highlighted
- **Prev/next navigation** - Links at bottom of each chapter page
- **Homepage** - Chapter index with progress statistics

### Homepage Statistics

The index page displays aggregate progress metrics:

- Total nodes by type (theorems, definitions, lemmas, etc.)
- Completion status (proved, stated, not ready)
- Progress bar with percentage
- Per-chapter breakdown

### Configuration Options

The `runway.json` config file supports:

```json
{
  "title": "Project Title",
  "projectName": "ProjectName",
  "githubUrl": "https://github.com/...",
  "baseUrl": "/",
  "docgen4Url": null,
  "blueprintTexPath": "blueprint/src/blueprint.tex",
  "assetsDir": "/path/to/dress-blueprint-action/assets"
}
```

| Field | Required | Purpose |
|-------|----------|---------|
| `blueprintTexPath` | Yes | LaTeX source file defining chapter structure |
| `assetsDir` | Yes | Directory containing CSS/JS assets to copy |

## Verso Integration

Runway follows Verso patterns to enable eventual upstream contribution:

### Html Type

```lean
-- Verso's Html type provides type-safe HTML generation
open Verso.Output Html

def renderNode (node : NodeInfo) : RenderM Html := do
  return .tag "div" #[("class", "sbs-container")] (
    divClass "sbs-latex-column" (...) ++
    divClass "sbs-lean-column" (...)
  )
```

### Theme System

```lean
structure Theme where
  name : String
  primaryTemplate : Template      -- HTML wrapper (head, body, nav)
  nodeTemplate : NodeTemplate     -- Individual node rendering
  indexTemplate : IndexTemplate   -- Site index page
  cssFiles : Array (String x String)
  jsFiles : Array (String x String x Bool)
```

### Asset Handling

Assets are maintained as external files and copied during site generation:

```
dress-blueprint-action/assets/
├── blueprint.css    (32 KB - full stylesheet)
├── plastex.js       (1.7 KB - proof toggles)
└── verso-code.js    (15 KB - hovers, bindings)
           ↓
runway.json: "assetsDir": "/path/to/dress-blueprint-action/assets"
           ↓
Runway copies to output/assets/ during build
           ↓
HTML references: <link href="assets/blueprint.css">
```

This allows standard CSS/JS tooling, syntax highlighting, and easier collaboration.

## Build Process

### Local Build (Pure Lean)

```bash
# 1. Build Lean project with Dress artifact generation
rm -rf .lake/build/dressed .lake/build/lib/YourProject .lake/build/ir/YourProject
BLUEPRINT_DRESS=1 lake build

# 2. Generate library index and dependency graph
lake build :blueprint

# 3. Generate site with Runway
lake exe runway build runway.json

# 4. Serve locally
lake exe runway serve
# Or: python3 -m http.server -d .lake/build/runway
```

### Using build_blueprint.sh

```bash
./scripts/build_blueprint.sh
```

This script:
1. Builds local dependency forks (SubVerso, LeanArchitect, Dress, Runway)
2. Fetches Mathlib cache
3. Builds with `BLUEPRINT_DRESS=1`
4. Runs `lake build :blueprint`
5. Runs `lake exe runway build`
6. Serves the result locally

### GitHub Actions (dress-blueprint-action)

```yaml
# Using the dress-blueprint-action for full pipeline automation
- name: Build blueprint with Dress
  uses: e-vergo/dress-blueprint-action@v1
  with:
    build-dressed: true
    blueprint-facet: true
    build-pdf: true
    build-web: true
    use-mathlib-cache: true
    deploy-pages: true

# Or manual steps (no texlive container needed for pure Lean):
- name: Build blueprint
  run: |
    lake exe cache get
    BLUEPRINT_DRESS=1 lake build
    lake build :blueprint
    lake exe runway build runway.json

- name: Deploy to GitHub Pages
  uses: actions/upload-pages-artifact@v3
  with:
    path: .lake/build/runway
```

## CSS Classes

### Side-by-Side Layout

| Class | Purpose |
|-------|---------|
| `.sbs-container` | CSS grid container (75ch + flexible) |
| `.sbs-latex-column` | Left column - LaTeX statement/proof |
| `.sbs-lean-column` | Right column - Lean code |
| `.lean-signature` | Lean signature (always visible) |
| `.lean-proof-body` | Lean proof body (synced with LaTeX toggle) |

### plasTeX Compatibility

| Class | Purpose |
|-------|---------|
| `.theorem_thmwrapper` | Outer wrapper with env-specific styling |
| `.theorem_thmheading` | Header with caption + label + status |
| `.theorem_thmcontent` | Statement content |
| `.proof_wrapper` | Collapsible proof container |
| `.proof_heading` | Clickable proof header |
| `.proof_content` | Proof text (hidden by default) |

### Semantic Highlighting (from SubVerso/Verso)

| Class | Element |
|-------|---------|
| `.keyword.token` | `def`, `theorem`, `by`, `fun` |
| `.const.token` | Constants and functions |
| `.var.token` | Local variables |
| `.literal.token` | String/number literals |
| `.doc-comment.token` | Doc comments |

### Interactive Features

| Attribute | Purpose |
|-----------|---------|
| `data-lean-hovers` | JSON map of hover ID -> tooltip HTML |
| `data-verso-hover` | Links token to hover data entry |
| `data-binding` | Unique binding ID for variable highlighting |
| `.binding-hl` | Yellow background for highlighted bindings |

## Configuration

### lakefile.toml

```toml
[[require]]
name = "Dress"
git = "https://github.com/e-vergo/Dress"
rev = "main"
```

### runway.json

```json
{
  "title": "Project Title",
  "projectName": "ProjectName",
  "githubUrl": "https://github.com/...",
  "baseUrl": "/",
  "docgen4Url": null,
  "blueprintTexPath": "blueprint/src/blueprint.tex",
  "assetsDir": "/path/to/dress-blueprint-action/assets"
}
```

### Lean Files

```lean
import Dress  -- Re-exports LeanArchitect

@[blueprint "thm:my-theorem"
  (statement := /-- The statement in LaTeX. -/)
  (proof := /-- Proof explanation. -/)]
theorem myTheorem : 2 + 2 = 4 := rfl
```

## Roadmap

### Phase 1: Core Rendering (Complete)
- [x] Load Dress artifacts (decl.html, dep-graph.json)
- [x] plasTeX-compatible HTML structure
- [x] Side-by-side layout CSS
- [x] MathJax integration
- [x] Proof toggle JavaScript
- [x] Hover tooltips with type signatures
- [x] Token binding highlights
- [x] Sidebar navigation

### Phase 2: Blueprint Feature Parity (Complete)
- [x] "Uses:" dependency display removed (dependencies shown only in graph)
- [x] Proof toggle synchronization (both columns animate together)
- [x] Code splitting (signature vs proof body)
- [x] Multi-page chapter generation (parse `blueprint.tex`)
- [x] Homepage statistics (progress bar, counts by type/status)
- [x] `blueprintTexPath` and `assetsDir` config options
- [x] Prev/next chapter navigation
- [x] Dependency graph page with modals
- [x] External CSS/JS assets
- [x] manifest.json (replaces nodes/ directory)

### Phase 3: ar5iv Paper Generation (Current Priority)
- [ ] Full paper generation (not just blueprint)
- [ ] MathJax rendering (like current blueprint)
- [ ] No direct Lean code display (just links)
- [ ] Defined by tex file, uses Dress artifacts
- [ ] Same build pattern as blueprint

### Phase 4: Polish and Extended Features
- [ ] Tactic state expansion
- [ ] doc-gen4 cross-linking
- [ ] Define `Blueprint : Genre` following reference manual patterns
- [ ] Document DSL for expository content (`#doc`, `{node}`)

### Phase 5: Upstream
- [ ] Propose as official Verso genre or FRO tool
- [ ] doc-gen4 integration (bidirectional links)
- [ ] Archive Python leanblueprint

## Dependency Chain

```
Consumer Projects:
+-- General_Crystallographic_Restriction (production example)
+-- SBS-Test (CI validation)
    |
    +-- Dress (e-vergo/Dress)
        +-- LeanArchitect (e-vergo/LeanArchitect)
        |   +-- batteries
        +-- SubVerso (e-vergo/subverso, fork)
        |   +-- (Lean core)
        +-- Verso (leanprover/verso)

Site Generation (local forks):
+-- Runway (e-vergo/Runway)
    +-- Dress (for artifact types)
    +-- Verso (for Html type)
```

At build time:
```
Lean Project + Dress -> .lake/build/dressed/ artifacts
                            |
                      Runway (local fork)
                            |
                      .lake/build/runway/ (static site)
                            |
                      GitHub Pages deployment
```
