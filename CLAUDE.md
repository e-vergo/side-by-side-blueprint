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
| **Runway** | Site generator + dashboard + paper/PDF | `Main.lean`, `Render.lean`, `Site.lean`, `DepGraph.lean`, `Theme.lean`, `Pdf.lean`, `Latex/Parser.lean` |
| **Dress** | Artifact generation + stats + validation | `Capture/ElabRules.lean`, `Graph/Types.lean`, `Graph/Build.lean`, `Graph/Json.lean` |
| **LeanArchitect** | `@[blueprint]` attribute with 8 metadata + 5 status options | `Architect/Attribute.lean`, `Architect/Basic.lean` |
| **subverso** | Syntax highlighting extraction (fork with optimizations) | `Highlighting/Highlighted.lean`, `Highlighting/Code.lean` |
| **SBS-Test** | Minimal test project (11 nodes, all features) | `SBSTest/StatusDemo.lean`, `blueprint/src/blueprint.tex` |
| **General_Crystallographic_Restriction** | Production example with paper generation | Full formalization project |
| **PrimeNumberTheoremAnd** | Large-scale integration (530 annotations, 33 files) | Terence Tao's PNT+ project |
| **dress-blueprint-action** | GitHub Action for CI + external assets | `assets/blueprint.css`, `assets/plastex.js`, `assets/verso-code.js`, `action.yml` |

## Dependency Chain

```
SubVerso -> LeanArchitect -> Dress -> Runway
                              |
                          Consumer projects (SBS-Test, GCR, PNT)
```

Changes to upstream repos require rebuilding downstream. The build script handles ordering.

## Current Status

**Phase 7 + Dashboard + Paper Phases Complete**: Blueprint, dashboard, dependency graph, and paper generation are feature-complete.

**Completed features**:
- Side-by-side display with proof toggles
- Dashboard homepage with stats, key theorems, messages, project notes
- 8 metadata + 5 status flag `@[blueprint]` attribute options
- Stats computed upstream in Dress (soundness guarantee via manifest.json)
- Dependency graph with Sugiyama layout, edge routing, pan/zoom
- Dependency graph sidebar navigation
- Rich modals with MathJax, Tippy.js, proof toggles
- CI/CD with GitHub Pages deployment (~340-line workflows)
- `title` propagation for cleaner labels (renamed from `displayName`)
- Parser fixes for large documents (3989+ tokens)
- Real dependency inference via `Node.inferUses` (traces Lean code, not manual `\uses{}`)
- CSS fixes for non-Lean content column width
- docs-static branch pattern for pre-generated docgen4 documentation
- **PDF/Paper generation** (`\paperstatement{}`, `\paperfull{}` hooks)
- **Declaration-specific paper links** (navigate to correct chapter pages)
- **Multiple LaTeX compilers** (tectonic, pdflatex, xelatex, lualatex)
- **Validation checks** (connectivity, cycle detection)
- **PrimeNumberTheoremAnd integration** (530 annotations, 33 files, zero proof changes)
- **O(n^3) transitive reduction skip** for large graphs (>100 nodes)

Reference for quality targets:
- `goal2.png`: Hierarchical sidebar, numbered theorems (4.1.1), prose between declarations
- `goal1.png`: Clean side-by-side rendering with proof toggle

## Development Workflow

### SBS-Test (fast iteration)

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test
./scripts/build_blueprint.sh
# Serves at localhost:8000
```

### GCR (production example with paper)

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/General_Crystallographic_Restriction
./scripts/build_blueprint.sh
# Serves at localhost:8000
```

