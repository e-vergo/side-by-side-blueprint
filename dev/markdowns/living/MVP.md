# Side-by-Side Blueprint: MVP Definition

A pure Lean toolchain for formalization documentation, building on leanblueprint's foundation with enhanced visualization and authoring capabilities.

---

## Core Value Proposition

Display formal Lean proofs alongside LaTeX theorem statements in a unified, interactive document. Enable mathematicians and formalization researchers to:

1. **Read proofs in context** - See the mathematical statement and its formal proof side-by-side
2. **Navigate dependencies** - Visualize and explore the logical structure of a formalization
3. **Verify completeness** - Understand proof status at a glance through visual indicators

---

## MVP Requirements

### 1. Side-by-Side Display

The defining feature. Each theorem/lemma/definition shows:
- **Left column**: LaTeX-rendered mathematical statement
- **Right column**: Syntax-highlighted Lean proof with interactive hovers

Both columns synchronized - expanding the LaTeX proof expands the Lean proof.

### 2. Dual Authoring Modes

**TeX Mode** (primary MVP authoring mode, leanblueprint-compatible)
- Author documents in LaTeX (`.tex` files)
- Familiar workflow for existing leanblueprint users
- `\inputleannode{label}` inserts side-by-side displays

**Verso Mode** (future capability, native Lean)
- Author documents in Verso (`.lean` files)
- Type-checked documentation with IDE support
- `:::leanNode "label"` inserts side-by-side displays
- **Planned for post-MVP** -- infrastructure exists but not yet an active deliverable

TeX mode is the primary authoring path for MVP. Verso mode will produce equivalent HTML output once fully integrated.

### 3. Dependency Graph

Interactive visualization of the proof dependency structure:
- Nodes represent theorems/lemmas/definitions
- Edges show logical dependencies (statement uses vs proof uses)
- Click nodes to view details and navigate to source
- Pan, zoom, and fit controls

### 4. Status Indicators

Six-color status model reflecting proof state:

| Status | Color | Meaning |
|--------|-------|---------|
| Not Ready | Sandy Brown | Theorem stated but not ready for formalization |
| Ready | Light Sea Green | Ready to be formalized |
| Sorry | Dark Red | Proof contains `sorry` |
| Proven | Light Green | Complete proof |
| Fully Proven | Forest Green | Proven with all dependencies also proven |
| Mathlib Ready | Light Blue | Ready for mathlib contribution |

Status automatically inferred from proof state, with manual override options.

### 5. Dashboard

Landing page providing project overview:
- Aggregate statistics (proven/total, sorry count, etc.)
- Key theorems highlighted
- Messages and notes from authors
- Navigation to all sections

### 6. Paper Generation

Academic paper output from the same source:
- ar5iv-style HTML rendering
- PDF generation via LaTeX
- Verification badges linking statements to formal proofs
- Verification badges showing formalization status (Verified, In Progress, Not Started) next to theorem statements
- Primary support for TeX authoring (Verso planned for future)

### 7. CI/CD Integration

GitHub Action for automated deployment:
- Single workflow file addition
- Builds toolchain, generates site, deploys to Pages
- No local tooling installation required for users

---

## Visual Standards

Professional presentation with clean aesthetics:
- Consistent typography and spacing
- Manual dark/light theme toggle with system preference fallback
- Desktop/landscape layout optimized for wide screens
- Rainbow bracket highlighting for Lean code readability
- No horizontal scrollbars -- all content, including side-by-side displays, must fit within the viewport width
- Hover tooltips bounded in width with consistent styling

### 8. Interactive Components & Design Consistency

- Working proof toggles (expand/collapse with synchronized LaTeX and Lean panels)
- Graph node modals with status, statement, and proof details
- Lean code hover tooltips with type signatures (bounded width, consistent styling)
- Theme toggle (dark/light) with localStorage persistence and system preference fallback
- Sidebar navigation across all page types (dashboard, graph, blueprint chapters, paper)
- Chapter prev/next navigation
- Design language consistency across all page types -- unified colors, typography, spacing

---

## Compatibility

### With leanblueprint
- TeX document structure compatible
- Similar LaTeX commands for inserting Lean content
- Familiar workflow for existing users

### With LeanArchitect
- Uses `@[blueprint]` attribute for theorem annotation
- Supports all 8 metadata options and 3 status flags
- Dependency inference from attribute

### With Mathlib
- Works with mathlib-based projects
- Fetches mathlib cache for fast builds
- Handles large-scale formalizations (500+ nodes tested)

---

## Showcase Repository Requirements

The toolchain's credibility depends on compelling demonstrations. Each showcase serves a distinct purpose:

### SBS-Test: Feature Completeness

The test project must exercise every feature:
- All 6 status colors represented (nodes in each state)
- Both authoring modes (TeX and Verso documents)
- Dependency graph with meaningful structure (not just linear)
- Dashboard with populated stats, key theorems, messages
- Paper generation (HTML and PDF)
- All interactive features (hovers, toggles, modals, zoom/pan)
- Edge cases: multi-paragraph proofs, complex LaTeX, nested structures

**Criterion:** A developer can point to SBS-Test to answer "does feature X work?"

### GCR: Polished Showcase

A complete, professional example:
- Finished mathematical content (complete proof, no `sorry`)
- Full blueprint document with proper narrative
- Complete academic paper (HTML and PDF)
- All metadata populated (authors, abstract, references)
- Visual polish appropriate for public demonstration

**Criterion:** GCR is what we show to potential users. It must look finished.

### PNT: Scale Validation

Integration stress test and existence proof:
- 500+ nodes rendering correctly
- Build completes in reasonable time
- All interactive features remain responsive at scale
- Dependency graph performance acceptable (zoom/pan/click must not lag significantly)
- No visual degradation (graph legible, navigation works)
- Demonstrates compatibility with real-world, in-progress projects

**Criterion:** "If it works on PNT, it works." Undeniable artifact for credibility with the formal verification community. (PNT is maintained by Terence Tao and Alex Kontorovich—high-profile validation.)

---

## What MVP Does NOT Include

- Automatic synchronization with upstream mathlib changes
- Multi-project aggregation (single project per site)
- Collaborative editing features
- Version history or diff visualization
- Mobile/tablet responsive layout (desktop-only)
- Verso-native document generation (planned for future)
- Dependency graph filter controls

---

## Success Criteria

MVP is complete when:

1. **Side-by-side works** - Theorems display with LaTeX left, Lean right
2. **TeX authoring mode works** - TeX documents render correctly (Verso planned)
3. **Dependency graph works** - Interactive visualization with all controls
4. **Status colors work** - All six states display with correct colors
5. **Dashboard works** - Stats, key theorems, navigation functional
6. **Paper generation works** - HTML and PDF output from same source
7. **CI/CD works** - GitHub Action deploys functional site
8. **Visual quality** - Professional appearance, no jarring elements
9. **Interactive components work** - Toggles, modals, hovers, navigation all functional
10. **Design consistency** - No horizontal scrollbars, no visual artifacts, cohesive design language
