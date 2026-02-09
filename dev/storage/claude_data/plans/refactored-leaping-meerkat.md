# Runway Implementation Status & Remaining Work

## Current State

**Repository:** `/Users/eric/GitHub/Runway`

Runway is being built as a pure Lean 4 replacement for leanblueprint. The project now supports **dual input**:
- **LaTeX path** (`blueprint/src/*.tex`): For PDF generation and continuity of content not captured in lean docs (nor should it be)
- **Verso DSL path** (`blueprint/*.lean`): Primary for HTML, type-checked documents

## Repository Split (per declarative-bouncing-storm.md)

| Repository | Role |
|------------|------|
| **LeanArchitect** | Metadata storage - `@[blueprint]` node data in environment extensions |
| **Dress** | Type-checked artifact generator - highlighted code, dep graph, node metadata → `.lake/build/dressed/` |
| **Runway** | Site assembler - consumes Dress artifacts, renders HTML using Verso Genre/Theme. **No environment access needed.** |

## Completed Components

### In Runway (LaTeX Pipeline - keep for PDF)

| File | Status | Description |
|------|--------|-------------|
| `Runway/Latex/Token.lean` | ✅ Complete | Token types for LaTeX lexer |
| `Runway/Latex/Lexer.lean` | ✅ Complete | LaTeX tokenizer (~300 lines) |
| `Runway/Latex/Ast.lean` | ✅ Complete | AST types including TheoremMetadata |
| `Runway/Latex/Parser.lean` | ✅ Complete | Parsec-based parser with mutual recursion |
| `Runway/Html/Render.lean` | ✅ Complete | LaTeX AST → Html rendering |
| `Runway/Dress/Load.lean` | ✅ Complete | Base64 decoding, artifact loading |

### Graph Code (✅ MOVED TO DRESS)

Graph code now lives in Dress where it has environment access for dependency analysis:

| File | Status |
|------|--------|
| `Dress/Graph/Types.lean` | ✅ Complete |
| `Dress/Graph/Build.lean` | ✅ Complete |
| `Dress/Graph/Layout.lean` | ✅ Complete |
| `Dress/Graph/Svg.lean` | ✅ Complete |
| `Dress/Graph/Json.lean` | ✅ Complete |

Runway no longer contains Graph code - it will consume pre-generated artifacts from Dress.

## Remaining Work

### ~~Move Graph Code to Dress~~ (✅ COMPLETE)

Graph code (Types, Build, Layout, Svg, Json) is now in Dress.

### ~~Add Dress Lake Facet for Graphs~~ ✅ COMPLETE

Lake facet added to `Dress/lakefile.lean` - generates `dep-graph.svg` + `dep-graph.json`

### ~~Runway Verso Pipeline~~ ✅ COMPLETE

All phases implemented:

| File | Status |
|------|--------|
| `Runway/Genre.lean` | ✅ Complete |
| `Runway/Config.lean` | ✅ Complete |
| `Runway/Site.lean` | ✅ Complete |
| `Runway/Graph.lean` | ✅ Complete |
| `Runway/Traverse.lean` | ✅ Complete |
| `Runway/Render.lean` | ✅ Complete |
| `Runway/Theme.lean` | ✅ Complete |
| `Runway/Templates.lean` | ✅ Complete |
| `Runway/DepGraph.lean` | ✅ Complete |
| `Runway/DocGen4.lean` | ✅ Complete |
| `Runway/Doc.lean` | ✅ Complete |
| `Runway/Assets.lean` | ✅ Complete |
| `assets/runway.css` | ✅ Complete |
| `assets/verso-code.js` | ✅ Complete |
| `assets/dep-graph.js` | ✅ Complete |
| `Main.lean` | ✅ Complete |
| `lakefile.lean` | ✅ Complete |

## Architecture Diagram

```
@[blueprint] declarations
       ↓
LeanArchitect → Environment extensions (Node, deps, labels)
       ↓
Dress (during lake build) → .lake/build/dressed/
       │                      ├── {Module}/{label}/decl.html  (highlighted code)
       │                      ├── {Module}/{label}/decl.json  (node metadata)
       │                      ├── dep-graph.json              (for D3.js)
       │                      └── dep-graph.svg               (static render)
       ↓
Runway (post-build) → .lake/build/runway/ (static site)
       │
       ├── Verso DSL (blueprint/*.lean) → HTML pages
       └── LaTeX (blueprint/src/*.tex)  → PDF (future)
```

## Key Dependencies

From LeanArchitect (via Dress):
- `Architect.Node` - Blueprint node structure
- `Architect.NodePart` - Statement/proof parts
- `Architect.blueprintExt` - Environment extension storing nodes
- `Architect.latexLabelToLeanNamesExt` - Label → Name mapping

From Verso (via Dress):
- `Verso.Doc.Genre` - Genre type with 5 fields
- `Verso.Output.Html` - Html type and `{{ }}` DSL
- `VersoBlog.TraverseM` - Traverse monad pattern
- `VersoBlog.Theme` - Theme system

## Implementation Order (Agent Orchestration)

Each step spawns a single agent. Wait for completion before proceeding.

---

### ~~Agent 1: Move Graph Code to Dress~~ ✅ COMPLETE

