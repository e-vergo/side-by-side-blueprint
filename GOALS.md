# Side-by-Side Blueprint: Project Goals

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
> "When reviewing the blueprint graph I noticed an oddity in the Erdos 392 project: the final theorems were mysteriously disconnected from the rest of the lemmas; and the (AI-provided) proofs were suspiciously short. After some inspection I realized the problem: I had asked to prove the (trivial) statements that n! can be factored into **at least** n factors... when in fact the Erdos problem asks for **at most** n factors. The trivial factorization n! = 1 × ... × n would satisfy the previous versions."
>
> "Another cautionary tale not to blindly trust AI auto-formalization, even when it typechecks..."

**The core insight**: A proof can typecheck while proving something entirely different from what was intended. Side-by-side display and dependency visualization make these mismatches visible.

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

## Soundness Guarantees

The toolchain enforces guarantees beyond "typechecks":

| Guarantee | Description |
|-----------|-------------|
| **No sorry** | Build fails if any `sorry` remains in formalized declarations |
| **Connected graph** | Warn on disconnected dependency subgraphs (the Tao check) |
| **Label consistency** | Verify `\inputleannode{label}` matches actual Lean declaration |
| **Uses completeness** | Compare `\uses{}` annotations against actual code dependencies |

These are type-checkable properties of the formalization project itself.

## Expanded Definition of "Verified"

**Traditional:** All proofs typecheck without sorry

**Expanded:**
- Dependency graph is connected (no orphan theorems)
- All dependencies explicitly declared and accurate
- Human-readable statement exists for every formal theorem
- Side-by-side display available for inspection
- Build-time checks pass

## Core Features

### 1. Side-by-Side Display
LaTeX theorem statements on the left, syntax-highlighted Lean code on the right. Mathematicians verify the formal statement matches their intent without parsing Lean syntax.

### 2. Proof Toggle Synchronization
Collapsible proof sections animate together - LaTeX prose and Lean tactics expand/collapse in sync.

### 3. Dependency Graphs
Visual representation of lemma dependencies. **Critical for catching logical errors** - disconnected nodes or unexpected dependencies signal problems.

### 4. Hover Tooltips
Type signatures and documentation appear on hover, making Lean code navigable by non-experts.

### 5. Chapter/Section Structure
LaTeX `\chapter{}` and `\section{}` commands drive HTML structure. Prose interleaves with formal declarations. Numbered theorems (4.1.1, 4.1.2) match LaTeX conventions.

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

## Repository Architecture

```
Side-by-Side-Blueprint/
├── Runway/           # Site generator (replaces Python leanblueprint)
├── Dress/            # Artifact generation during Lean elaboration
├── LeanArchitect/    # @[blueprint] attribute and metadata storage
├── subverso/         # Syntax highlighting extraction (fork)
├── SBS-Test/         # Minimal test project for fast iteration
├── General_Crystallographic_Restriction/  # Production example
└── dress-blueprint-action/  # GitHub Action for CI automation
```

**Dependency chain:** SubVerso → LeanArchitect → Dress → Runway → Consumer projects

## Success Criteria

1. **SBS-Test builds and serves** with chapter/section structure matching `blueprint.tex`
2. **Output matches goal images** - hierarchical navigation, numbered theorems, prose between declarations
3. **General_Crystallographic_Restriction** deploys via GitHub Actions with pure Lean stack
4. **dress-blueprint-action** works for external consumers without Python/texlive
5. **Soundness checks** catch disconnected graphs and missing dependencies

## Non-Goals (Current Phase)

- Tactic state expansion (future)
- Full doc-gen4 bidirectional linking (future)
- Verso Genre with document DSL (future)
- Mobile-optimized responsive design
- Offline/PWA support

## Why Pure Lean Matters

1. **Single toolchain** - No Python/pip/texlive installation
2. **Incremental builds** - Lake handles dependencies properly
3. **Type safety** - Catch errors at compile time, not runtime
4. **Ecosystem alignment** - Benefits from Lean FRO improvements
5. **Contribution path** - Could become official Verso genre

## Timeline Context

- **Lean Together 2026**: Leo de Moura discussed tooling like this
- **Current**: Port ~85% complete, working on LaTeX structure parsing
- **Next**: Feature parity with Python leanblueprint
- **Future**: Propose as official FRO tool
