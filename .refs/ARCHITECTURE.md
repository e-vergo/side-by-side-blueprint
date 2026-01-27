# Side-by-Side Blueprint Architecture

> **Prototype Status**: Alpha software with known bugs, slow workflows, and incomplete features.

## Overview

Seven repositories work together to produce formalization documentation:

| Repository | Purpose |
|------------|---------|
| **SubVerso** | Syntax highlighting extraction from Lean info trees |
| **LeanArchitect** | `@[blueprint]` attribute with 7 metadata options |
| **Dress** | Artifact generation + dependency graph layout + stats computation |
| **Runway** | Site generator with dashboard + rich modal rendering |
| **SBS-Test** | Minimal test project for iteration |
| **General_Crystallographic_Restriction** | Production example |
| **dress-blueprint-action** | GitHub Action + external CSS/JS assets + Runway CI support |

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
  - Computes stats (StatusCounts) and extracts project metadata
  - Writes manifest.json with precomputed stats and project notes
        |
        v
RUNWAY (post-build):
  - Parses blueprint.tex for chapter/section structure
  - Loads artifacts from .lake/build/dressed/
  - Loads manifest.json (precomputed stats, no recomputation)
  - Copies assets from assetsDir to output
  - Generates dashboard homepage + multi-page static site
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
├── dep_graph.html            # Full dependency graph with rich modals
├── chapter{N}.html           # Per-chapter pages
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

**Dress** generates `manifest.json` with precomputed statistics and project metadata (soundness: stats computed at source):

```json
{
  "stats": {
    "notReady": 1, "stated": 0, "ready": 1, "hasSorry": 2,
    "proven": 24, "fullyProven": 1, "mathlibReady": 2, "inMathlib": 1,
    "total": 32
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
- Node lookup from dependency graph modals
- Cross-page linking

## Repository Details

### LeanArchitect

Lightweight metadata store. Only depends on `batteries`.

| File | Purpose |
|------|---------|
| `Architect/Basic.lean` | `Node`, `NodePart`, `NodeStatus` structures with 7 metadata fields |
| `Architect/Attribute.lean` | `@[blueprint]` attribute with all options |
| `Architect/CollectUsed.lean` | Dependency inference |

**Attribute options**:

| Option | Type | Purpose |
|--------|------|---------|
| `displayName` | String | Custom node label in dependency graph |
| `keyTheorem` | Bool | Highlight in dashboard Key Theorems section |
| `message` | String | User notes (appears in Messages panel) |
| `priorityItem` | Bool | Flag for Attention column in dashboard |
| `blocked` | String | Reason for blockage (Attention column) |
| `potentialIssue` | String | Known concerns (Attention column) |
| `technicalDebt` | String | Cleanup notes (Attention column) |
| `misc` | String | Catch-all notes (Attention column) |

**Example usage**:
```lean
@[blueprint (keyTheorem := true, message := "Main result of paper")]
theorem main_theorem : ...

@[blueprint (priorityItem := true, blocked := "Waiting for upstream PR")]
lemma helper_lemma : ...

