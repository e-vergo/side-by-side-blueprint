# Side-by-Side Blueprint: Project Goals

![Lean](https://img.shields.io/badge/Lean-v4.27.0-blue)
![License](https://img.shields.io/badge/License-Apache%202.0-green)

> **Prototype Status**: This is alpha software with known bugs, slow workflows, and incomplete features. Not yet production-ready.

## Table of Contents

- [Vision](#vision)
- [The Problem This Solves](#the-problem-this-solves)
- [What We're Building](#what-were-building)
- [Target Audience](#target-audience)
- [Relationship to Existing Tools](#relationship-to-existing-tools)
- [Technical Design](#technical-design)
- [Current Status](#current-status)
- [Quality Targets](#quality-targets)

## Vision

Create a pure Lean toolchain that displays formalized mathematical proofs alongside their LaTeX statements, reducing the burden on mathematicians and formalization researchers to verify that formal proofs actually prove what they claim.

**Key principles:**
- Couple document generation to build process for soundness guarantees
- Tighter coupling of formal to informal mathematics
- Expand what it means to "have a project verified"
- Platform for type-checked proof properties
- Gold standard auto-generated documentation (like docgen4, Lean reference manual)

**Technical inspiration:** [Lean Reference Manual](https://github.com/leanprover/reference-manual) - automated building, Verso, SubVerso, 100% Lean

**Feature inspiration:** [Crystallographic Restriction Blueprint](https://e-vergo.github.io/General_Crystallographic_Restriction/blueprint/) - side-by-side display, chapter structure, dependency graphs

## The Problem This Solves

**Terence Tao, January 2026 (PNT+ Zulip):**
> "When reviewing the blueprint graph I noticed an oddity in the Erdos 392 project: the final theorems were mysteriously disconnected from the rest of the lemmas; and the (AI-provided) proofs were suspiciously short. After some inspection I realized the problem: I had asked to prove the (trivial) statements that n! can be factored into **at least** n factors... when in fact the Erdos problem asks for **at most** n factors. The trivial factorization n! = 1 x ... x n would satisfy the previous versions."
>
> "Another cautionary tale not to blindly trust AI auto-formalization, even when it typechecks..."

**The core insight**: A proof can typecheck while proving something entirely different from what was intended. Side-by-side display and dependency visualization make these mismatches visible.

This incident directly motivated the connectivity validation feature: disconnected subgraphs in the dependency graph indicate that "proven" theorems may not actually follow from the foundational lemmas.

## What We're Building

### From: Python leanblueprint
- Requires Python, pip, texlive (~10 min CI overhead)
- Stringly-typed Jinja2 templates
- No incremental builds
- Separate from Lean ecosystem

### To: Pure Lean (Runway + Dress + LeanArchitect)
- 100% Lean, single toolchain
- Type-safe HTML generation via Verso
- Incremental builds via Lake
- Semantic syntax highlighting with hover tooltips
- Integrated dependency graph visualization
- Build-time soundness checks
- Rainbow bracket matching for nested expressions
- Automatic dependency inference from Lean code

## Soundness Guarantees

The toolchain offers guarantees beyond "typechecks":

| Guarantee | Status | Description |
|-----------|--------|-------------|
| **No sorry** | Implemented | Status auto-detected from proof body |
| **Connected graph** | Implemented | `findComponents` detects disconnected subgraphs |
| **Cycle detection** | Implemented | `detectCycles` finds circular dependencies |
| **Label consistency** | Implemented | `\inputleannode{label}` verified against manifest |
| **Uses completeness** | Implemented | `Node.inferUses` traces actual code dependencies |
| **Fully proven** | Implemented | O(V+E) graph traversal verifies all ancestors |

These are type-checkable properties of the formalization project itself.

## Expanded Definition of "Verified"

**Traditional:** All proofs typecheck without sorry

**Expanded:**
- Dependency graph is connected (no orphan theorems)
- All dependencies explicitly declared and accurate
- Human-readable statement exists for every formal theorem
- Side-by-side display available for inspection
- Validation checks pass (connectivity, cycles)
- `fullyProven` status indicates complete verification chain

## Core Features

### 1. Side-by-Side Display
LaTeX theorem statements on the left, syntax-highlighted Lean code on the right. Mathematicians verify the formal statement matches their intent without parsing Lean syntax.

### 2. Proof Toggle Synchronization
Collapsible proof sections animate together - LaTeX prose and Lean tactics expand/collapse in sync.

### 3. Dependency Graphs
Visual representation of lemma dependencies with Sugiyama hierarchical layout. **Critical for catching logical errors** - disconnected nodes or unexpected dependencies signal problems.

### 4. Hover Tooltips
Type signatures and documentation appear on hover via Tippy.js, making Lean code navigable by non-experts.

### 5. Chapter/Section Structure
LaTeX `\chapter{}` and `\section{}` commands drive HTML structure. Prose interleaves with formal declarations. Numbered theorems (4.1.1, 4.1.2) match LaTeX conventions.

### 6. Rainbow Bracket Highlighting
Bracket pairs colored by nesting depth (6 colors cycling). Makes deeply nested expressions readable.

### 7. Module References
`\inputleanmodule{ModuleName}` in LaTeX includes all `@[blueprint]`-annotated declarations from a Lean module. Useful for organizing large projects by mathematical topic.

### 8. Paper Generation
Academic papers with `\paperstatement{}` and `\paperfull{}` hooks linking to formalizations. ar5iv-style layout with verification badges.

## Audience

### Primary: Mathematicians doing formalization
- May not be Lean experts
- Need to verify formal statements match mathematical intent
- Use blueprints to plan and track formalization projects
- Examples: PNT+, Erdos problems, Sphere Eversion

### Secondary: Formalization researchers
- Building AI-assisted formalization tools
- Need dependency information for proof search
- Need ground truth for training/evaluation

### Tertiary: Lean tooling developers
- Verso/SubVerso maintainers
- Potential upstream contribution target

## Relationship to Existing Tools

**Complementary to docgen4**, not competing:
- docgen4: API documentation for libraries (every declaration, auto-generated)
- This toolchain: Blueprint documentation for formalization projects (curated, narrative structure)

**Inspired by Lean Reference Manual**: Same technical foundation (Verso, SubVerso, 100% Lean), different purpose (reference docs vs formalization blueprints)

**Port of leanblueprint**: Pure Lean reimplementation of Patrick Massot's Python/Plastex blueprint system

## Monorepo Architecture

```
Side-by-Side-Blueprint/
  forks/                    # Forked Lean 4 repositories
    subverso/               # Syntax highlighting (O(1) indexed lookups)
    verso/                  # Document framework (SBSBlueprint/VersoPaper genres)
    LeanArchitect/          # @[blueprint] attribute (8 metadata + 3 status)
  toolchain/                # Core toolchain components
    Dress/                  # Artifact generation during Lean elaboration
    Runway/                 # Site generator (replaces Python leanblueprint)
    SBS-Test/               # Minimal test project for fast iteration
    dress-blueprint-action/ # GitHub Action (432 lines) + CSS/JS assets (3,805 lines)
  showcase/                 # Production examples
    General_Crystallographic_Restriction/  # Production example with paper (57 nodes)
    PrimeNumberTheoremAnd/                 # Large-scale integration (591 nodes)
  dev/                      # Development tooling
    scripts/                # sbs CLI and Python tooling
    storage/                # Archive (screenshots, metrics, rubrics)
    .refs/                  # Detailed reference docs
    markdowns/              # Public documentation (this file)
    build-sbs-test.sh       # One-click SBS-Test build
    build-gcr.sh            # One-click GCR build
    build-pnt.sh            # One-click PNT build
```

**Dependency chain:** SubVerso -> LeanArchitect -> Dress -> Runway -> Consumer projects

**Monorepo refactor (February 2026):** Consolidated all repositories into a single monorepo for easier cross-repo development and dependency management. Forks, toolchain, and showcase projects are now organized into separate directories.

## Current Status

### Completed

| Feature | Status |
|---------|--------|
| Side-by-side display | Complete |
| Dashboard homepage | Complete |
| Dependency graph with Sugiyama layout | Complete |
| 6-status color model | Complete |
| `fullyProven` auto-computation | Complete |
| Rainbow bracket highlighting | Complete |
| Module reference support | Complete |
| Paper generation (HTML + PDF) | Complete |
| Validation checks (connectivity, cycles) | Complete |
| Hover tooltips via Tippy.js | Complete |
| Dark/light theme toggle | Complete |
| GitHub Action for CI/CD | Complete |
| Visual compliance testing | Complete |
| Archive system with iCloud sync | Complete |
| 8-dimensional quality scoring (T1-T8) | Complete |

### Production Examples

| Project | Nodes | Status |
|---------|-------|--------|
| SBS-Test | 33 | All features demonstrated |
| GCR | 57 | Complete formalization with paper |
| PNT | 591 | Large-scale integration working |

### Known Limitations

- Verso LaTeX export not implemented (`pdf_verso` removed from active surfaces; infrastructure preserved)
- Dashboard is single-column layout (intentional)
- Build time dominated by SubVerso highlighting (93-99%)

## Quality Validation

The toolchain now includes an 8-dimensional quality scoring system for design validation:

| Category | Tests | Description |
|----------|-------|-------------|
| Deterministic (50%) | T1, T2, T5, T6 | CLI execution, ledger health, color matching, CSS coverage |
| Heuristic (50%) | T3, T4, T7, T8 | Dashboard clarity, toggle discoverability, jarring-free, professional score |

**Current Score:** 91.77/100 (as of 2026-02-01)

Design validators in `dev/scripts/sbs/tests/validators/design/` automate quality assessment, providing measurable quality targets for UI work.

## Quality Targets

### Blueprint (Achieved)
1. **SBS-Test builds and serves** with chapter/section structure matching `blueprint.tex`
2. **Output matches goal images** - hierarchical navigation, numbered theorems, prose between declarations
3. **dress-blueprint-action** works for external consumers without Python/texlive
4. **External assets architecture** - CSS/JS in `dress-blueprint-action/assets/`, configured via `assetsDir`
5. **Validation checks** - disconnected graphs and cycles detected and reported

### ar5iv Paper Generation (Achieved)
6. **Full paper rendering** with MathJax, verification badges
7. **Links to formalization** instead of displaying code directly
8. **Same build workflow** - defined by tex, uses Dress artifacts
9. **Paper metadata extraction** from `\title{}`, `\author{}`, `\begin{abstract}`

### Future Directions

- Verso document DSL as primary authoring format (reducing LaTeX dependency)
- Tactic state expansion in tooltips
- Full docgen4 bidirectional linking
- Mobile-optimized responsive design
- Upstream contribution to official Verso/SubVerso

## Why Pure Lean Matters

1. **Single toolchain** - No Python/pip/texlive installation
2. **Incremental builds** - Lake handles dependencies properly
3. **Type safety** - Catch errors at compile time, not runtime
4. **Ecosystem alignment** - Benefits from Lean FRO improvements
5. **Contribution path** - Could become official Verso genre

## Timeline Context

- **Lean Together 2026**: Leo de Moura discussed tooling goals aligned with this project
- **January 2026**: Tao incident motivates connectivity validation
- **Current**: Feature-complete prototype, production examples working
- **Next**: Stabilization, documentation, community feedback
- **Future**: Propose as official FRO tool

## Tooling

For build commands, screenshot capture, compliance validation, archive management, and custom rubrics, see the [Storage & Tooling Hub](../storage/README.md).

## Related Documents

- [GRAND_VISION.md](GRAND_VISION.md) - The broader vision: SBS in the age of AI-assisted mathematics
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical architecture and build pipeline
- [README.md](../living/README.md) - Agent-facing monorepo overview
- [TAXONOMY.md](TAXONOMY.md) - Document classification system
- [Archive_Orchestration_and_Agent_Harmony.md](Archive_Orchestration_and_Agent_Harmony.md) - Script-agent boundary, archive roles
- [dev/storage/README.md](../../storage/README.md) - Central tooling hub
- [dev/.refs/ARCHITECTURE.md](../../.refs/ARCHITECTURE.md) - Detailed technical reference
