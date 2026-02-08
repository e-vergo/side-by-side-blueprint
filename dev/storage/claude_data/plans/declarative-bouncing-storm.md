# Runway: Pure Lean Blueprint Generator

## Goal

Replicate the [Lean reference manual](https://github.com/leanprover/reference-manual) building pipeline for mathematical blueprints. Replace the Python/plasTeX leanblueprint with a 100% Lean implementation. Funnel as much as possible through the Lean kernel for type safety and ecosystem alignment.

**Input Sources:**
- **`@[blueprint]` attributes** in Lean files: Statement/proof LaTeX extracted via Dress
- **`blueprint/src/*.tex`**: Expository content (chapters, sections, prose) - RETAINED
- **PDF generation**: Continues using LaTeX toolchain with existing `.tex` files

## Repository Responsibilities

| Repository | Role | Why |
|------------|------|-----|
| **LeanArchitect** | Metadata storage | Stores `@[blueprint]` node data in environment extensions. Lightweight, no artifact generation. Could be upstreamed independently. |
| **Dress** | Type-checked artifact generator | Generates all artifacts requiring environment access during elaboration: highlighted code, dependency graph, node metadata. Writes to `.lake/build/dressed/`. |
| **Runway** | Site assembler | Consumes Dress artifacts, renders final HTML using Verso's Genre/Theme system. Pure site generator - no environment access needed. |
| **SubVerso** | Syntax highlighting | Extracts semantic highlighting from Lean's info trees. Upstream FRO library (we use fork with tactic-hover-support). |

**Why this split:**
- **LeanArchitect** is minimal - just data structures and environment extensions
- **Dress** does heavy lifting during `lake build` - everything needing type info happens here
- **Runway** is a pure site generator - could run on CI without rebuilding Lean
- Mirrors how reference manual separates SubVerso (highlighting) from Verso (rendering)

**Data flow:**
```
@[blueprint] declarations
       ↓
LeanArchitect → Environment extensions (Node, deps, labels)
       ↓
Dress (during elaboration) → .lake/build/dressed/
       │                         ├── {Module}/{label}/decl.html
       │                         ├── {Module}/{label}/decl.json
       │                         ├── dep-graph.json (nodes + edges)
       │                         └── dep-graph.svg (static render)
       ↓
Runway (post-build) → .lake/build/runway/ (static site)
```

## Design Principles

1. **Ecosystem alignment** - Use Verso patterns so Runway could eventually become an official Verso genre or FRO-maintained tool
2. **doc-gen4 integration** - Bidirectional links between blueprint explanations and API documentation
3. **Reuse over reinvent** - Leverage Verso's `Html` type, `HtmlT` monad, theme system, and asset management

## Current Architecture (3 languages)

```
@[blueprint] → Dress (Lean) → .tex/.html/.json artifacts
                    ↓
              Lake facets → module.tex, library.tex
                    ↓
              leanblueprint (Python/plasTeX) → HTML website
```

**Pain points:**
- Base64 encode/decode overhead
- Two build systems (Lake + pip/texlive)
- CI needs texlive container (~10 min overhead)
- No incremental website builds
- Jinja2 templates are stringly-typed
- No integration with doc-gen4

## Target Architecture (100% Lean, Verso-based)

```
@[blueprint] → LeanArchitect → Environment extensions (Node, deps)
                    ↓
              Dress elab hooks → Highlighted code (SubVerso)
                    ↓
              Runway (Verso Genre) → Two-phase pipeline
                    ↓
              lake exe runway → .lake/build/runway/ (static site)
```

**Benefits:**
- Single `lake exe runway` command (or `lake build :runway` facet)
- No Python/texlive dependencies
- Incremental builds via Lake
- Type-safe HTML generation (Verso's `Html` type + `{{ }}` DSL)
- Simpler CI (~5 min)
- Consistent with Lean reference manual patterns
- doc-gen4 cross-linking

## Repository Changes

### 1. LeanArchitect (minimal changes)
Keep as-is. Already stores blueprint metadata in environment extensions (`blueprintExt`, `latexLabelToLeanNamesExt`).

### 2. Dress (type-checked artifact generator)
Dress generates **all artifacts that benefit from environment access** during elaboration. Everything goes to `.lake/build/dressed/`.

**Artifacts generated per declaration:**
- `decl.html` - Syntax-highlighted code with hover data
- `decl.json` - Node metadata (name, label, status, kind, dependencies)

**Artifacts generated per library (Lake facet):**
- `dep-graph.json` - Nodes and edges for D3.js visualization
- `dep-graph.svg` - Static SVG render (Sugiyama layout)
- `nodes-index.json` - Label → path mapping for lookups

**Why generate graphs in Dress:**
- Full access to dependency information from environment
- Sugiyama layout algorithm runs once during build, not on every page load
- SVG available for PDF/static contexts, JSON for interactive web
- Future: custom graph layouts, filtering, clustering

**Keep:**
- `Dress/Capture/*` - Elaboration hooks capture highlighting
- `Dress/HtmlRender.lean` - Verso HTML rendering
- `Dress/Highlighting.lean` - SubVerso integration
- `Dress/Graph/*` - Dependency graph generation (JSON + SVG)

**Remove (after Runway stable):**
- `Dress/Generate/Latex.lean` - No more .tex generation
- `Dress/Base64.lean` - No more encoding for LaTeX
- Lake facets for .tex output

### 3. Runway (NEW - `/Users/eric/GitHub/Runway`)
Pure Lean website generator built on Verso patterns.

**Structure:**
```
Runway/
├── Runway.lean              # Main entry point, re-exports
├── Runway/
│   ├── Genre.lean           # Blueprint : Genre definition
│   ├── Site.lean            # Site structure (BlueprintSite, BlueprintNode)
│   ├── Config.lean          # RunwayConfig (title, github, home, docgen4Url)
│   ├── Traverse.lean        # TraverseM: collect nodes, deps, cross-refs
│   ├── Render.lean          # HtmlT: render nodes to Html
│   ├── Theme.lean           # Theme with templates (primary, node, index)
│   ├── Templates.lean       # HTML templates using Verso's {{ }} DSL
│   ├── DepGraph.lean        # Dependency graph JSON generation
│   ├── DocGen4.lean         # doc-gen4 URL generation and linking
│   └── Assets.lean          # CSS/JS content (include_str)
├── assets/
│   ├── runway.css           # Styles (migrated from leanblueprint)
│   ├── verso-code.js        # Hover tooltips, binding highlight
│   ├── dep-graph.js         # D3.js visualization
│   └── katex/               # KaTeX for math rendering
└── lakefile.lean            # CLI executable + Lake facet
```

**Genre Definition (following Verso patterns):**
```lean
-- Runway/Genre.lean
def Blueprint : Genre where
  PartMetadata := Blueprint.Meta        -- title, status, dependencies
  Block := Blueprint.BlockExt           -- theorem, definition, proof blocks
  Inline := Blueprint.InlineExt         -- lean refs, math
  TraverseContext := Blueprint.Context  -- site config, doc-gen4 URLs
  TraverseState := Blueprint.State      -- collected nodes, dep graph
```

**Two-Phase Pipeline (like reference manual):**
```lean
-- Phase 1: Traverse - collect all nodes and cross-references
def traverseBlueprint (site : Site) : IO Blueprint.State

-- Phase 2: Render - generate HTML using Verso's HtmlT
def renderBlueprint (site : Site) (state : Blueprint.State) : IO Unit
```

**Entry points:**
```lean
-- CLI executable
def main : IO Unit := do
  let config ← loadConfig
  let env ← loadEnvironment config.imports
  let site := buildSite env
  runwayGenerate config site

-- Or as Lake facet in consumer project
package_facet runway : FilePath := do
  runwayGenerate ...
```

### 4. doc-gen4 Integration

**Bidirectional linking:**
```lean
-- In Runway/DocGen4.lean
structure DocGen4Config where
  baseUrl : String  -- e.g., "https://leanprover-community.github.io/mathlib4_docs"

def docGen4Url (config : DocGen4Config) (name : Name) : String :=
  s!"{config.baseUrl}/find/#{name}"

-- In node rendering, add link to API docs
def renderDeclLink (name : Name) : HtmlT Blueprint Html := do
  let config ← getConfig
  let url := docGen4Url config.docgen4 name
  return {{ <a href={url} class="docgen4-link" title="API Documentation">📖</a> }}
```

**doc-gen4 side (future):** Could add `@[blueprint]` attribute recognition to link back to blueprint explanations.

### 5. leanblueprint (deprecate)
Archive for projects not ready to migrate. No new development.

### 6. dress-blueprint-action (simplify → runway-action)
```yaml
# Before (texlive container, ~15 min)
- uses: e-vergo/dress-blueprint-action@main
  with:
    build-pdf: true
    build-web: true

# After (pure Lean, ~5 min)
- run: lake exe runway
- uses: actions/upload-pages-artifact@v3
  with:
    path: .lake/build/runway
```

## Key Design Decisions

### 1. Verso Integration Strategy

Use Verso's full pipeline, not just the `Html` type:

```lean
-- Define Blueprint as a Verso Genre (like the reference manual)
def Blueprint : Genre where
  PartMetadata := Blueprint.Meta
  Block := Blueprint.BlockExt
  Inline := Blueprint.InlineExt
  TraverseContext := Blueprint.Context
  TraverseState := Blueprint.State

-- Use Verso's two-phase pattern
-- Phase 1: Traverse collects cross-references, validates deps
-- Phase 2: Render generates HTML using HtmlT monad
```

**Why full Verso integration:**
- Consistent with reference manual patterns (easier upstream path)
- Get traverse phase for free (handles forward references)
- Theme/template system already battle-tested
- Asset deduplication built-in

### 2. Theme System

Single theme initially, following Verso's `Theme` structure:

```lean
def blueprintTheme : Theme where
  primaryTemplate := blueprintPrimaryTemplate    -- HTML wrapper, nav, footer
  pageTemplate := blueprintPageTemplate          -- Node/declaration layout
  postTemplate := blueprintPageTemplate          -- Reuse for consistency
  archiveEntryTemplate := nodeEntryTemplate      -- Index list items
  cssFiles := #[("blueprint.css", blueprintCss), ("verso-code.css", versoCodeCss)]
  jsFiles := #[("verso-code.js", versoCodeJs, false), ("dep-graph.js", depGraphJs, false)]
```

### 3. Dependency Graph

**Generated by Dress** (during `lake build`):
- `dep-graph.json` - Nodes and edges for D3.js
- `dep-graph.svg` - Static SVG with Sugiyama layered layout

**Consumed by Runway:**
- Embeds SVG directly in index.html (no JS required for basic view)
- Includes D3.js for interactive version (zoom, pan, click-to-navigate, path highlighting)

```lean
-- Dress/Graph/Types.lean
structure DepGraphNode where
  id : String           -- label
  name : String         -- Lean name
  status : NodeStatus   -- proven, sorry, notReady
  kind : String         -- theorem, definition, lemma
  x : Float             -- layout position (computed by Sugiyama)
  y : Float

structure DepGraph where
  nodes : Array DepGraphNode
  edges : Array (String × String)  -- (from, to)
```

**Why generate in Dress:**
- Full environment access for dependency analysis
- Layout computed once at build time, not per page load
- SVG works in PDF and non-JS contexts
- Future: custom layouts, clustering, filtering

### 4. Math Rendering

**KaTeX client-side** (same as current):
- Keep LaTeX in `statement`/`proof` docstrings
- KaTeX renders on page load
- Zero migration for existing projects

### 5. Static Assets

Use Verso's asset collection pattern:

```lean
-- During traverse phase
def addBlueprintAssets : TraverseM Unit := do
  addCssFile "blueprint.css" blueprintCss
  addCssFile "katex.min.css" katexCss
  addJsFile "verso-code.js" versoCodeJs none
  addJsFile "katex.min.js" katexJs none
  addJsFile "dep-graph.js" depGraphJs none
```

### 6. Output Structure

```
.lake/build/blueprint/
├── index.html              # Overview + embedded dep graph
├── dep-graph.html          # Full-page interactive graph
├── dep-graph.json          # Graph data for D3.js
├── nodes/
│   ├── thm-main.html       # Per-node pages (by label)
│   └── lem-helper.html
├── modules/
│   └── MyProject/
│       └── Basic.html      # Per-module listing
├── assets/
│   ├── blueprint.css
│   ├── verso-code.js
│   ├── katex.min.css
│   ├── katex.min.js
│   └── dep-graph.js
└── _redirects              # For Netlify/Cloudflare (optional)
```

### 7. doc-gen4 Integration

**Blueprint → doc-gen4:**
Every declaration rendering includes link to API docs:
```html
<a href="https://leanprover-community.github.io/mathlib4_docs/find/#MyTheorem"
   class="docgen4-link">📖 API Docs</a>
```

**doc-gen4 → Blueprint (future):**
doc-gen4 could recognize `@[blueprint]` and add "See blueprint explanation" links.

**Configuration:**
```lean
-- In project's lakefile or blueprint config
def blueprintConfig : BlueprintConfig := {
  title := "My Project Blueprint"
  github := "https://github.com/user/project"
  home := "https://user.github.io/project/blueprint"
  docgen4 := some "https://user.github.io/project/docs"
}
```

### 8. Expository Content

Blueprints contain substantial expository content beyond `@[blueprint]` declarations:
- Introductory sections explaining mathematical context
- Narrative connecting theorems and explaining proof strategies
- Chapter/section organization
- References, acknowledgments

**Current Approach: LaTeX Source Files (RETAINED)**

Expository content stays in `blueprint/src/*.tex` LaTeX files:
- **No conversion required** - existing LaTeX files remain the source of truth
- **PDF generation** - continues using standard LaTeX toolchain
- **HTML generation** - Runway reads declaration content from Dress artifacts

The `@[blueprint]` attributes in Lean files provide:
- Statement/proof LaTeX text (extracted to decl.tex by Dress)
- Lean code highlighting (extracted to decl.html by Dress)
- Dependency information (from `\uses{}`)

**Future Option: Verso Document DSL**

For projects that want type-checked document structure, a Verso DSL could be supported:

```lean
-- blueprint/Introduction.lean (OPTIONAL - not required for migration)
open Runway.Doc in
#doc Introduction where
%%%
# Introduction
...
%%%
{node "thm:main"}
```

This is a **future enhancement**, not a migration requirement. Existing LaTeX-based projects work without changes.

## Implementation Phases

### Phase 1: Verso Genre Foundation
- [ ] `Runway/Genre.lean` - Define `Blueprint` genre with metadata types
- [ ] `Runway/Site.lean` - Site structure (`BlueprintSite`, `BlueprintNode`)
- [ ] `Runway/Config.lean` - `RunwayConfig` (title, urls, docgen4)
- [ ] `Runway/Doc.lean` - Document DSL (`#doc`, `{node}`, `%%%` blocks)
- [ ] `Runway/Traverse.lean` - Traverse phase (collect nodes, build dep graph)
- [ ] Basic `lake exe runway` CLI that runs pipeline

### Phase 2: Rendering
- [ ] `Runway/Theme.lean` - Theme definition with templates
- [ ] `Runway/Render.lean` - Node rendering (signature, proof, metadata)
- [ ] `Runway/Templates.lean` - Primary, page, index templates
- [ ] Migrate CSS from leanblueprint (`assets/runway.css`)
- [ ] Migrate JS from leanblueprint (`assets/verso-code.js`)

### Phase 3: Dependency Graph (Dress generates, Runway consumes)
**In Dress:**
- [ ] `Dress/Graph/Types.lean` - DepGraph, DepGraphNode structures
- [ ] `Dress/Graph/Build.lean` - Build graph from environment extensions
- [ ] `Dress/Graph/Layout.lean` - Sugiyama layered layout algorithm
- [ ] `Dress/Graph/Svg.lean` - Static SVG generation
- [ ] `Dress/Graph/Json.lean` - JSON output for D3.js

**In Runway:**
- [ ] Embed `dep-graph.svg` in index.html
- [ ] `assets/dep-graph.js` - D3.js interactive overlay
- [ ] Status coloring (proven=green, sorry=red, notReady=yellow)

### Phase 4: doc-gen4 Integration
- [ ] `Runway/DocGen4.lean` - URL generation
- [ ] Add "📖 API Docs" links to declaration rendering
- [ ] Configuration for custom doc-gen4 base URLs
- [ ] (Future) PR to doc-gen4 for reverse links

### Phase 5: Polish & Testing
- [ ] Migration guide (leanblueprint → Runway)
- [ ] Create runway-action (or simplify dress-blueprint-action)
- [ ] Test on GCR and PNT
- [ ] Archive Python leanblueprint

## Execution Strategy

Two Claude instances coordinate implementation:
- **declarative-bouncing-storm** (this instance): Orchestration, completed Agent 1-2, handles final integration
- **refactored-leaping-meerkat** (other instance): Executing Agents 3-11

### Agent Tasks Status

**1. Move Graph Code to Dress** ✅ COMPLETE (declarative-bouncing-storm)
```
Completed: Graph code moved to Dress/Graph/
- Types.lean, Build.lean, Layout.lean, Svg.lean
- Runway/Graph/ removed, Runway.lean updated
- Both repos build successfully
```

**2. Add Graph JSON Export to Dress** ✅ COMPLETE (declarative-bouncing-storm)
```
Completed: Dress/Graph/Json.lean created
- ToJson instances for Node, Edge, Graph, LayoutNode, LayoutEdge, LayoutGraph
- writeJsonFile, writeJsonFileCompact utilities
- Uses Batteries.Lean.Json for Float serialization
- Dress builds successfully
```

**3. Runway Genre Foundation** 🔄 IN PROGRESS (refactored-leaping-meerkat)
```
Agent: general-purpose
Repo: /Users/eric/GitHub/Runway
Task: Create Runway/Genre.lean - Blueprint : Genre definition
      Create Runway/Config.lean - RunwayConfig structure
      Create Runway/Site.lean - BlueprintSite, BlueprintNode
      Follow Verso patterns from reference manual
```

**4-10. Remaining Tasks** 📋 ASSIGNED (refactored-leaping-meerkat)

Per `/Users/eric/.claude/plans/refactored-leaping-meerkat.md`:
- Agent 3: Dress Lake Facet for Graphs
- Agent 4: Runway Genre Foundation
- Agent 5: Runway Traverse Phase
- Agent 6: Runway Render Phase
- Agent 7: Runway Graph Embedding
- Agent 8: doc-gen4 Integration
- Agent 9: Document DSL
- Agent 10: CLI and Assets
- Agent 11: Integration Test on GCR

### Coordination Model

```
declarative-bouncing-storm (this instance):
  ├── ✅ Agent 1: Move Graph Code to Dress
  ├── ✅ Agent 2: Add Graph JSON Export
  └── 👀 Monitor progress, assist if needed

refactored-leaping-meerkat (other instance):
  ├── 🔄 Agent 3: Dress Lake Facet
  └── 📋 Agents 4-11: Runway implementation
```

### This Instance's Role

1. **Completed work:**
   - Moved Graph code (Types, Build, Layout, Svg) to Dress
   - Created Json.lean for D3.js output
   - Removed Runway/Graph/, updated Runway.lean

2. **Current role:**
   - Monitor other instance's progress via plan file
   - Available to assist with issues or blockers
   - Handle any tasks that arise outside their scope

3. **Check progress:**
   ```bash
   cat /Users/eric/.claude/plans/refactored-leaping-meerkat.md | grep -E "✅|🔄|🔴"
   ```

## Files to Create

### Runway/ (new repository at `/Users/eric/GitHub/Runway`)
```
Runway/
├── Runway.lean          # Main entry, re-exports
├── Runway/
│   ├── Genre.lean       # Blueprint : Genre definition
│   ├── Site.lean        # BlueprintSite, BlueprintNode structures
│   ├── Config.lean      # RunwayConfig, read from runway.toml or lakefile
│   ├── Doc.lean         # Document DSL (#doc, {node}, %%% blocks)
│   ├── Traverse.lean    # TraverseM implementation
│   ├── Render.lean      # HtmlT node rendering
│   ├── Theme.lean       # runwayTheme definition
│   ├── Templates.lean   # HTML templates (primary, page, index)
│   ├── DepGraph.lean    # Dependency graph JSON
│   ├── DocGen4.lean     # doc-gen4 URL utilities
│   └── Assets.lean      # CSS/JS content (include_str)
├── Main.lean            # CLI entry point
├── assets/
│   ├── runway.css       # Migrated from leanblueprint/static
│   ├── verso-code.css   # Code highlighting styles
│   ├── verso-code.js    # Hover tooltips, binding highlight
│   ├── dep-graph.js     # D3.js visualization (new)
│   ├── katex.min.css    # KaTeX styles
│   └── katex.min.js     # KaTeX runtime
└── lakefile.lean        # Dependencies: Verso, LeanArchitect, Dress
```

### Consumer Project Blueprint Structure
```
blueprint/
├── Blueprint.lean       # Site definition, imports sections
├── Introduction.lean    # #doc with expository content
├── MainResults.lean     # #doc with {node "..."} references
├── Proofs.lean          # #doc with detailed proofs
└── runway.toml          # Optional config (title, urls)
```

### Consumer Project Changes
Projects using Runway add to `lakefile.toml`:
```toml
[[require]]
name = "Runway"
git = "https://github.com/e-vergo/Runway"
rev = "main"
```

Then run:
```bash
lake exe runway
# or
lake build :runway  # if facet is defined
```

### Dress Changes (after Runway stable)
- Remove `Dress/Generate/Latex.lean`
- Remove `Dress/Base64.lean`
- Keep highlighting capture (Runway reads from environment)

### runway-action (new or rename dress-blueprint-action)
- `action.yml` - Just `lake exe runway` + upload

## Current Task: Match leanblueprint Output

The immediate priority is making Runway's output visually match the existing leanblueprint tool's output at:
https://e-vergo.github.io/General_Crystallographic_Restriction/blueprint/sect0002.html

### Key Features to Replicate

1. **Side-by-side layout**: CSS grid with LaTeX (75ch fixed) on left, Lean code (flexible) on right
   - `.sbs-container` - Grid container for each theorem/definition
   - `.sbs-latex-column` - Left column (max-width: 75ch) with math statement/proof
   - `.sbs-lean-column` - Right column with syntax-highlighted Lean code

2. **MathJax integration**: Client-side LaTeX rendering (keep same as leanblueprint)
   - Add MathJax CDN script in head
   - Configure for `$...$` inline and `$$...$$` display math

3. **Tippy.js hover tooltips**: Type signatures on hover
   - Use `data-lean-hovers` attribute on `.lean-code` blocks
   - JSON map of hover ID → HTML content
   - Themes: `lean`, `warning`, `info`, `error`, `tactic`

4. **Token binding highlight**: Yellow background on all occurrences of a variable when hovering
   - `.binding-hl` class
   - `data-binding` attribute on tokens

5. **Collapsible proofs**: Click to expand/collapse proof content
   - `.proof_heading` click handler
   - `.proof_content` with jQuery `slideToggle`
   - `▶`/`▼` expand icons

6. **Sidebar navigation**: Hierarchical TOC like plasTeX
   - Fixed left sidebar with section hierarchy
   - Blue gradient header from theme-blue.css
   - Expandable subsections

### Files to Modify

**Runway/Assets.lean** - Replace CSS/JS with leanblueprint versions:
```lean
def runwayCss : String := -- Copy from blueprint/web/styles/blueprint.css
def versoCodeJs : String := -- Copy from blueprint/web/js/verso-code.js
def plastexJs : String := -- Copy from blueprint/web/js/plastex.js
```

**Runway/Theme.lean** - Update `primaryTemplate`:
- Add MathJax script tags
- Add Tippy.js/Popper.js CDN scripts
- Add jQuery CDN script
- Add sidebar navigation HTML structure
- Update body classes for plasTeX compatibility

**Runway/Render.lean** - Update `renderNode`:
- Output `.sbs-container` with two columns
- Left: `.sbs-latex-column` with statement/proof HTML (from Dress artifact)
- Right: `.sbs-lean-column` with `.lean-code` block and hover data
- Add `data-lean-hovers` attribute with JSON hover map
- Add `.proof_heading` with expand icon for proofs

**Runway/Templates.lean** - Add sidebar templates:
- `sidebarNav` - Table of contents with sections
- `expandToc` - Expandable section items

### CSS Classes Structure (from leanblueprint)

```css
/* Side-by-side container */
.sbs-container {
  display: grid;
  grid-template-columns: minmax(0, 75ch) 1fr;
  gap: 1rem;
}

/* LaTeX column */
.sbs-latex-column {
  max-width: 75ch;
}

/* Lean column */
.sbs-lean-column {
  min-width: 0;
  overflow-x: auto;
}

/* Lean code block with hover data */
.lean-code {
  font-family: var(--mono-font);
  white-space: pre-wrap;
}

/* Binding highlight */
.binding-hl {
  background-color: #ffffcc;
}

/* Tippy themes */
[data-tippy-theme~='lean'] { /* ... */ }
[data-tippy-theme~='warning'] { /* ... */ }
```

### External Dependencies (CDN)

```html
<!-- MathJax -->
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

<!-- Tippy.js + Popper -->
<script src="https://unpkg.com/@popperjs/core@2"></script>
<script src="https://unpkg.com/tippy.js@6"></script>

<!-- jQuery (for proof toggles) -->
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>

<!-- marked.js (for docstrings) -->
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
```

### Node HTML Template (target output)

```html
<div class="theorem_thmwrapper sbs-container theorem-style-definition" id="lem:label">
  <div class="sbs-latex-column">
    <div class="theorem_thmheading">
      <span class="theorem_thmcaption">Theorem</span>
      <span class="theorem_thmlabel">2.0.1</span>
      <div class="thm_header_extras">✓</div>
    </div>
    <div class="theorem_thmcontent">
      <p>Statement with $\LaTeX$ math...</p>
    </div>
    <div class="proof_wrapper proof_inline" id="proof-id">
      <div class="proof_heading">
        <span class="proof_caption">Proof</span>
        <span class="expand-proof">▶</span>
      </div>
      <div class="proof_content"><p>Proof text...</p></div>
    </div>
  </div>
  <div class="sbs-lean-column">
    <pre class="lean-code" data-lean-hovers='{"0":"<code>...</code>"}'>
      <code class="hl lean lean-signature">...</code>
      <code class="hl lean lean-proof-body">...</code>
    </pre>
  </div>
</div>
```

### Implementation Steps

1. **Update Assets.lean** - Replace CSS/JS with leanblueprint versions:
   - Copy `blueprint/web/styles/theme-blue.css` + `blueprint.css` + `style.css` → `blueprintCss`
   - Copy `blueprint/web/js/verso-code.js` (233 lines) → `versoCodeJs`
   - Copy `blueprint/web/js/plastex.js` (69 lines) → `plastexJs`

2. **Update Theme.lean `primaryTemplate`**:
   - Add MathJax config + CDN script in `<head>`
   - Add plasTeX body structure: `<header>`, `.wrapper`, `nav.toc`, `.content`
   - Add jQuery, Popper.js, Tippy.js CDN scripts before `</body>`
   - Add blue gradient header from theme-blue.css

3. **Update Render.lean `renderNode`**:
   - Change container from `.node` to `.[env]_thmwrapper.sbs-container`
   - `.sbs-latex-column`: heading + content + proof_wrapper
   - `.sbs-lean-column`: `<pre class="lean-code" data-lean-hovers='...'>`
   - Get hover JSON data from Dress artifacts (already base64 decoded)

4. **Update Templates.lean** - Add sidebar:
   - `sidebarNav` renders `nav.toc` with `ul.sub-toc-0`
   - Section items with `.active.current` for current page
   - Expandable subsections with `.expand-toc` span

5. **Test on GCR project**:
   ```bash
   ./scripts/build_blueprint.sh
   # Compare: http://localhost:8000 vs leanblueprint output
   ```
   Verify: MathJax renders, hovers show types, proofs collapse, bindings highlight

## Verification

1. **Build GCR:** `lake exe runway`
2. **Check output:** Verify `.lake/build/runway/` contains:
   - `index.html` with node list and embedded dep graph
   - `nodes/*.html` for each `@[blueprint]` declaration
   - `assets/` with CSS/JS
   - `dep-graph.json` with valid graph data
3. **Serve locally:** `python -m http.server -d .lake/build/runway`
4. **Test features:**
   - Hover tooltips show type signatures
   - Variable binding highlight (yellow on hover)
   - Proof toggle expands/collapses
   - Dep graph is interactive (zoom, pan, click)
   - doc-gen4 links work (if configured)
5. **Compare with current:** Side-by-side with leanblueprint output
6. **CI test:** Run on GCR without texlive container, verify deployment

## Migration Path

### For existing leanblueprint projects:

1. **Add Runway to lakefile.toml:**
   ```toml
   [[require]]
   name = "Runway"
   git = "https://github.com/e-vergo/Runway"
   rev = "main"
   ```

2. **Create runway.toml** (or add to lakefile):
   ```toml
   [runway]
   title = "My Project"
   github = "https://github.com/..."
   docgen4 = "https://..."  # optional
   ```

3. **Update CI:**
   ```yaml
   # Remove dress-blueprint-action, just:
   - run: lake exe runway
   - uses: actions/upload-pages-artifact@v3
     with:
       path: .lake/build/runway
   ```

4. **Expository content stays in LaTeX:**
   - `blueprint/src/*.tex` - **RETAINED** as source of truth for expository content
   - `blueprint/lean_decls` - still used for declaration index
   - `blueprint/web.tex`, `print.tex` - still used for PDF generation
   - Runway reads Dress artifacts which extract content from `@[blueprint]` attributes

### What stays the same:
- `@[blueprint "label" ...]` attribute syntax
- `blueprint/src/*.tex` LaTeX source files for chapters/sections
- LaTeX math in docstrings (rendered by MathJax)
- `\uses{}`, `\leanok`, etc. in statement/proof text
- Dependency inference from Lean code
- PDF generation via LaTeX toolchain

## Upstream Path

To eventually contribute to the Lean ecosystem:

1. **Phase 1 (current):** Build Runway as standalone package, prove the design works
2. **Phase 2:** Stabilize API, document thoroughly
3. **Phase 3:** Propose as Verso genre or separate FRO tool
4. **Phase 4:** If accepted, doc-gen4 integration becomes official

**Key for upstream acceptance:**
- Clean separation of concerns (genre vs rendering vs assets)
- Minimal dependencies beyond Verso/SubVerso
- Good documentation and examples
- Battle-tested on real projects (GCR, PNT)

## Immediate Fix: Visual Comparison Issues (2025-01-25)

### Problem Analysis

Comparing `current.png` vs `goal.png` revealed critical rendering issues:

**Current output problems:**
1. Left column shows Lean code instead of rendered LaTeX mathematical statements
2. Right column shows full decorated code (including `@[blueprint]` attribute and docstrings)
3. MathJax not rendering LaTeX in statement/proof text

**Root cause in `Traverse.lean` `parseDeclTex`:**
- `statementHtml` is populated from `\leansignaturesourcehtml` (Lean signature HTML) - WRONG
- `proofHtml` is populated from `\leanproofsourcehtml` (Lean proof body HTML) - WRONG

**decl.tex structure:**
```latex
\begin{theorem}
\label{lem:one-mem-orders}
\lean{Crystallographic.one_mem_integerMatrixOrders}
\leansignaturesourcehtml{...base64 Lean signature...}   ← For RIGHT column
\leanproofsourcehtml{...base64 Lean proof body...}      ← For RIGHT column
\leanhoverdata{...base64 hover JSON...}
\uses{integerMatrixOrders-def}
\leanok
Order $1$ is achievable in any dimension.               ← For LEFT column (LaTeX)
\end{theorem}
\begin{proof}
\leanok
The identity matrix $I$ has order $1$ in any dimension. ← For LEFT column (LaTeX)
\end{proof}
```

### Fix Plan

1. **Update `DeclArtifact` structure** in `Runway/Traverse.lean`:
   ```lean
   structure DeclArtifact where
     name : String
     label : String
     -- LaTeX content for left column (MathJax rendered)
     latexStatement : Option String := none
     latexProof : Option String := none
     -- Lean code HTML for right column (syntax highlighted)
     leanSignatureHtml : Option String := none
     leanProofBodyHtml : Option String := none
     -- Hover data
     hoverData : Option String := none
     uses : Array String := #[]
     leanOk : Bool := false
   ```

2. **Update `parseDeclTex`** to extract LaTeX statement/proof text:
   - Extract text between `\leanok`/`\uses{...}` and `\end{theorem}`
   - Extract text between `\begin{proof}...\leanok` and `\end{proof}`

3. **Update `NodeInfo` structure** in `Runway/Site.lean`:
   - Keep `statementHtml` for LaTeX statement (left column)
   - Keep `proofHtml` for LaTeX proof (left column)
   - Use `codeHtml` for combined Lean signature+proof (right column)

4. **Update `Main.lean` `buildSiteFromArtifacts`**:
   - `statementHtml` ← artifact's LaTeX statement
   - `proofHtml` ← artifact's LaTeX proof
   - `codeHtml` ← combine signature + proof body HTML from base64 fields

5. **Update `Render.lean` `renderNode`**:
   - Left column: render `statementHtml` and `proofHtml` (MathJax will process)
   - Right column: render `codeHtml` (clean Lean signature + proof)

### Files to Modify

| File | Changes |
|------|---------|
| `Runway/Traverse.lean` | Update `DeclArtifact`, `parseDeclTex` to extract LaTeX text |
| `Runway/Main.lean` | Update `buildSiteFromArtifacts` field mapping |

### Verification

After fix:
1. Rebuild GCR: `BLUEPRINT_DRESS=1 lake build && lake exe runway build`
2. Left column should show: "Order $1$ is achievable..." with MathJax-rendered math
3. Right column should show: clean Lean signature and proof body (no `@[blueprint]` attr)

---

## Phase 2: Multi-Page Chapters + Proof Toggle Sync (2025-01-25)

### Overview

Three features to implement:
1. **Proof toggle sync** - Hide/show Lean proof body when LaTeX proof is toggled
2. **Chapter organization** - Parse `blueprint.tex`, split into separate pages per chapter
3. **Homepage statistics** - Show aggregate progress metrics

### Task 0: Remove "Uses:" Display

**Current State:**
Each node displays "Uses: label1, label2, ..." above the theorem statement, showing dependencies.

**Problem:** This clutters the display. The goal output doesn't show this - dependencies are shown only in the graph.

**Solution:**
Remove or comment out the "Uses:" rendering in `Runway/Render.lean`.

**File to modify:** `Runway/Render.lean` - Remove/hide the uses display

---

### Task 1: Proof Toggle Synchronization

**Current State:**
- Dress generates separate `\leansignaturesourcehtml` and `\leanproofsourcehtml` base64 fields
- Runway decodes these into `leanSignatureHtml` and `leanProofBodyHtml`
- Currently rendered as single block with class `lean-signature`
- JS MutationObserver in `verso-code.js` already watches for `.lean-proof-body` visibility sync

**Problem:** Lean code is rendered as one block - no separate `.lean-proof-body` element exists.

**Solution:**
1. **Update `Render.lean`** - Render signature and proof body as separate elements:
   ```lean
   -- Right column: Lean code with separate signature and proof body
   divClass "sbs-lean-column" (
     .tag "pre" #[("class", "lean-code hl lean"), ("data-lean-hovers", hoverJson)] (
       .tag "code" #[("class", "hl lean lean-signature")] (Html.text false sigHtml) ++
       .tag "code" #[("class", "hl lean lean-proof-body")] (Html.text false proofHtml)
     )
   )
   ```

2. **Update CSS in `Assets.lean`**:
   ```css
   .lean-proof-body {
     display: none;  /* Hidden by default, synced with LaTeX proof toggle */
   }

   .lean-proof-body.visible {
     display: inline;
   }
   ```

3. **Update JS in `Assets.lean`** - Add jQuery slideToggle for Lean proof body:
   ```javascript
   $("div.proof_heading").click(function() {
     var expand_span = $(this).children('span.expand-proof');
     var container = $(this).closest('.sbs-container');
     var leanProofBody = container.find('.lean-proof-body');

     if ($(expand_span).html() == "▼") {
       $(expand_span).html("▶");
       leanProofBody.slideUp();  // Animate Lean proof body closed
     } else {
       $(expand_span).html("▼");
       leanProofBody.slideDown();  // Animate Lean proof body open
     };
     $(this).siblings("div.proof_content").slideToggle();
   });
   ```

**Files to modify:**
- `Runway/Render.lean` - Split code into signature + proof body elements
- `Runway/Assets.lean` - Update CSS and JS for synchronized toggle

---

### Task 2: Chapter Organization (Parse blueprint.tex)

**Current State:**
- All nodes rendered on single `index.html` page
- No chapter/section structure
- `blueprint.tex` defines chapters with `\chapter{}`, `\section{}`, `\inputleanmodule{}`, `\inputleannode{}`

**Solution:** Parse `blueprint.tex` to extract chapter structure and generate multi-page output.

#### Step 2.1: Create LaTeX Parser (`Runway/LaTeX/Parser.lean`)

Parse these LaTeX commands:
- `\chapter{Title}` - Start new chapter
- `\section{Title}` - Start new section within chapter
- `\inputleanmodule{Module.Name}` - Include all nodes from module
- `\inputleannode{label}` - Include specific node by label
- Prose text between commands - Expository content

```lean
inductive LaTeXBlock
  | chapter (title : String)
  | section (title : String)
  | inputModule (moduleName : String)
  | inputNode (label : String)
  | prose (content : String)  -- Text between commands
  | bibliography (entries : Array BibEntry)
  deriving Repr

structure Chapter where
  number : Nat
  title : String
  sections : Array Section
  isAppendix : Bool := false

structure Section where
  number : Option Nat  -- None for unnumbered sections
  title : String
  content : Array LaTeXBlock  -- Prose + node references
```

#### Step 2.2: LaTeX to HTML Converter (`Runway/LaTeX/Render.lean`)

Convert prose LaTeX to HTML (MathJax handles math):
- `\textbf{...}` → `<strong>...</strong>`
- `\textit{...}`, `\emph{...}` → `<em>...</em>`
- `\medskip`, `\bigskip` → `<br/><br/>`
- `$...$` → Leave as-is (MathJax renders)
- `$$...$$` → Leave as-is (MathJax renders)
- `\[...\]` → Leave as-is (MathJax renders)
- `\begin{itemize}...\end{itemize}` → `<ul>...</ul>`
- `\item` → `<li>`
- `\cite{...}` → `<a href="#bib-...">[...]</a>`
- `\noindent` → (ignore)
- `\begin{thebibliography}...\end{thebibliography}` → Parse bibliography

#### Step 2.3: Update Site Structure (`Runway/Site.lean`)

```lean
structure ChapterInfo where
  number : Nat
  title : String
  slug : String           -- URL-safe name (e.g., "psi-function")
  isAppendix : Bool
  sections : Array SectionInfo
  nodes : Array NodeInfo  -- Nodes belonging to this chapter

structure SectionInfo where
  number : Option Nat
  title : String
  slug : String
  content : Html          -- Rendered prose + nodes

structure BlueprintSite where
  config : Config
  chapters : Array ChapterInfo
  nodes : Array NodeInfo  -- All nodes (for cross-referencing)
  depGraph : Graph
  -- ... rest unchanged
```

#### Step 2.4: Multi-Page Output

Generate these files:
```
.lake/build/runway/
├── index.html              # Homepage with stats + chapter list
├── dep-graph.html          # Full dependency graph page
├── chapter1.html           # Introduction
├── chapter2.html           # The Psi Function
├── chapter3.html           # Integer Matrix Orders
├── chapter4.html           # Companion Matrices
├── chapter5.html           # The Crystallographic Restriction Theorem
├── appendix.html           # Appendix
├── runway.css
├── runway.js
├── plastex.js
└── verso-code.js
```

#### Step 2.5: Navigation

Add prev/next navigation and sidebar:

```html
<!-- Sidebar navigation -->
<nav class="toc">
  <ul class="sub-toc-0">
    <li><a href="chapter1.html">1. Introduction</a></li>
    <li class="active"><a href="chapter2.html">2. The Psi Function</a></li>
    <li><a href="chapter3.html">3. Integer Matrix Orders</a></li>
    <!-- ... -->
  </ul>
</nav>

<!-- Bottom prev/next -->
<nav class="prev-next">
  <a href="chapter1.html" class="prev">← Introduction</a>
  <a href="chapter3.html" class="next">Integer Matrix Orders →</a>
</nav>
```

**Files to create:**
- `Runway/LaTeX/Parser.lean` - LaTeX parser
- `Runway/LaTeX/Render.lean` - LaTeX to HTML conversion

**Files to modify:**
- `Runway/Site.lean` - Add `ChapterInfo`, `SectionInfo`
- `Runway/Config.lean` - Add `blueprintTexPath` config option
- `Runway/Theme.lean` - Add sidebar and prev/next navigation
- `Main.lean` - Parse blueprint.tex, generate chapter pages

---

### Task 3: Homepage Statistics

**Display on `index.html`:**

```html
<div class="blueprint-stats">
  <h2>Progress</h2>
  <div class="stat-grid">
    <div class="stat">
      <span class="stat-value">47</span>
      <span class="stat-label">Theorems</span>
    </div>
    <div class="stat">
      <span class="stat-value">14</span>
      <span class="stat-label">Definitions</span>
    </div>
    <div class="stat proved">
      <span class="stat-value">58</span>
      <span class="stat-label">Proved</span>
    </div>
    <div class="stat stated">
      <span class="stat-value">3</span>
      <span class="stat-label">Stated</span>
    </div>
  </div>
  <div class="progress-bar">
    <div class="progress-fill" style="width: 95%"></div>
  </div>
  <p class="progress-text">95% formalized (58 of 61 nodes)</p>
</div>
```

**Statistics to compute:**
- Total nodes
- By type: theorems, definitions, lemmas, propositions, corollaries
- By status: proved, stated, notReady
- Completion percentage
- Per-chapter breakdown

**Files to modify:**
- `Main.lean` - Compute statistics
- `Runway/Render.lean` - Add `renderStats` function
- `Runway/Assets.lean` - Add stats CSS

---

### Execution Strategy

Execute tasks sequentially via orchestrated agents:

**Agent 1: Proof Toggle Sync + Remove Uses Display**
```
Repository: /Users/eric/GitHub/Runway
Files: Runway/Render.lean, Runway/Assets.lean
Task:
  1. Remove "Uses:" display from renderNode (Task 0)
  2. Update renderNode to split Lean code into signature + proof body
  3. Add .lean-proof-body CSS
  4. Update plastex.js to animate both columns
  5. Test with: lake exe runway build && python3 -m http.server -d .lake/build/runway
```

**Agent 2: LaTeX Parser**
```
Repository: /Users/eric/GitHub/Runway
Files: Create Runway/LaTeX/Parser.lean, Runway/LaTeX/Render.lean
Task:
  1. Parse \chapter{}, \section{}, \inputleanmodule{}, \inputleannode{}
  2. Extract prose text between commands
  3. Convert basic LaTeX formatting to HTML
  4. Unit tests with GCR's blueprint.tex
```

**Agent 3: Multi-Page Generation**
```
Repository: /Users/eric/GitHub/Runway
Files: Runway/Site.lean, Runway/Theme.lean, Main.lean
Task:
  1. Add ChapterInfo, SectionInfo structures
  2. Update buildSiteFromArtifacts to group nodes by chapter
  3. Generate separate HTML files per chapter
  4. Add sidebar navigation and prev/next links
```

**Agent 4: Homepage Statistics**
```
Repository: /Users/eric/GitHub/Runway
Files: Main.lean, Runway/Render.lean, Runway/Assets.lean
Task:
  1. Compute statistics from nodes array
  2. Render stats section on index.html
  3. Add progress bar CSS
  4. Add chapter list with links
```

**Agent 5: Integration Test**
```
Repository: /Users/eric/GitHub/General_Crystallographic_Restriction
Task:
  1. Rebuild with BLUEPRINT_DRESS=1 lake build
  2. Run lake exe runway build
  3. Verify chapter pages generated
  4. Test proof toggle on both columns
  5. Compare with reference: https://e-vergo.github.io/General_Crystallographic_Restriction/blueprint/
```

---

### Verification Checklist

- [ ] "Uses:" dependency line NOT displayed on nodes
- [ ] Proof toggle animates both LaTeX and Lean proof body
- [ ] Separate chapter pages: chapter1.html, chapter2.html, etc.
- [ ] Sidebar navigation with chapter links
- [ ] Prev/next navigation at bottom of each chapter
- [ ] Homepage shows statistics (total, by type, by status, percentage)
- [ ] Prose content from blueprint.tex rendered (with MathJax math)
- [ ] All nodes grouped correctly by chapter
- [ ] Hover tooltips still work
- [ ] Dependency graph page accessible