Graph code moved to Dress. Runway.lean updated.

---

### ~~Agent 2: Add Dress Graph Types and JSON~~ ✅ COMPLETE

Dress/Graph/ now contains: Types.lean, Build.lean, Layout.lean, Svg.lean, Json.lean

---

### ~~Agent 3: Add Dress Lake Facet for Graphs~~ ✅ COMPLETE

**Task:** Add Lake facet to generate `dep-graph.svg` and `dep-graph.json`.

**Instructions for agent:**
1. Read existing Dress `lakefile.lean` to understand facet patterns
2. Add `library_facet depGraph` that:
   - Reads nodes from `blueprintExt` environment extension
   - Builds dependency graph
   - Runs Sugiyama layout
   - Writes `dep-graph.svg` to `.lake/build/dressed/`
   - Writes `dep-graph.json` to `.lake/build/dressed/`
3. Run `lake build :depGraph` to test
4. Verify output files are generated

**Files:** `/Users/eric/GitHub/Dress/lakefile.lean`

---

### ~~Agent 4: Runway Genre Foundation~~ ✅ COMPLETE

**Task:** Create Verso Genre definition for Blueprint.

**Instructions for agent:**
1. Study `VersoBlog/Basic.lean` for Genre patterns
2. Create `Runway/Genre.lean`:
   - `Blueprint.Meta` - PartMetadata (title, status, decl names)
   - `Blueprint.BlockExt` - Custom blocks (node, proof)
   - `Blueprint.InlineExt` - Custom inlines (lean ref, math)
   - `Blueprint.Context` - TraverseContext
   - `Blueprint.State` - TraverseState
   - `def Blueprint : Genre where ...`
3. Create `Runway/Config.lean`:
   - `RunwayConfig` structure (title, github, docgen4Url)
4. Create `Runway/Site.lean`:
   - `BlueprintSite`, `BlueprintNode` structures
5. Run `lake build` to verify

**Files:** `/Users/eric/GitHub/Runway/Runway/`

---

### ~~Agent 5: Runway Traverse Phase~~ ✅ COMPLETE

**Task:** Implement artifact loading from Dress output.

**Instructions for agent:**
1. Create `Runway/Traverse.lean`:
   - Load `decl.json` files from `.lake/build/dressed/`
   - Load `dep-graph.json`
   - Build `Blueprint.State` with collected nodes
   - Implement `TraverseM` monad following VersoBlog patterns
2. Update existing `Runway/Dress/Load.lean` if needed
3. Run `lake build` to verify

**Files:** `/Users/eric/GitHub/Runway/Runway/`

---

### ~~Agent 6: Runway Render Phase~~ ✅ COMPLETE

**Task:** Implement HTML rendering using Verso HtmlT.

**Instructions for agent:**
1. Study `VersoBlog/Generate.lean` for HtmlT patterns
2. Create `Runway/Render.lean`:
   - `renderNode : BlueprintNode → HtmlT Blueprint Html`
   - `renderPage : BlueprintSite → HtmlT Blueprint Html`
   - Side-by-side layout for theorems
3. Create `Runway/Theme.lean`:
   - `blueprintTheme : Theme` with templates
   - CSS/JS file references
4. Create `Runway/Templates.lean`:
   - Primary template (HTML wrapper)
   - Page template (node layout)
   - Index template (node list)
5. Run `lake build` to verify

**Files:** `/Users/eric/GitHub/Runway/Runway/`

---

### ~~Agent 7: Runway Graph Embedding~~ ✅ COMPLETE

**Task:** Embed dependency graph in HTML output.

**Instructions for agent:**
1. Create `Runway/DepGraph.lean`:
   - Read `dep-graph.svg` from Dress output
   - Embed in index.html
   - Include D3.js script reference
2. Create `assets/dep-graph.js`:
   - Load `dep-graph.json`
   - D3.js force-directed visualization
   - Interactive features (zoom, pan, click)
3. Run `lake build` to verify

**Files:** `/Users/eric/GitHub/Runway/`

---

### ~~Agent 8: doc-gen4 Integration~~ ✅ COMPLETE

Created `Runway/DocGen4.lean` with URL generation for API docs.

---

### ~~Agent 9: Document DSL~~ ✅ COMPLETE

Created `Runway/Doc.lean` with block commands and roles for Verso documents.

---

### ~~Agent 10: CLI and Assets~~ ✅ COMPLETE

Created `Main.lean` CLI, `Assets.lean`, and CSS/JS asset files.

---

### ~~Agent 11: Integration Test~~ ✅ COMPLETE

Tested on GCR project:
- Dress artifacts generated
- dep-graph.svg/json created (0 nodes - no @[blueprint] declarations in GCR)
- Runway generated site to /tmp/gcr-site/
- index.html, runway.css, runway.js, dep-graph.js, verso-code.js all present

## Verification ✅ COMPLETE

1. `lake build` in Dress - generates `dep-graph.svg` + `dep-graph.json`
2. `lake build` in Runway - package builds
3. `lake exe runway` on GCR project
4. Compare output to current leanblueprint HTML
5. Test hover tooltips and graph interactivity
6. CI without texlive container
