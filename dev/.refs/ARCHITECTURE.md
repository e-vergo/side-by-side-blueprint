# Side-by-Side Blueprint: System Architecture

Pure Lean toolchain for formalization documentation that displays formal proofs alongside LaTeX theorem statements. Generates interactive websites with dependency graphs, dashboards, and paper/PDF output.

## Monorepo Structure

```
Side-by-Side-Blueprint/
  forks/                    # Forked Lean 4 repositories
    subverso/               # Syntax highlighting (O(1) indexed lookups)
    verso/                  # Document framework (SBSBlueprint/VersoPaper genres)
    LeanArchitect/          # @[blueprint] attribute (8 metadata + 3 status)
  toolchain/                # Core toolchain components
    Dress/                  # Artifact generation, graph layout, validation
    Runway/                 # Site generator, dashboard, paper/PDF
    SBS-Test/               # Minimal test project (33 nodes)
    dress-blueprint-action/ # GitHub Action + CSS/JS assets
  showcase/                 # Production examples
    General_Crystallographic_Restriction/  # 57 nodes, paper generation
    PrimeNumberTheoremAnd/                 # 591 nodes, large-scale
  dev/                      # Development tooling
    scripts/                # sbs CLI and Python tooling
    .refs/                  # Detailed reference docs (this file)
    markdowns/              # Public documentation
    dev/storage/                # Archive (screenshots, metrics, rubrics)
    build-sbs-test.sh       # One-click SBS-Test build
    build-gcr.sh            # One-click GCR build
    build-pnt.sh            # One-click PNT build
```

## Component Overview

```
SubVerso (fork) -> LeanArchitect (fork) -> Dress -> Runway
      |                                      |
      +-> Verso (fork) <---------------------+
                            (genres use SubVerso for highlighting)
```

| Component | Location | Purpose | Key Responsibility |
|-----------|----------|---------|-------------------|
| **SubVerso** | `forks/subverso/` | Syntax highlighting | Extract semantic tokens, type signatures, proof states during elaboration with O(1) indexed lookups via InfoTable |
| **LeanArchitect** | `forks/LeanArchitect/` | Metadata attribute | Define `@[blueprint]` attribute with 8 metadata + 3 status options, dependency inference via `CollectUsed` |
| **Dress** | `toolchain/Dress/` | Artifact generation | Capture highlighting, render HTML/LaTeX with rainbow brackets, build dependency graph, validate, compute stats |
| **Runway** | `toolchain/Runway/` | Site generation | Parse LaTeX structure, render dashboard, generate paper/PDF, expand module references |
| **Verso** | `forks/verso/` | Document framework | Provide `SBSBlueprint` and `VersoPaper` genres with rainbow bracket rendering via `toHtmlRainbow` |
| **dress-blueprint-action** | `toolchain/dress-blueprint-action/` | CI/CD + Assets | GitHub Action (432 lines, 14 steps), CSS (4 files, 3,196 lines), JavaScript (2 files, 609 lines) |

### Consumer Projects

