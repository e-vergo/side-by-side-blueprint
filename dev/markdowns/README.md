# Side-by-Side Blueprint

![Lean](https://img.shields.io/badge/Lean-v4.27.0-blue)
![License](https://img.shields.io/badge/License-Apache%202.0-green)

Pure Lean toolchain for formalization documentation that displays formal proofs alongside LaTeX theorem statements.

## Screenshots

![Dashboard](../../toolchain/SBS-Test/images/Dashboard.png)
*Dashboard with project stats, key theorems, and project notes*

![Blueprint](../../toolchain/SBS-Test/images/blueprint.png)
*Side-by-side LaTeX and Lean display with proof toggles*

![Dependency Graph](../../toolchain/SBS-Test/images/dep_graph.png)
*Interactive dependency visualization with Sugiyama layout*

![Paper](../../toolchain/SBS-Test/images/paper_web.png)
*Generated paper with verification badges*

## Features

- **Side-by-side display** of LaTeX statements and Lean proofs with toggleable proof sections
- **Interactive dependency graph** with Sugiyama hierarchical layout, pan/zoom, and rich modals
- **Dashboard homepage** with stats, key theorems, messages, and project notes
- **PDF/Paper generation** with `\paperstatement{}` and `\paperfull{}` hooks
- **6-status color model** for tracking formalization progress (notReady, ready, sorry, proven, fullyProven, mathlibReady)
- **Module reference support** via `\inputleanmodule{ModuleName}`
- **Rainbow bracket highlighting** for nested expressions (6-depth cycling)
- **Validation checks** detecting disconnected subgraphs and cycles
- **Auto-computed `fullyProven` status** via O(V+E) dependency graph traversal
- **Automatic dependency inference** from actual Lean code (replaces manual `\uses{}`)
- **Hover tooltips** with type signatures via Tippy.js
- **Dark/light theme toggle** with localStorage persistence
- **8-dimensional quality scoring** with automated design validation (T1-T8 test suite)

## Monorepo Structure

This monorepo contains the complete toolchain, forks, and example projects:

```
Side-by-Side-Blueprint/
  forks/                    # Forked Lean 4 repositories
  toolchain/                # Core toolchain components
  showcase/                 # Production examples
  dev/                      # Development tooling
    scripts/                # sbs CLI and Python tooling
    storage/                # Archive (screenshots, metrics, rubrics)
    build-*.sh              # One-click build scripts
```

### Forks

| Repository | Purpose | Documentation |
|------------|---------|---------------|
| [SubVerso](../../forks/subverso/) | Syntax highlighting extraction with O(1) indexed lookups | [README](../../forks/subverso/README.md) |
| [Verso](../../forks/verso/) | Document framework with SBSBlueprint and VersoPaper genres | [README](../../forks/verso/README.md) |
| [LeanArchitect](../../forks/LeanArchitect/) | `@[blueprint]` attribute with 8 metadata + 3 status options | [README](../../forks/LeanArchitect/README.md) |

### Toolchain Components

| Repository | Purpose | Documentation |
|------------|---------|---------------|
| [Dress](../../toolchain/Dress/) | Artifact generation, graph layout, validation | [README](../../toolchain/Dress/README.md) |
| [Runway](../../toolchain/Runway/) | Site generator, dashboard, paper/PDF generation | [README](../../toolchain/Runway/README.md) |
| [dress-blueprint-action](../../toolchain/dress-blueprint-action/) | GitHub Action (432 lines, 14 steps) + CSS/JS assets (3,805 lines) | [README](../../toolchain/dress-blueprint-action/README.md) |
| [SBS-Test](../../toolchain/SBS-Test/) | 33 nodes: Minimal test project (all 6 status colors, validation testing) | [README](../../toolchain/SBS-Test/README.md) |

### Showcase Projects

| Project | Scale | Purpose | Documentation |
|---------|-------|---------|---------------|
| [General_Crystallographic_Restriction](../../showcase/General_Crystallographic_Restriction/) | 57 nodes | Production example with paper generation | [README](../../showcase/General_Crystallographic_Restriction/README.md) |
| [PrimeNumberTheoremAnd](../../showcase/PrimeNumberTheoremAnd/) | 591 nodes | Large-scale integration (Tao's PNT project) | [README](../../showcase/PrimeNumberTheoremAnd/README.md) |

### Dependency Chain

```
SubVerso -> LeanArchitect -> Dress -> Runway
              |
              +-> Verso (genres use SubVerso for highlighting)
```

## Getting Started

### 1. Add Dress as a Dependency

In your `lakefile.toml`:

```toml
[[require]]
name = "Dress"
git = "https://github.com/e-vergo/Dress"
rev = "main"
```

### 2. Add `@[blueprint]` Annotations

```lean
import Dress

@[blueprint "thm:main"]
theorem main_result : 2 + 2 = 4 := rfl

@[blueprint "thm:key" (keyDeclaration := true, message := "Central result")]
theorem key_theorem : P := by
  sorry
```

### 3. Create Blueprint Structure

Create `blueprint/src/blueprint.tex` with your LaTeX document structure:

```latex
\documentclass{article}
\usepackage{blueprint}

\begin{document}
\chapter{Introduction}

\begin{theorem}[Main Result]\label{thm:main}
  The statement of your theorem.
\end{theorem}

\inputleannode{thm:main}

\end{document}
```

### 4. Configure `runway.json`

```json
{
  "title": "My Blueprint",
  "projectName": "MyProject",
  "githubUrl": "https://github.com/user/MyProject",
  "baseUrl": "/",
  "blueprintTexPath": "blueprint/src/blueprint.tex",
  "assetsDir": "../dress-blueprint-action/assets"
}
```

### 5. Build

```bash
# Fetch mathlib cache (if using mathlib)
lake exe cache get

# Build with artifact generation
BLUEPRINT_DRESS=1 lake build

# Generate Lake facets
lake build :blueprint

# Generate dependency graph and manifest
lake exe extract_blueprint graph MyProject

# Generate site
lake exe runway build runway.json
```

Output is written to `.lake/build/runway/`.

### 6. CI/CD

Use [dress-blueprint-action](https://github.com/e-vergo/dress-blueprint-action) for GitHub Actions:

```yaml
name: Blueprint

on:
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

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

## `@[blueprint]` Attribute Options

### Metadata Options (8)

| Option | Type | Purpose |
|--------|------|---------|
| `title` | String | Custom node label in dependency graph |
| `keyDeclaration` | Bool | Highlight in dashboard Key Theorems section |
| `message` | String | User notes displayed in Messages panel |
| `priorityItem` | Bool | Flag for dashboard Attention column |
| `blocked` | String | Reason the node is blocked |
| `potentialIssue` | String | Known concerns or issues |
| `technicalDebt` | String | Technical debt / cleanup notes |
| `misc` | String | Catch-all miscellaneous notes |

### Manual Status Flags (3)

| Option | Sets Status To | Color |
|--------|----------------|-------|
| `notReady` | notReady | Sandy Brown (#F4A460) |
| `ready` | ready | Light Sea Green (#20B2AA) |
| `mathlibReady` | mathlibReady | Light Blue (#87CEEB) |

### Auto-Detected Statuses

| Status | Color | Source |
|--------|-------|--------|
| `sorry` | Dark Red (#8B0000) | Proof contains `sorryAx` |
| `proven` | Light Green (#90EE90) | Complete proof without sorry |
| `fullyProven` | Forest Green (#228B22) | Proven and all ancestors are proven/fullyProven |

### Example

```lean
@[blueprint "thm:main"
  (keyDeclaration := true)
  (message := "Main theorem of the formalization")]
theorem mainTheorem : ... := ...

@[blueprint "lem:helper"
  (priorityItem := true)
  (blocked := "Waiting for mathlib PR #12345")]
lemma helperLemma : ... := sorry

@[blueprint "thm:upstream" (mathlibReady := true)]
theorem readyForMathlib : ... := ...
```

## Paper Generation

To generate an academic paper with links to Lean formalizations:

1. Add `paperTexPath` to `runway.json`:

```json
{
  "paperTexPath": "blueprint/src/paper.tex"
}
```

2. Use paper hooks in your LaTeX:

```latex
% Insert LaTeX statement with link to Lean code
\paperstatement{thm:main}

% Insert full side-by-side display
\paperfull{thm:main}
```

3. Paper metadata is automatically extracted from:
   - `\title{...}` - Paper title
   - `\author{...}` (split on `\and`) - Authors
   - `\begin{abstract}...\end{abstract}` - Abstract

## Module References

Include all declarations from a Lean module in your blueprint:

```latex
\chapter{Wiener's Theorem}
\inputleanmodule{PrimeNumberTheoremAnd.Wiener}
```

This expands to all `@[blueprint]`-annotated declarations from that module.

## Validation Features

The toolchain provides validation beyond "typechecks":

| Check | Purpose | Location |
|-------|---------|----------|
| **Connectivity** | Detect disconnected subgraphs (Tao-style errors) | `manifest.json` |
| **Cycles** | Find circular dependencies | `manifest.json` |
| **fullyProven** | Verify all ancestors are proven | Auto-computed |

Results are displayed in the dashboard and stored in `manifest.json` under `checkResults`.

## Tooling

For build commands, screenshot capture, compliance validation, archive management, and custom rubrics, see the [Storage & Tooling Hub](../storage/README.md).

### One-Click Build Scripts

From the monorepo root:

```bash
./dev/build-sbs-test.sh   # SBS-Test (~2 min)
./dev/build-gcr.sh        # GCR (~5 min)
./dev/build-pnt.sh        # PNT (~20 min)
```

## Documentation

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, build pipeline |
| [GOALS.md](GOALS.md) | Project vision and design goals |
| [dev/storage/README.md](../storage/README.md) | Central tooling hub (CLI, validators, rubrics) |
| [.refs/ARCHITECTURE.md](../.refs/ARCHITECTURE.md) | Detailed technical reference |
| [Individual READMEs](#monorepo-structure) | Per-component documentation |

## Live Examples

- [SBS-Test](https://e-vergo.github.io/SBS-Test/) - Minimal feature demonstration
- [General Crystallographic Restriction](https://e-vergo.github.io/General_Crystallographic_Restriction/) - Production example with paper

## Attribution

- **leanblueprint**: This project is a pure-Lean port of [leanblueprint](https://github.com/PatrickMassot/leanblueprint) by Patrick Massot
- **LeanArchitect**: Fork of [hanwenzhu/LeanArchitect](https://github.com/hanwenzhu/LeanArchitect)
- **SubVerso**: Fork of [leanprover/subverso](https://github.com/leanprover/subverso) by David Thrane Christiansen
- **Verso**: Fork of [leanprover/verso](https://github.com/leanprover/verso) by the Lean team

## License

Apache 2.0 - see [LICENSE](LICENSE)