@[blueprint (displayName := "Square Non-negative")]
theorem square_nonneg : ...
```

### Dress

Two-phase: per-declaration during elaboration, library-level via Lake facets.

| File | Purpose |
|------|---------|
| `Capture/ElabRules.lean` | elab_rules hooks |
| `Capture/InfoTree.lean` | SubVerso highlighting capture |
| `Generate/Declaration.lean` | Per-declaration artifact writer |
| `HtmlRender.lean` | Verso HTML rendering |
| `Graph/Types.lean` | `Node`, `Edge`, `StatusCounts` types |
| `Graph/Build.lean` | Graph construction + stats computation |
| `Graph/Json.lean` | Manifest serialization with stats/metadata |
| `Graph/Layout.lean` | Sugiyama algorithm, visibility graph edge routing |
| `Graph/Render.lean` | SVG generation with Bezier curves |
| `Paths.lean` | Centralized path management |
| `Main.lean` | Writes manifest.json with precomputed stats |

### Runway

Pure Lean site generator using Verso patterns.

| File | Purpose |
|------|---------|
| `Main.lean` | CLI entry point, loads manifest.json |
| `Render.lean` | Side-by-side node rendering, dashboard, modal content |
| `Theme.lean` | Page templates, sidebar |
| `DepGraph.lean` | Dependency graph page with sidebar + modal wrappers |
| `Site.lean` | `NodeInfo` structure with `displayName` field |
| `Latex/Parser.lean` | LaTeX parsing |
| `Latex/ToHtml.lean` | LaTeX to HTML |
| `Config.lean` | Site config including `assetsDir` |
| `Assets.lean` | Asset copying |

**Dashboard rendering** (`Render.lean`):
- `renderDashboard`: Main 2x2 grid layout
- `renderProgress`: Stats panel with Completion/Attention columns
- `renderKeyTheorems`: Key theorems with side-by-side preview
- `renderMessages`: User notes section
- `renderProjectNotes`: Blocked/Issues/Debt/Misc sections

### SubVerso

Fork of leanprover/subverso with optimizations.

| File | Purpose |
|------|---------|
| `Highlighting/Highlighted.lean` | Token.Kind, Highlighted types |
| `Highlighting/Code.lean` | Main highlighting logic |

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

**8-status color model**: stated, ready, wip, proved, proved_incomplete, sorry, axiom, sorry_axiom. Dark backgrounds use white text.

### Edge Rendering

- **Solid lines**: Regular dependencies
- **Dashed lines**: Weak/optional dependencies
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

### CI/CD Integration

`dress-blueprint-action` supports Runway toolchain:
- `use-runway` input (boolean): Enable Runway instead of Python leanblueprint
- `runway-target` input (string): Lake target for Runway build (e.g., `SBSTest:runway`)
- Assembles output from `.lake/build/runway/` when Runway is enabled

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

### Complete (through Phase 7 + Dashboard Phases)

**Blueprint Core**:
- Side-by-side display with proof toggle sync
- Hierarchical sidebar navigation
- Numbered theorems (4.1.1 format)
- Multi-page chapter generation
- Hover tooltips with type signatures
- Token binding highlights
- External CSS/JS assets

**Dashboard Homepage**:
- 2x2 grid layout: Stats / Key Theorems / Messages / Project Notes
- Stats panel with Completion column (proven, fullyProven, mathlibReady, inMathlib)
- Stats panel with Attention column (notReady, stated, ready, hasSorry)
- Key Theorems section with side-by-side preview and status dots
- Messages panel showing user notes from `message` attribute
- Project Notes: blocked/potentialIssues/technicalDebt/misc sections
- All stats computed upstream in Dress (soundness guarantee)
- `displayName` propagation for cleaner labels

**Dependency Graph**:
- Sugiyama layout algorithm (top-to-bottom, median heuristic)
- Node shapes: Ellipse (theorems) / Box (definitions)
- Edge styles: Solid/dashed with Bezier curves
- 8-status color model with appropriate text contrast
- Static legend embedded in SVG
- D3-style pan/zoom (cursor-centered, no D3 dependency)
- Edge routing: Visibility graph + Dijkstra + Bezier fitting
- Node hover border thickening
- Combined Fit button with corrected X-axis centering
- **Sidebar navigation** (chapters, Blueprint Home, Dependency Graph, Paper, GitHub links)

**Rich Modals (Verso Integration)**:
- Click node to open modal with full side-by-side content
- Reuses `renderNode` for consistent display
- MathJax rendering in modal content
- Tippy.js hover tooltips in modals
- LaTeX proof toggle (plastex.js)
- Lean proof toggle (CSS checkbox pattern)
- "View in Blueprint" link

**`@[blueprint]` Attribute Options**:
- `displayName`: Custom graph labels
- `keyTheorem`: Dashboard highlighting
- `message`: User notes
- `priorityItem`: Attention flagging (replaces Priority enum)
- `blocked`, `potentialIssue`, `technicalDebt`, `misc`: Project notes

**CI/CD**:
- `dress-blueprint-action` supports Runway via `use-runway` input
- Multi-repo CI workflow (SBS-Test, Dress, Runway as siblings)
- GitHub Pages deployment
- Build script auto-exits after 5 minutes (for CI/testing)

### Next Priority

- ar5iv-style paper generation (MathJax, links to Lean code, no inline display)

### Future

- Tactic state expansion
- doc-gen4 cross-linking
- Soundness checks (no sorry, connected graphs)
