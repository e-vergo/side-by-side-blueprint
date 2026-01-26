# Side-by-Side Blueprint Architecture

> **Prototype Status**: Alpha software with known bugs, slow workflows, and incomplete features.

## Overview

Seven repositories work together to produce formalization documentation:

| Repository | Purpose |
|------------|---------|
| **SubVerso** | Syntax highlighting extraction from Lean info trees |
| **LeanArchitect** | `@[blueprint]` attribute and metadata storage |
| **Dress** | Artifact generation during elaboration |
| **Runway** | Site generator (replaces Python leanblueprint) |
| **SBS-Test** | Minimal test project for iteration |
| **General_Crystallographic_Restriction** | Production example |
| **dress-blueprint-action** | GitHub Action + external CSS/JS assets |

**Dependency chain**: SubVerso -> LeanArchitect -> Dress -> Runway -> Consumer projects

**Toolchain**: All repos use `leanprover/lean4:v4.27.0-rc1`

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
        |
        v
RUNWAY (post-build):
  - Parses blueprint.tex for chapter/section structure
  - Loads artifacts from .lake/build/dressed/
  - Copies assets from assetsDir to output
  - Generates manifest.json (node index)
  - Generates multi-page static site
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
└── dep-graph.svg             # Static Sugiyama layout
```

### Runway Output (.lake/build/runway/)

```
.lake/build/runway/
├── index.html                # Homepage with stats
├── dep-graph.html            # Full dependency graph
├── chapter{N}.html           # Per-chapter pages
├── manifest.json             # Node index
└── assets/
    ├── blueprint.css         # From assetsDir
    ├── plastex.js            # Proof toggle
    └── verso-code.js         # Hovers, bindings
```

## External Assets Architecture

CSS and JavaScript are maintained as real files in `dress-blueprint-action/assets/`, not embedded strings:

| File | Size | Purpose |
|------|------|---------|
| `blueprint.css` | 32 KB | Full stylesheet |
| `plastex.js` | 1.7 KB | Proof toggle sync |
| `verso-code.js` | 15 KB | Hover tooltips, token binding |

**Configuration**: `runway.json` requires `assetsDir` field pointing to assets directory. Runway copies these to `output/assets/` during build.

```json
{
  "assetsDir": "/path/to/dress-blueprint-action/assets"
}
```

## manifest.json System

Runway generates `manifest.json` as a per-declaration index (replaces the old `nodes/` directory approach):

```json
{
  "nodes": [
    {
      "label": "thm:main",
      "declName": "MainTheorem",
      "module": "Project.Main",
      "file": "chapter1.html",
      "type": "theorem",
      "status": "proved"
    }
  ]
}
```

Used for:
- Node lookup from dependency graph modals
- Cross-page linking
- Homepage statistics

## Repository Details

### LeanArchitect

Lightweight metadata store. Only depends on `batteries`.

| File | Purpose |
|------|---------|
| `Architect/Basic.lean` | `Node`, `NodePart` structures |
| `Architect/Attribute.lean` | `@[blueprint]` attribute |
| `Architect/CollectUsed.lean` | Dependency inference |

### Dress

Two-phase: per-declaration during elaboration, library-level via Lake facets.

| File | Purpose |
|------|---------|
| `Capture/ElabRules.lean` | elab_rules hooks |
| `Capture/InfoTree.lean` | SubVerso highlighting capture |
| `Generate/Declaration.lean` | Per-declaration artifact writer |
| `HtmlRender.lean` | Verso HTML rendering |
| `Graph/*.lean` | Dependency graph generation |
| `Paths.lean` | Centralized path management |

### Runway

Pure Lean site generator using Verso patterns.

| File | Purpose |
|------|---------|
| `Main.lean` | CLI entry point |
| `Render.lean` | Side-by-side node rendering |
| `Theme.lean` | Page templates, sidebar |
| `Latex/Parser.lean` | LaTeX parsing |
| `Latex/ToHtml.lean` | LaTeX to HTML |
| `Config.lean` | Site config including `assetsDir` |
| `Assets.lean` | Asset copying |

### SubVerso

Fork of leanprover/subverso with optimizations.

| File | Purpose |
|------|---------|
| `Highlighting/Highlighted.lean` | Token.Kind, Highlighted types |
| `Highlighting/Code.lean` | Main highlighting logic |

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
  "assetsDir": "/path/to/dress-blueprint-action/assets"
}
```

| Field | Required | Purpose |
|-------|----------|---------|
| `blueprintTexPath` | Yes | LaTeX source defining structure |
| `assetsDir` | Yes | Directory with CSS/JS assets |

### lakefile.toml

```toml
[[require]]
name = "Dress"
git = "https://github.com/e-vergo/Dress"
rev = "main"
```

## Build Commands

```bash
# Full build via script
./scripts/build_blueprint.sh

# Manual steps
rm -rf .lake/build/dressed .lake/build/lib/YourProject
BLUEPRINT_DRESS=1 lake build
lake build :blueprint
lake exe runway build runway.json
python3 -m http.server -d .lake/build/runway 8000
```

## Feature Status

### Complete

- Side-by-side display with proof toggle sync
- Hierarchical sidebar navigation
- Numbered theorems (4.1.1 format)
- Multi-page chapter generation
- Homepage statistics
- Dependency graph with modals
- Hover tooltips with type signatures
- Token binding highlights
- External CSS/JS assets
- manifest.json node index

### Next Priority

- Dependency graph improvements (currently fragile)
- ar5iv-style paper generation

### Future

- Tactic state expansion
- doc-gen4 cross-linking
- Soundness checks (no sorry, connected graphs)
