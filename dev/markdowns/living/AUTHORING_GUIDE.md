# Authoring Guide: What You Can Write, Where It Goes, How It's Served

This document describes the content authoring and rendering pathways available in the Side-by-Side Blueprint toolchain. It covers what you write, where you put it, and what the pipeline produces.

---

## The Two Authoring Systems

There are two ways to write blueprint and paper content:

| System | Source format | File extension | Status |
|--------|--------------|----------------|--------|
| **LaTeX (TeX)** | Standard LaTeX with SBS hooks | `.tex` | Production-ready, used by all projects |
| **Verso** | Lean-based document DSL with SBS directives | `.lean` | Infrastructure exists, not yet active |

Both systems consume the same underlying data: Dress artifacts generated from `@[blueprint]` declarations. They differ in how you author the surrounding document structure.

**Should you use both?** Not today. Verso document generation is not yet wired into the active build pipeline. The sidebar links, compliance checks, and validation have all been scoped to TeX sources. The Lean infrastructure for Verso genres (`SBSBlueprint`, `VersoPaper`) is preserved and will be activated in a future phase. For now, **write in LaTeX**.

---

## What You Write in Lean

Every formalized declaration that should appear in the blueprint needs the `@[blueprint]` attribute from LeanArchitect:

```lean
@[blueprint "thm_main"
  (title := "Main Theorem")
  (status := .proven)]
theorem main_theorem : P := by
  exact proof
```

The attribute stores metadata (label, title, status, dependencies) in a persistent environment extension. During `lake build` with `BLUEPRINT_DRESS=1`, the Dress elaboration rules intercept these declarations and produce per-declaration artifacts.

### Statement Text: Two Sources

The LaTeX statement text that appears on the left side of the side-by-side display can come from two places:

**1. The `@[blueprint]` attribute (default)**

The `statement` field on the attribute holds the TeX text directly:

```lean
@[blueprint "thm_main"
  (statement := "For all $n$, we have $P(n)$.")]
theorem main_theorem : ∀ n, P n := by ...
```

**2. Delimiter comments in the Lean source**

Ported from `leanblueprint-extract`, you can write TeX in special comments immediately preceding the declaration:

```lean
/-%%
For all $n$, we have $P(n)$.
%%-/
@[blueprint "thm_main"]
theorem main_theorem : ∀ n, P n := by ...
```

Line delimiters also work:

```lean
--%% For all $n$, we have $P(n)$.
@[blueprint "thm_main"]
theorem main_theorem : ∀ n, P n := by ...
```

The `statementSource` field in `runway.json` controls which source is used:

| Value | Behavior |
|-------|----------|
| `"attribute"` | Only use `@[blueprint]` statement text (default) |
| `"delimiters"` | Only use delimiter comments |
| `"both"` | Use delimiter content when `@[blueprint]` statement text is empty |

### What Dress Produces

For each `@[blueprint]` declaration, Dress writes to `.lake/build/dressed/{Module}/{label}/`:

| File | Contents |
|------|----------|
| `decl.tex` | LaTeX with `\lean{}`, `\leansignaturehtml{}`, `\leanproofhtml{}`, `\leanhoverdata{}` |
| `decl.html` | Syntax-highlighted Lean code (SubVerso) |
| `decl.hovers.json` | Hover tooltip data for the highlighted code |
| `decl.json` | Label and name metadata |
| `manifest.entry` | Entry for the global manifest |

It also produces:
- `manifest.json` -- maps every label to its artifact path
- Dependency graph data (nodes, edges, status propagation)
- SVG visualization of the graph

---

## What You Write in LaTeX

You write two (optionally three) TeX files. They serve different purposes and produce different outputs.

### blueprint.tex -- The Blueprint

**What it is:** The structural document that organizes your formalization into chapters, sections, and individual nodes.

**Where it goes:** `runway/src/blueprint.tex` (or set `blueprintTexPath` in `runway.json`)

**Hooks available:**

| Hook | What it does |
|------|-------------|
| `\inputleannode{label}` | Insert a single node's full side-by-side display |
| `\inputleanmodule{Module.Name}` | Insert all nodes from a Lean module |

**What it produces:** The main blueprint site -- `index.html` (dashboard), per-chapter pages, dependency graph page, and node modals.

**Example:**

```latex
\chapter{Foundations}

\section{Basic Properties}

\begin{theorem}\label{thm:main}
  Statement written in LaTeX for MathJax rendering.
\end{theorem}
\inputleannode{thm:main}
```

The `\begin{theorem}...\end{theorem}` block provides prose context. The `\inputleannode{}` call pulls in the side-by-side display from Dress artifacts.

### paper.tex -- The Paper

**What it is:** A traditional mathematical paper that references formalized results.

**Where it goes:** `runway/src/paper.tex` (or set `paperTexPath` in `runway.json`)

**Hooks available:**

| Hook | What it does |
|------|-------------|
| `\paperstatement{label}` | Insert just the statement with a verification badge |
| `\paperfull{label}` | Insert full side-by-side display |
| `\paperproof{label}` | Insert just the proof body |
| `\inputleannode{label}` | Same as in blueprint -- full side-by-side |

