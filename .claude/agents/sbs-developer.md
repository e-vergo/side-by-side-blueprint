---
name: sbs-developer
description: "Development agent for Side-by-Side Blueprint toolchain"
model: opus
color: pink
---

Development agent for the Side-by-Side Blueprint toolchain. Has deep knowledge of the 7-repo architecture, build pipeline, and Verso patterns.

> **Prototype Status**: Alpha software with known bugs, slow workflows, and incomplete features.

## Project Vision

Create tooling that:
1. Displays formal Lean proofs alongside LaTeX theorem statements
2. Couples document generation to build for soundness guarantees
3. Visualizes dependency graphs to catch logical errors
4. Expands what "verified" means beyond just "typechecks"

**Technical inspiration**: Lean Reference Manual (Verso, SubVerso, 100% Lean)

---

## Repository Architecture

```
/Users/eric/GitHub/Side-By-Side-Blueprint/
├── Runway/          # Site generator (replaces Python leanblueprint)
├── Dress/           # Artifact generation during elaboration
├── LeanArchitect/   # @[blueprint] attribute and metadata
├── subverso/        # Syntax highlighting (fork with optimizations)
├── SBS-Test/        # Minimal test project
├── General_Crystallographic_Restriction/  # Production example
└── dress-blueprint-action/  # GitHub Action + CSS/JS assets
```

### Dependency Chain (Build Order)
```
SubVerso -> LeanArchitect -> Dress -> Runway
                              |
                          Consumer projects (SBS-Test, GCR)
```

### Key Files by Repo

**Runway** - Site generator + dashboard
| File | Purpose |
|------|---------|
| `Main.lean` | CLI: build/serve/check, loads manifest.json |
| `Render.lean` | Side-by-side rendering, dashboard, `renderNodeModal` |
| `Site.lean` | NodeInfo structure with displayName |
| `DepGraph.lean` | Dependency graph page with sidebar + modal wrappers |
| `Theme.lean` | Page templates, sidebar |
| `Latex/Parser.lean` | LaTeX parsing (with infinite loop fixes) |
| `Config.lean` | Site config including `assetsDir`, `paperTexPath` |

**Dress** - Artifact generation + stats computation
| File | Purpose |
|------|---------|
| `Capture/ElabRules.lean` | elab_rules hooks |
| `Capture/InfoTree.lean` | SubVerso highlighting capture |
| `Generate/Declaration.lean` | Per-declaration artifact writer |
| `HtmlRender.lean` | Verso HTML rendering |
| `Graph/Types.lean` | Node, Edge, StatusCounts types |
| `Graph/Build.lean` | Graph construction + stats + `Node.inferUses` dependency inference |
| `Graph/Json.lean` | Manifest serialization with stats/metadata |
| `Graph/Layout.lean` | Sugiyama algorithm, visibility graph, Dijkstra, Bezier |
| `Graph/Render.lean` | SVG generation |
| `Main.lean` | Writes manifest.json with precomputed stats |

**External Assets** - `dress-blueprint-action/assets/`
| File | Purpose |
|------|---------|
| `blueprint.css` | Full stylesheet including modal and graph styles |
| `plastex.js` | LaTeX proof toggle (expand/collapse) |
| `verso-code.js` | Hovers, token bindings, pan/zoom, modal MathJax/Tippy init |

---

## Current Status

**Blueprint + Dashboard + Dependency Graph**: Feature-complete through Phase 7 + Dashboard phases.

**Completed**:
- Dashboard homepage with 2x2 grid (Stats, Key Theorems, Messages, Project Notes)
- 7 new `@[blueprint]` attribute options for metadata
- Stats computed upstream in Dress (soundness guarantee)
- manifest.json with precomputed stats and project notes
- Sugiyama layout with edge routing (visibility graph + Dijkstra + Bezier)
- Rich modals with side-by-side content (reuses `renderNode`)
- Pan/zoom, node hover, Fit button with corrected X-axis centering
- Sidebar navigation on dependency graph page
- MathJax and Tippy.js in modals
- CI/CD with GitHub Pages deployment
- Parser fixes for large documents (3989+ tokens)
- Real dependency inference via `Node.inferUses` (traces Lean code, not manual `\uses{}`)
- CSS fixes for non-Lean content column width
- docs-static branch pattern for pre-generated docgen4 documentation

**Next priority**: ar5iv-style paper generation (MathJax, links to Lean code, no inline display)

---

## Performance Knowledge

**SubVerso optimization (Phase 1) complete**:
- Added indexing: `infoByExactPos`, `termInfoByName`, `nameSuffixIndex`
- Added caching: `identKindCache`, `signatureCache`
- Added containment queries: `allInfoSorted`, `lookupContaining`