### PNT (large-scale integration)

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/PrimeNumberTheoremAnd
./scripts/build_blueprint.sh
# Serves at localhost:8000
```

Inspect: `.lake/build/runway/` for HTML output (includes `manifest.json`), `.lake/build/dressed/` for artifacts.

**Required config**: `runway.json` must include `assetsDir` pointing to CSS/JS assets directory.

## Build Script Steps

```
Step 0:  Sync repos to GitHub (auto-commit/push changes)
Step 0b: Update lake manifests in dependency order
Step 1:  Build local forks (SubVerso -> LeanArchitect -> Dress -> Runway)
Step 2:  Fetch mathlib cache
Step 3:  Build with BLUEPRINT_DRESS=1 (or .dress file)
Step 4:  Build :blueprint facet
Step 5:  Generate dependency graph
Step 6:  Generate site with Runway
Step 7:  Generate paper (if paperTexPath configured)
Step 8:  Serve at localhost:8000
```

## Performance Context

**SubVerso optimization (Phase 1) complete**: Added indexing, caching, containment queries.

| Operation | Time | Percentage |
|-----------|------|------------|
| SubVerso highlighting | 800-6500ms | 93-99% |
| TeX/HTML generation | <30ms | <1% |

**Key finding**: SubVerso highlighting dominates build time. Cannot be deferred because info trees are ephemeral (only exist during elaboration). Deferred generation (Phase 2) was skipped - no performance benefit.

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
- Modal content generation (`Runway/Render.lean`)
- Attribute options (LeanArchitect `Basic.lean` and `Attribute.lean`)
- CI/CD workflow updates (`dress-blueprint-action`, project workflows)
- PDF/Paper generation (`Runway/Pdf.lean`, paper TeX hooks)
- Validation checks (`Dress/Graph/Build.lean`)

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
3. Run `build_blueprint.sh` (handles rebuild order)
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

**Declaration-specific links**:
- `pagePath` field in `NodeInfo` tracks which chapter page each node belongs to
- `assignPagePaths` in `Runway/Main.lean` populates during site generation
- `fullUrl` helper generates correct URLs like `basic-definitions.html#thm-main`
- Paper links navigate to correct chapter pages instead of just anchor links

**Parser fixes**:
- `Runway/Latex/Parser.lean` includes `let _ <- advance` in catch-all cases
- Prevents infinite loops when parsing large documents (3989+ tokens)

**CSS layout fixes**:
- Non-Lean content stays in left column via `.chapter-page > p` and `section.section > p` selectors

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
| `title` | String | Custom node label in graph (renamed from `displayName`) |
| `keyDeclaration` | Bool | Highlight in dashboard Key Theorems (renamed from `keyTheorem`) |
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

**Validation checks**:
- Connectivity: `findComponents` detects disconnected subgraphs (Tao-style errors)
- Cycles: `detectCycles` finds circular dependencies
- Results in `manifest.json` under `checkResults`
- SBS-Test includes disconnected cycle (cycleA <-> cycleB) for validation testing

**Performance fixes**:
- O(n^3) transitive reduction in `Dress/Graph/Types.lean` skipped for graphs >100 nodes
- PNT (530 nodes) was causing 3+ hour hangs: 530^3 = 149 million iterations
- Trade-off: some redundant edges appear but layout still works

**ToExpr bug fix**:
- Manual `ToExpr` instance for `Node` in `LeanArchitect/Architect/Basic.lean`
- Derived `ToExpr` for structures with default field values doesn't correctly serialize all fields
- This was causing status flags to not persist through the environment extension

**CI/CD**:
- `dress-blueprint-action` supports `use-runway` and `runway-target` inputs
- GCR and PNT use `full-build-deploy.yml` (~340 lines)
- Direct elan installation (not lean-action, which failed)
- Checks out 6 repos: SubVerso, LeanArchitect, Dress, Runway, dress-blueprint-action, project
- `runway-ci.json` pattern with `$WORKSPACE` placeholder
- Verification step checks for key output files
- **Toolchain cache disabled** (was restoring stale compiled binaries, ignoring code fixes)
- Mathlib cache still enabled (separate concern)

**docs-static branch pattern** (for pre-generated documentation):
1. Generate docs locally: `lake -R -Kenv=dev build Module:docs`
2. Create orphan branch: `git checkout --orphan docs-static`
3. Commit docs to branch root
4. CI downloads from branch instead of regenerating (~4,700 files in seconds vs. ~1 hour)

**PrimeNumberTheoremAnd integration**:
- 530 `@[blueprint]` annotations across 33 files
- Zero changes to Lean proof code
- Downgraded to Lean v4.27.0, pinned mathlib to v4.27.0
- Key theorems tagged: WeakPNT, MediumPNT, WeakPNT_AP
- No DocGen4 (simpler setup)

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

# Optional: doc-gen4 as dev dependency (v4.27.0 compatible)
[[require]]
scope = "dev"
name = "doc-gen4"
git = "https://github.com/leanprover/doc-gen4.git"
rev = "01e1433"
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
