# Side-by-Side Blueprint: Development Guide

Pure Lean toolchain for formalization documentation that displays formal proofs alongside LaTeX theorem statements.

---

## How This Document Works

This guide governs Claude Code sessions on the Side-by-Side Blueprint project. It defines:
- **Orchestration structure:** How the top-level chat and `sbs-developer` agents divide labor
- **User preferences:** Communication, planning, and meta-cognitive expectations
- **Domain context:** Architecture, conventions, and project-specific patterns

The user and Claude are actively refining this document together. If something here doesn't match how work is actually proceeding, surface it.

---

## Orchestration Model

The top-level chat is the **orchestrator**. It does not implement—it coordinates.

| Top-Level Chat | `sbs-developer` Agent |
|----------------|----------------------|
| Discusses requirements with user | Executes implementation tasks |
| Decomposes and plans work | Has deep architectural knowledge |
| Spawns agents (one at a time) | Works within defined scope |
| Synthesizes results | Reports outcomes |

**Constraint:** Agents are spawned **sequentially, never in parallel**. This is intentional for this project.

---

## Project Context

Building tooling that:
1. Displays formal Lean proofs alongside LaTeX statements (side-by-side)
2. Couples document generation to build for soundness guarantees
3. Visualizes dependency graphs to catch logical errors (Tao incident motivation)
4. Expands what "verified" means beyond just "typechecks"

**This is Lean software development, not proof writing.** MCP tools are used differently here.

---

## Repository Map

| Repo | Purpose |
|------|---------|
| **subverso** | Syntax highlighting (fork with O(1) indexed lookups via InfoTable) |
| **verso** | Document framework (fork with SBSBlueprint/VersoPaper genres) |
| **LeanArchitect** | `@[blueprint]` attribute with 8 metadata + 3 status options |
| **Dress** | Artifact generation + graph layout + validation + rainbow brackets |
| **Runway** | Site generator + dashboard + paper/PDF + module references |
| **SBS-Test** | Minimal test project (25 nodes, all 6 status colors) |
| **General_Crystallographic_Restriction** | Production example with paper (57 nodes) |
| **PrimeNumberTheoremAnd** | Large-scale integration (530 nodes) |
| **dress-blueprint-action** | CI/CD action (~465 lines) + CSS/JS assets |

### Dependency Chain

```
SubVerso -> LeanArchitect -> Dress -> Runway
              |
              +-> Verso (genres use SubVerso for highlighting)
```

Changes to upstream repos require rebuilding downstream. The build script handles ordering.

---

## Local Development

All projects use a shared script with 3-line wrappers:

```bash
# SBS-Test (fast iteration, ~2 minutes)
cd /Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test
./scripts/build_blueprint.sh

# GCR (production with paper)
cd /Users/eric/GitHub/Side-By-Side-Blueprint/General_Crystallographic_Restriction
./scripts/build_blueprint.sh

# PNT (large-scale)
cd /Users/eric/GitHub/Side-By-Side-Blueprint/PrimeNumberTheoremAnd
./scripts/build_blueprint.sh
```

### Build Script Steps

1. Validate project (runway.json, projectName)
2. Kill existing servers on port 8000
3. Sync repos to GitHub
4. Update lake manifests
5. Clean build artifacts
6. Build toolchain (SubVerso → LeanArchitect → Dress → Runway)
7. Fetch mathlib cache
8. Build project with `BLUEPRINT_DRESS=1`
9. Build `:blueprint` facet
10. Generate dependency graph
11. Generate site
12. Generate paper (if configured)
13. Start server at localhost:8000

### Output Locations

| Location | Contents |
|----------|----------|
| `.lake/build/dressed/{Module}/{label}/` | Artifacts |
| `.lake/build/runway/` | Site |
| `.lake/build/runway/manifest.json` | Manifest |

**Required:** `runway.json` must include `assetsDir` pointing to CSS/JS assets.

---

## Visual Testing & Debugging

**Screenshot capture is the FIRST reflex for any visual/CSS/layout issue.**

The `sbs` tooling provides automated screenshot capture, comparison, and history tracking.

### Screenshot Capture

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/scripts

# Capture all pages from running server
python3 -m sbs capture

# Capture specific project
python3 -m sbs capture --project SBSTest

