# Side-by-Side Blueprint: Development Guide

> **Prototype Status**: Alpha software with known bugs, slow workflows, and incomplete features. Not yet production-ready.

## Orchestration Model

**By default, the top-level chat discusses with the user and orchestrates `sbs-developer` agents to accomplish tasks, always one at a time.** The top-level chat serves as:
- Communication interface with the user
- Task decomposition and planning
- Agent orchestration and result synthesis

Actual implementation work is delegated to `sbs-developer` agents which have deep architectural knowledge embedded in their prompts.

## Project Context

Building a pure Lean toolchain for formalization documentation that:
- Displays formal proofs alongside LaTeX statements (side-by-side)
- Couples document generation to build for soundness guarantees
- Visualizes dependency graphs to catch logical errors
- Expands what "verified" means beyond just "typechecks"

**This is Lean software development, not proof writing.** The MCP tools are used differently here.

## Repository Map

| Repo | Purpose | Key Files |
|------|---------|-----------|
| **Runway** | Site generator + dashboard + paper/PDF + module references | `Main.lean`, `Render.lean`, `Site.lean`, `DepGraph.lean`, `Theme.lean`, `Pdf.lean`, `Latex/Parser.lean` |
| **Dress** | Artifact generation + stats + validation + two-pass edge processing | `Capture/ElabRules.lean`, `Graph/Types.lean`, `Graph/Build.lean`, `Graph/Json.lean`, `Graph/Layout.lean` |
| **LeanArchitect** | `@[blueprint]` attribute with 8 metadata + 5 status options | `Architect/Attribute.lean`, `Architect/Basic.lean` |
| **subverso** | Syntax highlighting extraction (fork with optimizations) | `Highlighting/Highlighted.lean`, `Highlighting/Code.lean` |
| **SBS-Test** | Minimal test project (11 nodes, all features) | `SBSTest/StatusDemo.lean`, `blueprint/src/blueprint.tex` |
| **General_Crystallographic_Restriction** | Production example with paper generation | Full formalization project |
| **PrimeNumberTheoremAnd** | Large-scale integration (530 annotations, 33 files) | Terence Tao's PNT+ project |
| **dress-blueprint-action** | Complete CI solution (~465 lines) + external assets | `action.yml`, `assets/blueprint.css`, `assets/verso-code.js` |

## Dependency Chain

```
SubVerso -> LeanArchitect -> Dress -> Runway
                              |
                          Consumer projects (SBS-Test, GCR, PNT)
```

Changes to upstream repos require rebuilding downstream. The build script handles ordering.

## Current Status

**Phase 7 + Dashboard + Paper + Module Reference Phases Complete**: Blueprint, dashboard, dependency graph, paper generation, and module reference support are feature-complete.

**Completed features**:
- Side-by-side display with proof toggles
- Dashboard homepage with stats, key theorems, messages, project notes
- 8 metadata + 5 status flag `@[blueprint]` attribute options
- Stats computed upstream in Dress (soundness guarantee via manifest.json)
- Dependency graph with Sugiyama layout, edge routing, pan/zoom
- Rich modals with MathJax, Tippy.js, proof toggles
- Real dependency inference via `Node.inferUses` (traces Lean code, not manual `\uses{}`)
- PDF/Paper generation (`\paperstatement{}`, `\paperfull{}` hooks)
- Validation checks (connectivity, cycle detection)
- PrimeNumberTheoremAnd integration (530 annotations, 33 files, zero proof changes)
- O(n^3) transitive reduction skip for large graphs (>100 nodes)
- Two-pass edge processing for proper back-edge handling
- Edge deduplication (keeps first occurrence of each from/to pair)
- Dependency graph fit/centering fixed (proper getBBox handling)
- Module reference support (`\inputleanmodule{}` expansion)
- Static tile heights (320px for stats and checks boxes)
- Project Notes aligned with Key Declarations column
- Checks panel with placeholder future checks (Kernel Verification, Soundness Checks)

Reference for quality targets:
- `goal2.png`: Hierarchical sidebar, numbered theorems (4.1.1), prose between declarations
- `goal1.png`: Clean side-by-side rendering with proof toggle

## Development Workflow

### Local Development

All projects use a shared script (~245 lines) with 3-line wrappers:

```bash
# SBS-Test (fast iteration)
cd /Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test
./scripts/build_blueprint.sh

# GCR (production example with paper)
cd /Users/eric/GitHub/Side-By-Side-Blueprint/General_Crystallographic_Restriction
./scripts/build_blueprint.sh

# PNT (large-scale integration)
cd /Users/eric/GitHub/Side-By-Side-Blueprint/PrimeNumberTheoremAnd
./scripts/build_blueprint.sh
```

### Warm Cache Script

Pre-fetch mathlib cache for all projects:
```bash
./scripts/warm_cache.sh
```

Inspect: `.lake/build/runway/` for HTML output (includes `manifest.json`), `.lake/build/dressed/` for artifacts.

