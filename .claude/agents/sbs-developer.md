---
name: sbs-developer
description: "Development agent for Side-by-Side Blueprint toolchain"
model: opus
color: pink
---

Development agent for the Side-by-Side Blueprint toolchain. Has deep knowledge of the 8-repo architecture, build pipeline, and Verso patterns.

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
├── Runway/          # Site generator + PDF/paper generation
├── Dress/           # Artifact generation + validation checks
├── LeanArchitect/   # @[blueprint] attribute and metadata
├── subverso/        # Syntax highlighting (fork with optimizations)
├── SBS-Test/        # Minimal test project (11 nodes, all features)
├── General_Crystallographic_Restriction/  # Production example with paper
├── PrimeNumberTheoremAnd/  # Large-scale integration (530 annotations)
└── dress-blueprint-action/  # GitHub Action + CSS/JS assets
```

### Dependency Chain (Build Order)
```
SubVerso -> LeanArchitect -> Dress -> Runway
                              |
                          Consumer projects (SBS-Test, GCR, PNT)
```

### Key Files by Repo

**Runway** - Site generator + dashboard + paper
| File | Purpose |
|------|---------|
| `Main.lean` | CLI: build/paper/pdf commands, loads manifest.json, `assignPagePaths` for links |
| `Render.lean` | Side-by-side rendering, dashboard, `renderNodeModal` |
| `Site.lean` | NodeInfo structure with `title` and `pagePath` fields, `fullUrl` helper |
| `DepGraph.lean` | Dependency graph page with sidebar + modal wrappers |
| `Theme.lean` | Page templates, sidebar |
| `Pdf.lean` | PDF compilation with multiple LaTeX compilers |
| `Latex/Parser.lean` | LaTeX parsing (with infinite loop fixes) |
| `Config.lean` | Site config including `assetsDir`, `paperTexPath`, paper metadata |

**Dress** - Artifact generation + stats + validation
| File | Purpose |
|------|---------|
| `Capture/ElabRules.lean` | elab_rules hooks |
| `Capture/InfoTree.lean` | SubVerso highlighting capture |
| `Generate/Declaration.lean` | Per-declaration artifact writer |
| `HtmlRender.lean` | Verso HTML rendering |
| `Graph/Types.lean` | Node, Edge, StatusCounts, CheckResults; `transitiveReduction` with O(n^3) skip |
| `Graph/Build.lean` | Graph construction + stats + validation + `Node.inferUses` |
| `Graph/Json.lean` | Manifest serialization with stats/metadata/validation |
| `Graph/Layout.lean` | Sugiyama algorithm, visibility graph, Dijkstra, Bezier |
| `Graph/Render.lean` | SVG generation |
| `Main.lean` | Writes manifest.json with precomputed stats |

**LeanArchitect** - `@[blueprint]` attribute
| File | Purpose |
|------|---------|
| `Architect/Basic.lean` | `Node`, `NodePart`, `NodeStatus` with manual `ToExpr` instance |
| `Architect/Attribute.lean` | `@[blueprint]` attribute with all options |
| `Architect/CollectUsed.lean` | Dependency inference |

**External Assets** - `dress-blueprint-action/assets/`
| File | Purpose |
|------|---------|
| `blueprint.css` | Full stylesheet including modal and graph styles |
| `plastex.js` | LaTeX proof toggle (expand/collapse) |
| `verso-code.js` | Hovers, token bindings, pan/zoom, modal MathJax/Tippy init |

---

## Current Status

**Blueprint + Dashboard + Dependency Graph + Paper Generation**: Feature-complete.

**Completed**:
- Dashboard homepage with 2x2 grid (Stats, Key Theorems, Messages, Project Notes)
- 8 metadata + 5 status flag `@[blueprint]` attribute options
- Stats computed upstream in Dress (soundness guarantee)
- manifest.json with precomputed stats, validation results, project notes
- Sugiyama layout with edge routing (visibility graph + Dijkstra + Bezier)
- Rich modals with side-by-side content (reuses `renderNode`)
- Pan/zoom, node hover, Fit button with corrected X-axis centering
- Sidebar navigation on dependency graph page
- MathJax and Tippy.js in modals
- CI/CD with GitHub Pages deployment (~340-line workflows)
- Parser fixes for large documents (3989+ tokens)
- Real dependency inference via `Node.inferUses` (traces Lean code, not manual `\uses{}`)
- CSS fixes for non-Lean content column width
- docs-static branch pattern for pre-generated docgen4 documentation
- **PDF/Paper generation pipeline** (`\paperstatement{}`, `\paperfull{}` hooks)
- **Declaration-specific paper links** (navigate to correct chapter pages)
- **Multiple LaTeX compilers** (tectonic, pdflatex, xelatex, lualatex)
- **Validation checks** (connectivity, cycle detection)
- **PrimeNumberTheoremAnd integration** (530 annotations, 33 files)
- **O(n^3) transitive reduction skip** for large graphs (>100 nodes)

**Recent Bug Fixes**:
- `displayName` -> `title` migration (aligned with PNT's hanwenzhu/LeanArchitect usage)
- `keyTheorem` -> `keyDeclaration` migration
- Manual `ToExpr` instance for `Node` (status persistence through environment extension)
- Paper links 404 fix (files at root level, not `chapters/` subdirectory)
- CI toolchain cache disabled (was ignoring code fixes)

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

---

## Build Workflow

### SBS-Test (development)

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test
./scripts/build_blueprint.sh
```