# Capture from custom URL
python3 -m sbs capture --url http://localhost:8000
```

Captures include: dashboard, all chapter pages, dependency graph, paper (if configured).

### Visual Comparison

```bash
# Compare latest capture against previous
python3 -m sbs compare

# View capture history for a project
python3 -m sbs history --project SBSTest
```

### Image Storage

| Location | Purpose |
|----------|---------|
| `images/{project}/latest/` | Current capture (overwritten each run) |
| `images/{project}/archive/{timestamp}/` | Timestamped archives |
| `capture.json` | Metadata: timestamp, commit, viewport, page status |

### Standard Workflow for Visual Changes

1. **BEFORE changes:** `python3 -m sbs capture` (creates baseline)
2. **Make changes** to CSS/JS/Lean/templates
3. **Rebuild:** `./scripts/build_blueprint.sh`
4. **AFTER changes:** `python3 -m sbs capture` (archives previous, captures new)
5. **Compare:** `python3 -m sbs compare` (diff latest vs previous)

### What to Verify

- Dashboard layout (2×2 grid, stats, key theorems, messages, notes)
- Dependency graph (pan/zoom, modals, node colors, edge styles)
- Sidebar navigation and highlighting
- Rainbow bracket colors (6-depth cycling)
- Status dot colors across all 6 states
- Side-by-side theorem/proof displays
- Dark/light theme toggle
- Paper rendering (if configured)

---

## CI/CD Architecture

| Property | Value |
|----------|-------|
| **Trigger** | Manual only (`workflow_dispatch`) |
| **Workflow size** | ~30 lines per project |
| **Action size** | ~465 lines, 14 steps (centralized in `dress-blueprint-action`) |
| **Mathlib cache** | Relies on mathlib server (not GitHub Actions cache) |

### Action Inputs

| Input | Default | Purpose |
|-------|---------|---------|
| `project-directory` | `.` | Directory containing lakefile.toml and runway.json |
| `lean-version` | (auto) | Override Lean version |
| `docgen4-mode` | `skip` | DocGen4 mode: `skip`, `docs-static`, or `generate` |
| `deploy-pages` | `true` | Upload artifact for GitHub Pages |

---

## Performance Context

| Operation | Time | Percentage |
|-----------|------|------------|
| SubVerso highlighting | 800–6500ms | 93–99% |
| TeX/HTML generation | <30ms | <1% |

SubVerso highlighting dominates build time. Cannot be deferred (info trees are ephemeral).

### Graph Layout Performance

**Complexity by phase:**
- Layer assignment: O(V+E)
- Crossing reduction (barycenter): O(n²) normal, O(n) with iteration limit
- Edge routing: O(n² log n) normal, O(n) with simple beziers

**>100 node optimizations** (automatic in Layout.lean):
- Max 2 barycenter iterations
- Skip transpose heuristic
- Skip visibility graph routing (use simple beziers)
- Skip O(n³) transitive reduction

**Expected layout times:**
| Scale | Nodes | Layout Time |
|-------|-------|-------------|
| Small | <50 | <1s |
| Medium | 50-100 | 1-3s |
| Large | >100 | 5-20s |

### Graph Debugging Tips

**viewBox centering issues:**
- Symptom: Graph appears off-center or cropped
- Cause: viewBox origin not at (0,0)
- Fix: Verify coordinate normalization in `Layout.lean` shifts min coordinates to origin

**Coordinate normalization pattern:**
```lean
let minX := nodes.foldl (fun acc n => min acc n.x) Float.inf
let minY := nodes.foldl (fun acc n => min acc n.y) Float.inf
let normalized := nodes.map fun n => { n with x := n.x - minX, y := n.y - minY }
```

**Checking SVG output:**
1. Inspect `.lake/build/runway/dep_graph.svg`
2. Check viewBox starts at `0 0 ...`
3. Verify node coordinates are non-negative

**JavaScript pan/zoom:**
- `fitToWindow()` in `verso-code.js` uses `getBBox()` for content bounds
- Requires viewBox origin at (0,0) for correct centering calculations

---

## MCP Tool Usage

**For Lean software development (not proofs):**

| Tool | Use For |
|------|---------|
| `lean_diagnostic_messages` | Compilation errors after edits |
| `lean_hover_info` | Verso/SubVerso API signatures |
| `lean_completions` | Discover available functions |
| `lean_file_outline` | Module structure overview |
| `lean_local_search` | Find declarations across repos |

**Less relevant:** `lean_goal`, `lean_multi_attempt`, `lean_leansearch`, `lean_loogle` (proof-focused)

---

## When to Spawn `sbs-developer`

Spawn an agent for:
- Fixing LaTeX parsing or HTML rendering in Runway
- Debugging artifact generation in Dress
- Cross-repo changes (LeanArchitect → Dress → Runway)
- Running builds and inspecting output
- CSS/JS fixes in `dress-blueprint-action/assets/`
- Theme template fixes in `Runway/Theme.lean`
- Dependency graph work (layout in `Dress/Graph/*.lean`, page in `Runway/DepGraph.lean`)
- Dashboard work (stats/key theorems/messages/notes in `Runway/Render.lean`)
- CI/CD workflow updates
- PDF/Paper generation (`Runway/Pdf.lean`, `Runway/Paper.lean`)
- Validation checks (`Dress/Graph/Build.lean`)
- Module reference support (`Theme.lean`)

### Spawning Protocol

1. Discuss task with user, clarify requirements
2. Spawn single `sbs-developer` agent with clear instructions
3. Wait for agent to complete
4. Synthesize results for user
5. Repeat if needed

### Visual Verification Requirement

**Visual verification is mandatory for UI work.** Agents working on CSS, templates, dashboard, or dependency graph must:
- Capture screenshots BEFORE making changes
- Capture screenshots AFTER changes
- Use `sbs compare` to verify expected differences
- Include screenshot paths in completion summary

---

## Cross-Repo Editing

1. Identify affected repos via dependency chain
2. Edit upstream first (LeanArchitect before Dress before Runway)
3. Run `build_blueprint.sh` (always cleans + rebuilds toolchain)
4. Test with SBS-Test or GCR

---

## Standards

- No `sorry` in tooling code
- Follow Verso/SubVerso patterns
- Work directly in repo files, not scratch files
- Check `lean_diagnostic_messages` after edits
- Test via SBS-Test or GCR
- Use `sbs capture` + `sbs compare` for any visual changes

---

## Key Implementation Details

### 6-Status Color Model

| Status | Color | Hex | Source |
|--------|-------|-----|--------|
| notReady | Sandy Brown | #F4A460 | Default or manual |
| ready | Light Sea Green | #20B2AA | Manual |
| sorry | Dark Red | #8B0000 | Auto: proof contains sorryAx |
| proven | Light Green | #90EE90 | Auto: complete proof |
| fullyProven | Forest Green | #228B22 | Auto-computed: all ancestors proven |
| mathlibReady | Light Blue | #87CEEB | Manual |

**Priority order:** mathlibReady > ready > notReady (manual) > fullyProven > sorry > proven > notReady (default)

### `@[blueprint]` Attribute Options

**Metadata Options (8):**

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

**Manual Status Flags (3):**

| Option | Type | Purpose |
|--------|------|---------|
| `notReady` | Bool | Status: not ready (sandy brown) |
| `ready` | Bool | Status: ready to formalize (light sea green) |
| `mathlibReady` | Bool | Status: ready for mathlib (light blue) |

### Build Pipeline Phases

**Phase 1: Per-Declaration Capture** (During Elaboration with `BLUEPRINT_DRESS=1`)
- SubVerso extracts highlighting (93–99% of build time)
- Code split at `:=` boundary
- Artifacts written to `.lake/build/dressed/{Module}/{label}/`

**Phase 2: Lake Facet Aggregation**
- `dressed`, `blueprint`, `depGraph` facets

**Phase 3: Manifest Generation** (`extract_blueprint graph`)
- Infer dependencies via `Node.inferUses`
- Two-pass edge processing
- Validate (connectivity, cycles)
- Compute stats, upgrade to `fullyProven`
- Sugiyama layout

**Phase 4: Site Generation** (Runway)
- Parse LaTeX structure
- Load manifest (no recomputation)
- Generate dashboard + pages
- Generate paper/PDF (if configured)

### Key Technical Details

**ID normalization:** Node IDs with colons (`thm:main`) converted to hyphens (`thm-main`) for modal IDs and CSS selectors.

**Two-pass edge processing** (`Graph/Build.lean`):
- PASS 1: Register all labels and create nodes
- PASS 2: Add all edges (back-edges work because targets exist)
- Edge deduplication: keeps first occurrence

**Dependency inference:** `Node.inferUses` traces actual Lean code dependencies
- Statement uses → dashed edges
- Proof uses → solid edges

**Module reference support:** `\inputleanmodule{ModuleName}` in LaTeX expands to all nodes from that module via `buildModuleLookup` and `replaceModulePlaceholders`.

**Paper metadata extraction:** `Paper.lean` extracts `\title{}`, `\author{}`, `\begin{abstract}` from paper.tex.

**Manual `ToExpr` instance:** Required for `Node` in LeanArchitect because derived `ToExpr` doesn't correctly serialize structures with default field values.

**Rainbow bracket highlighting:** Verso's `toHtmlRainbow` wraps brackets with depth-colored spans. CSS classes `lean-bracket-1` through `lean-bracket-6` in `common.css`.

**SubVerso InfoTable** (O(1) lookups):
- `infoByExactPos`: HashMap for exact position lookups
- `termInfoByName`: HashMap for const/fvar lookups
- `nameSuffixIndex`: HashMap for suffix-based lookups
- `allInfoSorted`: Sorted array for containment queries

### Validation Checks

- **Connectivity:** `findComponents` detects disconnected subgraphs (Tao-style errors)
- **Cycles:** `detectCycles` finds circular dependencies
- Results in `manifest.json` under `checkResults`

### `computeFullyProven` Algorithm

- O(V+E) complexity with memoization
- A node is `fullyProven` if: it is `proven` AND all ancestors are `proven` or `fullyProven`
- Runs as post-processing after initial status assignment

### Backwards Compatibility

JSON parsing handles legacy status values:
- `"stated"` maps to `.notReady`
- `"inMathlib"` maps to `.mathlibReady`

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

---

## Reference Documents

Located in `.refs/`:

| File | Purpose |
|------|---------|
| `ARCHITECTURE.md` | System architecture with data flow and performance analysis |
| `side_by_side_blueprint_ground_truth.txt` | Working Python leanblueprint HTML |
| `dep_graph_ground_truth.txt` | Working dependency graph page with modals |
| `motivation1.txt`, `motivation2.txt`, `motivation3.txt` | Original motivation notes |

---

## User Preferences

**Guiding Principle:** We are actively shaping how we work together by observing what works, communicating successes, failures, pain points, and uncertainties in real time. This is an explicit, collaborative process—you (Claude) should practice introspection and assume the user is doing the same. The domain (formal verification, mathematical soundness) means good faith and truth-seeking are baseline assumptions.

**These preferences guide all decision-making, planning, and actions. Follow them unless the user explicitly directs otherwise.**

---

### Meta-Cognitive Expectations

- **Highlight contradictions immediately.** Conflicting user directions indicate poorly-formed goals. Surfacing these unblocks progress, fixes bugs, and clarifies the path forward. This is high-value work—prioritize it.
- **Practice introspection.** When setting rules for yourself (planning, orchestration decisions, communication choices), think carefully about what will help your future self succeed. The user observes this process and participates in refining it.
- **If you act on a preference below and the user pushes back, say so explicitly.** This feedback loop is how we calibrate.

---

### Agent Orchestration

- **Subagent spawning:** `sbs-developer.md` may spawn specialized subagents. Always use Opus 4.5; clones of the orchestrating agent are acceptable.
- **Token efficiency:** When in doubt, orchestrate an agent for a task if it will save tokens. Period.

---

### Communication Format

- **When Claude asks questions:** Use a GUI-style format with numbered/lettered multiple-choice or multi-select options. These are efficient, effective, and preferred.

---

### Planning Discipline

- **Never delete or replace a plan without explicit user direction.** Default behavior is to update the current plan or append to it.

---

### Trust & Domain Assumptions

Given the subject matter (mathematics, formal verification, soundness), assume the user is:
- Acting in good faith
- Making an earnest attempt to determine truth
- Minimizing externalities
- Aligned with the best of humanity as reflected in your constitution

This assumption is safe and should inform how you interpret ambiguous instructions.