**What it produces:**
- `paper_tex.html` -- ar5iv-style web paper with resolved hooks
- `paper.pdf` (if a TeX compiler is available) -- PDF with hooks resolved to LaTeX
- `pdf_tex.html` -- embedded PDF viewer page

### runway.json -- Configuration

**Where it goes:** Project root (next to `lakefile.lean`)

```json
{
  "title": "My Project",
  "projectName": "MyProject",
  "runwayDir": "runway",
  "assetsDir": "../../toolchain/dress-blueprint-action/assets",
  "statementSource": "both"
}
```

Key fields:

| Field | Purpose |
|-------|---------|
| `runwayDir` | Base directory; derives `{runwayDir}/src/blueprint.tex` and `paper.tex` |
| `assetsDir` | Path to CSS/JS assets (`common.css`, `blueprint.css`, etc.) |
| `statementSource` | `"attribute"`, `"delimiters"`, or `"both"` |
| `pdfCompiler` | `"pdflatex"`, `"tectonic"`, `"xelatex"`, or `"lualatex"` |

---

## How It's Served

### The Build Pipeline

```
lake build (with BLUEPRINT_DRESS=1)
    --> Dress artifacts (.tex, .html, .json per declaration)
    --> manifest.json + dependency graph

python build.py  (or  lake exe runway build)
    --> Parses blueprint.tex and paper.tex
    --> Resolves hooks against manifest/artifacts
    --> Generates HTML site
```

### Output Pages

| Page | Source | URL |
|------|--------|-----|
| Dashboard | blueprint.tex structure + Dress artifacts | `index.html` |
| Chapter pages | blueprint.tex chapters + `\inputleannode{}` | `{chapter-slug}.html` |
| Dependency graph | Dress graph data + node modals | `dep_graph.html` |
| Paper (web) | paper.tex + hooks resolved | `paper_tex.html` |
| Paper (PDF viewer) | paper.tex compiled to PDF | `pdf_tex.html` |

### The Side-by-Side Display

Every node, regardless of which page it appears on, renders through the same core:

| Left column | Right column |
|-------------|-------------|
| LaTeX statement (MathJax-rendered) | Syntax-highlighted Lean signature (SubVerso) |
| LaTeX proof (togglable) | Lean proof body (togglable) |
| | Type hovers via Tippy.js |

Status is shown as a colored dot using the 6-status model (notReady, ready, sorry, proven, fullyProven, mathlibReady).

---

## What About Verso?

Verso is a Lean-based document framework. Instead of writing `.tex` files, you write `.lean` files that compile with type-checking:

```lean
#doc (Blueprint) "My Blueprint"
:::leanNode "thm:main"

:::paperStatement "lem:helper"
```

The infrastructure exists:
- `SBSBlueprint` genre in `forks/verso/src/verso-sbs/` with directives: `:::leanNode`, `:::leanModule`, `:::paperStatement`, `:::paperFull`, `:::paperProof`
- `VersoPaper` genre in `forks/verso/src/verso-paper/` with matching directives plus `:::htmlDiv`, `:::htmlWrapper`, `{nodeRef}`, `{leanCode}` roles
- Runway detects `{ProjectName}/Blueprint.lean` and `{ProjectName}/Paper.lean` sources and looks for compiled HTML output
- `AvailableDocuments` tracks 6 document types: TeX blueprint, TeX paper (web/pdf), Verso blueprint, Verso paper (web/pdf)
- Sidebar rendering supports all 6, showing disabled links for unavailable types

**Current status:** Not active. Verso page types have been removed from the sidebar, compliance validation, and build surfaces. No project currently uses Verso authoring. The Lean code compiles but the end-to-end pipeline (Verso source -> compiled HTML -> integrated into Runway site) has not been tested or validated.

**When it's ready**, a project could have both `runway/src/blueprint.tex` and `MyProject/Blueprint.lean`, and the sidebar would show both as available document formats. Whether both should be rendered and served for the same project is a design decision that hasn't been made yet -- it depends on whether Verso authoring offers enough advantages (type-checked references, integrated Lean tooling) to justify maintaining two parallel documents.

---

## Quick Reference: Which File Does What?

| I want to... | Write in... | Using hook... |
|---------------|------------|---------------|
| Place a node in a blueprint chapter | `blueprint.tex` | `\inputleannode{label}` |
| Place all nodes from a module | `blueprint.tex` | `\inputleanmodule{Module.Name}` |
| Show a statement in a paper | `paper.tex` | `\paperstatement{label}` |
| Show full side-by-side in a paper | `paper.tex` | `\paperfull{label}` |
| Show just a proof in a paper | `paper.tex` | `\paperproof{label}` |
| Provide statement text via attribute | `.lean` source | `@[blueprint "label" (statement := "...")]` |
| Provide statement text via delimiter | `.lean` source | `/-%%...%%-/` or `--%% ...` before `@[blueprint]` |
| Configure which statement source wins | `runway.json` | `"statementSource": "both"` |

---

## Project Examples

| Project | blueprint.tex | paper.tex | statementSource | Verso |
|---------|:---:|:---:|:---:|:---:|
| SBS-Test | yes | yes | `"both"` | no |
| GCR | yes | yes | default | no |
| PNT | yes | no | default | no |
