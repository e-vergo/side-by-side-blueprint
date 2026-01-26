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
| **Runway** | Site generator (replaces Python leanblueprint) | `Main.lean`, `Render.lean`, `Theme.lean`, `Latex/Parser.lean` |
| **Dress** | Artifact generation during elaboration | `Capture/ElabRules.lean`, `Generate/Declaration.lean`, `HtmlRender.lean` |
| **LeanArchitect** | `@[blueprint]` attribute and metadata | `Architect/Attribute.lean`, `Architect/Basic.lean` |
| **subverso** | Syntax highlighting extraction (fork with optimizations) | `Highlighting/Highlighted.lean`, `Highlighting/Code.lean` |
| **SBS-Test** | Minimal test project for fast iteration | `SBSTest/Chapter{1,2,3}/*.lean`, `blueprint/src/blueprint.tex` |
| **General_Crystallographic_Restriction** | Production example (goal reference) | Full formalization project |
| **dress-blueprint-action** | GitHub Action for CI + external assets | `assets/blueprint.css`, `assets/plastex.js`, `assets/verso-code.js`, `action.yml` |

## Dependency Chain

```
SubVerso -> LeanArchitect -> Dress -> Runway
                              |
                          Consumer projects (SBS-Test)
```

Changes to upstream repos require rebuilding downstream. The build script handles ordering.

## Current Status

**Phase 7 Complete**: Blueprint and dependency graph are feature-complete.

**Completed features**:
- Side-by-side display with proof toggles
- Dependency graph with Sugiyama layout, edge routing, pan/zoom
- Rich modals with MathJax, Tippy.js, proof toggles
- CI/CD with GitHub Pages deployment
- `displayName` option in `@[blueprint]` attribute

**Next priority**: ar5iv paper generation (full paper rendering with MathJax, links to Lean code instead of inline display).

Reference for quality targets:
- `goal2.png`: Hierarchical sidebar, numbered theorems (4.1.1), prose between declarations
- `goal1.png`: Clean side-by-side rendering with proof toggle

## Development Workflow

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test
./scripts/build_blueprint.sh
# Serves at localhost:8000, auto-exits after 5 minutes
```

Inspect: `.lake/build/runway/` for HTML output (includes `manifest.json`), `.lake/build/dressed/` for artifacts.

**Required config**: `runway.json` must include `assetsDir` pointing to CSS/JS assets directory.

**Note**: Build script auto-terminates after 5 minutes (useful for CI/testing).

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
- Modal content generation (`Runway/Render.lean`)
- CI/CD workflow updates (`dress-blueprint-action`, `SBS-Test/.github/workflows/`)

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
4. Test with SBS-Test, compare to goal images

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
- Test via SBS-Test and visual inspection

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

**CI/CD**:
- `dress-blueprint-action` supports `use-runway` and `runway-target` inputs
- SBS-Test workflow checks out 4 repos as siblings with `runway-ci.json`
