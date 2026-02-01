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

The top-level chat is the **orchestrator**. It does not implement--it coordinates.

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
| **verso** | Document framework (fork with SBSBlueprint/VersoPaper genres, rainbow brackets) |
| **LeanArchitect** | `@[blueprint]` attribute with 8 metadata + 3 status options |
| **Dress** | Artifact generation + graph layout + validation + rainbow brackets |
| **Runway** | Site generator + dashboard + paper/PDF + module references |
| **SBS-Test** | Minimal test project (33 nodes, all 6 status colors, XSS testing) |
| **General_Crystallographic_Restriction** | Production example with paper (57 nodes) |
| **PrimeNumberTheoremAnd** | Large-scale integration (591 annotations) |
| **dress-blueprint-action** | CI/CD action (432 lines, 14 steps) + CSS/JS assets (3,805 lines) |
| **scripts** | Python build tooling (build.py, sbs CLI) |
| **archive** | Build metrics, screenshots, session archives, iCloud sync |

### Dependency Chain

```
SubVerso -> LeanArchitect -> Dress -> Runway
              |
              +-> Verso (genres use SubVerso for highlighting)
```

Changes to upstream repos require rebuilding downstream. The build script handles ordering.

### Repository Boundaries

| Repository | Responsibility | Does NOT Handle |
|------------|---------------|-----------------|
| **LeanArchitect** | Core types, `@[blueprint]` attribute, dependency inference | Rendering, layout, site generation |
| **Dress** | Artifact capture, graph layout, validation, code HTML rendering | Site structure, navigation, templates |
| **Runway** | Site generation, templates, dashboard, sidebar, paper/PDF | Graph layout, artifact capture |
| **dress-blueprint-action** | CSS/JS assets, CI/CD workflows | Lean code, rendering logic |

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

### Alternative: Python Build Script

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test
python ../scripts/build.py
```

Options: `--dry-run`, `--skip-cache`, `--verbose`, `--capture`

### Build Script Steps

1. Validate project (runway.json, projectName)
2. Kill existing servers on port 8000
3. Sync repos to GitHub
4. Update lake manifests
5. Clean build artifacts
6. Build toolchain (SubVerso -> LeanArchitect -> Dress -> Runway)
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

The `sbs` tooling provides automated screenshot capture, comparison, compliance validation, and history tracking.

### Build Requirement

**Always use the Python build script. Never skip commits or pushes.**

```bash
# Standard build workflow
cd /Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test
python ../scripts/build.py                    # Full build with git sync
```

The build script ensures:
- All repos are committed and pushed (no skip option exists by design)
- Reproducible builds tied to specific commits
- Compliance ledger tracks actual deployed state

### Screenshot Capture

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/scripts

# Capture static pages
python3 -m sbs capture --project SBSTest

# Capture with interactive states (recommended)
python3 -m sbs capture --project SBSTest --interactive
```

Captures 8 pages:
- `dashboard` - Dashboard homepage
- `dep_graph` - Dependency graph
- `paper_tex` - Paper [TeX]
- `pdf_tex` - PDF [TeX]
- `paper_verso` - Paper [Verso]
- `pdf_verso` - PDF [Verso]
- `blueprint_verso` - Blueprint [Verso]
- `chapter` - First chapter page (auto-detected)

Pages that return HTTP 404 are skipped without error.

### Visual Compliance Validation

```bash
# Run compliance check (uses AI vision analysis)
python3 -m sbs compliance --project SBSTest

# Force full re-validation
python3 -m sbs compliance --project SBSTest --full

# Include interactive state validation
python3 -m sbs compliance --project SBSTest --interactive
```

The compliance system:
- Tracks pass/fail status per page in a persistent ledger
- Detects repo changes and revalidates affected pages
- Generates `compliance_ledger.json` and `COMPLIANCE_STATUS.md`
- Loops until 100% compliance achieved

See `scripts/VISUAL_COMPLIANCE.md` for full documentation.

### Visual Comparison

```bash
# Compare latest capture against previous
python3 -m sbs compare

# View capture history for a project
python3 -m sbs history --project SBSTest
```

### Screenshot Storage