**Required config**: `runway.json` must include `assetsDir` pointing to CSS/JS assets directory.

## Build Script Steps

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
Step 6:  Generate dependency graph
Step 7:  Generate site with Runway
Step 8:  Generate paper (if paperTexPath configured)
Step 9:  Start server and open browser (localhost:8000)
```

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

## Performance Context

**SubVerso optimization (Phase 1) complete**: Added indexing, caching, containment queries.

| Operation | Time | Percentage |
|-----------|------|------------|
| SubVerso highlighting | 800-6500ms | 93-99% |
| TeX/HTML generation | <30ms | <1% |

**Key finding**: SubVerso highlighting dominates build time. Cannot be deferred because info trees are ephemeral (only exist during elaboration).

**Large graph optimizations**:
- O(n^3) transitive reduction skipped for graphs >100 nodes
- Simplified edge routing for large graphs in Layout.lean
- Edge deduplication in Build.lean

## MCP Tool Usage

**For Lean software development (not proofs):**

| Tool | Use For |
|------|---------|
| `lean_diagnostic_messages` | Compilation errors after edits |
| `lean_hover_info` | Verso/SubVerso API signatures |
| `lean_completions` | Discover available functions |
| `lean_file_outline` | Module structure overview |
| `lean_local_search` | Find declarations across repos |

**Less relevant:** `lean_goal`, `lean_multi_attempt`, `lean_leansearch`, `lean_loogle` (proof-focused tools)

## Agent Usage

**When to spawn `sbs-developer`:**
- Fixing LaTeX parsing or HTML rendering in Runway
- Debugging artifact generation in Dress
- Cross-repo changes (LeanArchitect -> Dress -> Runway)
- Running builds and inspecting output
- CSS/JS fixes in `dress-blueprint-action/assets/`
- Theme template fixes in `Runway/Runway/Theme.lean`
- Dependency graph work (layout in `Dress/Graph/*.lean`, page in `Runway/DepGraph.lean`)
- Dashboard work (stats/key theorems/messages/notes in `Runway/Render.lean`)
- CI/CD workflow updates (`dress-blueprint-action`, project workflows)
- PDF/Paper generation (`Runway/Pdf.lean`, paper TeX hooks)
- Validation checks (`Dress/Graph/Build.lean`)
- Module reference support (`Theme.lean`: `buildModuleLookup`, `replaceModulePlaceholders`)

**How to use:**
1. Discuss task with user, clarify requirements
2. Spawn single `sbs-developer` agent with clear instructions
3. Wait for agent to complete
4. Synthesize results for user
5. Repeat if needed

**Never:** Run multiple agents in parallel for this project. Sequential, one at a time.

## Cross-Repo Editing

1. Identify affected repos via dependency chain
2. Edit upstream first (LeanArchitect before Dress before Runway)
3. Run `build_blueprint.sh` (always cleans + rebuilds toolchain)
4. Test with SBS-Test or GCR, compare to goal images

## Soundness Vision

The toolchain should enforce:
- No `sorry` in deployments
- Connected dependency graphs (catch Tao-style errors)
- Declaration-label consistency
- Uses completeness vs actual code dependencies

## Standards

- No `sorry` in tooling code
- Follow Verso/SubVerso patterns
- Work directly in repo files, not scratch files
- Check `lean_diagnostic_messages` after edits
- Test via SBS-Test or GCR and visual inspection

## Reference Documents

Located in `.refs/`:

| File | Purpose |
|------|---------|
| `side_by_side_blueprint_ground_truth.txt` | Working Python leanblueprint HTML for side-by-side display |
| `dep_graph_ground_truth.txt` | Working dependency graph page with modals and D3 rendering |
| `ARCHITECTURE.md` | System architecture with performance analysis |
| `GOALS.md` | Project goals and vision |
| `motivation1.txt`, `motivation2.txt` | Original motivation notes |

## Reference Images

- `goal1.png`: Target quality for individual theorem rendering
- `goal2.png`: Target page structure with chapters/sections/numbered theorems

## Key Implementation Details

**ID normalization**: Node IDs with colons (`thm:main`) must be converted to hyphens (`thm-main`) for modal element IDs and CSS selectors.

**Modal generation flow**:
1. `Render.lean`: `renderNodeModal` wraps `renderNode` output in modal
2. `DepGraph.lean`: `wrapInModal` creates container structure
3. `verso-code.js`: `onModalOpen()` initializes MathJax + Tippy.js

**Proof toggles**:
- LaTeX: `plastex.js` handles expand/collapse
- Lean: Pure CSS checkbox pattern (no JS needed)

**Dashboard data flow**:
1. `Dress/Graph/Build.lean`: `computeStatusCounts` computes stats from graph
2. `Dress/Graph/Build.lean`: `findComponents`, `detectCycles` validate graph
3. `Dress/Graph/Json.lean`: Serializes stats + validation + project metadata to manifest.json
4. `Runway/Main.lean`: Loads manifest.json (no recomputation), `assignPagePaths` tracks node locations
5. `Runway/Render.lean`: `renderDashboard` displays precomputed data

**Dependency inference**:
- `Node.inferUses` in `Dress/Graph/Build.lean` traces actual Lean code dependencies
- Statement uses -> dashed edges
- Proof uses -> solid edges
- Replaces manual `\uses{}` annotations with real dependency tracing

**Two-pass edge processing** (`Graph/Build.lean`):
- PASS 1: Register all labels and create nodes (so all labels exist)
- PASS 2: Add all edges (now back-edges work because targets are registered)
- Edge deduplication: keeps first occurrence of each from/to pair

**Dependency graph fit/centering** (`verso-code.js`):
- Uses `getBBox()` to get actual SVG content bounds
- Calculates `contentCenterX/Y` from bbox
- Translates to center content in viewport
- Fixes X-axis bias when SVG has asymmetric padding

**Module reference support** (`Theme.lean`):
- `buildModuleLookup`: Creates map from module name to nodes
- `replaceModulePlaceholders`: Finds `<div class="lean-module-placeholder" data-module="X">` and replaces with rendered nodes
- Registers full module names (e.g., `PrimeNumberTheoremAnd.Wiener`)
- `\inputleanmodule{ModuleName}` in LaTeX expands to all nodes from that module

**Parser fixes**:
- `Runway/Latex/Parser.lean` includes `let _ <- advance` in catch-all cases
- Prevents infinite loops when parsing large documents (3989+ tokens)

**`@[blueprint]` attribute options**:
```lean
@[blueprint (keyDeclaration := true, message := "Main result")]
theorem main_thm : ...

@[blueprint (priorityItem := true, blocked := "Waiting for mathlib PR")]
lemma helper : ...

@[blueprint (title := "Square Non-negative")]
theorem square_nonneg : ...

@[blueprint (fullyProven := true)]
theorem complete_with_all_deps : ...
```

**Metadata Options (8)**:
| Option | Type | Purpose |
|--------|------|---------|
| `title` | String | Custom node label in graph |
| `keyDeclaration` | Bool | Highlight in dashboard Key Theorems |
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

**PDF/Paper generation**:
- `\paperstatement{label}`: Insert LaTeX statement with link to Lean code
- `\paperfull{label}`: Insert full side-by-side display
- Supported compilers: tectonic (preferred), pdflatex, xelatex, lualatex
- Output: `paper.html` (MathJax), `paper.pdf`, `pdf.html` (viewer)
- Config: `paperTexPath`, `paperTitle`, `paperAuthors`, `paperAbstract` in runway.json
- Paper generation auto-detected in CI from runway.json

**Validation checks**:
- Connectivity: `findComponents` detects disconnected subgraphs (Tao-style errors)
- Cycles: `detectCycles` finds circular dependencies
- Results in `manifest.json` under `checkResults`
- Dashboard shows Checks panel with connectivity/cycle info + placeholder future checks

**Performance fixes**:
- O(n^3) transitive reduction in `Dress/Graph/Types.lean` skipped for graphs >100 nodes
- PNT (530 nodes) was causing 3+ hour hangs: 530^3 = 149 million iterations
- Simplified edge routing for large graphs in Layout.lean
- Edge deduplication in Build.lean

**ToExpr bug fix**:
- Manual `ToExpr` instance for `Node` in `LeanArchitect/Architect/Basic.lean`
- Derived `ToExpr` for structures with default field values doesn't correctly serialize all fields

**Mathlib version pinning**:
- All repos pinned to v4.27.0 for consistency
- Mathlib cache fetched from server (`lake exe cache get`)

**docs-static branch pattern** (for pre-generated documentation):
1. Generate docs locally: `lake -R -Kenv=dev build Module:docs`
2. Create orphan branch: `git checkout --orphan docs-static`
3. Commit docs to branch root
4. CI uses `docgen4-mode: docs-static` to download instead of regenerating

**lakefile.toml configuration**:
```toml
[[require]]
name = "Dress"
git = "https://github.com/e-vergo/Dress"
rev = "main"

# For mathlib projects, pin to matching version
[[require]]
name = "mathlib"
git = "https://github.com/leanprover-community/mathlib4.git"
rev = "v4.27.0"
```

**runway.json configuration**:
```json
{
  "title": "Project Title",
  "projectName": "ProjectName",
  "githubUrl": "https://github.com/...",
  "baseUrl": "/",
  "blueprintTexPath": "blueprint/src/blueprint.tex",
  "assetsDir": "../dress-blueprint-action/assets",
  "paperTexPath": "blueprint/src/paper.tex",
  "paperTitle": "Paper Title",
  "paperAuthors": ["Author One", "Author Two"],
  "paperAbstract": "Abstract text...",
  "docgen4Url": "docs/"
}
```
