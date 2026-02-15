# Side-by-Side Blueprint

A Lean 4 formalization documentation toolchain that generates rich, interactive web documentation from annotated Lean projects. Displays formal Lean proofs alongside LaTeX theorem statements with dependency tracking, status visualization, and automatic proof verification.

> **Prototype Status**: Alpha software with known bugs, slow workflows, and incomplete features.

## Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **SubVerso** | `forks/subverso/` | Syntax highlighting extraction from Lean info trees with O(1) indexed lookups |
| **Verso** | `forks/verso/` | Document framework with SBSBlueprint and VersoPaper genres |
| **LeanArchitect** | `forks/LeanArchitect/` | `@[blueprint]` attribute with 8 metadata options + 3 manual status flags |
| **Dress** | `toolchain/Dress/` | Artifact generation, dependency graph layout (Sugiyama algorithm), validation |
| **Runway** | `toolchain/Runway/` | Site generator with dashboard, side-by-side displays, paper/PDF generation |
| **dress-blueprint-action** | `toolchain/dress-blueprint-action/` | GitHub Action for CI/CD + CSS/JS assets |

## Dependency Chain

```
SubVerso -> LeanArchitect -> Dress -> Runway
              |
              +-> Verso (genres use SubVerso for highlighting)
```

## Showcase Projects

| Project | Location | Scale | Notes |
|---------|----------|-------|-------|
| **SBS-Test** | `toolchain/SBS-Test/` | 49 nodes | Minimal test project, exercises all 6 status colors |
| **GCR** | `showcase/General_Crystallographic_Restriction/` | 128 nodes | Production example with full paper generation |
| **PNT** | `showcase/PrimeNumberTheoremAnd/` | 591 annotations | Large-scale integration |
| **Quine** | `showcase/Quine/` | 8 nodes | Self-verifying quine in Lean 4 ([live site](https://e-vergo.github.io/Lean_quine/)) |

## Getting Started

Add Dress as a Lake dependency in your `lakefile.toml`:

```toml
[[require]]
name = "Dress"
git = "https://github.com/e-vergo/Dress"
rev = "main"
```

Annotate declarations with the `@[blueprint]` attribute:

```lean
@[blueprint "thm:main" (keyDeclaration := true, message := "Main result")]
theorem main_thm : P := by
  ...
```

### Configuration

Create a `runway.json` in your project root:

```json
{
  "title": "Project Title",
  "projectName": "ProjectName",
  "githubUrl": "https://github.com/...",
  "baseUrl": "/",
  "blueprintTexPath": "blueprint/src/blueprint.tex",
  "assetsDir": "/path/to/dress-blueprint-action/assets"
}
```

Optional fields: `paperTexPath` (for paper/PDF generation), `docgen4Url` (for doc links).

### Building

Build with `BLUEPRINT_DRESS=1` to enable artifact capture during elaboration:

```bash
BLUEPRINT_DRESS=1 lake build
lake build +:blueprint
lake exe dress extract_blueprint graph
lake exe runway build runway.json
```

## The `@[blueprint]` Attribute

### Metadata Options

| Option | Type | Purpose |
|--------|------|---------|
| `title` | String | Custom graph label |
| `keyDeclaration` | Bool | Highlight in dashboard |
| `message` | String | User notes |
| `priorityItem` | Bool | Attention column |
| `blocked` | String | Blockage reason |
| `potentialIssue` | String | Known concerns |
| `technicalDebt` | String | Cleanup notes |
| `misc` | String | Catch-all |

### Manual Status Flags

| Option | Sets Status To |
|--------|----------------|
| `notReady` | notReady (sandy brown) |
| `ready` | ready (light sea green) |
| `mathlibReady` | mathlibReady (light blue) |

## 6-Status Color Model

Six status colors track formalization progress:

| Status | Color | Hex | Source |
|--------|-------|-----|--------|
| `notReady` | Sandy Brown | #F4A460 | Default or manual: `(notReady := true)` |
| `ready` | Light Sea Green | #20B2AA | Manual: `(ready := true)` |
| `sorry` | Dark Red | #8B0000 | Auto-detected: proof contains `sorryAx` |
| `proven` | Light Green | #90EE90 | Auto-detected: complete proof |
| `fullyProven` | Forest Green | #228B22 | Auto-computed: proven and all ancestors proven |
| `mathlibReady` | Light Blue | #87CEEB | Manual: `(mathlibReady := true)` |

**Priority** (manual always wins): mathlibReady > ready > notReady (explicit) > fullyProven > sorry > proven > notReady (default)

**Color source of truth**: Lean code in `Dress/Graph/Svg.lean` defines canonical hex values.

## Build Pipeline

```
@[blueprint "label"] theorem foo ...
        |
        v
DRESS (during elaboration):
  - SubVerso extracts highlighting from info trees
  - Splits code into signature + proof body
  - Renders HTML with hover data via Verso
  - Applies rainbow bracket highlighting
  - Writes: decl.tex, decl.html, decl.json, decl.hovers.json
        |
        v
LAKE FACETS (after compilation):
  - :blueprint aggregates module artifacts
  - :depGraph generates dep-graph.json + dep-graph.svg
  - Computes stats and validates graph (connectivity, cycles)
  - Uses Node.inferUses for real Lean code dependency inference
  - Writes manifest.json with precomputed stats and validation
        |
        v
RUNWAY (post-build):
  - Parses blueprint.tex for chapter/section structure
  - Loads artifacts and manifest.json
  - Generates dashboard homepage + multi-page static site
  - Optionally: paper.html + paper.pdf
```

## Dependency Graph

The layout algorithm implements Sugiyama-style hierarchical drawing:

1. **Acyclic transformation**: DFS identifies and reverses back-edges
2. **Layer assignment**: Top-to-bottom, respecting edge directions
3. **Crossing reduction**: Median heuristic for node ordering within layers
4. **Position refinement**: Iterative adjustment for better spacing
5. **Edge routing**: Visibility graph + Dijkstra shortest path + Bezier fitting

| Shape | Used For |
|-------|----------|
| Rectangle | def, abbrev, structure, class, instance |
| Ellipse | theorem, lemma, proposition, corollary, example |

| Edge Style | Meaning |
|------------|---------|
| Solid | Proof dependency |
| Dashed | Statement dependency |

### Large Graph Optimizations (>100 nodes)

| Optimization | Normal | >100 nodes |
|--------------|--------|------------|
| Barycenter iterations | Unlimited | Max 2 |
| Transpose heuristic | Yes | Skipped |
| Visibility graph routing | Yes | Skipped |
| Transitive reduction | Yes | Skipped |

## CI/CD

The `dress-blueprint-action` GitHub Action provides one-step deployment:

| Input | Default | Purpose |
|-------|---------|---------|
| `project-directory` | `.` | Directory containing lakefile.toml and runway.json |
| `lean-version` | (auto) | Override Lean version |
| `docgen4-mode` | `skip` | `skip`, `docs-static`, or `generate` |
| `deploy-pages` | `true` | Upload artifact for GitHub Pages |

## Performance

SubVerso highlighting dominates build time (93-99%). Cannot be deferred because info trees are ephemeral.

| Project | Nodes | Layout Time | Total Build |
|---------|-------|-------------|-------------|
| SBS-Test | 49 | <1s | ~2 min |
| GCR | 128 | ~2s | ~5 min |
| PNT | 591 | ~15s | ~20 min |

## License

Apache 2.0