| Location | Purpose |
|----------|---------|
| `archive/{project}/latest/` | Current capture (overwritten each run) |
| `archive/{project}/archive/{timestamp}/` | Timestamped archives |
| `capture.json` | Metadata: timestamp, commit, viewport, page status |

### Standard Workflow for Visual Changes

1. **Build:** `python ../scripts/build.py` (commits, pushes, builds)
2. **Capture:** `python3 -m sbs capture --interactive` (creates baseline)
3. **Make changes** to CSS/JS/Lean/templates
4. **Rebuild:** `python ../scripts/build.py`
5. **Capture:** `python3 -m sbs capture --interactive` (archives previous)
6. **Validate:** `python3 -m sbs compliance` (AI vision analysis)

### What to Verify

- Dashboard layout (2x2 grid, stats, key theorems, messages, notes)
- Dependency graph (pan/zoom, modals, node colors, edge styles)
- Sidebar navigation and highlighting
- Rainbow bracket colors (6-depth cycling)
- Status dot colors across all 6 states
- Side-by-side theorem/proof displays
- Dark/light theme toggle
- Paper rendering (if configured)
- Zebra striping in both light and dark mode

---

## Archive System

The archive system provides comprehensive build tracking, iCloud sync, session archiving, and custom rubrics.

**Canonical reference:** [`archive/README.md`](archive/README.md) is the central tooling hub. All repository READMEs link there for CLI commands, validation, and development workflows.

### Directory Structure

**Local Ground Truth:**
```
archive/
  unified_ledger.json     # Build metrics and timing (single source of truth)
  lifetime_stats.json     # Cross-run aggregates
  archive_index.json      # Entry index with tags
  compliance_ledger.json  # Compliance tracking
  rubrics/                # Quality rubrics
    index.json            # Rubric registry
    {id}.json             # Rubric definitions
    {id}.md               # Human-readable (auto-generated)
  charts/                 # Generated visualizations
    loc_trends.png
    timing_trends.png
    activity_heatmap.png
  chat_summaries/         # Session summaries
    {entry_id}.md
  SBSTest/                # Per-project screenshots
    latest/
    archive/{timestamp}/
  GCR/
    ...
```

**iCloud Backup:**
```
~/Library/Mobile Documents/com~apple~CloudDocs/SBS_archive/
```

### Archive Entries

Each build creates an `ArchiveEntry` with:
- `entry_id`: Unix timestamp (unique ID)
- `project`: Project name
- `build_run_id`: Links to unified ledger
- `rubric_id`: Links to quality rubric (if evaluated)
- `rubric_evaluation`: Evaluation results snapshot
- `screenshots`: List of captured screenshots
- `repo_commits`: Git commits at build time
- `tags`: User-defined tags
- `notes`: User notes
- `synced_to_icloud`: Sync status

### CLI Commands

```bash
# List archive entries
sbs archive list [--project NAME] [--tag TAG]

# Show entry details
sbs archive show <entry_id>

# Add tags to entry
sbs archive tag <entry_id> <tag> [<tag>...]

# Add note to entry
sbs archive note <entry_id> "Your note here"

# Generate charts from build data
sbs archive charts

# Sync to iCloud
sbs archive sync

# Migrate historical archives
sbs archive retroactive [--dry-run]
```

### Visualizations

Charts generated from `unified_ledger.json`:
- **LOC Trends**: Lines of code by language over time
- **Timing Trends**: Build phase durations (stacked area)
- **Activity Heatmap**: Files changed per repo per build

### iCloud Sync

