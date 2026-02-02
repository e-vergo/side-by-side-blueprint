# Side-by-Side Blueprint Architecture

![Lean](https://img.shields.io/badge/Lean-v4.27.0-blue)
![License](https://img.shields.io/badge/License-Apache%202.0-green)

> **Prototype Status**: Alpha software with known bugs, slow workflows, and incomplete features.

Pure Lean toolchain for formalization documentation that displays formal proofs alongside LaTeX theorem statements.

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
    storage/                # Archive (screenshots, metrics, rubrics)
    .refs/                  # Detailed reference docs
    markdowns/              # Public documentation (this file)
    build-sbs-test.sh       # One-click SBS-Test build
    build-gcr.sh            # One-click GCR build
    build-pnt.sh            # One-click PNT build
```

## Table of Contents

- [Overview](#overview)
- [Dependency Chain](#dependency-chain)
- [Build Pipeline](#build-pipeline)
- [Output Directories](#output-directories)
- [Node Status Model](#node-status-model)
- [Dependency Graph](#dependency-graph)
- [Validation Checks](#validation-checks)
- [Performance](#performance)
- [CI/CD Architecture](#cicd-architecture)
- [Configuration](#configuration)

## Overview

Components work together to produce formalization documentation:

| Component | Location | Purpose |
|-----------|----------|---------|
| **SubVerso** | `forks/subverso/` | Syntax highlighting extraction from Lean info trees with O(1) indexed lookups |
| **LeanArchitect** | `forks/LeanArchitect/` | `@[blueprint]` attribute with 8 metadata options + 3 manual status flags |
| **Dress** | `toolchain/Dress/` | Artifact generation, rainbow brackets, dependency graph layout, stats computation, validation |
| **Runway** | `toolchain/Runway/` | Site generator with dashboard, PDF/paper generation, module reference support |
| **Verso** | `forks/verso/` | Document framework with SBSBlueprint and VersoPaper genres |
| **dress-blueprint-action** | `toolchain/dress-blueprint-action/` | GitHub Action (432 lines, 14 steps) + CSS/JS assets (3,805 lines) |
| **SBS-Test** | `toolchain/SBS-Test/` | Minimal test project (33 nodes, all 6 status colors, validation testing) |
| **General_Crystallographic_Restriction** | `showcase/General_Crystallographic_Restriction/` | Production example with full paper generation (57 nodes) |
| **PrimeNumberTheoremAnd** | `showcase/PrimeNumberTheoremAnd/` | Large-scale integration (591 annotations) |

## Dependency Chain

```
SubVerso -> LeanArchitect -> Dress -> Runway
              |
              +-> Verso (genres use SubVerso for highlighting)
```

All components use Lean v4.27.0.

## Build Pipeline

```
@[blueprint "label"] theorem foo ...
        |
        v
DRESS (during elaboration):
  - SubVerso extracts highlighting from info trees (800-6500ms, 93-99% of time)
  - Splits code into signature + proof body
  - Renders HTML with hover data via Verso
  - Applies rainbow bracket highlighting (toHtmlRainbow)
  - Writes: decl.tex, decl.html, decl.json, decl.hovers.json
        |
        v
LAKE FACETS (after compilation):
  - :blueprint aggregates module artifacts
  - :depGraph generates dep-graph.json + dep-graph.svg
  - Computes stats (StatusCounts) and extracts project metadata
  - Uses Node.inferUses for real Lean code dependency inference
  - Validates graph: connectivity check, cycle detection
  - Two-pass edge processing for proper back-edge handling
  - Writes manifest.json with precomputed stats and validation results
        |
        v
RUNWAY (post-build):
  - Parses blueprint.tex for chapter/section structure
  - Loads artifacts from .lake/build/dressed/
  - Loads manifest.json (precomputed stats, no recomputation)
  - Expands `\inputleanmodule{ModuleName}` placeholders
  - Copies assets from assetsDir to output
  - Generates dashboard homepage + multi-page static site
  - Optionally: paper.html + paper.pdf + pdf.html (viewer)
```

## Output Directories

### Dress Artifacts (.lake/build/dressed/)

```
.lake/build/dressed/
  {Module/Path}/
    {sanitized-label}/
      decl.tex          # LaTeX with base64 HTML
      decl.html         # Syntax-highlighted HTML with rainbow brackets
      decl.json         # Metadata + highlighting
      decl.hovers.json  # Tooltip data
  dep-graph.json        # D3.js graph data
  dep-graph.svg         # Static Sugiyama layout
  manifest.json         # Stats, validation, project metadata
```

### Runway Output (.lake/build/runway/)

```
.lake/build/runway/
  index.html            # Dashboard homepage
  dep_graph.html        # Full dependency graph with rich modals
  chapter*.html         # Per-chapter pages
  paper_tex.html        # Paper with MathJax + Lean links (if configured)
  paper.pdf             # Compiled PDF (requires LaTeX compiler)
  pdf_tex.html          # Embedded PDF viewer page
  manifest.json         # Node index
  assets/
    common.css          # Theme toggle, base styles, status dots, rainbow brackets
    blueprint.css       # Full stylesheet including modal and graph styles
    paper.css           # Paper-specific styles
    dep_graph.css       # Graph page styles
    plastex.js          # LaTeX proof toggle
    verso-code.js       # Hovers, bindings, pan/zoom, modal init
```

## Node Status Model

Six status colors for tracking formalization progress:

| Status | Color | Hex | Source |
|--------|-------|-----|--------|
| notReady | Sandy Brown | #F4A460 | Default + Manual: `(notReady := true)` |
| ready | Light Sea Green | #20B2AA | Manual: `(ready := true)` |
| sorry | Dark Red | #8B0000 | Auto: proof contains sorryAx |
| proven | Light Green | #90EE90 | Auto: complete proof |
| fullyProven | Forest Green | #228B22 | Auto-computed: proven + all ancestors proven/fullyProven |
| mathlibReady | Light Blue | #87CEEB | Manual: `(mathlibReady := true)` |

**Priority order** (manual always wins):
1. `mathlibReady` (manual) - highest
2. `ready` (manual)
3. `notReady` (manual, if explicitly set)
4. `fullyProven` (auto-computed from graph)
5. `sorry` (auto-detected via sorryAx)
6. `proven` (auto-detected, has Lean without sorry)
7. `notReady` (default, no Lean code)

**Color source of truth:** Lean code in `Dress/Graph/Svg.lean` defines canonical hex values. CSS variables in `common.css` must match exactly.

### Node Shapes and Edge Styles

| Shape | Used For |
|-------|----------|
| Rectangle (box) | def, abbrev, structure, class, instance |
| Ellipse | theorem, lemma, proposition, corollary, example |

| Edge Style | Meaning |
|------------|---------|
| Solid | Proof dependency (from `Node.inferUses` proofUses) |
| Dashed | Statement dependency (from `Node.inferUses` statementUses) |

## Dependency Graph

### Layout Algorithm (Dress/Graph/Layout.lean)

Sugiyama-style hierarchical layout (~1500 lines):
1. **Acyclic transformation**: DFS identifies and reverses back-edges
2. **Layer assignment**: Top-to-bottom, respecting edge directions
3. **Crossing reduction**: Median heuristic for node ordering within layers
4. **Position refinement**: Iterative adjustment for better spacing
5. **Edge routing**: Visibility graph + Dijkstra shortest path + Bezier fitting

### Large Graph Optimizations (>100 nodes)

| Optimization | Normal | >100 nodes | Rationale |
|--------------|--------|------------|-----------|
| Barycenter iterations | Unlimited | Max 2 | O(n) per iteration |
| Transpose heuristic | Yes | Skipped | O(n^2) adjacent swaps |
| Visibility graph routing | Yes | Skipped | O(n^2) graph construction |
| Transitive reduction | O(n^3) Floyd-Warshall | Skipped | Multi-hour build times |

## Validation Checks

**Connectivity** (`findComponents`): Detects disconnected subgraphs (warns about unreachable nodes)

**Cycles** (`detectCycles`): Finds circular dependencies via DFS

Results stored in `manifest.json`:
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

**`computeFullyProven` algorithm**: O(V+E) with memoization. A node is `fullyProven` if it is `proven` AND all ancestors are `proven` or `fullyProven`.

## Performance

| Operation | Time | Percentage |
|-----------|------|------------|
| SubVerso highlighting | 800-6500ms | 93-99% |
| TeX/HTML generation | <30ms | <1% |

SubVerso highlighting dominates build time. Cannot be deferred (info trees are ephemeral).

**Expected build times:**

| Project | Nodes | Layout Time | Total Build |
|---------|-------|-------------|-------------|
| SBS-Test | 33 | <1s | ~2 min |
| GCR | 57 | ~2s | ~5 min |
| PNT | 591 | ~15s | ~20 min |

## CI/CD Architecture

### Design Philosophy

- **Manual triggers only**: `workflow_dispatch` - user controls deployments
- **Simplified workflows**: ~30 lines per project
- **Centralized complexity**: `dress-blueprint-action` (432 lines, 14 steps)
- **No GitHub Actions mathlib cache**: relies on mathlib server (`lake exe cache get`)

### Action Inputs

| Input | Default | Purpose |
|-------|---------|---------|
| `project-directory` | `.` | Directory containing lakefile.toml and runway.json |
| `lean-version` | (auto) | Override Lean version |
| `docgen4-mode` | `skip` | DocGen4 mode: `skip`, `docs-static`, or `generate` |
| `deploy-pages` | `true` | Upload artifact for GitHub Pages |

### DocGen4 Modes

| Mode | Behavior |
|------|----------|
| `skip` | No DocGen4 (fastest, default) |
| `docs-static` | Download from `docs-static` branch |
| `generate` | Run `lake -R -Kenv=dev build +:docs` (slow, ~1 hour) |

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
  "paperTexPath": "paper/paper.tex",
  "assetsDir": "/path/to/dress-blueprint-action/assets"
}
```

Paper metadata (title, authors, abstract) is extracted from `paper.tex` using `\title{}`, `\author{}` (split on `\and`), and `\begin{abstract}...\end{abstract}`.

### lakefile.toml

```toml
[[require]]
name = "Dress"
git = "https://github.com/e-vergo/Dress"
rev = "main"

# Optional: mathlib (pin to v4.27.0)
[[require]]
name = "mathlib"
git = "https://github.com/leanprover-community/mathlib4.git"
rev = "v4.27.0"

# Optional: Verso documents
[[require]]
name = "verso"
git = "https://github.com/e-vergo/verso.git"
rev = "main"
```

## Quality Validation

The toolchain includes an 8-dimensional quality scoring system:

**Deterministic Tests (T1, T2, T5, T6):** CLI execution, ledger population, status color matching, CSS variable coverage

**Heuristic Tests (T3, T4, T7, T8):** Dashboard clarity, toggle discoverability, jarring-free check, professional score

**Current Score:** 91.77/100 (as of 2026-02-01)

Design validators in `dev/scripts/sbs/tests/validators/design/` automate quality checks. Run with:
```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
/opt/homebrew/bin/pytest sbs/tests/pytest/ -v
```

## Tooling

For build commands, screenshot capture, compliance validation, archive management, and custom rubrics, see the [Storage & Tooling Hub](../storage/README.md).

### MCP Tools

The `sbs-lsp-mcp` server (located at `forks/sbs-lsp-mcp/`) provides 29 tools: 18 Lean tools for proof development and 11 SBS tools for orchestration, testing, and archive management. See the server README for full documentation.

### One-Click Build Scripts

From the monorepo root:

```bash
./dev/build-sbs-test.sh   # SBS-Test (~2 min)
./dev/build-gcr.sh        # GCR (~5 min)
./dev/build-pnt.sh        # PNT (~20 min)
```

These scripts wrap `python dev/scripts/build.py` with the correct working directory.

## Document Taxonomy

Documentation is organized into three categories, each with distinct characteristics and update expectations.

### Categories

| Category | Location | Change Frequency | Meaning of Changes |
|----------|----------|------------------|-------------------|
| **Permanent** | `dev/markdowns/permanent/` | Months+ | Architectural shifts - changes affect agent behavior and assumptions |
| **Living** | `dev/markdowns/living/` | Days to weeks | Progress updates - normal development activity |
| **Generated** | Various locations | On source change | Informational - regenerate from source when needed |

### Permanent Documents

Architectural bedrock. Changes are significant events, not routine updates.

| Document | Purpose |
|----------|---------|
| `ARCHITECTURE.md` | Build pipeline, component responsibilities, dependency chain |
| `Archive_Orchestration_and_Agent_Harmony.md` | Script-agent boundary, archive roles, state machine model |
| `GOALS.md` | Project vision, problem statement, target audience |

### Living Documents

Current state and evolving documentation. Changes are expected and normal.

| Document | Purpose |
|----------|---------|
| `README.md` | Meta-document for agents about monorepo purpose |
| `MVP.md` | Current minimum viable product definition |

### Generated Documents

Auto-produced from code or other sources. Manual edits will be overwritten.

| File | Source | Generator |
|------|--------|-----------|
| `.claude/agents/sbs-oracle.md` | All repository READMEs | `sbs oracle compile` |
| `dev/storage/{project}/QUALITY_SCORE.md` | Validator results | Quality scoring system |
| `dev/storage/COMPLIANCE_STATUS.md` | Compliance ledger | Compliance validation |

### Decision Guide

When creating or updating documentation:

1. **Auto-generated from code?** -> Generated category (ensure regeneration pipeline exists)
2. **Changes frequently with progress?** -> Living category (`dev/markdowns/living/`)
3. **Fundamental architectural decision?** -> Permanent category (`dev/markdowns/permanent/`)
4. **Reference for agents that should be stable?** -> Permanent category

## Related Documents

- [GOALS.md](GOALS.md) - Project vision and design goals
- [README.md](../living/README.md) - Agent-facing monorepo overview
- [Archive_Orchestration_and_Agent_Harmony.md](Archive_Orchestration_and_Agent_Harmony.md) - Script-agent boundary, archive roles
- [dev/storage/README.md](../../storage/README.md) - Central tooling hub
- [dev/.refs/ARCHITECTURE.md](../../.refs/ARCHITECTURE.md) - Detailed technical reference
