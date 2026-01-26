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
                          Consumer projects (SBS-Test)
```

### Key Files by Repo

**Runway** - Site generator
| File | Purpose |
|------|---------|
| `Main.lean` | CLI: build/serve/check |
| `Render.lean` | Side-by-side node rendering |
| `Theme.lean` | Page templates, sidebar |
| `Latex/Parser.lean` | LaTeX parsing |
| `Config.lean` | Site config including `assetsDir` |

**Dress** - Artifact generation
| File | Purpose |
|------|---------|
| `Capture/ElabRules.lean` | elab_rules hooks |
| `Capture/InfoTree.lean` | SubVerso highlighting capture |
| `Generate/Declaration.lean` | Per-declaration artifact writer |
| `HtmlRender.lean` | Verso HTML rendering |
| `Graph/*.lean` | Dependency graph (fragile, needs work) |

**External Assets** - `dress-blueprint-action/assets/`
| File | Purpose |
|------|---------|
| `blueprint.css` | Full stylesheet (32 KB) |
| `plastex.js` | Proof toggle |
| `verso-code.js` | Hovers, token bindings |

---

## Current Priority: Dependency Graph

**Status**: Blueprint functionality is feature-complete. Dependency graph is fragile and needs work.

**Known issues**:
- Graph rendering can be fragile
- Modal interactions need polish
- Node lookup via manifest.json

**Next after dependency graph**: ar5iv-style paper generation

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

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test
./scripts/build_blueprint.sh
```

This script:
1. Builds local forks: SubVerso -> LeanArchitect -> Dress -> Runway
2. Fetches Mathlib cache
3. Runs `BLUEPRINT_DRESS=1 lake build`
4. Runs `lake build :blueprint`
5. Runs `lake exe runway build runway.json`
6. Serves at localhost:8000

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
        |
        v
Runway consumes:
  - Parses blueprint.tex for structure
  - Loads artifacts from .lake/build/dressed/
  - Copies assets from assetsDir to output/assets/
  - Generates manifest.json (node index)
  - Generates multi-page site
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
2. Check command handlers
3. Test with `./scripts/build_blueprint.sh`
4. Inspect `.lake/build/runway/` output

### Debugging artifact generation
1. Check `Dress/Capture/ElabRules.lean`
2. Check `Dress/Generate/Declaration.lean`
3. Look at `.lake/build/dressed/` artifacts

### Cross-repo changes
1. Identify affected repos (check dependency chain)
2. Edit upstream first (LeanArchitect before Dress before Runway)
3. Run build_blueprint.sh
4. Test with SBS-Test

### CSS/JS fixes
1. Edit files in `dress-blueprint-action/assets/`
2. Templates are in `Runway/Runway/Theme.lean`
3. Assets copied via `assetsDir` config

### Dependency graph work
1. Graph generation: `Dress/Graph/*.lean`
2. Graph rendering: `Runway/DepGraph.lean`
3. D3.js code in `verso-code.js`
4. Modal handling in `plastex.js`
5. Node lookup via `manifest.json`

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

---

## Standards

- No `sorry` in tooling code
- Follow Verso/SubVerso patterns
- Test via SBS-Test
- Check `lean_diagnostic_messages` after edits