| Project | Location | Scale | Purpose |
|---------|----------|-------|---------|
| **SBS-Test** | `toolchain/SBS-Test/` | 33 nodes (32 Lean + 1 LaTeX) | Feature testing: all 6 status colors, XSS prevention, rainbow brackets (depths 1-10), module references, validation testing (cycles, disconnected components), visual compliance baseline |
| **General_Crystallographic_Restriction** | `showcase/General_Crystallographic_Restriction/` | 57 nodes | Production example with paper generation, complete formalization of the crystallographic restriction theorem |
| **PrimeNumberTheoremAnd** | `showcase/PrimeNumberTheoremAnd/` | 591 annotations | Large-scale integration (Tao's PNT project), exercises >100 node optimizations, validates connectivity checks, origin of Tao incident motivation |

---

## Build Pipeline

### Phase 1: Per-Declaration Capture (During Elaboration)

When Lean compiles with `BLUEPRINT_DRESS=1`:

1. Dress `elab_rules` in `Capture/ElabRules.lean` intercepts each `@[blueprint]` declaration
2. Standard elaboration runs first (the hook calls `elabCommandTopLevel`)
3. SubVerso extracts highlighting from info trees (93-99% of build time)
4. Code is split at `:=` boundary (signature vs proof body)
5. Artifacts written to `.lake/build/dressed/{Module/Path}/{sanitized-label}/`:
   - `decl.tex` - LaTeX source
   - `decl.html` - Syntax-highlighted HTML with rainbow brackets via `toHtmlRainbow`
   - `decl.json` - Metadata including SubVerso highlighting data
   - `decl.hovers.json` - Hover tooltip data (JSON mapping IDs to content)
   - `manifest.entry` - Label-to-path mapping

Info trees are ephemeral (only exist during elaboration), so highlighting must be captured immediately.

### Phase 2: Lake Facet Aggregation

After compilation, Lake facets aggregate per-declaration artifacts:

| Facet | Level | Output |
|-------|-------|--------|
| `dressed` | Module | `module.json` aggregating declarations |
| `blueprint` | Module | `module.tex` with `\input{}` directives |
| `blueprint` | Library | `library/{LibName}.tex` index with `\inputleanmodule` macro |
| `depGraph` | Library | `dep-graph.svg` and `dep-graph.json` |

### Phase 3: Manifest Generation

The `extract_blueprint graph` command performs:

1. Load modules and extract blueprint nodes from environment
2. Infer dependencies via `Node.inferUses` (traces actual Lean code)
3. Two-pass edge processing:
   - PASS 1: Register all labels and create nodes
   - PASS 2: Add all edges (back-edges work because targets exist)
4. Edge deduplication (first occurrence kept)
5. Validate graph (connectivity, cycle detection)
6. Compute status counts and upgrade nodes to `fullyProven`
7. Apply transitive reduction (skipped for >100 nodes)
8. Run Sugiyama layout for hierarchical visualization
9. Write `manifest.json`, `dep-graph.json`, `dep-graph.svg`

### Phase 4: Site Generation

Runway consumes artifacts to produce:

1. Parse `blueprint.tex` for chapter/section structure
2. Load `manifest.json` (precomputed stats, no recomputation)
3. Expand `\inputleanmodule{}` placeholders via module lookup
4. Generate dashboard homepage with 2x2 grid (Stats, Key Theorems, Messages, Project Notes)
5. Generate chapter pages with side-by-side displays
6. Generate dependency graph page with pan/zoom and modals
7. Optionally: Generate `paper_tex.html`, `paper.pdf`, `pdf_tex.html`
8. Optionally: Generate Verso documents (`blueprint_verso.html`, `paper_verso.html`)
9. Copy CSS/JS assets from `assetsDir`

---

## Data Flow

```
@[blueprint "label"] theorem foo ...
        |
        v
+-------------------+
|   LeanArchitect   |  Stores Node in environment extension
+-------------------+
        |
        v
+-------------------+
|      Dress        |  Captures during elaboration:
+-------------------+  - SubVerso highlighting (O(1) indexed lookups)
        |              - Rainbow bracket wrapping via Verso
        |              - Renders HTML with hover data
        |              - Writes per-declaration artifacts
        v
+-------------------+
|   Lake Facets     |  Aggregates artifacts:
+-------------------+  - Builds dependency graph
        |              - Computes stats, validates
        |              - Infers dependencies via Node.inferUses
        |              - Two-pass edge processing
        v
+-------------------+
|     Runway        |  Generates site:
+-------------------+  - Parses LaTeX structure
        |              - Loads precomputed manifest
        |              - Renders dashboard + pages
        |              - Generates paper/PDF
        v
    HTML Site
```

---

## Node Status Model

6-status color model for tracking formalization progress:

| Status | Color | Hex | Source |
|--------|-------|-----|--------|
| `notReady` | Sandy Brown | #F4A460 | Default or manual `(notReady := true)` |
| `ready` | Light Sea Green | #20B2AA | Manual `(ready := true)` |
| `sorry` | Dark Red | #8B0000 | Auto-detected: proof contains `sorryAx` |
| `proven` | Light Green | #90EE90 | Auto-detected: complete proof |
| `fullyProven` | Forest Green | #228B22 | Auto-computed: all ancestors proven |
| `mathlibReady` | Light Blue | #87CEEB | Manual `(mathlibReady := true)` |

**Priority order** (manual flags win):
1. `mathlibReady` (manual)
2. `ready` (manual)
3. `notReady` (manual, if explicitly set)
4. `fullyProven` (auto-computed)
5. `sorry` (auto-detected)
6. `proven` (auto-detected)
7. `notReady` (default)

**Color source of truth:** Lean code (`Dress/Graph/Svg.lean`) defines the canonical hex values. CSS variables in `common.css` must match these exactly.

### `fullyProven` Algorithm

Located in `Dress/Graph/Build.lean`:

- O(V+E) complexity with memoization
- Uses iterative worklist algorithm (not recursion)
- A node is `fullyProven` if: it is `proven` AND all ancestors are `proven` or `fullyProven`
- Detects and handles cycles (marks as incomplete)
- Runs as post-processing after initial status assignment

### Node Shapes

| Shape | Used For |
|-------|----------|
| Rectangle (box) | def, abbrev, structure, class, instance |
| Ellipse | theorem, lemma, proposition, corollary, example |

### Edge Styles

| Style | Meaning |
|-------|---------|
| Solid | Proof dependency (used in proof body) |
| Dashed | Statement dependency (used in signature) |

---

## Dependency Graph Layout

### Sugiyama Algorithm (`Dress/Graph/Layout.lean`)

~1500 lines implementing Sugiyama-style hierarchical layout.

**Acyclic Transformation**:
- DFS identifies back-edges (edges creating cycles)
- Back-edges reversed one at a time (Graphviz approach)
- Safety bound: maximum iterations = `graph.edges.size + 1`
- Reversed edges marked with `isReversed` flag for correct arrow direction
- `reverseBezierPoints` handles control point reversal

**Layer Assignment**:
- Longest-path algorithm assigns nodes to vertical layers
- Nodes with no incoming edges placed at layer 0
- Each node placed one layer above its highest dependency

**Crossing Reduction**:
- Median heuristic minimizes edge crossings
- Alternate forward and backward passes
- Transpose pass swaps adjacent nodes if it reduces crossings

**Coordinate Assignment**:
- Barycenter-based positioning with refinement
- Iterative refinement pulls nodes toward median of connected neighbors
- Overlap resolution prevents node collisions

### Edge Routing

For small graphs (<=100 nodes):
1. Visibility graph: collect vertices at obstacle corners (rectangles) or octants (ellipses)
2. Liang-Barsky for rectangle intersection, parametric approach for ellipse intersection
3. Dijkstra's algorithm (O(V^2)): find shortest path around obstacles
4. Catmull-Rom interpolation: convert polyline to smooth cubic Bezier curves
5. Clip endpoints to node boundaries based on shape

For large graphs (>100 nodes):
- Simplified direct Bezier curves with offset-based control points
- Avoids O(V^2) per-edge visibility graph construction

### Coordinate Normalization

Final coordinates are normalized so content starts at (padding, padding) with viewBox origin at (0,0):

```lean
let minX := nodes.foldl (fun acc n => min acc n.x) Float.inf
let minY := nodes.foldl (fun acc n => min acc n.y) Float.inf
let offsetX := padding - minX
let offsetY := padding - minY
-- All nodes shifted by (offsetX, offsetY)
```

This normalization is required for proper SVG centering because JavaScript's `getBBox()` expects the viewBox origin to be (0,0).

---

## Validation Checks

### Connectivity (`findComponents`)

BFS-based component detection with O(V+E) complexity:
- Treats graph as undirected for connectivity purposes
- Single component = fully connected graph
- Multiple components may indicate missing dependencies (Tao-style errors)

### Cycle Detection (`detectCycles`)

DFS with gray/black coloring (O(V+E) complexity):
- White nodes: unvisited
- Gray nodes: in current DFS path
- Black nodes: fully processed
- Back-edge to gray node = cycle
- Returns array of detected cycles

**Results in manifest.json**:
```json
{
  "checkResults": {
    "isConnected": true,
    "numComponents": 1,
    "componentSizes": [32],
    "cycles": []
  }
}
```

---

## Performance Characteristics

### SubVerso Optimization

O(1) indexed lookups via `InfoTable`:

| Field | Purpose | Complexity |
|-------|---------|------------|
| `infoByExactPos` | HashMap for exact syntax position (start, end) | O(1) |
| `termInfoByName` | HashMap for const/fvar by name | O(1) |
| `nameSuffixIndex` | HashMap for suffix-based lookups | O(1) |
| `allInfoSorted` | Sorted array for containment queries | O(n) worst |

Additional caches in `HighlightState`:
- `identKindCache`: Memoizes identifier classification by (position, name)
- `signatureCache`: Memoizes pretty-printed type signatures by constant name
- `hasTacticCache` / `childHasTacticCache`: Memoizes tactic info searches

### Build Time Breakdown

| Operation | Time | Percentage |
|-----------|------|------------|
| SubVerso highlighting | 800-6500ms | 93-99% |
| TeX/HTML generation | <30ms | <1% |

SubVerso highlighting dominates. Cannot be deferred because info trees are ephemeral.

### Large Graph Optimizations

Triggered automatically at >100 nodes:

| Optimization | Normal | >100 nodes | Rationale |
|--------------|--------|------------|-----------|
| Barycenter iterations | Unlimited | Max 2 | O(n) per iteration |
| Transpose heuristic | Yes | Skipped | O(n^2) adjacent swaps |
| Visibility graph routing | Yes | Skipped | O(n^2) graph construction |
| Transitive reduction | O(n^3) Floyd-Warshall | Skipped | Multi-hour build times |

### Expected Build Times

| Project | Nodes | Layout Time | Total Build |
|---------|-------|-------------|-------------|
| SBS-Test | 33 | <1s | ~2 min |
| GCR | 57 | ~2s | ~5 min |
| PNT | 591 | ~15s | ~20 min |

### String Performance

`Parser.lean` uses Array-based building (O(n)) instead of repeated `++` (O(n^2)).

---

## Manifest Schema

The `manifest.json` file contains precomputed data consumed by Runway:

```json
{
  "stats": {
    "notReady": 2,
    "ready": 3,
    "hasSorry": 2,
    "proven": 5,
    "fullyProven": 8,
    "mathlibReady": 1,
    "total": 21
  },
  "keyDeclarations": ["thm:main", "thm:secondary"],
  "messages": [
    {"id": "thm:main", "label": "Main Theorem", "message": "Central result"}
  ],
  "projectNotes": {
    "priority": [],
    "blocked": [],
    "potentialIssues": [],
    "technicalDebt": [],
    "misc": []
  },
  "nodes": {"thm:main": "#thm:main"},
  "checks": {
    "isConnected": true,
    "numComponents": 1,
    "componentSizes": [21],
    "cycles": []
  }
}
```

Statistics computed upstream in Dress provide a soundness guarantee: displayed stats match actual graph state.

---

## Key Implementation Details

### ID Normalization

Node IDs with colons (`thm:main`) converted to hyphens (`thm-main`) for:
- Modal element IDs
- CSS selectors
- JavaScript querySelector calls

### Two-Pass Edge Processing (`Graph/Build.lean`)

- PASS 1: Register all labels and create nodes
- PASS 2: Add all edges (back-edges work because targets exist)
- Edge deduplication: keeps first occurrence of each from/to pair

### Dependency Inference

`Node.inferUses` traces actual Lean code dependencies:
- Statement uses -> dashed edges
- Proof uses -> solid edges
- Replaces manual `\uses{}` annotations with real dependency tracing

### Rainbow Bracket Highlighting

Verso's `toHtmlRainbow` wraps brackets with depth-colored spans:
- Single global depth counter shared across all bracket types (`()`, `[]`, `{}`)
- Cycles through 6 colors (`lean-bracket-1` through `lean-bracket-6`)
- Opening brackets increment depth, closing brackets decrement
- Brackets inside string literals and doc comments are not colored
- CSS in `common.css` provides light and dark mode colors

### Module Reference Support

`\inputleanmodule{ModuleName}` in LaTeX expands to all nodes from that module:
1. `buildModuleLookup` creates map from module name to nodes
2. `replaceModulePlaceholders` substitutes placeholder divs with rendered content
3. Module names must be fully qualified (e.g., `PrimeNumberTheoremAnd.Wiener`)

### Paper Metadata Extraction

`Paper.lean` extracts from `paper.tex`:
- `\title{...}` -> paper title (fallback to config.title)
- `\author{...}` split on `\and` -> authors array
- `\begin{abstract}...\end{abstract}` -> abstract text

### Manual ToExpr Instance

`Node` in LeanArchitect uses manual `ToExpr` instance. Derived `ToExpr` for structures with default field values doesn't correctly serialize all fields through environment extensions.

### Backwards Compatibility

JSON parsing handles legacy status values:
- `"stated"` maps to `.notReady`
- `"inMathlib"` maps to `.mathlibReady`

---

## CI/CD Architecture

### Design Philosophy

- **Manual triggers only**: `workflow_dispatch` - user controls deployments
- **Simplified workflows**: ~30 lines per project
- **Centralized complexity**: `dress-blueprint-action` (432 lines, 14 steps)
- **No GitHub Actions mathlib cache**: relies on mathlib server (`lake exe cache get`)

### dress-blueprint-action Steps

1. Free disk space (removes Android SDK, .NET, Haskell)
2. Checkout toolchain repos (SubVerso, LeanArchitect, Dress, Runway, assets)
3. Install elan
4. Install Lean toolchain
5. Install LaTeX (texlive packages)
6. Fetch mathlib cache
7. Build toolchain in dependency order: SubVerso -> LeanArchitect -> Dress -> Runway
8. Build project with Dress artifact generation
9. Build `:blueprint` Lake facet
10. Generate dependency graph and manifest
11. Generate site with Runway
12. Generate paper (if configured)
13. Handle DocGen4 (skip/docs-static/generate)
14. Upload Pages artifact

### Action Inputs

| Input | Default | Purpose |
|-------|---------|---------|
| `project-directory` | `.` | Directory containing lakefile.toml and runway.json |
| `lean-version` | (auto) | Override Lean version |
| `docgen4-mode` | `skip` | DocGen4 mode: `skip`, `docs-static`, or `generate` |
| `deploy-pages` | `true` | Upload artifact for GitHub Pages |

### DocGen4 Mode Options

| Mode | Behavior |
|------|----------|
| `skip` | No DocGen4 documentation |
| `docs-static` | Download pre-generated docs from `docs-static` branch |
| `generate` | Run `lake -R -Kenv=dev build +:docs` (slow, ~1 hour for mathlib projects) |

### docs-static Branch Pattern

For projects with pre-generated DocGen4 documentation:

1. Generate docs locally: `lake -R -Kenv=dev build Module:docs`
2. Create orphan branch: `git checkout --orphan docs-static`
3. Commit docs to branch root
4. CI uses `docgen4-mode: docs-static` to download instead of regenerating

---

## Configuration Files

### lakefile.toml

```toml
[[require]]
name = "Dress"
git = "https://github.com/e-vergo/Dress"
rev = "main"

# For mathlib projects
[[require]]
name = "mathlib"
git = "https://github.com/leanprover-community/mathlib4.git"
rev = "v4.27.0"

# For Verso documents (optional)
[[require]]
name = "verso"
git = "https://github.com/e-vergo/verso.git"
rev = "main"
```

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

| Field | Required | Purpose |
|-------|----------|---------|
| `title` | No | Site title (default: "Blueprint") |
| `projectName` | Yes | Lean project name (must match lakefile) |
| `blueprintTexPath` | Yes | Path to blueprint.tex |
| `assetsDir` | Yes | Directory containing CSS/JS assets |
| `githubUrl` | No | Repository URL for links |
| `baseUrl` | No | Base URL for site links (default: "/") |
| `paperTexPath` | No | Path to paper.tex (enables paper generation) |
| `docgen4Url` | No | URL to DocGen4 documentation |
| `pdfCompiler` | No | LaTeX compiler: tectonic, pdflatex, xelatex, lualatex |
| `runwayDir` | No | Alternative: directory containing `src/blueprint.tex` and `src/paper.tex` |

---

## Output Structure

### Dressed Artifacts

```
.lake/build/dressed/
  {Module/Path}/
    {label}/
      decl.tex
      decl.html
      decl.json
      decl.hovers.json
      manifest.entry
  library/
    {LibName}.tex
  dep-graph.json
  dep-graph.svg
  manifest.json
```

### Runway Output

```
.lake/build/runway/
  index.html              # Dashboard homepage
  chapter-*.html          # Chapter pages
  dep_graph.html          # Dependency graph page
  paper_tex.html          # Paper (if configured)
  pdf_tex.html            # PDF viewer (if configured)
  paper.pdf               # PDF (if configured)
  blueprint_verso.html    # Verso Blueprint (if Blueprint.lean exists)
  paper_verso.html        # Verso Paper (if Paper.lean exists)
  manifest.json           # Copied from Dress
  assets/
    blueprint.css
    common.css
    dep_graph.css
    paper.css
    plastex.js
    verso-code.js
```

---

## CSS Architecture

### File Organization

| File | Lines | Purpose |
|------|-------|---------|
| `common.css` | 1,104 | Design system: CSS variables, status dots, Lean syntax highlighting, Tippy tooltips, modals, dark mode toggle, rainbow brackets |
| `blueprint.css` | 1,283 | Blueprint pages: plasTeX base styles, sidebar, chapter layout, dashboard grid, side-by-side displays, zebra striping |
| `paper.css` | 271 | Paper pages: ar5iv-style academic layout, verification badges, print styles |
| `dep_graph.css` | 538 | Dependency graph: pan/zoom viewport, toolbar, legend, SVG node styling |

### Design System Variables

`:root` in `common.css` defines:
- Grayscale palette
- Semantic mappings (backgrounds, text, borders, links)
- Tooltip themes (warning, error, info)
- Graph and legend colors
- Status colors (must match Lean definitions)

### Status Dot Sizes

| Class | Size | Usage |
|-------|------|-------|
| `.status-dot` | 8px | Base size |
| `.header-status-dot` | 10px | Blueprint headers |
| `.paper-status-dot` | 10px | Paper headers |
| `.modal-status-dot` | 12px | Dependency graph modals |

### Rainbow Bracket Colors

`.lean-bracket-1` through `.lean-bracket-6` with light and dark mode variants:

| Class | Light Mode | Dark Mode |
|-------|------------|-----------|
| `lean-bracket-1` | #d000ff | #e040ff |
| `lean-bracket-2` | #5126ff | #7156ff |
| `lean-bracket-3` | #0184BC | #01a4dc |
| `lean-bracket-4` | #4078F2 | #5098ff |
| `lean-bracket-5` | #50A14F | #70c16f |
| `lean-bracket-6` | #E45649 | #f47669 |

### Dark Mode

- Controlled via `html[data-theme="dark"]`
- Toggle persists to localStorage (`sbs-theme`)
- Defaults to light mode
- Toggle via `window.toggleSbsTheme()`

### Zebra Striping

Light mode: `#fff` / `#ebebeb`
Dark mode: `#1a1a1a` / `#252525`

---

## JavaScript Functionality

**Total JavaScript: 609 lines** (verso-code.js: 490, plastex.js: 119)

### verso-code.js (490 lines)

| Function | Purpose |
|----------|---------|
| Token binding | Highlights all occurrences of a variable on hover |
| Tippy.js initialization | Type signatures, docstrings, tactic states |
| Proof sync | Syncs Lean proof body visibility with LaTeX toggle |
| Pan/zoom | Mouse wheel zoom (centered on cursor), pointer drag panning |
| `fitToWindow()` | Fits graph to viewport using `getBBox()` |
| `onModalOpen()` | Initializes MathJax and Tippy in modal, positions blueprint link |
| Node click handling | Opens corresponding modal when graph node clicked |

Tippy themes: `lean`, `warning`, `error`, `info`, `tactic`

Pan/zoom uses pointer events:
- `pointerdown` initiates drag (captures pointer for reliable tracking)
- `pointermove` updates translation
- `pointerup`/`pointercancel` ends drag
- Scale clamped to 0.1-5x range

### plastex.js (119 lines)

| Function | Purpose |
|----------|---------|
| `toggleSbsTheme()` | Toggles dark/light mode, persists to localStorage |
| TOC toggle | Mobile sidebar show/hide via `#toc-toggle` |
| Proof toggle | Expands/collapses LaTeX proofs with jQuery animation, syncs Lean proof visibility |

---

## Sidebar Architecture

The sidebar is fully static. All chapters and sections are rendered as plain HTML links at build time.

- No JavaScript-driven expand/collapse
- Active section highlighting via CSS classes (`.active`)
- Full-width highlight achieved via `::before` pseudo-elements

### Full-Width Highlight Pattern

```css
.sidebar-item {
  position: relative;
}

.sidebar-item.active::before {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  left: -0.8rem;
  right: -1rem;
  background-color: var(--active-bg);
  z-index: -1;
}
```

This pattern bypasses `overflow-x: hidden` on parent elements.

---

## Quality Validation Framework

### 8-Dimensional Test Suite

The toolchain includes an automated quality scoring system tracking 8 dimensions:

**Deterministic Tests (50% weight):**

| Test | Name | Weight | Description |
|------|------|--------|-------------|
| T1 | CLI Execution | 10% | All sbs CLI commands execute without error |
| T2 | Ledger Population | 10% | Unified ledger fields are populated correctly |
| T5 | Status Color Match | 15% | 6 status colors match between Lean and CSS |
| T6 | CSS Variable Coverage | 15% | Hardcoded colors use CSS variables |

**Heuristic Tests (50% weight):**

| Test | Name | Weight | Description |
|------|------|--------|-------------|
| T3 | Dashboard Clarity | 10% | Dashboard answers 3 key questions at a glance |
| T4 | Toggle Discoverability | 10% | Proof toggles and theme switches are findable |
| T7 | Jarring-Free Check | 15% | No visually jarring elements (AI vision) |
| T8 | Professional Score | 15% | Overall polish and alignment (AI vision) |

**Score Calculation:**
```
quality_score = Σ(test_score × weight)
```

**Score History:**
| Date | Score | Changes |
|------|-------|---------|
| 2026-02-01 | 87.21 | Baseline measurement |
| 2026-02-01 | 89.69 | Fixed 20 CSS violations, removed dead ledger fields |
| 2026-02-01 | 91.77 | Excluded syntax colors from T6, improved toggle styling |

### Design Validators

Located in `scripts/sbs/tests/validators/design/`:

| Validator | Purpose |
|-----------|---------|
| `color_match.py` | T5: Verifies status colors match between Lean and CSS |
| `variable_coverage.py` | T6: Measures CSS variable coverage vs hardcoded colors |
| `dashboard_clarity.py` | T3: AI-based dashboard question answerability check |
| `toggle_discoverability.py` | T4: AI-based toggle findability scoring |
| `jarring_check.py` | T7: AI detection of jarring design elements |
| `professional_score.py` | T8: AI-based professional polish assessment |
| `css_parser.py` | Shared CSS parsing utilities |

### Running Quality Tests

```bash
# From the monorepo root, use convenience scripts
./dev/build-sbs-test.sh   # SBS-Test (~2 min)
./dev/build-gcr.sh        # GCR (~5 min)
./dev/build-pnt.sh        # PNT (~20 min)

# Or from project directories
cd /Users/eric/GitHub/Side-By-Side-Blueprint/toolchain/SBS-Test
python ../../dev/scripts/build.py

# Run all deterministic tests
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
/opt/homebrew/bin/pytest sbs/tests/ -v

# Run specific validator
python -c "
from pathlib import Path
from sbs.validators import ValidationContext, discover_validators, registry
discover_validators()
validator = registry.get('ledger-health')
ctx = ValidationContext(project='SBSTest', project_root=Path('.'), commit='test')
result = validator.validate(ctx)
print(result.metrics)
"
```

---

## Visual Testing Infrastructure

### Screenshot Capture (`sbs capture`)

Captures 8 pages from a running server:

| Page | Path | Description |
|------|------|-------------|
| dashboard | `index.html` | Dashboard homepage |
| dep_graph | `dep_graph.html` | Dependency graph |
| paper_tex | `paper_tex.html` | Paper [TeX] |
| pdf_tex | `pdf_tex.html` | PDF [TeX] |
| paper_verso | `paper_verso.html` | Paper [Verso] |
| pdf_verso | `pdf_verso.html` | PDF [Verso] |
| blueprint_verso | `blueprint_verso.html` | Blueprint [Verso] |
| chapter | (auto-detected) | First chapter with content |

Pages that don't exist (HTTP 404) are skipped without error.

With `--interactive` flag, also captures:
- Theme toggles (light/dark)
- Zoom controls
- Node clicks
- Proof toggles

### Visual Compliance Validation

```bash
python3 -m sbs compliance --project SBSTest
```

The compliance system:
- Tracks pass/fail status per page in persistent ledger
- Detects repo changes and revalidates affected pages
- Uses AI vision analysis against criteria
- Loops until 100% compliance achieved

Key files:
- `dev/storage/compliance_ledger.json` - Persistent status
- `dev/storage/COMPLIANCE_STATUS.md` - Human-readable report
- `scripts/sbs/tests/compliance/criteria.py` - Compliance criteria per page

### Image Storage

```
dev/storage/
  {project}/
    latest/           # Current capture (overwritten each run)
      capture.json    # Metadata: timestamp, commit, viewport, page status
      dashboard.png
      dep_graph.png
      *_interactive.png
      ...
    dev/storage/          # Timestamped history
      {timestamp}/
```

### Standard Workflow

1. **Build:** `python ../scripts/build.py` (commits, pushes, builds)
2. **Capture:** `python3 -m sbs capture --interactive` (creates baseline)
3. **Make changes** to CSS/JS/Lean/templates
4. **Rebuild:** `python ../scripts/build.py`
5. **Capture:** `python3 -m sbs capture --interactive` (archives previous)
6. **Validate:** `python3 -m sbs compliance` (AI vision analysis)

---

## Archive System

The archive system provides comprehensive build tracking, iCloud sync, session archiving, and custom rubrics.

**Canonical reference:** [`dev/storage/README.md`](../storage/README.md) is the central tooling hub. All repository READMEs link there for CLI commands, validation, and development workflows.

### Directory Structure

```
dev/storage/
  unified_ledger.json     # Build metrics and timing (single source of truth)
  lifetime_stats.json     # Cross-run aggregates
  archive_index.json      # Entry index with tags
  compliance_ledger.json  # Compliance tracking
  rubrics/                # Quality rubrics
    index.json            # Rubric registry
    {id}.json             # Rubric definitions
    {id}.md               # Human-readable (auto-generated)
    {id}_eval_*.json      # Evaluation results
  charts/                 # Generated visualizations
    loc_trends.png
    timing_trends.png
    activity_heatmap.png
  chat_summaries/         # Session summaries
    {entry_id}.md
  SBSTest/                # Per-project screenshots
    latest/
    dev/storage/{timestamp}/
  GCR/
    ...
```

### Rubric System

Custom quality rubrics enable structured improvement workflows. Created during `/execute --grab-bag` sessions.

```bash
sbs rubric create --name "my-rubric"    # Create empty rubric
sbs rubric list                          # List all rubrics
sbs rubric show <id>                     # Display rubric
sbs rubric evaluate <id> --project X     # Evaluate project
```

### Visualizations

Charts generated from `unified_ledger.json`:
- **LOC Trends**: Lines of code by language over time
- **Timing Trends**: Build phase durations (stacked area)
- **Activity Heatmap**: Files changed per repo per build

### iCloud Sync

Archive data syncs to `~/Library/Mobile Documents/com~apple~CloudDocs/SBS_dev/storage/`:
- Non-blocking (failures logged but don't break builds)
- Syncs: unified ledger, archive index, charts, screenshots, rubrics
- Manual sync: `sbs archive sync`

---

## Validator Plugin Architecture

Located in `scripts/sbs/tests/validators/`, this system provides pluggable validation.

### Registered Validators

| Name | Category | Purpose |
|------|----------|---------|
| `visual-compliance` | visual | AI vision validation of screenshots |
| `timing` | timing | Build phase timing metrics |
| `git-metrics` | git | Commit/diff tracking |
| `code-stats` | code | LOC and file counts |
| `ledger-health` | code | Unified ledger field population (T2) |
| `rubric` | code | Custom rubric evaluation |

### Design Validators (`scripts/sbs/tests/validators/design/`)

| Name | Test ID | Purpose |
|------|---------|---------|
| `color_match.py` | T5 | Status color matching (Lean vs CSS) |
| `variable_coverage.py` | T6 | CSS variable coverage analysis |
| `dashboard_clarity.py` | T3 | AI dashboard clarity assessment |
| `toggle_discoverability.py` | T4 | AI toggle findability scoring |
| `jarring_check.py` | T7 | AI jarring element detection |
| `professional_score.py` | T8 | AI professional polish assessment |
| `css_parser.py` | - | Shared CSS parsing utilities |

### Protocol

```python
class Validator(Protocol):
    name: str
    category: str  # visual, timing, code, git

    def validate(self, context: ValidationContext) -> ValidatorResult: ...
```

### Integration with Build

Build.py automatically:
1. Records phase timings
2. Captures git state before/after
3. Saves metrics to unified ledger

---

## Known Limitations

### Verso LaTeX Export

Verso's LaTeX export functionality is not yet implemented. The `pdf_verso` page type is disabled. Paper/PDF generation uses TeX sources directly via `paper_tex` and `pdf_tex`.

### Dashboard Layout

The dashboard displays a single-column layout without the chapter panel sidebar. This is intentional - the dashboard is not a blueprint chapter page. Controlled by `isBlueprintPage` returning `false` when `currentSlug == none`.
