# Task Plan: KaTeX Fix + Grid Restructure + Separation Docs + Doc Update

## Context

7 open issues remain after the overnight 23-issue execution. This session tackles the 4 actionable items: #280 (KaTeX parser), #244 (grid restructure), #266 (separation architecture docs), and comprehensive documentation refresh. Also closes #231 (already complete). Issues #223, #209 remain deferred (require user domain decisions).

## Alignment Decisions

- **#280:** State-machine parser (not extended regex)
- **#244:** Full visual QA (screenshots before/after)
- **#266:** Comprehensive separation architecture document
- **#231:** Close (extension configured and working)
- **Debug instrumentation:** Keep KaTeX debug lines in blueprintPanel.tsx
- **Execution:** Waves 1+3 parallel, then Wave 2, then Wave 4

---

## Wave 1: KaTeX State-Machine Parser (#280)

**File:** `forks/vscode-lean4/lean4-infoview/src/infoview/blueprintPanel.tsx` (lines 59-111)

### Problem

Current regex `text.split(/(\$\$[^$]+\$\$|\$[^$]+\$)/g)` fails on:
- `\begin{equation}...\end{equation}` (no $ delimiters)
- `\begin{aligned}` nested inside `\begin{equation}`
- `\[...\]` display math
- Multi-line environments

Real PNT examples that break:
```latex
\begin{equation}\label{eq:singdot}
\begin{aligned}
R(x) &= \sum_{k\leq K} M\left(\sqrt{\frac{x}{k}}\right) ...
\end{aligned}
\end{equation}
```

### Implementation

Replace the regex split with a `parseLatexSegments(text: string)` function that returns `Array<{type: 'text'|'inline'|'display', content: string}>`.

**Parser states:** `text`, `inline_math` (after `$`), `display_dollar` (after `$$`), `display_bracket` (after `\[`), `display_env` (after `\begin{...}`)

**Handled delimiters:**
| Delimiter | Type | Close |
|-----------|------|-------|
| `$...$` | inline | `$` |
| `$$...$$` | display | `$$` |
| `\[...\]` | display | `\]` |
| `\begin{equation}` | display | `\end{equation}` |
| `\begin{align}` | display | `\end{align}` |
| `\begin{aligned}` | display | `\end{aligned}` |
| `\begin{gather}` | display | `\end{gather}` |
| `\begin{split}` | display | `\end{split}` |
| `\begin{multline}` | display | `\end{multline}` |

**Nesting:** Environments nest (e.g. `aligned` inside `equation`). The parser tracks nesting depth — only the outermost environment boundary matters for segment splitting.

**Escaped delimiters:** `\$` is treated as literal text, not a math delimiter.

**Integration:** The `MathStatement` component replaces line 81's `text.split(...)` with `parseLatexSegments(text)`, then maps segments to KaTeX render calls. Keep all existing debug `console.warn` and visible diagnostic lines.

### Build & Deploy

```bash
cd forks/vscode-lean4/lean4-infoview && npm run build
cd forks/vscode-lean4/vscode-lean4 && npm run build
cp -r forks/vscode-lean4/vscode-lean4/dist/lean4-infoview/ ~/.vscode/extensions/leanprover.lean4-0.0.222/dist/lean4-infoview/
```

### Verification

- User reloads VSCode window
- Open SBS-Test `PolynomialDemo.lean` — simple `$...$` still renders
- Open PNT `StrongPNT.lean` — `\begin{equation}` blocks now render
- Open PNT `MobiusLemma.lean` — nested `\begin{aligned}` renders

---

## Wave 2: SBS Grid Restructure (#244)

### Current Structure (from SideBySide.lean)

```html
<div class="sbs-container">           <!-- 2-col × 1-row grid -->
  <div class="sbs-latex-column">       <!-- All LaTeX in one cell -->
    <div class="theorem_thmheading">heading + status dot</div>
    <div class="theorem_thmcontent">statement</div>
    <div class="proof_wrapper">proof toggle + body</div>
  </div>
  <div class="sbs-lean-column">        <!-- All Lean in one cell -->
    <pre class="lean-code">
      <code class="lean-signature">signature</code>
      <code class="lean-proof-body">proof body</code>
    </pre>
  </div>
</div>
```