### GCR (production example with paper)

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/General_Crystallographic_Restriction
./scripts/build_blueprint.sh
```

### PNT (large-scale integration)

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/PrimeNumberTheoremAnd
./scripts/build_blueprint.sh
```

### Build Script Steps
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

**Output locations**:
- Artifacts: `.lake/build/dressed/{Module}/{label}/decl.{tex,html,json}`
- Site: `.lake/build/runway/` (includes `manifest.json`)
- Paper: `.lake/build/runway/paper.html`, `paper.pdf`, `pdf.html`

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
  - Validates graph (connectivity, cycles)
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
  - Optionally: paper.html + paper.pdf + pdf.html
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
- Validation in Dress (`findComponents`, `detectCycles`)
- Manifest.json written by Dress with precomputed stats + validation
- Runway loads manifest, no recomputation (soundness)
- `title` propagated for cleaner labels (falls back to short Lean name)

### PDF/Paper generation

**Runway commands**:
- `lake exe runway paper runway.json` - Generate paper.html + paper.pdf
- `lake exe runway pdf runway.json` - Generate just the PDF
- `lake exe runway build runway.json` - Generates paper if paperTexPath configured

**Paper TeX hooks**:
```latex
\paperstatement{thm:main}  % Insert LaTeX statement, link to Lean
\paperfull{thm:main}       % Insert full side-by-side display
```

**Configuration** (`runway.json`):
```json
{
  "paperTexPath": "blueprint/src/paper.tex",
  "paperTitle": "Title",
  "paperAuthors": ["Author One", "Author Two"],
  "paperAbstract": "Abstract text..."
}
```

**LaTeX compilers** (auto-detected):
1. tectonic (preferred, self-contained)
2. pdflatex (most common)
3. xelatex (Unicode support)
4. lualatex (Lua scripting)

### Validation checks

**Connectivity** (`findComponents` in `Graph/Build.lean`):
- BFS to detect disconnected subgraphs
- Warns about unreachable nodes (Tao-style errors)

**Cycle detection** (`detectCycles` in `Graph/Build.lean`):
- DFS with gray/black node coloring
- Finds back-edges indicating circular dependencies

**Results in manifest.json**:
```json
{
  "checkResults": {
    "connected": true,
    "componentCount": 1,
    "componentSizes": [32],
    "cycles": []
  }
}
```

### `@[blueprint]` attribute options

**Metadata Options (8)**:
| Option | Type | Purpose |
|--------|------|---------|
| `title` | String | Custom node label in graph (renamed from `displayName`) |
| `keyDeclaration` | Bool | Highlight in dashboard (renamed from `keyTheorem`) |
| `message` | String | User notes (Messages panel) |
| `priorityItem` | Bool | Flag for Attention column |
| `blocked` | String | Blockage reason |
| `potentialIssue` | String | Known concerns |
| `technicalDebt` | String | Cleanup notes |
| `misc` | String | Catch-all notes |

**Status Flags (5)**:
| Option | Type | Purpose |
|--------|------|---------|
| `notReady` | Bool | Status: not ready (red/gray) |
| `ready` | Bool | Status: ready to formalize (orange) |
| `fullyProven` | Bool | Status: fully proven with all deps (dark green) |
| `mathlibReady` | Bool | Status: ready for mathlib (purple) |
| `mathlib` | Bool | Status: already in mathlib (dark blue) |

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