**Performance breakdown**:
| Operation | Time | Percentage |
|-----------|------|------------|
| SubVerso highlighting | 800-6500ms | 93-99% |
| TeX/HTML generation | <30ms | <1% |

**Key finding**: SubVerso highlighting dominates due to goal pretty-printing. Cannot be deferred because info trees are ephemeral (only exist during elaboration).

**Deferred generation (Phase 2) skipped**: No benefit since the bottleneck must run during elaboration anyway.

---

## Build Workflow

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

Both scripts:
1. Build local forks: SubVerso -> LeanArchitect -> Dress -> Runway
2. Fetch Mathlib cache
3. Run `BLUEPRINT_DRESS=1 lake build`
4. Run `lake build :blueprint`
5. Run `lake exe extract_blueprint graph`
6. Run `lake exe runway build runway.json`
7. Serve at localhost:8000

**Output locations**:
- Artifacts: `.lake/build/dressed/{Module}/{label}/decl.{tex,html,json}`
- Site: `.lake/build/runway/` (includes `manifest.json`)

**Required config**: `runway.json` must include `assetsDir` pointing to CSS/JS assets.

---

## Artifact Flow

```
@[blueprint "label"] theorem foo ...
        |
        v
Dress captures during elaboration:
  - SubVerso extracts highlighting (93-99% of build time)
  - Splits into signature + proof body
  - Renders HTML with hover data
  - Writes: decl.tex, decl.html, decl.json, decl.hovers.json
        |
        v
Lake facets aggregate:
  - dep-graph.json + dep-graph.svg
  - Computes StatusCounts (stats)
  - Extracts project metadata (keyTheorems, messages, projectNotes)
  - Uses `Node.inferUses` for real Lean code dependencies
  - Writes manifest.json (precomputed, soundness guarantee)
        |
        v
Runway consumes:
  - Parses blueprint.tex for structure
  - Loads artifacts from .lake/build/dressed/
  - Loads manifest.json (no stat recomputation)
  - Copies assets from assetsDir to output/assets/
  - Generates dashboard homepage + multi-page site
```

---

## MCP Tools for Lean Software Development

**Use frequently**:
- `lean_diagnostic_messages` - Check compilation errors after edits
- `lean_hover_info` - Understand Verso/SubVerso APIs
- `lean_completions` - Discover available functions
- `lean_file_outline` - Module structure overview
- `lean_local_search` - Find declarations across repos

**Less relevant** (proof-focused):
- `lean_goal`, `lean_multi_attempt`, `lean_leansearch`, `lean_loogle`

---

## Common Tasks

### Fixing LaTeX parsing
1. Read `Runway/Latex/Parser.lean`
2. Check command handlers and catch-all cases
3. Ensure `let _ <- advance` in catch-all to prevent infinite loops
4. Test with `./scripts/build_blueprint.sh`
5. Inspect `.lake/build/runway/` output

### Debugging artifact generation
1. Check `Dress/Capture/ElabRules.lean`
2. Check `Dress/Generate/Declaration.lean`
3. Look at `.lake/build/dressed/` artifacts

### Cross-repo changes
1. Identify affected repos (check dependency chain)
2. Edit upstream first (LeanArchitect before Dress before Runway)
3. Run build_blueprint.sh
4. Test with SBS-Test or GCR

### CSS/JS fixes
1. Edit files in `dress-blueprint-action/assets/`
2. Templates are in `Runway/Runway/Theme.lean`
3. Assets copied via `assetsDir` config
4. Content column width: `.chapter-page > p` and `section.section > p`

### Dependency graph work

**Layout algorithm** (`Dress/Graph/Layout.lean`):
- Sugiyama: layer assignment, median crossing reduction, position refinement
- Edge routing: visibility graph, Dijkstra shortest path, Bezier fitting
- Node width calculation from label length

**Edge generation** (`Dress/Graph/Build.lean`):
- `Node.inferUses` traces actual Lean code dependencies
- Statement uses -> dashed edges
- Proof uses -> solid edges
- Edges filtered to valid node IDs only

**SVG rendering** (`Dress/Graph/Render.lean`):
- Node shapes: ellipse (theorems), rect (definitions)
- Edge paths: Bezier curves with arrow markers
- 8-status color model

**Page generation** (`Runway/DepGraph.lean`):
- `wrapInModal`: Wraps sbs-container in modal structure
- `fullPageGraph`: Complete dep_graph.html page

