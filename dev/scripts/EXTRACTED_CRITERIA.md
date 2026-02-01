# Extracted Visual Compliance Criteria

**Source:** 5 historical plan files
**Extracted:** 2026-01-31
**Total Criteria:** 52

---

## Summary

| Category | Count | Description |
|----------|-------|-------------|
| global | 5 | Site-wide requirements |
| dashboard | 5 | Dashboard homepage |
| dep_graph | 14 | Dependency graph page |
| sidebar | 6 | Navigation sidebar |
| chapter | 13 | Chapter/blueprint pages |
| code_display | 4 | Syntax highlighting |
| paper | 6 | Paper and PDF pages |
| blueprint_verso | 4 | Blueprint Verso documents |

**By Verification Type:** 36 visual, 9 interactive, 7 automated

---

## Global (5 criteria)

Site-wide requirements that apply to all pages.

| ID | Type | Description |
|----|------|-------------|
| `theme_toggle_visible` | interaction | Theme toggle button visible in header |
| `theme_toggle_functional` | interaction | Theme toggle switches between light and dark modes |
| `no_console_errors` | functional | No JavaScript console errors on page load |
| `responsive_layout` | layout | No horizontal overflow on viewport |
| `6_status_colors` | color | All 6 status colors render correctly site-wide |

### Status Color Reference

| Status | Color | Hex |
|--------|-------|-----|
| notReady | Sandy Brown | `#F4A460` |
| ready | Light Sea Green | `#20B2AA` |
| sorry | Dark Red | `#8B0000` |
| proven | Light Green | `#90EE90` |
| fullyProven | Forest Green | `#228B22` |
| mathlibReady | Light Blue | `#87CEEB` |

---

## Dashboard (5 criteria)

Dashboard homepage requirements.

| ID | Type | Description |
|----|------|-------------|
| `no_chapter_panel` | layout | Dashboard has NO secondary sidebar (chapter panel) |
| `stats_panel_visible` | content | Stats panel shows node counts by status |
| `stats_6_colors` | color | Stats panel displays all 6 status colors |
| `key_theorems_populated` | content | Key theorems panel populated with keyDeclaration nodes |
| `messages_panel` | content | Messages panel shows @[blueprint message] content |

---

## Dependency Graph (14 criteria)

Dependency graph page requirements.

| ID | Type | Description |
|----|------|-------------|
| `legend_6_colors` | color | Legend shows all 6 status colors with labels |
| `notReady_color` | color | notReady nodes: Sandy Brown `#F4A460` |
| `ready_color` | color | ready nodes: Light Sea Green `#20B2AA` |
| `sorry_color` | color | sorry nodes: Dark Red `#8B0000` |
| `proven_color` | color | proven nodes: Light Green `#90EE90` |
| `fullyProven_color` | color | fullyProven nodes: Forest Green `#228B22` |
| `mathlibReady_color` | color | mathlibReady nodes: Light Blue `#87CEEB` |
| `nodes_clickable` | interaction | Clicking a node opens modal with details |
| `modal_content` | content | Modal shows label, status, statement, and proof |
| `pan_controls` | interaction | Pan controls visible and functional |
| `zoom_controls` | interaction | Zoom in/out/fit controls visible and functional |
| `graph_centered` | layout | Graph centered in viewport on initial load |
| `edges_connecting` | layout | Edges connect source nodes to target nodes |
| `viewBox_origin` | technical | SVG viewBox starts at (0, 0) |

---

## Sidebar (6 criteria)

Navigation sidebar requirements.

| ID | Type | Description |
|----|------|-------------|
| `consistent_all_pages` | layout | Sidebar identical across all blueprint pages |
| `active_highlighted` | visual | Active page/section is highlighted |
| `highlight_full_width` | layout | Active highlight extends to viewport edge |
| `disabled_greyed` | visual | Disabled items are greyed out correctly |
| `chapters_listed` | content | All chapters listed in sidebar |
| `verso_docs_appear` | content | Verso documents appear in sidebar when present |

---

## Chapter (13 criteria)

Chapter/blueprint page requirements.

| ID | Type | Description |
|----|------|-------------|
| `side_by_side_aligned` | layout | Informal/formal displays horizontally aligned |
| `proof_collapse_state` | interaction | Proof bodies match collapse toggle state |
| `rainbow_brackets_6` | color | Rainbow brackets cycle through 6 colors |
| `bracket_level_0_consistent` | color | Level 0 brackets same color across ALL code blocks |
| `bracket_level_1_consistent` | color | Level 1 brackets same color across ALL code blocks |
| `bracket_level_2_consistent` | color | Level 2 brackets same color across ALL code blocks |
| `bracket_level_3_consistent` | color | Level 3 brackets same color across ALL code blocks |
| `bracket_level_4_consistent` | color | Level 4 brackets same color across ALL code blocks |
| `bracket_level_5_consistent` | color | Level 5 brackets same color across ALL code blocks |
| `hover_tooltips` | interaction | Hover tooltips functional on Lean code tokens |
| `tactic_state_toggle` | interaction | Tactic state toggles work |
| `zebra_striping_light` | visual | Zebra striping visible in light mode |
| `zebra_striping_dark` | visual | Zebra striping visible in dark mode |

### Bracket CSS Classes

| Level | CSS Class |
|-------|-----------|
| 0 | `lean-bracket-1` |
| 1 | `lean-bracket-2` |
| 2 | `lean-bracket-3` |
| 3 | `lean-bracket-4` |
| 4 | `lean-bracket-5` |
| 5 | `lean-bracket-6` |

---

## Code Display (4 criteria)

Code display and syntax highlighting requirements.

| ID | Type | Description |
|----|------|-------------|
| `syntax_highlighted` | visual | Lean code has syntax highlighting applied |
| `line_comments_styled` | visual | Line comments: `#6A9955`, italic |
| `line_comment_class` | technical | Line comments have class `line-comment` |
| `bracket_class_format` | technical | Brackets have class `lean-bracket-N` (N=1-6) |

---

## Paper (6 criteria)

Paper and PDF page requirements.

| ID | Type | Description |
|----|------|-------------|
| `tex_renders` | functional | paper.html generated from paper.tex |
| `verso_renders` | functional | paper_verso.html generated from Paper.lean |
| `pdf_generated` | functional | PDF compiled from TeX source |
| `leanStatement_renders` | content | :::leanStatement hook renders formal statement |
| `leanProof_renders` | content | :::leanProof hook renders formal proof |
| `sideBySide_renders` | layout | :::sideBySide hook renders side-by-side display |

---

## Blueprint Verso (4 criteria)

Blueprint Verso document requirements.

| ID | Type | Description |
|----|------|-------------|
| `leanNode_renders` | content | :::leanNode hook renders full side-by-side display |
| `leanModule_renders` | content | :::leanModule renders all nodes from module |
| `nodeRef_links` | interaction | Node references link to correct node |
| `statusDot_colors` | color | Status dots show correct colors per status |

---

## Source Files

| File | Focus |
|------|-------|
| `dapper-wondering-riddle.md` | Verso Blueprint & Paper authoring |
| `eager-soaring-cupcake.md` | Compliance loop design |
| `mighty-exploring-sunrise.md` | Release plan with 12 phases |
| `parsed-conjuring-torvalds.md` | Chrome MCP testing patterns |
| `wise-mapping-tarjan.md` | Verso integration & features |