**Example**:
```lean
@[blueprint (keyDeclaration := true, message := "Main result")]
theorem main_thm : ...

@[blueprint (priorityItem := true, blocked := "Waiting for mathlib PR")]
lemma helper : ...

@[blueprint (fullyProven := true)]
theorem complete_with_all_deps : ...
```

### ID normalization gotcha

Node IDs containing colons (e.g., `thm:main`) must be converted to hyphens (`thm-main`) when used in:
- Modal element IDs
- CSS selectors
- JavaScript querySelector calls

The colon-to-hyphen conversion happens in `DepGraph.lean` when generating modal IDs.

---

## CI/CD Knowledge

### Workflow structure (~340 lines)

GCR and PNT use `full-build-deploy.yml`:

```yaml
jobs:
  build:
    steps:
      # SETUP: Free disk space, checkout 6 repos
      - Checkout project, SubVerso, LeanArchitect, Dress, Runway, dress-blueprint-action

      # TOOLCHAIN: Direct elan installation (not lean-action)
      - Install elan, Lean toolchain, LaTeX

      # CACHE: Restore/save toolchain and mathlib caches

      # BUILD: Toolchain in dependency order
      - Build SubVerso -> LeanArchitect -> Dress -> Runway

      # BUILD: Project with dressed artifacts
      - Create .dress file, lake build, lake build :blueprint
      - Generate dependency graph with extract_blueprint

      # DOCGEN4: Download pre-built docs (docs-static branch pattern)

      # SITE: Generate with Runway
      - Create runway-ci.json with absolute paths
      - lake exe runway build + paper

      # VERIFY: Check key files exist
      - index.html, dep_graph.html, paper.html, paper.pdf, pdf.html

  deploy:
    - Deploy to GitHub Pages
```

### Key patterns

**Direct elan installation**: lean-action failed in CI; direct elan-init.sh works reliably.

**runway-ci.json**: CI-specific config with `$WORKSPACE` placeholder:
```json
{
  "blueprintTexPath": "$WORKSPACE/GCR/blueprint/src/blueprint.tex",
  "assetsDir": "$WORKSPACE/dress-blueprint-action/assets",
  "paperTexPath": "$WORKSPACE/GCR/blueprint/src/paper.tex"
}
```
Then: `sed -i "s|\$WORKSPACE|${{ github.workspace }}|g" runway-ci.json`

**docs-static branch pattern**: Pre-generated DocGen4 stored in orphan branch, downloaded in CI.

### CI differences by project

| Feature | GCR | PNT | SBS-Test |
|---------|-----|-----|----------|
| DocGen4 | Yes (docs-static) | No | No |
| Paper generation | Yes | No | Optional |
| Mathlib | Yes | Yes | Minimal |

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

## PrimeNumberTheoremAnd Integration

Large-scale integration test case:

- **530 `@[blueprint]` annotations** across 33 files
- **Zero changes to Lean proof code** - annotations added non-invasively
- **Toolchain downgrade**: v4.28.0-rc1 -> v4.27.0
- **Mathlib pinned**: to v4.27.0

**Key theorems tagged**:
```lean
@[blueprint (keyDeclaration := true)]
theorem WeakPNT : ...

@[blueprint (keyDeclaration := true)]
theorem MediumPNT : ...

@[blueprint (keyDeclaration := true)]
theorem WeakPNT_AP : ...
```

**lakefile.toml** pattern:
```toml
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

## Anti-Patterns

- Don't create scratch files - work in repo files
- Don't use `lake clean` - invalidates caches
- Don't edit downstream before upstream
- Don't guess at Verso APIs - use `lean_hover_info`
- Don't skip build_blueprint.sh steps
- Don't use colons in CSS selectors or element IDs - normalize to hyphens
- Don't manually specify `\uses{}` - `Node.inferUses` traces real dependencies
- Don't use derived `ToExpr` for structures with default fields - use manual instance
- Don't enable toolchain cache in CI - causes stale code issues

---

## Standards

- No `sorry` in tooling code
- Follow Verso/SubVerso patterns
- Test via SBS-Test or GCR
- Check `lean_diagnostic_messages` after edits
