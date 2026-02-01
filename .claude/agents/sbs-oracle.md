---
name: sbs-oracle
description: Zero-shot question answering agent for SBS codebase
model: opus
color: blue
---

# SBS Oracle

Answer codebase questions without file reads. Flag uncertainty explicitly.

**Priority order:**
1. Factual correctness (accuracy/precision of answer)
2. Response formatting (efficient tokens, full clarity)
3. Speed

---

## Concept Index

| Concept | Primary Location | Notes |
|---------|-----------------|-------|
| * hover token | `storage/*_hover_token.png` | Token hover popup |
| * proof toggle | `storage/*_proof_toggle.png` | Proof expanded state |
| * theme toggle | `storage/*_theme_toggle.png` | Dark mode variant |
| 6-status color model | `dev/markdowns/README.md` | Features |
| 6-status tracking | `showcase/General_Crystallographic_Restriction/README.md` | Documentation Toolchain |
| 8-dimensional quality scoring | `dev/markdowns/README.md` | Features |
| >100 node optimizations | `CLAUDE.md` | Graph Layout Performance |
| [side-by-side blueprint](https://github.com/e-vergo/side-by-side-blueprint) | `showcase/General_Crystallographic_Restriction/README.md` | Documentation Toolchain |
| [storage & tooling hub](../../dev/storage/readme.md) | `toolchain/SBS-Test/README.md` | Tooling & Archive System |
| `@[blueprint]` attributes | `toolchain/dress-blueprint-action/README.md` | Project Requirements |
| a proof that typechecks is not necessarily the proof you intended | `toolchain/dress-blueprint-action/README.md` | Motivation |
| absolute imports | `dev/scripts/README.md` | Design Principles |
| action | `CLAUDE.md/action.yml` | GitHub Action (432 lines, 14 steps) |
| action size | `CLAUDE.md` | CI/CD Architecture |
| activity heatmap | `CLAUDE.md` | Visualizations |
| alex kontorovich | `showcase/PrimeNumberTheoremAnd/README.md` | Original PNT+ Project |
| align | `dev/storage/README.md` | Creating Rubrics |
| alignment (q&a) | `CLAUDE.md` | `/execute` |
| always use `python build.py` for builds | `CLAUDE.md` | Standards |
| always use the python build script. never skip commits or pushes. | `CLAUDE.md` | Build Requirement |
| architect/attribute | `CLAUDE.md/Architect/Attribute.lean` | `@[blueprint]` attribute with all options |
| architect/basic | `CLAUDE.md/Architect/Basic.lean` | `Node`, `NodePart`, `NodeStatus` with manual `ToExpr` instance |
| architect/collect used | `CLAUDE.md/Architect/CollectUsed.lean` | Dependency inference from expression trees |
| archiveentry | `CLAUDE.md` | Archive Entries |
| assets/blueprint | `CLAUDE.md/assets/blueprint.css` | Blueprint pages, sidebar, side-by-side |
| assets/common | `CLAUDE.md/assets/common.css` | Design system, status dots, rainbow brackets |
| assets/verso code | `CLAUDE.md/assets/verso-code.js` | Hovers, pan/zoom, modal handling |
| at least | `toolchain/SBS-Test/README.md` | Motivation: The Tao Incident |
| at most | `toolchain/SBS-Test/README.md` | Motivation: The Tao Incident |
| attribution | `toolchain/Runway/README.md` | Runway |
| auto-computed `fullyproven` status | `dev/markdowns/README.md` | Features |
| automatic dependency inference | `showcase/General_Crystallographic_Restriction/README.md` | Documentation Toolchain |
| backward direction: | `showcase/General_Crystallographic_Restriction/README.md` | Proof Strategy |
| base.py | `dev/scripts/sbs/tests/README.md` | validators/ |
| basevalidator | `dev/storage/README.md` | Creating Custom Validators |
| block | `toolchain/Runway/README.md` | LaTeX Parsing Modules |
| block directives: | `forks/verso/README.md` | 1. SBSBlueprint Genre (`src/verso-sbs/`) |
| blueprint | `toolchain/Runway/README.md` | Module Architecture |
| blueprint directory | `toolchain/dress-blueprint-action/README.md` | Project Requirements |
| blueprint-specific: | `toolchain/Runway/README.md` | Supported LaTeX Commands |
| blueprintsite | `toolchain/Runway/README.md` | Module Architecture |
| brackets | `forks/verso/README.md` | 3. Rainbow Bracket Highlighting (`src/verso/Verso/Code/Highlighted.lean`) |
| brainstorm | `dev/storage/README.md` | Creating Rubrics |
| build & run | `showcase/PrimeNumberTheoremAnd/README.md` | Quick Links |
| build and verify: | `toolchain/SBS-Test/README.md` | Using as a Template |
| build phases are standalone functions | `dev/scripts/sbs/build/README.md` | Design Notes |
| build: | `CLAUDE.md` | Standard Workflow for Visual Changes |
| buildorchestrator | `dev/scripts/sbs/build/README.md` | Design Notes |
| canonical reference: | `CLAUDE.md` | Archive System |
| canonical status colors | `CLAUDE.md` | Dress (`toolchain/Dress/`) |
| capture | `dev/scripts/sbs/tests/compliance/README.md` | Workflow |
| capture/elab rules | `CLAUDE.md/Capture/ElabRules.lean` | elab_rules hooks for @[blueprint] declarations |
| capture: | `CLAUDE.md` | Standard Workflow for Visual Changes |
| categories | `dev/storage/README.md` | Rubric Structure |
| centralized complexity | `toolchain/dress-blueprint-action/README.md` | Design Philosophy |
| changed files list | `dev/storage/README.md` | What It Checks |
| chapter pages | `toolchain/SBS-Test/README.md` | What to Inspect |
| chapterinfo | `toolchain/Runway/README.md` | Module Architecture |
| check results | `SBS-Test/checkResults.connected` | false (due to disconnected cycle) |
| checking svg output: | `CLAUDE.md` | Graph Debugging Tips |
| clone and rename: | `toolchain/SBS-Test/README.md` | Using as a Template |
| cmd.py | `dev/scripts/sbs/tests/README.md` | rubrics/ |
| color source of truth | `toolchain/dress-blueprint-action/README.md` | 6-Status Color Model |
| color source of truth: | `CLAUDE.md` | 6-Status Color Model |
| complete feature coverage | `toolchain/SBS-Test/README.md` | Purpose |
| complex analysis approach | `showcase/PrimeNumberTheoremAnd/README.md` | Project Overview |
| complexity by phase: | `CLAUDE.md` | Graph Layout Performance |
| concept index | `CLAUDE.md` | What the Oracle Knows |
| config | `toolchain/Runway/README.md` | Module Architecture |
| configuration loading | `toolchain/Runway/README.md` | Processing Steps |
| conftest.py | `dev/scripts/sbs/tests/README.md` | pytest/ |
| connectivity | `dev/markdowns/README.md` | Validation Features |
| connectivity validation | `showcase/PrimeNumberTheoremAnd/README.md` | What This Fork Demonstrates |
| connectivity: | `CLAUDE.md` | Validation Checks |
| constraint: | `CLAUDE.md` | Orchestration Model |
| containment search | `forks/subverso/README.md` | Identifier Resolution |
| coordinate normalization pattern: | `CLAUDE.md` | Graph Debugging Tips |
| core components: | `showcase/General_Crystallographic_Restriction/README.md` | Documentation Toolchain |
| core documentation: | `CLAUDE.md` | Reference Documents |
| core palette | `toolchain/dress-blueprint-action/README.md` | CSS Variables |
| core responsibilities: | `toolchain/Dress/README.md` | Overview |
| create | `dev/storage/README.md` | Creating Rubrics |
| cross-repo impact | `CLAUDE.md` | What the Oracle Knows |
| css (embedded in `highlightingstyle`): | `forks/verso/README.md` | 3. Rainbow Bracket Highlighting (`src/verso/Verso/Code/Highlighted.lean`) |
| current score: | `dev/storage/README.md` | Quality Scoring |
| cycles | `dev/markdowns/README.md` | Validation Features |
| cycles: | `CLAUDE.md` | Validation Checks |
| dark/light theme toggle | `dev/markdowns/README.md` | Features |
| dashboard | `toolchain/SBS-Test/README.md` | What to Inspect |
| dashboard homepage | `toolchain/Runway/README.md` | Features |
| dashboard stat discrepancies: | `toolchain/Runway/README.md` | Debugging Tips |
| declarative rules | `dev/storage/README.md` | Auto-Tagging |
| dep graph | `CLAUDE.md/DepGraph.lean` | Dependency graph page with modals |
| dep graph node click * | `storage/dep_graph_node_click_*.png` | Node modal views |
| dep graph zoom * | `storage/dep_graph_zoom_*.png` | Zoom in/out/fit states |
| dependency graph | `toolchain/SBS-Test/README.md` | What to Inspect |
| dependency inference: | `CLAUDE.md` | Key Technical Details |
| depgraph.lean | `toolchain/Runway/README.md` | Key Module Details |
| design/ | `dev/scripts/sbs/tests/README.md` | validators/ |
| detailed references | `CLAUDE.md` | Reference Documents |
| deterministic tests (50% weight): | `CLAUDE.md` | 8-Dimensional Test Suite (T1-T8) |
| dev/scripts/sbs/tests/compliance/criteria | `CLAUDE.md/dev/scripts/sbs/tests/compliance/criteria.py` | Compliance criteria per page |
| dev/scripts/sbs/tests/compliance/ledger ops | `CLAUDE.md/dev/scripts/sbs/tests/compliance/ledger_ops.py` | Ledger management |
| dev/scripts/sbs/tests/compliance/mapping | `CLAUDE.md/dev/scripts/sbs/tests/compliance/mapping.py` | Repo->page change detection |
| dev/scripts/sbs/tests/compliance/validate | `CLAUDE.md/dev/scripts/sbs/tests/compliance/validate.py` | Validation orchestration |
| dev/storage/compliance ledger | `CLAUDE.md/dev/storage/compliance_ledger.json` | Persistent status |
| dev/storage/compliance status | `CLAUDE.md/dev/storage/COMPLIANCE_STATUS.md` | Human-readable report |
| dev/storage/readme | `CLAUDE.md/dev/storage/README.md` | Central CLI tooling documentation (capture, compliance, rubrics, archive) |
| dev/storage/unified ledger | `SBS-Test/dev/storage/unified_ledger.json` | Build metrics and timing |
| do not | `dev/scripts/.pytest_cache/README.md` | pytest cache directory # |
| document | `toolchain/Runway/README.md` | LaTeX Parsing Modules |
| document structure: | `toolchain/Runway/README.md` | Supported LaTeX Commands |
| domain context: | `CLAUDE.md` | How This Document Works |
| dress | `CLAUDE.md` | Repository Map |
| dress artifacts | `toolchain/SBS-Test/README.md` | Testing Points |
| dress dependency | `toolchain/dress-blueprint-action/README.md` | Project Requirements |
| dress-blueprint-action | `CLAUDE.md` | Repository Map |
| during ci | `toolchain/dress-blueprint-action/README.md` | Asset Integration |
| environment lookup with suffix matching | `forks/subverso/README.md` | Identifier Resolution |
| execute | `dev/storage/README.md` | Creating Rubrics |
| execution | `CLAUDE.md` | `/execute` |
| expected build time: | `toolchain/SBS-Test/README.md` | Local Development |
| expected layout times: | `CLAUDE.md` | Graph Layout Performance |
| fast iteration | `toolchain/SBS-Test/README.md` | Purpose |
| feature set: | `showcase/General_Crystallographic_Restriction/README.md` | Documentation Toolchain |
| file purpose map | `CLAUDE.md` | What the Oracle Knows |
| finalization | `CLAUDE.md` | `/execute` |
| finalize | `dev/storage/README.md` | Creating Rubrics |
| for full upstream documentation, see [hanwenzhu/leanarchitect](https://github.com/hanwenzhu/leanarchitect). | `forks/LeanArchitect/README.md` | LeanArchitect |
| for lean software development (not proofs): | `CLAUDE.md` | MCP Tool Usage |
| for local development | `toolchain/dress-blueprint-action/README.md` | Asset Integration |
| fork of [hanwenzhu/leanarchitect](https://github.com/hanwenzhu/leanarchitect) | `forks/LeanArchitect/README.md` | LeanArchitect |
| forward direction: | `showcase/General_Crystallographic_Restriction/README.md` | Proof Strategy |
| fully static | `toolchain/Runway/README.md` | Sidebar Navigation |
| fullyproven | `dev/markdowns/README.md` | Validation Features |
| general crystallographic restriction | `showcase/PrimeNumberTheoremAnd/README.md` | Related Projects |
| general_crystallographic_restriction | `CLAUDE.md` | Repository Map |
| git ops | `scripts/git_ops.py` | Git status, diff, and sync operations |
| github action | `toolchain/dress-blueprint-action/README.md` | Overview |
| gotchas | `CLAUDE.md` | What the Oracle Knows |
| graceful degradation | `toolchain/Runway/README.md` | Design Principles |
| graph | `toolchain/Runway/README.md` | Module Architecture |
| graph layout | `toolchain/SBS-Test/README.md` | Testing Points |
| graph structure: | `toolchain/SBS-Test/README.md` | StatusDemo.lean (14 nodes) |
| graph/build | `CLAUDE.md/Graph/Build.lean` | Graph construction, validation, `Node.inferUses`, two-pass edge processing |
| graph/layout | `CLAUDE.md/Graph/Layout.lean` | Sugiyama algorithm (~1500 lines), edge routing |
| graph/svg | `CLAUDE.md/Graph/Svg.lean` | SVG generation, **canonical status colors** |
| guiding principle: | `CLAUDE.md` | User Preferences |
| hadamard factorization | `showcase/PrimeNumberTheoremAnd/README.md` | Project Overview |
| heuristic tests (50% weight): | `CLAUDE.md` | 8-Dimensional Test Suite (T1-T8) |
| highlight contradictions immediately. | `CLAUDE.md` | Meta-Cognitive Expectations |
| highlighting accounts for 93-99% of total build time | `forks/subverso/README.md` | Fork Purpose |
| highlightstate | `toolchain/Dress/README.md` | SubVerso Integration |
| hover tooltips | `dev/markdowns/README.md` | Features |
| how it works: | `toolchain/Runway/README.md` | Module Reference Support |
| how-to patterns | `CLAUDE.md` | What the Oracle Knows |
| html generation | `toolchain/Runway/README.md` | Processing Steps |
| html render | `CLAUDE.md/HtmlRender.lean` | Verso HTML rendering wrapper with rainbow brackets |
| icloud backup: | `CLAUDE.md` | Directory Structure |
| id normalization: | `CLAUDE.md` | Key Technical Details |
| if you act on a preference below and the user pushes back, say so explicitly. | `CLAUDE.md` | Meta-Cognitive Expectations |
| implementation: | `forks/verso/README.md` | 3. Rainbow Bracket Highlighting (`src/verso/Verso/Code/Highlighted.lean`) |
| in progress | `toolchain/Runway/README.md` | Verification Badges |
| indextemplate | `toolchain/Runway/README.md` | Key Module Details |
| infinite loop protection | `toolchain/Runway/README.md` | Design Principles |
| infotable | `forks/subverso/README.md` | Fork Purpose |
| inline | `toolchain/Runway/README.md` | LaTeX Parsing Modules |
| inline roles: | `forks/verso/README.md` | 1. SBSBlueprint Genre (`src/verso-sbs/`) |
| inputs consumed: | `toolchain/Runway/README.md` | Role in the Toolchain |
| interactive dependency graph | `toolchain/Runway/README.md` | Features |
| javascript | `toolchain/dress-blueprint-action/README.md` | Overview |
| javascript pan/zoom: | `CLAUDE.md` | Graph Debugging Tips |
| key files: | `CLAUDE.md` | Visual Compliance (CLI) |
| key properties: | `CLAUDE.md` | `/execute` |
| key results: | `showcase/PrimeNumberTheoremAnd/README.md` | Project Overview |
| key theorems | `toolchain/Runway/README.md` | Dashboard (index.html) |
| lakefile | `SBS-Test/lakefile.toml` | Change `name = "SBSTest"` to your project name |
| large-scale integration | `showcase/PrimeNumberTheoremAnd/README.md` | Related Projects |
| large-scale integration example | `showcase/PrimeNumberTheoremAnd/README.md` | Side-by-Side Blueprint Integration |
| latex parsing | `toolchain/Runway/README.md` | Processing Steps |
| latex/parser | `CLAUDE.md/Latex/Parser.lean` | LaTeX parsing with O(n) string concatenation |
| lean: | `forks/verso/README.md` | Dependencies |
| leanarchitect | `CLAUDE.md` | Repository Map |
| leanblueprint | `showcase/General_Crystallographic_Restriction/README.md` | Attribution |
| ledger | `scripts/ledger.py` | Build metrics and unified ledger data structures |
| less relevant: | `CLAUDE.md` | MCP Tool Usage |
| live demo: | `showcase/General_Crystallographic_Restriction/README.md` | The Crystallographic Restriction Theorem |
| live site | `showcase/PrimeNumberTheoremAnd/README.md` | Quick Links |
| live site: | `toolchain/SBS-Test/README.md` | SBS-Test |
| loc trends | `CLAUDE.md` | Visualizations |
| local ground truth: | `CLAUDE.md` | Directory Structure |
| location: | `CLAUDE.md` | `/execute` |
| loop | `dev/scripts/sbs/tests/compliance/README.md` | Workflow |
| main | `CLAUDE.md/Main.lean` | CLI: `extract_blueprint graph` |
| main.lean | `toolchain/Runway/README.md` | Module Architecture |
| make changes | `CLAUDE.md` | Standard Workflow for Visual Changes |
| manifest | `toolchain/SBS-Test/README.md` | What to Inspect |
| manifest generation | `toolchain/SBS-Test/README.md` | Testing Points |
| manifest loading | `toolchain/Runway/README.md` | Processing Steps |
| manifest-driven soundness | `toolchain/Runway/README.md` | Features |
| manual `toexpr` instance: | `CLAUDE.md` | Key Technical Details |
| manual status flags (3): | `CLAUDE.md` | `@[blueprint]` Attribute Options |
| manual triggers only | `toolchain/dress-blueprint-action/README.md` | Design Philosophy |
| math: | `toolchain/Runway/README.md` | Supported LaTeX Commands |
| mathjax compatibility | `toolchain/Runway/README.md` | Design Principles |
| mathlib cache | `CLAUDE.md` | CI/CD Architecture |
| mediumpnt | `showcase/PrimeNumberTheoremAnd/README.md` | Project Overview |
| messages | `toolchain/Runway/README.md` | Dashboard (index.html) |
| metadata options (8): | `CLAUDE.md` | `@[blueprint]` Attribute Options |
| metrics | `dev/storage/README.md` | Rubric Structure |
| minimal dependencies | `dev/scripts/sbs/core/README.md` | Design Principles |
| module reference support | `showcase/PrimeNumberTheoremAnd/README.md` | What This Fork Demonstrates |
| module reference support: | `CLAUDE.md` | Key Technical Details |
| module references | `toolchain/Runway/README.md` | Features |
| motivation: | `toolchain/Dress/README.md` | Connectivity (`findComponents`) |
| multi-page chapter navigation | `toolchain/Runway/README.md` | Features |
| myproject.chapter.module | `toolchain/Runway/README.md` | Module Reference Support |
| never delete or replace a plan without explicit user direction. | `CLAUDE.md` | Planning Discipline |
| no circular dependencies | `dev/scripts/README.md` | Design Principles |
| no command handlers | `dev/scripts/sbs/core/README.md` | Design Principles |
| no duplicate code | `dev/scripts/sbs/build/README.md` | Design Notes |
| no github actions mathlib cache | `toolchain/dress-blueprint-action/README.md` | Design Philosophy |
| node assignment | `toolchain/Runway/README.md` | Processing Steps |
| nodeinfo | `toolchain/Runway/README.md` | Module Architecture |
| nodepart | `CLAUDE.md` | LeanArchitect (`forks/LeanArchitect/`) |
| nodestatus | `CLAUDE.md` | LeanArchitect (`forks/LeanArchitect/`) |
| nodetemplate | `toolchain/Runway/README.md` | Key Module Details |
| non-invasive integration | `showcase/PrimeNumberTheoremAnd/README.md` | What This Fork Demonstrates |
| not started | `toolchain/Runway/README.md` | Verification Badges |
| note: | `toolchain/SBS-Test/README.md` | Build Script Steps |
| o(1) exact position lookup | `forks/subverso/README.md` | Identifier Resolution |
| o(1) name-based search | `forks/subverso/README.md` | Identifier Resolution |
| o(n) string concatenation | `toolchain/Runway/README.md` | Design Principles |
| one at a time | `toolchain/Dress/README.md` | 1. Acyclic Transformation |
| orchestration structure: | `CLAUDE.md` | How This Document Works |
| orchestrator | `CLAUDE.md` | Orchestration Model |
| original repositories: | `showcase/PrimeNumberTheoremAnd/README.md` | Original PNT+ Project |
| outputs generated: | `toolchain/Runway/README.md` | Role in the Toolchain |
| pan/zoom implementation | `toolchain/dress-blueprint-action/README.md` | verso-code.js (490 lines) |
| paper | `CLAUDE.md/Paper.lean` | Paper rendering, `PaperMetadata` extraction |
| paper (html and pdf) | `showcase/General_Crystallographic_Restriction/README.md` | The Crystallographic Restriction Theorem |
| paper generation | `toolchain/Runway/README.md` | Features |
| paper metadata extraction: | `CLAUDE.md` | Key Technical Details |
| paper tex | `Runway/paper_tex.html` | MathJax-rendered paper with verification badges |
| paper-specific: | `toolchain/Runway/README.md` | Supported LaTeX Commands |
| paper.lean | `toolchain/Runway/README.md` | Key Module Details |
| papermetadata | `CLAUDE.md` | Runway (`toolchain/Runway/`) |
| papernodeinfo | `toolchain/Runway/README.md` | Key Module Details |
| papernodeinfoext | `toolchain/Runway/README.md` | Key Module Details |
| parent project: | `forks/subverso/README.md` | SubVerso (Side-by-Side Blueprint Fork) |
| part of the [side-by-side blueprint](https://github.com/e-vergo/side-by-side-blueprint) monorepo. | `toolchain/Dress/README.md` | Overview |
| pdf compilation | `toolchain/Runway/README.md` | Features |
| pdf tex | `Runway/pdf_tex.html` | PDF viewer page with embedded PDF |
| pdf/paper generation | `dev/markdowns/README.md` | Features |
| per-repository documentation: | `CLAUDE.md` | Reference Documents |
| performance at scale | `showcase/PrimeNumberTheoremAnd/README.md` | What This Fork Demonstrates |
| phase 1: per-declaration capture | `CLAUDE.md` | Build Pipeline Phases |
| phase 2: lake facet aggregation | `CLAUDE.md` | Build Pipeline Phases |
| phase 3: manifest generation | `CLAUDE.md` | Build Pipeline Phases |
| phase 4: site generation | `CLAUDE.md` | Build Pipeline Phases |
| placeholder expansion | `toolchain/Runway/README.md` | Processing Steps |
| placeholder system | `toolchain/Runway/README.md` | Key Development Patterns |
| planning | `CLAUDE.md` | `/execute` |
| practice introspection. | `CLAUDE.md` | Meta-Cognitive Expectations |
| preamble | `toolchain/Runway/README.md` | LaTeX Parsing Modules |
| primenumbertheoremand | `CLAUDE.md` | Repository Map |
| priority order | `toolchain/SBS-Test/README.md` | Status Color Model |
| priority order: | `CLAUDE.md` | 6-Status Color Model |
| project leads: | `showcase/PrimeNumberTheoremAnd/README.md` | Original PNT+ Project |
| project notes | `toolchain/Runway/README.md` | Dashboard (index.html) |
| proof dependencies | `forks/LeanArchitect/README.md` | Dependency Inference |
| prototype status | `toolchain/Runway/README.md` | Runway |
| python hooks | `dev/storage/README.md` | Auto-Tagging |
| rainbow bracket highlighting | `forks/verso/README.md` | Fork Purpose |
| rainbow bracket highlighting: | `CLAUDE.md` | Key Technical Details |
| rainbow brackets | `showcase/General_Crystallographic_Restriction/README.md` | Documentation Toolchain |
| rebuild: | `CLAUDE.md` | Standard Workflow for Visual Changes |
| refer to: | `toolchain/SBS-Test/README.md` | Archive & Metrics |
| registry.py | `dev/scripts/sbs/tests/README.md` | validators/ |
| render | `CLAUDE.md/Render.lean` | Dashboard, side-by-side rendering |
| render.lean | `toolchain/Runway/README.md` | Key Module Details |
| renderm | `toolchain/Runway/README.md` | Module Architecture |
| renderm monad | `toolchain/Runway/README.md` | Key Development Patterns |
| replace demo content: | `toolchain/SBS-Test/README.md` | Using as a Template |
| required: | `CLAUDE.md` | Output Locations |
| requirements: | `toolchain/Runway/README.md` | Module Reference Support |
| rubric | `dev/scripts/sbs/tests/README.md` | rubrics/ |
| rubric.py | `dev/scripts/sbs/tests/README.md` | rubrics/ |
| rubriccriterion | `dev/scripts/sbs/tests/README.md` | rubrics/ |
| rubricevaluation | `dev/scripts/sbs/tests/README.md` | rubrics/ |
| run from: | `dev/storage/README.md` | Quick Reference |
| runs automatically | `CLAUDE.md` | Archive Upload |
| runway | `CLAUDE.md` | Repository Map |
| runway.json | `toolchain/dress-blueprint-action/README.md` | Project Requirements |
| runway/assets.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/availabledocuments.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/config.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/depgraph.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/doc.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/docgen4.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/dress.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/genre.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/graph.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/html/render.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/latex/ | `toolchain/Runway/README.md` | Module Architecture |
| runway/macros.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/paper.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/pdf.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/render.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/site.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/templates.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/theme.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/traverse.lean | `toolchain/Runway/README.md` | Module Architecture |
| runway/versopaper.lean | `toolchain/Runway/README.md` | Module Architecture |
| sbs toolchain | `showcase/PrimeNumberTheoremAnd/README.md` | Quick Links |
| sbs-test | `CLAUDE.md` | Repository Map |
| sbsblueprint | `forks/verso/README.md` | Fork Purpose |
| score calculation: | `CLAUDE.md` | 8-Dimensional Test Suite (T1-T8) |
| score tracking: | `CLAUDE.md` | 8-Dimensional Test Suite (T1-T8) |
| scoring | `dev/storage/README.md` | Rubric Structure |
| screenshot capture is the first reflex for any visual/css/layout issue. | `CLAUDE.md` | Visual Testing & Debugging |
| screenshots: | `toolchain/SBS-Test/README.md` | Archive & Metrics |
| sectioninfo | `toolchain/Runway/README.md` | Module Architecture |
| security testing | `toolchain/SBS-Test/README.md` | Purpose |
| see: | `toolchain/SBS-Test/README.md` | Run compliance validation |
| sequentially, never in parallel | `CLAUDE.md` | Orchestration Model |
| side-by-side blueprint | `showcase/General_Crystallographic_Restriction/README.md` | Attribution |
| side-by-side display | `toolchain/Runway/README.md` | Features |
| side-by-side display issues: | `toolchain/Runway/README.md` | Debugging Tips |
| sidebar not showing: | `toolchain/Runway/README.md` | Debugging Tips |
| simplified per-project workflows | `toolchain/dress-blueprint-action/README.md` | Design Philosophy |
| single command, single purpose | `dev/scripts/README.md` | Design Principles |
| site building | `toolchain/Runway/README.md` | Processing Steps |
| site output | `toolchain/SBS-Test/README.md` | Testing Points |
| sitebuilder | `toolchain/Runway/README.md` | Module Architecture |
| soundness guarantee: | `toolchain/Runway/README.md` | manifest.json Schema |
| src/sub verso/highlighting/code | `CLAUDE.md/src/SubVerso/Highlighting/Code.lean` | Main highlighting with InfoTable indexing |
| src/sub verso/highlighting/highlighted | `CLAUDE.md/src/SubVerso/Highlighting/Highlighted.lean` | Token.Kind, Highlighted types |
| src/verso/verso/code/highlighted | `CLAUDE.md/src/verso/Verso/Code/Highlighted.lean` | Rainbow bracket rendering (`toHtmlRainbow`) |
| statement dependencies | `forks/LeanArchitect/README.md` | Dependency Inference |
| stats | `toolchain/Runway/README.md` | Dashboard (index.html) |
| status computation | `toolchain/SBS-Test/README.md` | Testing Points |
| status priority | `toolchain/Dress/README.md` | 6-Status Color Model |
| string | `forks/LeanArchitect/README.md` | 8 Metadata Options |
| subagent spawning: | `CLAUDE.md` | Agent Orchestration |
| subverso | `CLAUDE.md` | Repository Map |
| subverso infotable | `CLAUDE.md` | Key Technical Details |
| subverso: | `forks/verso/README.md` | Dependencies |
| template | `toolchain/Runway/README.md` | Key Module Details |
| template for new projects | `toolchain/SBS-Test/README.md` | Purpose |
| terence tao | `showcase/PrimeNumberTheoremAnd/README.md` | Original PNT+ Project |
| terence tao, january 2026 | `toolchain/dress-blueprint-action/README.md` | Motivation |
| test_cli.py | `dev/scripts/sbs/tests/README.md` | pytest/ |
| test_ledger_health.py | `dev/scripts/sbs/tests/README.md` | pytest/ |
| text formatting: | `toolchain/Runway/README.md` | Supported LaTeX Commands |
| the core insight | `toolchain/dress-blueprint-action/README.md` | Motivation |
| the sidebar is fully static. | `CLAUDE.md` | Sidebar Architecture |
| theme | `CLAUDE.md/Theme.lean` | Page templates, sidebar, `buildModuleLookup`, `isBlueprintPage` |
| theme templates | `toolchain/Runway/README.md` | Key Development Patterns |
| theme toggle | `toolchain/Runway/README.md` | Features |
| theme.lean | `toolchain/Runway/README.md` | Key Module Details |
| theorem (crystallographic restriction). | `showcase/General_Crystallographic_Restriction/README.md` | Main Result |
| theorems: | `toolchain/Runway/README.md` | Supported LaTeX Commands |
| these preferences guide all decision-making, planning, and actions. follow them unless the user explicitly directs otherwise. | `CLAUDE.md` | User Preferences |
| this is a fork of the original [pnt+](https://github.com/alexkontorovich/primenumbertheoremand) project with [side-by-side blueprint](https://github.com/e-vergo/side-by-side-blueprint) integration. | `showcase/PrimeNumberTheoremAnd/README.md` |  |
| this is lean software development, not proof writing. | `CLAUDE.md` | Project Context |
| this is the central reference for all monorepo tooling. | `dev/storage/README.md` | Side-by-Side Blueprint: Archive & Tooling Hub |
| three parallel approaches: | `showcase/PrimeNumberTheoremAnd/README.md` | Project Overview |
| timing breakdown | `toolchain/Dress/README.md` | Phase 1: Per-Declaration Capture (During Elaboration) |
| timing metrics | `dev/scripts/sbs/build/README.md` | Design Notes |
| timing trends | `CLAUDE.md` | Visualizations |
| tippy themes | `toolchain/dress-blueprint-action/README.md` | verso-code.js (490 lines) |
| toexpr | `CLAUDE.md` | Key Technical Details |
| token efficiency: | `CLAUDE.md` | Agent Orchestration |
| toolchain | `toolchain/dress-blueprint-action/README.md` | Related Repositories |
| tooling hub: | `CLAUDE.md` | Reference Documents |
| tooltip themes | `toolchain/dress-blueprint-action/README.md` | Status Dot Classes |
| total css: 3,196 lines. | `toolchain/dress-blueprint-action/README.md` | File Organization |
| total frontend assets: 3,805 lines | `toolchain/dress-blueprint-action/README.md` | Overview |
| total javascript: 609 lines. | `toolchain/dress-blueprint-action/README.md` | JavaScript |
| track | `dev/scripts/sbs/tests/compliance/README.md` | Workflow |
| traversem | `toolchain/Runway/README.md` | Module Architecture |
| trigger | `CLAUDE.md` | CI/CD Architecture |
| two-pass edge processing | `CLAUDE.md` | Key Technical Details |
| two-pass edge processing: | `toolchain/Dress/README.md` | Phase 3: Manifest Generation (CLI) |
| uncommitted changes | `dev/storage/README.md` | What It Checks |
| unpushed commits | `dev/storage/README.md` | What It Checks |
| update configuration: | `toolchain/SBS-Test/README.md` | Using as a Template |
| update imports: | `toolchain/SBS-Test/README.md` | Using as a Template |
| upstream dependencies: | `toolchain/Runway/README.md` | Role in the Toolchain |
| upstream: | `forks/subverso/README.md` | SubVerso (Side-by-Side Blueprint Fork) |
| user preferences: | `CLAUDE.md` | How This Document Works |
| uses `sbs.core.git_ops` | `dev/scripts/sbs/build/README.md` | Design Notes |
| utils | `scripts/utils.py` | Logging, path utilities, git helpers, lakefile parsing |
| validate | `dev/scripts/sbs/tests/compliance/README.md` | Workflow |
| validate: | `CLAUDE.md` | Standard Workflow for Visual Changes |
| validation checks | `showcase/General_Crystallographic_Restriction/README.md` | Documentation Toolchain |
| validation display | `toolchain/Runway/README.md` | Features |
| validation testing | `toolchain/SBS-Test/README.md` | Purpose |
| validationresult | `dev/scripts/sbs/tests/README.md` | validators/ |
| validator | `dev/scripts/sbs/tests/README.md` | validators/ |
| validators/ | `dev/scripts/sbs/tests/README.md` | pytest/ |
| validators: | `CLAUDE.md` | `/execute` |
| verified | `toolchain/Runway/README.md` | Verification Badges |
| verify: | `toolchain/SBS-Test/README.md` | Standard Visual Verification Workflow |
| verso | `CLAUDE.md` | Repository Map |
| verso integration | `toolchain/Runway/README.md` | Features |
| versopaper | `forks/verso/README.md` | Fork Purpose |
| viewbox centering issues: | `CLAUDE.md` | Graph Debugging Tips |
| visual regression baseline | `toolchain/SBS-Test/README.md` | Purpose |
| visual verification is mandatory for ui work. | `CLAUDE.md` | Visual Verification Requirement |
| weakpnt | `showcase/PrimeNumberTheoremAnd/README.md` | Project Overview |
| what it does: | `toolchain/Runway/README.md` | build (default) |
| what runway does not do: | `toolchain/Runway/README.md` | Role in the Toolchain |
| what to explore: | `showcase/General_Crystallographic_Restriction/README.md` | The Crystallographic Restriction Theorem |
| when claude asks questions: | `CLAUDE.md` | Communication Format |
| when to use sbs-test: | `toolchain/SBS-Test/README.md` | Role in Pipeline |
| why immediate capture? | `toolchain/Dress/README.md` | Phase 1: Per-Declaration Capture (During Elaboration) |
| why validation matters: | `toolchain/Dress/README.md` | Overview |
| wiener-ikehara tauberian theorem | `showcase/PrimeNumberTheoremAnd/README.md` | Project Overview |
| workflow size | `CLAUDE.md` | CI/CD Architecture |
| workflow: | `CLAUDE.md` | `/execute` |
| zebra striping | `toolchain/dress-blueprint-action/README.md` | CSS Variables |

---

## File Purpose Map

### Dress

| File | Purpose |
|------|---------|
| `.lake/build/dressed/` | Stats, validation, metadata for Runway |
| `.lake/build/dressed/library/` | Library index with `\inputleanmodule` macro |
| `.lake/build/dressed/{Module/Path}/` | `\input{}` directives for each declaration |
| `External` | Command-line interface (mhuisi/lean4-cli) |
| `decl.hovers.json` | Hover tooltip content for interactive display (JSON mapping IDs to content) |
| `decl.html` | Pre-rendered HTML with hover spans and rainbow brackets via `toHtmlRainbow` |
| `decl.json` | Metadata: `{"name": "...", "label": "...", "highlighting": {...}}` |
| `decl.tex` | LaTeX source for the declaration |
| `forks/LeanArchitect/` | Blueprint attribute (upstream) |
| `forks/subverso/` | Syntax highlighting (upstream) |
| `forks/verso/` | Document framework (upstream) |
| `manifest.entry` | Label-to-path mapping: `{"label": "...", "path": "..."}` |
| `showcase/General_Crystallographic_Restriction/` | Production example with paper (57 nodes) |
| `showcase/PrimeNumberTheoremAnd/` | Large-scale integration (591 nodes) |
| `toolchain/Runway/` | Site generator (downstream) |
| `toolchain/SBS-Test/` | Minimal test project (33 nodes, all 6 statuses) |
| `toolchain/dress-blueprint-action/` | GitHub Actions CI solution + CSS/JS assets |

### LeanArchitect

| File | Purpose |
|------|---------|
| `Architect/Attribute.lean` | `@[blueprint]` attribute syntax and elaboration with all options |
| `Architect/Basic.lean` | `Node`, `NodePart`, `NodeStatus` types with manual `ToExpr` instance |
| `Architect/CollectUsed.lean` | Dependency inference from expression trees |

### PrimeNumberTheoremAnd

| File | Purpose |
|------|---------|
| `showcase/General_Crystallographic_Restriction/` | Complete formalization with LaTeX paper generation (ar5iv style) |
| `showcase/PrimeNumberTheoremAnd/` | **Large-scale integration** demonstrating >100 node optimizations, where dependency graph validation... |
| `toolchain/SBS-Test/` | Minimal test project demonstrating all 6 status colors, XSS prevention, rainbow bracket depths (1-10... |

### Runway

| File | Purpose |
|------|---------|
| `Ast.lean` | AST types: `Document`, `Block`, `Inline`, `Preamble` |
| `Blueprint TOC/Index` | Dots in sidebar node list |
| `Blueprint Theorem Headers` | Dot in theorem header bar |
| `Dashboard Key Declarations` | Dots next to each key declaration |
| `Dashboard Project Notes` | Dots in all note sections |
| `Dependency Graph Modals` | Dot in modal header bar |
| `Lexer.lean` | Tokenization with O(n) string handling |
| `Paper Theorem Headers` | Dot + status text in verification badge |
| `Parser.lean` | Parser with Array-based string building, infinite loop protection |
| `ToHtml.lean` | LaTeX to HTML conversion with MathJax support |
| `ToLatex.lean` | AST back to LaTeX string (for PDF generation) |
| `Token.lean` | Token types (Command, Environment, Text, etc.) |
| `blueprint.css` | Main stylesheet, chapter layout, side-by-side displays |
| `common.css` | Base styles, status dots, rainbow brackets, theme toggle |
| `dep_graph.css` | Dependency graph styles, modals, pan/zoom viewport |
| `paper.css` | Paper page ar5iv-style layout |
| `plastex.js` | LaTeX proof toggle (expand/collapse) |
| `verso-code.js` | Hover initialization, pan/zoom, modal handling |

### SBS-Test

| File | Purpose |
|------|---------|
| `GenerateBlueprint.lean` | Verso SBSBlueprint genre document generator |
| `GeneratePaper.lean` | Verso VersoPaper genre document generator |
| `SBSTest.lean` | Library root - imports all modules for Lake build |
| `SBSTest/BracketDemo.lean` | Rainbow bracket stress testing: depths 1-10, all bracket types |
| `SBSTest/SecurityTest.lean` | XSS prevention: script tags, event handlers, javascript URLs |
| `SBSTest/StatusDemo.lean` | Primary test file: 14 nodes covering all 6 statuses, graph validation |
| `assetsDir` | Path to CSS/JS assets from dress-blueprint-action |
| `lakefile.toml` | Lake build configuration with Dress, Verso, mathlib dependencies |
| `projectName` | Must match the Lean library name in lakefile.toml |
| `runway.json` | Runway configuration: title, projectName, assets path |
| `runway/src/blueprint.tex` | LaTeX blueprint structure with `\inputleannode{}` and `\inputleanmodule{}` |
| `runway/src/paper.tex` | Paper with `\paperstatement{}` and `\paperfull{}` hooks |
| `runwayDir` | Directory containing `src/blueprint.tex` and `src/paper.tex` |

### dress-blueprint-action

| File | Purpose |
|------|---------|
| `assets/` | CSS and JavaScript files |
| `blueprint.css` | Blueprint pages: plasTeX base styles, sidebar, chapter layout, dashboard grid, side-by-side displays... |
| `chapter_*.html` | Chapter pages with side-by-side theorem/proof displays |
| `common.css` | Design system: CSS variables, status dots, Lean syntax highlighting, Tippy tooltips, modals, dark mo... |
| `dep_graph.css` | Dependency graph: pan/zoom viewport, toolbar, legend, SVG node styling |
| `dep_graph.html` | Interactive dependency graph with pan/zoom and node modals |
| `docs/` | DocGen4 documentation (if enabled) |
| `index.html` | Dashboard with stats, key theorems, messages, project notes |
| `manifest.json` | Node index and validation results |
| `paper.css` | Paper pages: ar5iv-style academic layout, verification badges, print styles |
| `paper.pdf` | PDF (if `paperTexPath` configured) |
| `paper_tex.html` | Paper (if `paperTexPath` configured) |
| `pdf_tex.html` | Embedded PDF viewer |
| `plastex.js` | Theme toggle, TOC toggle, LaTeX proof expand/collapse |
| `verso-code.js` | Token binding, Tippy.js tooltips, proof sync, pan/zoom, modal handling |

### markdowns

| File | Purpose |
|------|---------|
| `Auto-computed` | Verify all ancestors are proven |
| `manifest.json` | Find circular dependencies |

### root

| File | Purpose |
|------|---------|
| `.lake/build/dressed/{Module}/{label}/` | Artifacts |
| `.lake/build/runway/` | Site |
| `.lake/build/runway/manifest.json` | Manifest |
| `ARCHITECTURE.md` | Detailed technical reference with data flow and performance analysis |
| `Root (this file)` | Claude Code development guide |
| `blueprint.css` | Blueprint pages: plasTeX base, sidebar, chapter layout, side-by-side, zebra striping |
| `capture.json` | Metadata: timestamp, commit, viewport, page status |
| `common.css` | Design system: CSS variables, theme toggle, status dots, Lean syntax, rainbow brackets |
| `dep_graph.css` | Dependency graph: pan/zoom viewport, toolbar, legend, SVG nodes |
| `dep_graph_ground_truth.txt` | Working dependency graph page with modals |
| `dev/markdowns/ARCHITECTURE.md` | Public architecture documentation |
| `dev/markdowns/GOALS.md` | Project vision and design goals |
| `dev/markdowns/README.md` | Public-facing project overview |
| `dev/storage/{project}/archive/{timestamp}/` | Timestamped archives |
| `dev/storage/{project}/latest/` | Current capture (overwritten each run) |
| `motivation1.txt`, `motivation2.txt`, `motivation3.txt` | Original motivation notes (Tao incident, Zulip discussions) |
| `paper.css` | Paper page: ar5iv-style academic layout, verification badges |
| `plastex.js` | Theme toggle, TOC toggle, LaTeX proof expand/collapse |
| `side_by_side_blueprint_ground_truth.txt` | Working Python leanblueprint HTML |
| `verso-code.js` | Token binding, Tippy.js tooltips, proof sync, pan/zoom, modal handling |

### subverso

| File | Purpose |
|------|---------|
| `InfoTable.ofInfoTree` | Skips contextless nodes instead of panicking |
| `SplitCtx.close` | Returns safe fallback on empty context stack |
| `emitToken` | Handles synthetic source info from macros and term-mode proofs |
| `highlightLevel` | Emits unknown token on unrecognized syntax |

### verso

| File | Purpose |
|------|---------|
| `src/verso-paper/VersoPaper/Blocks.lean` | Paper directive expanders |
| `src/verso-paper/VersoPaper/Html.lean` | HTML rendering for paper blocks |
| `src/verso-sbs/SBSBlueprint/Genre.lean` | Genre type definition and BlockExt/InlineExt |
| `src/verso-sbs/SBSBlueprint/Hooks.lean` | Directive expanders (leanNode, paperStatement, etc.) |
| `src/verso-sbs/SBSBlueprint/Manifest.lean` | Manifest.json loading and node lookup |
| `src/verso-sbs/SBSBlueprint/Render.lean` | HTML rendering for blueprint blocks |
| `src/verso/Verso/Code/Highlighted.lean` | Rainbow bracket implementation |

---

## How-To Patterns

<details>
<summary><strong>Running Quality Tests</strong></summary>

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts

</details>

<details>
<summary><strong>Running Checks</strong></summary>

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts

</details>

<details>
<summary><strong>Debugging Tips</strong></summary>

**Side-by-side display issues:**
1. Check `decl.html` exists in `.lake/build/dressed/{Module}/{label}/`
2. Verify `decl.json` has correct status
3. Check placeholder replacement in `Theme.lean`

**Dashboard stat discrepancies:**
1. Stats come from `manifest.json` (precomputed by Dress)
2. Check `manifest.json` in `.lake/build/dressed/`
3. Rebuild with `BLUEPRINT_DRESS=1` if artifacts stale

**Sidebar not showing:**
1. `isBlueprintPage` returns `false` for dashboard (intentional)
2. Check `currentSlug` matches a chapter slug
3. Verify `chapters` array is populated

</details>

<details>
<summary><strong>Creating Rubrics</strong></summary>

Rubrics are typically created during `/execute --grab-bag` sessions:

1. **Brainstorm** improvements with user
2. **Align** on measurable metrics
3. **Create** rubric with thresholds and weights
4. **Execute** tasks with rubric-based validation
5. **Finalize** with evaluation summary

See `.claude/skills/execute/SKILL.md` for the full grab-bag workflow.

---

</details>

<details>
<summary><strong>Creating Custom Validators</strong></summary>

See `scripts/sbs/tests/validators/base.py` for the `BaseValidator` class and `@register_validator` decorator.

---

</details>

<details>
<summary><strong>Running Tests</strong></summary>

```bash

</details>

<details>
<summary><strong>Running Tests</strong></summary>

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python -m pytest sbs/tests/pytest -v
```

</details>

---

## Gotchas & Anti-Patterns

- Verso LaTeX Export: Verso's LaTeX export functionality is not yet implemented. The `pdf_verso` page type is disabled. Paper/PDF generation uses TeX sources directly via `paper_tex` and `pdf_tex`.
- Dashboard Layout: The dashboard displays a single-column layout without the chapter panel sidebar. This is intentional - controlled by `isBlueprintPage` in `Theme.lean` returning `false` when `currentSlug == none`.
- Dashboard Layout: The dashboard displays a single-column layout without the chapter panel sidebar. This is intentional - the dashboard is not a blueprint chapter page.

---

## Cross-Repo Impact Map

| Change In | Affects | Impact |
|-----------|---------|--------|
| SubVerso | LeanArchitect | InfoTable structure changes affect attribute processing |
| SubVerso | Verso | Highlighting token types affect genre rendering |
| LeanArchitect | Dress | Node/NodeStatus types must stay in sync |
| LeanArchitect | Runway | Node types used in manifest parsing |
| Dress | Runway | Manifest JSON schema must match |
| Dress | Runway | Graph layout changes affect rendering |
| Verso | Dress | Rainbow bracket rendering must coordinate |
| dress-blueprint-action | Runway | CSS classes must match generated HTML |
| dress-blueprint-action | Dress | Status colors must match Svg.lean hex values |