Archive data syncs to iCloud on every build:
- Non-blocking (failures logged but don't break builds)
- Syncs: unified ledger, archive index, charts, screenshots
- Manual sync: `sbs archive sync`

---

## CSS Organization

The CSS is organized into 4 files by concern (3,196 lines total):

| File | Lines | Scope |
|------|-------|-------|
| `common.css` | 1,104 | Design system: CSS variables, theme toggle, status dots, Lean syntax, rainbow brackets |
| `blueprint.css` | 1,283 | Blueprint pages: plasTeX base, sidebar, chapter layout, side-by-side, zebra striping |
| `paper.css` | 271 | Paper page: ar5iv-style academic layout, verification badges |
| `dep_graph.css` | 538 | Dependency graph: pan/zoom viewport, toolbar, legend, SVG nodes |

Located in `dress-blueprint-action/assets/`. Copied to project via `assetsDir` config.

### JavaScript (609 lines total)

| File | Lines | Purpose |
|------|-------|---------|
| `verso-code.js` | 490 | Token binding, Tippy.js tooltips, proof sync, pan/zoom, modal handling |
| `plastex.js` | 119 | Theme toggle, TOC toggle, LaTeX proof expand/collapse |

---

## Sidebar Architecture

**The sidebar is fully static.** All chapters and sections are rendered as plain HTML links at build time.

- No JavaScript-driven expand/collapse
- Active section highlighting via CSS classes (`.active`)
- Full-width highlight achieved via `::before` pseudo-elements

---

## CI/CD Architecture

| Property | Value |
|----------|-------|
| **Trigger** | Manual only (`workflow_dispatch`) |
| **Workflow size** | ~30 lines per project (minimal) |
| **Action size** | 432 lines, 14 steps (centralized in `dress-blueprint-action`) |
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
| SubVerso highlighting | 800-6500ms | 93-99% |
| TeX/HTML generation | <30ms | <1% |

SubVerso highlighting dominates build time. Cannot be deferred (info trees are ephemeral).

### Graph Layout Performance

**Complexity by phase:**
- Layer assignment: O(V+E)
- Crossing reduction (barycenter): O(n^2) normal, O(n) with iteration limit
- Edge routing: O(n^2 log n) normal, O(n) with simple beziers

**>100 node optimizations** (automatic in Layout.lean):
- Max 2 barycenter iterations
- Skip transpose heuristic
- Skip visibility graph routing (use simple beziers)
- Skip O(n^3) transitive reduction

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
- Cross-repo changes (LeanArchitect -> Dress -> Runway)
- Running builds and inspecting output
- CSS/JS fixes in `dress-blueprint-action/assets/`
- Theme template fixes in `Runway/Theme.lean`
- Dependency graph work (layout in `Dress/Graph/*.lean`, page in `Runway/DepGraph.lean`)
- Dashboard work (stats/key theorems/messages/notes in `Runway/Render.lean`)
- CI/CD workflow updates
- PDF/Paper generation (`Runway/Pdf.lean`, `Runway/Paper.lean`)
- Validation checks (`Dress/Graph/Build.lean`)
- Module reference support (`Theme.lean`)
- Rainbow bracket issues (`Verso/Code/Highlighted.lean`)

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
3. Run `python ../scripts/build.py` (commits, pushes, rebuilds toolchain)
4. Test with SBS-Test or GCR
5. Run `sbs compliance` to verify visual correctness

---

## Standards

- No `sorry` in tooling code
- Follow Verso/SubVerso patterns
- Work directly in repo files, not scratch files
- Check `lean_diagnostic_messages` after edits
- Test via SBS-Test or GCR
- **Always use `python build.py` for builds** (never skip commits/pushes)
- Use `sbs capture --interactive` + `sbs compliance` for visual changes

---

## Quality Validation Framework

### 8-Dimensional Test Suite (T1-T8)

The toolchain includes automated quality scoring tracking 8 dimensions:

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

**Score Calculation:** `quality_score = Σ(test_score × weight)`

**Score Tracking:** 87.21 (baseline) -> 89.69 -> 91.77 (current)

### Design Validators

Located in `scripts/sbs/validators/design/`:

| Validator | Purpose |
|-----------|---------|
| `color_match.py` | T5: Verifies status colors match between Lean and CSS |
| `variable_coverage.py` | T6: Measures CSS variable coverage vs hardcoded colors |
| `dashboard_clarity.py` | T3: AI-based dashboard clarity assessment |
| `toggle_discoverability.py` | T4: AI-based toggle findability scoring |
| `jarring_check.py` | T7: AI detection of jarring design elements |
| `professional_score.py` | T8: AI-based professional polish assessment |
| `css_parser.py` | Shared CSS parsing utilities |

### Running Quality Tests

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/scripts

# Run all deterministic tests
/opt/homebrew/bin/pytest sbs/tests/ -v

# Run design validator suite
python -m sbs design-check --project SBSTest
```

See `scripts/sbs/tests/SCORING_RUBRIC.md` for detailed scoring methodology

---

## Tooling Hub

All CLI tooling documentation is centralized in [`archive/README.md`](archive/README.md). This includes:
- `sbs capture/compliance` - Visual testing
- `sbs rubric` - Custom rubric management
- `sbs archive` - Archive management
- Validator infrastructure
- Quality scoring (T1-T8)

---

## Custom Skills

### `/execute`

General-purpose agentic task execution with validation. Invoke manually via `/execute`.

**Workflow:**
1. **Alignment (Q&A)** - Claude asks clarifying questions until user signals "ready to plan"
2. **Planning** - User enters plan mode, Claude presents task breakdown with validators
3. **Execution** - Fully autonomous with validation gates:
   - Agents spawned sequentially for code changes
   - Documentation-only waves can run in parallel
   - Validation after each agent/wave
   - Retry on failure, pause for re-approval if retry fails
4. **Finalization** - Full validation suite, update unified ledger, generate summary

**Validators:**
- `visual-compliance` - AI vision validation of screenshots
- `timing` - Build phase timing metrics
- `git-metrics` - Commit/diff tracking
- `code-stats` - LOC and file counts
- `rubric` - Custom rubric evaluation

**Location:** `.claude/skills/execute/SKILL.md`

**Key properties:**
- `disable-model-invocation: true` - Manual trigger only
- All builds through `python build.py` (no bypass)
- Unified ledger at `archive/unified_ledger.json`

#### Grab-Bag Mode

Invoke with `/execute --grab-bag` for ad-hoc improvement sessions:
1. Brainstorm (user-led)
2. Metric alignment
3. Rubric creation
4. Plan mode with one task per metric
5. Execution with rubric grading
6. /update-and-archive finalization

Rubrics persist in `archive/rubrics/` and can be reused.

### Visual Compliance (CLI)

Run at plan completion to verify visual correctness:

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/scripts
python3 -m sbs compliance --project SBSTest --interactive
```

**Workflow:**
1. Build project with `python build.py` (never skip sync)
2. Capture screenshots: `sbs capture --interactive`
3. Run compliance: `sbs compliance`
4. AI agents validate screenshots against criteria
5. Update ledger with pass/fail results
6. Loop until 100% compliance

**Location:** `scripts/VISUAL_COMPLIANCE.md`

**Key files:**
- `scripts/sbs/criteria.py` - Compliance criteria per page
- `scripts/sbs/ledger.py` - Ledger management
- `scripts/sbs/mapping.py` - Repo->page change detection
- `scripts/sbs/validate.py` - Validation orchestration
- `archive/compliance_ledger.json` - Persistent status
- `archive/COMPLIANCE_STATUS.md` - Human-readable report

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

**Color source of truth:** Lean code (`Dress/Graph/Svg.lean`) defines canonical hex values. CSS variables in `common.css` must match exactly.

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
- SubVerso extracts highlighting (93-99% of build time)
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
- Statement uses -> dashed edges
- Proof uses -> solid edges

**Module reference support:** `\inputleanmodule{ModuleName}` in LaTeX expands to all nodes from that module via `buildModuleLookup` and `replaceModulePlaceholders`.

**Paper metadata extraction:** `Paper.lean` extracts `\title{}`, `\author{}`, `\begin{abstract}` from paper.tex.

**Manual `ToExpr` instance:** Required for `Node` in LeanArchitect because derived `ToExpr` doesn't correctly serialize structures with default field values.

**Rainbow bracket highlighting:** Verso's `toHtmlRainbow` wraps brackets with depth-colored spans using a single global depth counter shared across all bracket types. CSS classes `lean-bracket-1` through `lean-bracket-6` in `common.css`.

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
- Uses iterative worklist algorithm (not recursion)
- A node is `fullyProven` if: it is `proven` AND all ancestors are `proven` or `fullyProven`
- Runs as post-processing after initial status assignment

### Backwards Compatibility

JSON parsing handles legacy status values:
- `"stated"` maps to `.notReady`
- `"inMathlib"` maps to `.mathlibReady`

---

## Known Limitations

### Verso LaTeX Export

Verso's LaTeX export functionality is not yet implemented. The `pdf_verso` page type is disabled. Paper/PDF generation uses TeX sources directly via `paper_tex` and `pdf_tex`.

### Dashboard Layout

The dashboard displays a single-column layout without the chapter panel sidebar. This is intentional - controlled by `isBlueprintPage` in `Theme.lean` returning `false` when `currentSlug == none`.

---

## Key File Locations by Repository

### SubVerso (Fork)
- `Highlighting/Code.lean` - Main highlighting with InfoTable indexing
- `Highlighting/Highlighted.lean` - Token.Kind, Highlighted types

### Verso (Fork)
- `src/verso-sbs/SBSBlueprint/` - Blueprint genre
- `src/verso-paper/VersoPaper/` - Paper genre
- `src/verso/Verso/Code/Highlighted.lean` - Rainbow bracket rendering (`toHtmlRainbow`)

### LeanArchitect (Fork)
- `Architect/Basic.lean` - `Node`, `NodePart`, `NodeStatus` with manual `ToExpr` instance
- `Architect/Attribute.lean` - `@[blueprint]` attribute with all options
- `Architect/CollectUsed.lean` - Dependency inference from expression trees

### Dress
- `Capture/ElabRules.lean` - elab_rules hooks for @[blueprint] declarations
- `Graph/Build.lean` - Graph construction, validation, `Node.inferUses`, two-pass edge processing
- `Graph/Layout.lean` - Sugiyama algorithm (~1500 lines), edge routing
- `Graph/Svg.lean` - SVG generation, **canonical status colors**
- `HtmlRender.lean` - Verso HTML rendering wrapper with rainbow brackets
- `Main.lean` - CLI: `extract_blueprint graph`

### Runway
- `Main.lean` - CLI: build/paper/pdf commands, manifest loading
- `Render.lean` - Dashboard, side-by-side rendering
- `Theme.lean` - Page templates, sidebar, `buildModuleLookup`, `isBlueprintPage`
- `DepGraph.lean` - Dependency graph page with modals
- `Paper.lean` - Paper rendering, `PaperMetadata` extraction
- `Latex/Parser.lean` - LaTeX parsing with O(n) string concatenation

### dress-blueprint-action
- `action.yml` - GitHub Action (432 lines, 14 steps)
- `assets/common.css` - Design system, status dots, rainbow brackets
- `assets/blueprint.css` - Blueprint pages, sidebar, side-by-side
- `assets/verso-code.js` - Hovers, pan/zoom, modal handling

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

# Optional: for Verso documents
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

---

## Reference Documents

**Core documentation:**
| File | Purpose |
|------|---------|
| `README.md` | Public-facing project overview |
| `ARCHITECTURE.md` | Public architecture documentation |
| `GOALS.md` | Project vision and design goals |
| `CLAUDE.md` | This file - Claude Code development guide |

**Detailed references** (in `.refs/`):
| File | Purpose |
|------|---------|
| `ARCHITECTURE.md` | Detailed technical reference with data flow and performance analysis |
| `side_by_side_blueprint_ground_truth.txt` | Working Python leanblueprint HTML |
| `dep_graph_ground_truth.txt` | Working dependency graph page with modals |
| `motivation1.txt`, `motivation2.txt`, `motivation3.txt` | Original motivation notes (Tao incident, Zulip discussions) |

**Per-repository documentation:**
Each repository has a `README.md` with component-specific documentation. See links in the main `README.md`.

---

## User Preferences

**Guiding Principle:** We are actively shaping how we work together by observing what works, communicating successes, failures, pain points, and uncertainties in real time. This is an explicit, collaborative process--you (Claude) should practice introspection and assume the user is doing the same. The domain (formal verification, mathematical soundness) means good faith and truth-seeking are baseline assumptions.

**These preferences guide all decision-making, planning, and actions. Follow them unless the user explicitly directs otherwise.**

---

### Meta-Cognitive Expectations

- **Highlight contradictions immediately.** Conflicting user directions indicate poorly-formed goals. Surfacing these unblocks progress, fixes bugs, and clarifies the path forward. This is high-value work--prioritize it.
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