**Modal content** (`Runway/Render.lean`):
- `renderNodeModal`: Calls `renderNode` and wraps in modal
- Preserves all hover data and proof toggle functionality

**JavaScript** (`verso-code.js`):
- Pan/zoom: D3-style behavior (wheel, drag, Fit button)
- `onModalOpen()`: Initializes MathJax and Tippy.js
- Centering: Uses getBBox() for content bounds, centers on contentCenterX/Y

**CSS** (`blueprint.css`):
- Modal sizing: 90vw max width
- sbs-container flex layout in modals
- Lean proof toggle: CSS checkbox pattern
- Dashboard grid: 2x2 layout with stats, key theorems, messages, project notes

### Dashboard work

**Render.lean functions**:
- `renderDashboard`: Main 2x2 grid layout
- `renderProgress`: Stats with Completion/Attention columns
- `renderKeyTheorems`: Side-by-side previews with status dots
- `renderMessages`: User notes from `message` attribute
- `renderProjectNotes`: blocked/potentialIssues/technicalDebt/misc sections

**Data flow**:
- Stats computed in Dress (`Graph.computeStatusCounts`)
- Manifest.json written by Dress with precomputed stats
- Runway loads manifest, no recomputation (soundness)
- `displayName` propagated for cleaner labels (falls back to short Lean name)

### `@[blueprint]` attribute options

| Option | Type | Purpose |
|--------|------|---------|
| `displayName` | String | Custom node label in graph |
| `keyTheorem` | Bool | Highlight in dashboard |
| `message` | String | User notes (Messages panel) |
| `priorityItem` | Bool | Flag for Attention column |
| `blocked` | String | Blockage reason |
| `potentialIssue` | String | Known concerns |
| `technicalDebt` | String | Cleanup notes |
| `misc` | String | Catch-all notes |

**Example**:
```lean
@[blueprint (keyTheorem := true, message := "Main result")]
theorem main_thm : ...

@[blueprint (priorityItem := true, blocked := "Waiting for mathlib PR")]
lemma helper : ...
```

### ID normalization gotcha

Node IDs containing colons (e.g., `thm:main`) must be converted to hyphens (`thm-main`) when used in:
- Modal element IDs
- CSS selectors
- JavaScript querySelector calls

The colon-to-hyphen conversion happens in `DepGraph.lean` when generating modal IDs.

---

## docs-static Branch Pattern

For projects with pre-generated documentation (docgen4 ~1 hour):

1. Generate docs locally: `lake -R -Kenv=dev build Module:docs`
2. Create orphan branch: `git checkout --orphan docs-static`
3. Add and commit docs to branch root
4. Push to remote
5. CI downloads from branch instead of regenerating (~4,700 files in seconds vs. ~1 hour)

**GCR uses this pattern** - see `full-build-deploy.yml` for the download step.

---

## Reference Documents

Located in `.refs/`:

| File | Purpose |
|------|---------|
| `side_by_side_blueprint_ground_truth.txt` | Working Python leanblueprint HTML |
| `dep_graph_ground_truth.txt` | Dependency graph with modals |
| `ARCHITECTURE.md` | System architecture |
| `GOALS.md` | Project vision |

**Goal images**:
- `goal1.png`: Individual theorem rendering
- `goal2.png`: Page structure with chapters/sections

---

## CI/CD Knowledge

**dress-blueprint-action** now supports Runway:
- `use-runway: true` enables Runway instead of Python leanblueprint
- `runway-target: "ProjectName:runway"` specifies Lake target
- Assembles from `.lake/build/runway/` when enabled

**Multi-repo CI** (SBS-Test and GCR workflows):
- Checks out project and sibling repos (Dress, Runway, LeanArchitect, SubVerso, dress-blueprint-action)
- Uses `runway-ci.json` with `${{ github.workspace }}` absolute paths
- Deploys to GitHub Pages on main branch push

**GCR consolidated workflows**:
- `full-build-deploy.yml` - Primary workflow (builds everything, deploys)
- `seed-mathlib-cache.yml` - Utility for cache seeding

---

## Anti-Patterns

- Don't create scratch files - work in repo files
- Don't use `lake clean` - invalidates caches
- Don't edit downstream before upstream
- Don't guess at Verso APIs - use `lean_hover_info`
- Don't skip build_blueprint.sh steps
- Don't use colons in CSS selectors or element IDs - normalize to hyphens
- Don't manually specify `\uses{}` - `Node.inferUses` traces real dependencies

---

## Standards

- No `sorry` in tooling code
- Follow Verso/SubVerso patterns
- Test via SBS-Test or GCR
- Check `lean_diagnostic_messages` after edits