### Target Structure

```html
<div class="sbs-container">           <!-- 2-col × 3-row grid -->
  <!-- Row 1 -->
  <div class="sbs-heading">heading + status dot</div>
  <div class="sbs-heading-spacer"></div>
  <!-- Row 2 -->
  <div class="sbs-statement">statement</div>
  <div class="sbs-signature"><pre><code class="lean-signature">...</code></pre></div>
  <!-- Row 3 -->
  <div class="sbs-proof-latex">proof toggle + body</div>
  <div class="sbs-proof-lean"><pre><code class="lean-proof-body">...</code></pre></div>
</div>
```

### Files to Modify

1. **`toolchain/Dress/Dress/Render/SideBySide.lean`** (~lines 141-262)
   - Break `renderSideBySide` to emit 6 grid items instead of 2 column divs
   - Each item gets a semantic class name for grid placement
   - Split the `<pre class="lean-code">` into two separate `<pre>` elements

2. **`toolchain/dress-blueprint-action/assets/common.css`** (~lines 327-337)
   ```css
   .sbs-container {
     display: grid;
     grid-template-columns: 1fr 1fr;
     grid-template-rows: auto auto auto;
     gap: 1rem;
   }
   .sbs-heading         { grid-row: 1; grid-column: 1; }
   .sbs-heading-spacer  { grid-row: 1; grid-column: 2; }
   .sbs-statement       { grid-row: 2; grid-column: 1; align-self: start; }
   .sbs-signature       { grid-row: 2; grid-column: 2; align-self: start; }
   .sbs-proof-latex     { grid-row: 3; grid-column: 1; }
   .sbs-proof-lean      { grid-row: 3; grid-column: 2; }
   ```
   - Remove any `padding-top` alignment hacks

3. **`toolchain/dress-blueprint-action/assets/plastex.js`** (~lines 69-85)
   - Verify selectors still work: `$(this).closest('.sbs-container').find('.lean-proof-body')` — this searches the entire container, so it should find `.lean-proof-body` regardless of DOM nesting
   - Likely NO changes needed, but verify after build

### Visual QA Protocol

1. **Before screenshots:** `cd dev/scripts && python3 -m sbs capture --project SBSTest --interactive`
2. **Build:** `cd toolchain/SBS-Test && python3 ../../dev/scripts/build.py --force-lake`
3. **After screenshots:** `python3 -m sbs capture --project SBSTest --interactive`
4. **Compare:** `python3 -m sbs compare --project SBSTest`
5. **Compliance:** `python3 -m sbs compliance --project SBSTest`

### Verification

- Statement text and Lean signature align horizontally (row 2)
- Proof toggle and Lean proof body align horizontally (row 3)
- Proof toggle expand/collapse works
- All 33 SBS-Test nodes render correctly
- No regressions in heading/status dot display

---

## Wave 3: SBS/SLS Separation Architecture (#266)

**New file:** `dev/markdowns/permanent/SBS_SLS_SEPARATION.md`

### Document Structure

1. **Executive Summary** — Why separate, what changes, what stays
2. **Current State Map** — File-level categorization:
   - **SBS:** `toolchain/`, `showcase/`, `forks/{subverso,verso,LeanArchitect}`
   - **SLS:** `dev/`, `.claude/`, `CLAUDE.md`
   - **Hybrid:** `forks/sbs-lsp-mcp` (77 tools to split), `forks/vscode-lean4`
3. **MCP Tool Split Matrix** — All 77 tools categorized:
   - 18 Lean LSP → standard `lean-lsp-mcp`
   - ~10 SBS build/quality → SBS repo or shared package
   - ~30 SLS orchestration → `sls-mcp`
   - 8 browser/zulip → `sls-mcp`
4. **Python Scripts Split** — `dev/scripts/sbs/` categorized:
   - SBS: `build/`, `tests/`, `oracle/`
   - SLS: `archive/`, `labels/`, `readme/`, `test_catalog/`
   - Shared: `core/` (git_ops, utils)
