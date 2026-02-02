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
| 6-status color model: | `CLAUDE.md` | Quick Reference |
| 6-status tracking | `showcase/General_Crystallographic_Restriction/README.md` | Documentation Toolchain |
| >100 node optimizations | `toolchain/Dress/README.md` | Performance Characteristics |
| [side-by-side blueprint](https://github.com/e-vergo/side-by-side-blueprint) | `showcase/General_Crystallographic_Restriction/README.md` | Documentation Toolchain |
| [storage & tooling hub](../../dev/storage/readme.md) | `toolchain/SBS-Test/README.md` | Tooling & Archive System |
| `@[blueprint]` attributes | `toolchain/dress-blueprint-action/README.md` | Project Requirements |
| `global_state` | `dev/storage/README.md` | State Machine Fields |
| `state_transition` | `dev/storage/README.md` | State Machine Fields |
| a proof that typechecks is not necessarily the proof you intended | `toolchain/dress-blueprint-action/README.md` | Motivation |
| absolute imports | `dev/scripts/README.md` | Design Principles |
| agent parallelism: | `CLAUDE.md` | Orchestration Model |
| agentic and project-specific development tools | `dev/markdowns/living/README.md` | 2. Meta-Tooling Development |
| agents | `dev/markdowns/living/README.md` | 2. Meta-Tooling Development |
| alex kontorovich | `showcase/PrimeNumberTheoremAnd/README.md` | Original PNT+ Project |
| always use `python build.py` for builds | `CLAUDE.md` | Standards |
| archive inspection | `forks/sbs-lsp-mcp/README.md` | Overview |
| archive system | `dev/markdowns/living/README.md` | 2. Meta-Tooling Development |
| archiveentry | `dev/storage/README.md` | Archive Entries |
| at least | `toolchain/SBS-Test/README.md` | Motivation: The Tao Incident |
| at most | `toolchain/SBS-Test/README.md` | Motivation: The Tao Incident |
| attribution | `toolchain/Runway/README.md` | Runway |
| automatic dependency inference | `showcase/General_Crystallographic_Restriction/README.md` | Documentation Toolchain |
| backward direction: | `showcase/General_Crystallographic_Restriction/README.md` | Proof Strategy |
| base.py | `dev/scripts/sbs/tests/README.md` | validators/ |
| basevalidator | `dev/storage/README.md` | Creating Custom Validators |
| being tracked by the tools they're building | `dev/markdowns/living/README.md` | Why This Matters for Agents |
| block | `toolchain/Runway/README.md` | LaTeX Parsing Modules |
| block directives: | `forks/verso/README.md` | 1. SBSBlueprint Genre (`src/verso-sbs/`) |
| blueprint | `toolchain/Runway/README.md` | Module Architecture |
| blueprint directory | `toolchain/dress-blueprint-action/README.md` | Project Requirements |
| blueprint-specific: | `toolchain/Runway/README.md` | Supported LaTeX Commands |
| blueprintsite | `toolchain/Runway/README.md` | Module Architecture |
| brackets | `forks/verso/README.md` | 3. Rainbow Bracket Highlighting (`src/verso/Verso/Code/Highlighted.lean`) |
| build & run | `showcase/PrimeNumberTheoremAnd/README.md` | Quick Links |
| build and verify: | `toolchain/SBS-Test/README.md` | Using as a Template |
| build phases are standalone functions | `dev/scripts/sbs/build/README.md` | Design Notes |
| build tools | `forks/sbs-lsp-mcp/README.md` | Overview |
| build: | `CLAUDE.md` | Standard Workflow |
| building the product | `dev/markdowns/living/README.md` | Why This Matters for Agents |
| building the tools that build the product | `dev/markdowns/living/README.md` | Why This Matters for Agents |
| buildorchestrator | `dev/scripts/sbs/build/README.md` | Design Notes |
| capture | `dev/scripts/sbs/tests/compliance/README.md` | Workflow |
| capture: | `CLAUDE.md` | Standard Workflow |
| centralized complexity | `toolchain/dress-blueprint-action/README.md` | Design Philosophy |
| changed files list | `dev/storage/README.md` | What It Checks |
| chapter pages | `toolchain/SBS-Test/README.md` | What to Inspect |
| chapterinfo | `toolchain/Runway/README.md` | Module Architecture |
| check results | `SBS-Test/checkResults.connected` | false (due to disconnected cycle) |
| cli commands | `dev/storage/README.md` | What test-catalog Shows |
| clone and rename: | `toolchain/SBS-Test/README.md` | Using as a Template |
| cmd.py | `dev/scripts/sbs/tests/README.md` | rubrics/ |
| color source of truth | `toolchain/dress-blueprint-action/README.md` | 6-Status Color Model |
| color source of truth: | `CLAUDE.md` | Quick Reference |
| complete feature coverage | `toolchain/SBS-Test/README.md` | Purpose |
| complex analysis approach | `showcase/PrimeNumberTheoremAnd/README.md` | Project Overview |
| concept index | `dev/storage/README.md` | What the Oracle Knows |
| config | `toolchain/Runway/README.md` | Module Architecture |
| configuration loading | `toolchain/Runway/README.md` | Processing Steps |
| conftest.py | `dev/scripts/sbs/tests/README.md` | pytest/ |
| connectivity validation | `showcase/PrimeNumberTheoremAnd/README.md` | What This Fork Demonstrates |
| containment search | `forks/subverso/README.md` | Identifier Resolution |
| context generation | `forks/sbs-lsp-mcp/README.md` | Overview |
| core components: | `showcase/General_Crystallographic_Restriction/README.md` | Documentation Toolchain |
| core palette | `toolchain/dress-blueprint-action/README.md` | CSS Variables |
| core responsibilities: | `toolchain/Dress/README.md` | Overview |
| cross-repo impact | `dev/storage/README.md` | What the Oracle Knows |
| css (embedded in `highlightingstyle`): | `forks/verso/README.md` | 3. Rainbow Bracket Highlighting (`src/verso/Verso/Code/Highlighted.lean`) |
| current score: | `dev/storage/README.md` | Quality Scoring |
| dashboard | `toolchain/SBS-Test/README.md` | What to Inspect |
| dashboard homepage | `toolchain/Runway/README.md` | Features |
| dashboard stat discrepancies: | `toolchain/Runway/README.md` | Debugging Tips |
| debug | `forks/sbs-lsp-mcp/README.md` | Environment Variables |
| declarative rules | `dev/storage/README.md` | Auto-Tagging |
| dep graph node click * | `storage/dep_graph_node_click_*.png` | Node modal views |
| dep graph zoom * | `storage/dep_graph_zoom_*.png` | Zoom in/out/fit states |
| dependency graph | `toolchain/SBS-Test/README.md` | What to Inspect |
| depgraph.lean | `toolchain/Runway/README.md` | Key Module Details |
| design/ | `dev/scripts/sbs/tests/README.md` | validators/ |
| detailed references | `CLAUDE.md` | Reference Documents |
| deterministic tests (50% weight): | `CLAUDE.md` | Quality Validation Framework |
| dev/storage/compliance ledger | `SBS-Test/dev/storage/compliance_ledger.json` | Pass/fail status per page |
| dev/storage/compliance status | `SBS-Test/dev/storage/COMPLIANCE_STATUS.md` | Human-readable status report |
| dev/storage/unified ledger | `SBS-Test/dev/storage/unified_ledger.json` | Build metrics and timing |
| do not | `forks/sbs-lsp-mcp/.pytest_cache/README.md` | pytest cache directory # |
| document | `toolchain/Runway/README.md` | LaTeX Parsing Modules |
| document structure: | `toolchain/Runway/README.md` | Supported LaTeX Commands |
| domain context: | `CLAUDE.md` | How This Document Works |
| dress | `CLAUDE.md` | Repository Map |
| dress artifacts | `toolchain/SBS-Test/README.md` | Testing Points |
| dress dependency | `toolchain/dress-blueprint-action/README.md` | Project Requirements |
| dress-blueprint-action | `CLAUDE.md` | Repository Map |
| during ci | `toolchain/dress-blueprint-action/README.md` | Asset Integration |
| edit agents: | `CLAUDE.md` | Orchestration Model |
| environment lookup with suffix matching | `forks/subverso/README.md` | Identifier Resolution |
| epoch | `dev/storage/README.md` | Epoch Semantics |
| epoch summary structure: | `dev/storage/README.md` | Epoch Semantics |
| evergreen | `dev/storage/README.md` | Test Organization System |
| expected build time: | `toolchain/SBS-Test/README.md` | Local Development |
| expected layout times: | `toolchain/Dress/README.md` | Performance Characteristics |
| fast iteration | `toolchain/SBS-Test/README.md` | Purpose |
| feature set: | `showcase/General_Crystallographic_Restriction/README.md` | Documentation Toolchain |
| file purpose map | `dev/storage/README.md` | What the Oracle Knows |
| for full upstream documentation, see [hanwenzhu/leanarchitect](https://github.com/hanwenzhu/leanarchitect). | `forks/LeanArchitect/README.md` | LeanArchitect |
| for local development | `toolchain/dress-blueprint-action/README.md` | Asset Integration |
| fork of [hanwenzhu/leanarchitect](https://github.com/hanwenzhu/leanarchitect) | `forks/LeanArchitect/README.md` | LeanArchitect |
| forward direction: | `showcase/General_Crystallographic_Restriction/README.md` | Proof Strategy |
| fully static | `toolchain/Runway/README.md` | Sidebar Navigation |
| general crystallographic restriction | `showcase/PrimeNumberTheoremAnd/README.md` | Related Projects |
| git ops | `scripts/git_ops.py` | Git status, diff, and sync operations |
| github action | `toolchain/dress-blueprint-action/README.md` | Overview |
| gotchas | `dev/storage/README.md` | What the Oracle Knows |
| graceful degradation | `toolchain/Runway/README.md` | Design Principles |
| graph | `toolchain/Runway/README.md` | Module Architecture |
| graph layout | `toolchain/SBS-Test/README.md` | Testing Points |
| graph structure: | `toolchain/SBS-Test/README.md` | StatusDemo.lean (14 nodes) |
| guiding principle: | `CLAUDE.md` | User Preferences |
| hadamard factorization | `showcase/PrimeNumberTheoremAnd/README.md` | Project Overview |
| heuristic tests (50% weight): | `CLAUDE.md` | Quality Validation Framework |
| highlight contradictions immediately. | `CLAUDE.md` | Meta-Cognitive Expectations |
| highlighting accounts for 93-99% of total build time | `forks/subverso/README.md` | Fork Purpose |
| highlightstate | `toolchain/Dress/README.md` | SubVerso Integration |
| how it works: | `toolchain/Runway/README.md` | Module Reference Support |
| how-to patterns | `dev/storage/README.md` | What the Oracle Knows |
| html generation | `toolchain/Runway/README.md` | Processing Steps |
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
| investigation tools | `forks/sbs-lsp-mcp/README.md` | Overview |
| javascript | `toolchain/dress-blueprint-action/README.md` | Overview |
| key results: | `showcase/PrimeNumberTheoremAnd/README.md` | Project Overview |
| key theorems | `toolchain/Runway/README.md` | Dashboard (index.html) |
| lakefile | `SBS-Test/lakefile.toml` | Change `name = "SBSTest"` to your project name |
| large-scale integration | `showcase/PrimeNumberTheoremAnd/README.md` | Related Projects |
| large-scale integration example | `showcase/PrimeNumberTheoremAnd/README.md` | Side-by-Side Blueprint Integration |
| latex parsing | `toolchain/Runway/README.md` | Processing Steps |
| lean: | `forks/verso/README.md` | Dependencies |
| leanarchitect | `CLAUDE.md` | Repository Map |
| leanblueprint | `showcase/General_Crystallographic_Restriction/README.md` | Attribution |
| ledger | `scripts/ledger.py` | Build metrics and unified ledger data structures |
| live demo: | `showcase/General_Crystallographic_Restriction/README.md` | The Crystallographic Restriction Theorem |
| live site | `showcase/PrimeNumberTheoremAnd/README.md` | Quick Links |
| live site: | `toolchain/SBS-Test/README.md` | SBS-Test |
| location: | `CLAUDE.md` | `/task` |
| loop | `dev/scripts/sbs/tests/compliance/README.md` | Workflow |
| main.lean | `toolchain/Runway/README.md` | Module Architecture |
| make changes | `CLAUDE.md` | Standard Workflow |
| manifest | `toolchain/SBS-Test/README.md` | What to Inspect |
| manifest generation | `toolchain/SBS-Test/README.md` | Testing Points |
| manifest loading | `toolchain/Runway/README.md` | Processing Steps |
| manifest-driven soundness | `toolchain/Runway/README.md` | Features |
| manual triggers only | `toolchain/dress-blueprint-action/README.md` | Design Philosophy |
| math: | `toolchain/Runway/README.md` | Supported LaTeX Commands |
| mathjax compatibility | `toolchain/Runway/README.md` | Design Principles |
| mcp tool usage (via sbs-lsp-mcp): | `CLAUDE.md` | Quick Reference |
| mcp tools | `dev/markdowns/living/README.md` | 2. Meta-Tooling Development |
| mcp tools (11) | `dev/storage/README.md` | What test-catalog Shows |
| mediumpnt | `showcase/PrimeNumberTheoremAnd/README.md` | Project Overview |
| messages | `toolchain/Runway/README.md` | Dashboard (index.html) |
| metricscore | `dev/storage/README.md` | Implementation |
| minimal dependencies | `dev/scripts/sbs/core/README.md` | Design Principles |
| module reference support | `showcase/PrimeNumberTheoremAnd/README.md` | What This Fork Demonstrates |
| module references | `toolchain/Runway/README.md` | Features |
| motivation: | `toolchain/Dress/README.md` | Connectivity (`findComponents`) |
| multi-page chapter navigation | `toolchain/Runway/README.md` | Features |
| myproject.chapter.module | `toolchain/Runway/README.md` | Module Reference Support |
| naming: | `dev/storage/README.md` | Archive System |
| never delete or replace a plan without explicit user direction. | `CLAUDE.md` | Planning Discipline |
| no circular dependencies | `dev/scripts/README.md` | Design Principles |
| no command handlers | `dev/scripts/sbs/core/README.md` | Design Principles |
| no duplicate code | `dev/scripts/sbs/build/README.md` | Design Notes |
| no github actions mathlib cache | `toolchain/dress-blueprint-action/README.md` | Design Philosophy |
| node assignment | `toolchain/Runway/README.md` | Processing Steps |
| nodeinfo | `toolchain/Runway/README.md` | Module Architecture |
| nodepart | `forks/LeanArchitect/README.md` | Key Files |
| nodestatus | `forks/LeanArchitect/README.md` | Key Files |
| nodetemplate | `toolchain/Runway/README.md` | Key Module Details |
| non-invasive integration | `showcase/PrimeNumberTheoremAnd/README.md` | What This Fork Demonstrates |
| not started | `toolchain/Runway/README.md` | Verification Badges |
| note: | `forks/sbs-lsp-mcp/README.md` | Zulip Tools |
| o(1) exact position lookup | `forks/subverso/README.md` | Identifier Resolution |
| o(1) name-based search | `forks/subverso/README.md` | Identifier Resolution |
| o(n) string concatenation | `toolchain/Runway/README.md` | Design Principles |
| one at a time | `toolchain/Dress/README.md` | 1. Acyclic Transformation |
| oracle querying | `forks/sbs-lsp-mcp/README.md` | Overview |
| orchestration structure: | `CLAUDE.md` | How This Document Works |
| orchestrator | `CLAUDE.md` | Orchestration Model |
| original repositories: | `showcase/PrimeNumberTheoremAnd/README.md` | Original PNT+ Project |
| outputs generated: | `toolchain/Runway/README.md` | Role in the Toolchain |
| pan/zoom implementation | `toolchain/dress-blueprint-action/README.md` | verso-code.js (490 lines) |
| paper | `Runway/paper.pdf` | Compiled PDF (if LaTeX compiler available) |
| paper (html and pdf) | `showcase/General_Crystallographic_Restriction/README.md` | The Crystallographic Restriction Theorem |
| paper generation | `toolchain/Runway/README.md` | Features |
| paper tex | `Runway/paper_tex.html` | MathJax-rendered paper with verification badges |
| paper-specific: | `toolchain/Runway/README.md` | Supported LaTeX Commands |
| paper.lean | `toolchain/Runway/README.md` | Key Module Details |
| papermetadata | `toolchain/Runway/README.md` | Module Architecture |
| papernodeinfo | `toolchain/Runway/README.md` | Key Module Details |
| papernodeinfoext | `toolchain/Runway/README.md` | Key Module Details |
| parent project: | `forks/subverso/README.md` | SubVerso (Side-by-Side Blueprint Fork) |
| part of the [side-by-side blueprint](https://github.com/e-vergo/side-by-side-blueprint) monorepo. | `toolchain/Dress/README.md` | Overview |
| pdf compilation | `toolchain/Runway/README.md` | Features |
| pdf tex | `Runway/pdf_tex.html` | PDF viewer page with embedded PDF |
| per-session data: | `dev/storage/README.md` | Rich Data Extraction |
| per-snapshot aggregates: | `dev/storage/README.md` | Rich Data Extraction |
| performance at scale | `showcase/PrimeNumberTheoremAnd/README.md` | What This Fork Demonstrates |
| placeholder expansion | `toolchain/Runway/README.md` | Processing Steps |
| placeholder system | `toolchain/Runway/README.md` | Key Development Patterns |
| practice introspection. | `CLAUDE.md` | Meta-Cognitive Expectations |
| preamble | `toolchain/Runway/README.md` | LaTeX Parsing Modules |
| primenumbertheoremand | `showcase/PrimeNumberTheoremAnd/README.md` | Related Projects |
| priority order | `toolchain/SBS-Test/README.md` | Status Color Model |
| project leads: | `showcase/PrimeNumberTheoremAnd/README.md` | Original PNT+ Project |
| project notes | `toolchain/Runway/README.md` | Dashboard (index.html) |
| proof dependencies | `forks/LeanArchitect/README.md` | Dependency Inference |
| prototype status | `toolchain/Runway/README.md` | Runway |
| pytest tests | `dev/storage/README.md` | What test-catalog Shows |
| python hooks | `dev/storage/README.md` | Auto-Tagging |
| qualityscoreledger | `dev/storage/README.md` | Implementation |
| rainbow bracket highlighting | `forks/verso/README.md` | Fork Purpose |
| rainbow brackets | `showcase/General_Crystallographic_Restriction/README.md` | Documentation Toolchain |
| read-only agents: | `CLAUDE.md` | Orchestration Model |
| rebuild and re-capture | `CLAUDE.md` | Standard Workflow |
| rebuild: | `toolchain/SBS-Test/README.md` | Standard Visual Verification Workflow |
| refer to: | `toolchain/SBS-Test/README.md` | Archive & Metrics |
| registry.py | `dev/scripts/sbs/tests/README.md` | validators/ |
| render.lean | `toolchain/Runway/README.md` | Key Module Details |
| renderm | `toolchain/Runway/README.md` | Module Architecture |
| renderm monad | `toolchain/Runway/README.md` | Key Development Patterns |
| replace demo content: | `toolchain/SBS-Test/README.md` | Using as a Template |
| required: | `CLAUDE.md` | Direct Build Script Usage |
| requirements: | `toolchain/Runway/README.md` | Module Reference Support |
| rubric | `dev/scripts/sbs/tests/README.md` | rubrics/ |
| rubric.py | `dev/scripts/sbs/tests/README.md` | rubrics/ |
| rubriccriterion | `dev/scripts/sbs/tests/README.md` | rubrics/ |
| rubricevaluation | `dev/scripts/sbs/tests/README.md` | rubrics/ |
| rule of thumb: | `CLAUDE.md` | Orchestration Model |
| run from: | `dev/storage/README.md` | Quick Reference |
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
| sbs-lsp-mcp | `CLAUDE.md` | Repository Map |
| sbs-test | `CLAUDE.md` | Repository Map |
| sbsblueprint | `forks/verso/README.md` | Fork Purpose |
| screenshot capture is the first reflex for any visual/css/layout issue. | `CLAUDE.md` | Visual Testing |
| screenshots: | `toolchain/SBS-Test/README.md` | Archive & Metrics |
| sectioninfo | `toolchain/Runway/README.md` | Module Architecture |
| security testing | `toolchain/SBS-Test/README.md` | Purpose |
| see: | `toolchain/SBS-Test/README.md` | Run compliance validation |
| side-by-side blueprint | `showcase/General_Crystallographic_Restriction/README.md` | Attribution |
| side-by-side blueprint tool | `dev/markdowns/living/README.md` | 1. Tool Development |
| side-by-side display | `toolchain/Runway/README.md` | Features |
| side-by-side display issues: | `toolchain/Runway/README.md` | Debugging Tips |
| sidebar not showing: | `toolchain/Runway/README.md` | Debugging Tips |
| simplified per-project workflows | `toolchain/dress-blueprint-action/README.md` | Design Philosophy |
| single command, single purpose | `dev/scripts/README.md` | Design Principles |
| site building | `toolchain/Runway/README.md` | Processing Steps |
| site output | `toolchain/SBS-Test/README.md` | Testing Points |
| sitebuilder | `toolchain/Runway/README.md` | Module Architecture |
| skill substates: | `dev/storage/README.md` | State Machine Fields |
| skills | `dev/markdowns/living/README.md` | 2. Meta-Tooling Development |
| soundness guarantee: | `toolchain/Runway/README.md` | manifest.json Schema |
| statement dependencies | `forks/LeanArchitect/README.md` | Dependency Inference |
| stats | `toolchain/Runway/README.md` | Dashboard (index.html) |
| status computation | `toolchain/SBS-Test/README.md` | Testing Points |
| status priority | `toolchain/Dress/README.md` | 6-Status Color Model |
| string | `forks/LeanArchitect/README.md` | 8 Metadata Options |
| subagent spawning: | `CLAUDE.md` | Agent Orchestration |
| subverso | `CLAUDE.md` | Repository Map |
| subverso: | `forks/verso/README.md` | Dependencies |
| template | `toolchain/Runway/README.md` | Key Module Details |
| template for new projects | `toolchain/SBS-Test/README.md` | Purpose |
| temporary | `dev/storage/README.md` | Test Organization System |
| terence tao | `showcase/PrimeNumberTheoremAnd/README.md` | Original PNT+ Project |
| terence tao, january 2026 | `toolchain/dress-blueprint-action/README.md` | Motivation |
| test_cli.py | `dev/scripts/sbs/tests/README.md` | pytest/ |
| test_ledger_health.py | `dev/scripts/sbs/tests/README.md` | pytest/ |
| testing tools | `forks/sbs-lsp-mcp/README.md` | Overview |
| text formatting: | `toolchain/Runway/README.md` | Supported LaTeX Commands |
| the core insight | `toolchain/dress-blueprint-action/README.md` | Motivation |
| theme | `toolchain/Runway/README.md` | Module Architecture |
| theme templates | `toolchain/Runway/README.md` | Key Development Patterns |
| theme toggle | `toolchain/Runway/README.md` | Features |
| theme.lean | `toolchain/Runway/README.md` | Key Module Details |
| theorem (crystallographic restriction). | `showcase/General_Crystallographic_Restriction/README.md` | Main Result |
| theorems: | `toolchain/Runway/README.md` | Supported LaTeX Commands |
| these preferences guide all decision-making, planning, and actions. follow them unless the user explicitly directs otherwise. | `CLAUDE.md` | User Preferences |
| this is a fork of the original [pnt+](https://github.com/alexkontorovich/primenumbertheoremand) project with [side-by-side blueprint](https://github.com/e-vergo/side-by-side-blueprint) integration. | `showcase/PrimeNumberTheoremAnd/README.md` |  |
| this is lean software development, not proof writing. | `CLAUDE.md` | Project Context |
| this is the central reference for all monorepo tooling. | `dev/storage/README.md` | Side-by-Side Blueprint: Archive & Tooling Hub |
| this monorepo is the primary location for development of the side-by-side blueprint project. | `dev/markdowns/living/README.md` | Side-by-Side Blueprint Monorepo |
| three parallel approaches: | `showcase/PrimeNumberTheoremAnd/README.md` | Project Overview |
| timing breakdown | `toolchain/Dress/README.md` | Phase 1: Per-Declaration Capture (During Elaboration) |
| timing metrics | `dev/scripts/sbs/build/README.md` | Design Notes |
| tippy themes | `toolchain/dress-blueprint-action/README.md` | verso-code.js (490 lines) |
| toexpr | `forks/LeanArchitect/README.md` | Key Files |
| token efficiency: | `CLAUDE.md` | Agent Orchestration |
| toolchain | `toolchain/dress-blueprint-action/README.md` | Related Repositories |
| tooltip themes | `toolchain/dress-blueprint-action/README.md` | Status Dot Classes |
| total css: 3,196 lines. | `toolchain/dress-blueprint-action/README.md` | File Organization |
| total frontend assets: 3,805 lines | `toolchain/dress-blueprint-action/README.md` | Overview |
| total javascript: 609 lines. | `toolchain/dress-blueprint-action/README.md` | JavaScript |
| track | `dev/scripts/sbs/tests/compliance/README.md` | Workflow |
| traversem | `toolchain/Runway/README.md` | Module Architecture |
| two-pass edge processing: | `toolchain/Dress/README.md` | Phase 3: Manifest Generation (CLI) |
| uncommitted changes | `dev/storage/README.md` | What It Checks |
| unpushed commits | `dev/storage/README.md` | What It Checks |
| update configuration: | `toolchain/SBS-Test/README.md` | Using as a Template |
| update imports: | `toolchain/SBS-Test/README.md` | Using as a Template |
| upstream dependencies: | `toolchain/Runway/README.md` | Role in the Toolchain |
| upstream: | `forks/subverso/README.md` | SubVerso (Side-by-Side Blueprint Fork) |
| usage: | `CLAUDE.md` | `/log` |
| user preferences: | `CLAUDE.md` | How This Document Works |
| uses `sbs.core.git_ops` | `dev/scripts/sbs/build/README.md` | Design Notes |
| utils | `scripts/utils.py` | Logging, path utilities, git helpers, lakefile parsing |
| validate | `dev/scripts/sbs/tests/compliance/README.md` | Workflow |
| validate: | `CLAUDE.md` | Standard Workflow |
| validation checks | `showcase/General_Crystallographic_Restriction/README.md` | Documentation Toolchain |
| validation display | `toolchain/Runway/README.md` | Features |
| validation testing | `toolchain/SBS-Test/README.md` | Purpose |
| validationresult | `dev/scripts/sbs/tests/README.md` | validators/ |
| validator | `dev/scripts/sbs/tests/README.md` | validators/ |
| validators | `dev/markdowns/living/README.md` | 2. Meta-Tooling Development |
| validators/ | `dev/scripts/sbs/tests/README.md` | pytest/ |
| verified | `toolchain/Runway/README.md` | Verification Badges |
| verify: | `toolchain/SBS-Test/README.md` | Standard Visual Verification Workflow |
| verso | `CLAUDE.md` | Repository Map |
| verso integration | `toolchain/Runway/README.md` | Features |
| versopaper | `forks/verso/README.md` | Fork Purpose |
| visual regression baseline | `toolchain/SBS-Test/README.md` | Purpose |
| visual verification is mandatory for ui work. | `CLAUDE.md` | Visual Verification Requirement |
| weakpnt | `showcase/PrimeNumberTheoremAnd/README.md` | Project Overview |
| what gets backed up: | `dev/storage/README.md` | iCloud Sync |
| what it does: | `toolchain/Runway/README.md` | build (default) |
| what runway does not do: | `toolchain/Runway/README.md` | Role in the Toolchain |
| what to explore: | `showcase/General_Crystallographic_Restriction/README.md` | The Crystallographic Restriction Theorem |
| when claude asks questions: | `CLAUDE.md` | Communication Format |
| when to use sbs-test: | `toolchain/SBS-Test/README.md` | Role in Pipeline |
| why immediate capture? | `toolchain/Dress/README.md` | Phase 1: Per-Declaration Capture (During Elaboration) |
| why validation matters: | `toolchain/Dress/README.md` | Overview |
| wiener-ikehara tauberian theorem | `showcase/PrimeNumberTheoremAnd/README.md` | Project Overview |
| workflow: | `CLAUDE.md` | `/task` |
| zebra striping | `toolchain/dress-blueprint-action/README.md` | CSS Variables |
| zulip browsing | `forks/sbs-lsp-mcp/README.md` | Overview |

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

### root

| File | Purpose |
|------|---------|
| `Tooling hub` | CLI commands, validation, workflows |
| `dev/markdowns/living/README.md` | Agent-facing monorepo overview |
| `dev/markdowns/permanent/` | Script-agent boundary, archive roles |
| `dev/markdowns/permanent/ARCHITECTURE.md` | Build pipeline, components, document taxonomy |
| `dev/markdowns/permanent/GOALS.md` | Project vision and design goals |
| `dev/markdowns/permanent/GRAND_VISION.md` | SBS in the age of AI-assisted mathematics |
| `dev/storage/TEST_CATALOG.md` | Auto-generated testable components catalog |

### storage

| File | Purpose |
|------|---------|
| `ledger.py` | `QualityScoreLedger`, `MetricScore`, persistence |
| `reset.py` | Repo-change detection, metric invalidation |

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

- Verso LaTeX Export: Not yet implemented. The `pdf_verso` page type is disabled. Paper/PDF generation uses TeX sources directly via `paper_tex` and `pdf_tex`.
- Dashboard Layout: Displays single-column layout without chapter panel sidebar. Intentional - controlled by `isBlueprintPage` returning `false` for dashboard.
- Verso LaTeX Export: Verso's LaTeX export functionality is not yet implemented. The `pdf_verso` page type is disabled. Paper/PDF generation uses TeX sources directly via `paper_tex` and `pdf_tex`.
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