5. **Proposed Repository Structure** — New SBS monorepo layout, remaining SLS repo layout
6. **Migration Strategy** — 5-phase plan:
   - Phase 1: Extract Lean LSP tools to standard package
   - Phase 2: Create SBS monorepo, move toolchain + showcase + forks
   - Phase 3: Split sbs-lsp-mcp into sbs-tools + sls-tools
   - Phase 4: Split Python scripts
   - Phase 5: CI/CD migration (dress-blueprint-action references)
7. **Dependency Analysis** — What breaks, what stays connected, submodule impact
8. **Open Questions** — Oracle placement, shared core/ utilities, test catalog ownership

### Also Update

- `CLAUDE.md` — Add brief separation section referencing the new doc
- `dev/markdowns/permanent/Archive_Orchestration_and_Agent_Harmony.md` — Note planned separation

---

## Wave 4: Documentation Update + Issue Housekeeping

### Documentation Refresh

- **`CLAUDE.md`** — Verify MCP tool tables match current code (62+ tools), update KaTeX status to "partially working (#280)"
- **`dev/markdowns/living/README.md`** — Verify component descriptions match current state
- **`dev/storage/README.md`** — Verify CLI command documentation
- **`dev/markdowns/permanent/ARCHITECTURE.md`** — Verify build pipeline description, note grid restructure

### Issue Housekeeping

- **Close #231** — `gh issue close 231 --reason completed --comment "Extension fully configured and working"`
- **Update #224** — Edit epic body: all crushes complete, KaTeX partially working (fixed #267/#271, #280 in progress), grid restructure done (#244), remaining aspirational goals tracked

---

## Execution Order

```
┌─────────────────────┐  ┌─────────────────────────┐
│ Wave 1: KaTeX (#280) │  │ Wave 3: Separation (#266)│
│ [1 agent]            │  │ [1 agent]                │
└──────────┬──────────┘  └────────────┬────────────┘
           │                          │
           └──────────┬───────────────┘
                      ▼
           ┌──────────────────────┐
           │ Wave 2: Grid (#244)   │
           │ [1 agent + visual QA] │
           └──────────┬───────────┘
                      ▼
           ┌──────────────────────┐
           │ Wave 4: Docs + Close  │
           │ [2 parallel agents]   │
           └──────────────────────┘
```

Waves 1+3 run in parallel (no file overlap). Wave 2 follows (benefits from KaTeX fix for visual verification). Wave 4 last (references all prior changes).

## Gates

| Gate | Criteria |
|------|----------|
| After Wave 1 | KaTeX renders `\begin{equation}` blocks; simple `$...$` still works |
| After Wave 2 | Visual QA passes; proof toggles work; no regressions in SBS-Test |
| After Wave 3 | Separation doc complete and internally consistent |
| After Wave 4 | All living docs current; #231 closed; #224 updated |
| Final | `sbs_run_tests(tier="evergreen")` passes |

## Risk Factors

| Risk | Mitigation |
|------|------------|
| KaTeX state-machine edge cases | Keep debug instrumentation; test with SBS-Test (simple) and PNT (complex) |
| Grid restructure breaks existing CSS | Full visual QA before/after; revert if regressions |
| SideBySide.lean Lean compilation errors | Check `lean_diagnostic_messages` after edits; fix or revert |
| SBS-Test rebuild fails after grid changes | Build with `--force-lake`; check Lake output |

## Key Files

| File | Wave | Action |
|------|------|--------|
| `forks/vscode-lean4/lean4-infoview/src/infoview/blueprintPanel.tsx` | 1 | Replace regex with state-machine parser |
| `toolchain/Dress/Dress/Render/SideBySide.lean` | 2 | Restructure HTML to 6 grid items |
| `toolchain/dress-blueprint-action/assets/common.css` | 2 | 3-row grid CSS |
| `toolchain/dress-blueprint-action/assets/plastex.js` | 2 | Verify selectors (likely no changes) |
| `dev/markdowns/permanent/SBS_SLS_SEPARATION.md` | 3 | New comprehensive separation doc |
| `CLAUDE.md` | 3, 4 | Separation ref + doc refresh |
| `dev/markdowns/permanent/Archive_Orchestration_and_Agent_Harmony.md` | 3 | Separation note |
| `dev/markdowns/living/README.md` | 4 | Accuracy verification |
| `dev/markdowns/permanent/ARCHITECTURE.md` | 4 | Build pipeline update |
