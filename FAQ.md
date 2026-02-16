# Side-by-Side Blueprint FAQ

Frequently asked questions about the declaration status system, dependency graph, and `@[blueprint]` attribute.

---

## Getting Started

### How do I set up my Lean project with Side-by-Side Blueprint?

**Prerequisites:** A Lean 4 project with a `lakefile.toml`.

**Step 1:** Add Dress as a dependency in your `lakefile.toml`:

```toml
[[require]]
name = "Dress"
git = "https://github.com/e-vergo/Dress.git"
rev = "main"
```

**Step 2:** Run the quickstart command:

```bash
lake exe extract_blueprint quickstart --github-url https://github.com/you/your-project
```

This will:
- Create `runway.json` (site configuration)
- Create `.github/workflows/blueprint.yml` (CI/CD workflow)
- Create `runway/src/blueprint.tex` (LaTeX blueprint stub)
- Add `import Dress` to source files containing declarations

Use `--dry-run` to preview changes without modifying anything.

**Step 3:** Build your project and auto-tag declarations:

```bash
lake build
lake exe extract_blueprint auto-tag YourProjectLib
```

The `auto-tag` command analyzes the compiled environment and adds `@[blueprint]` attributes to all public declarations. Theorems and lemmas get `statement` and `proof` placeholders:

```lean
@[blueprint
  (statement := /--  -/)
  (proof := /--  -/)]
theorem my_theorem : P := by ...
```

**Step 4:** Generate the dependency graph and deploy:

```bash
lake exe extract_blueprint graph YourProjectLib
```

Push to GitHub to trigger the CI workflow, which builds the full blueprint site and deploys to GitHub Pages.

### What does quickstart create?

| File | Purpose |
|------|---------|
| `runway.json` | Site configuration (title, URLs, project name) |
| `.github/workflows/blueprint.yml` | CI workflow using `dress-blueprint-action` |
| `runway/src/blueprint.tex` | LaTeX blueprint document |

It also adds `import Dress` to source files that contain declarations (theorems, defs, lemmas, etc.) and don't already import it.

### What flags does quickstart accept?

| Flag | Description | Default |
|------|-------------|---------|
| `--github-url <url>` | GitHub repository URL | (optional, placeholder used if omitted) |
| `--title <title>` | Project title for the site | Project name from `lakefile.toml` |
| `--base-url <path>` | GitHub Pages base URL | `/<repo-name>/` |
| `--dry-run` (`-n`) | Preview changes without writing files | off |
| `--force` (`-f`) | Overwrite existing files | off |

### Can I run quickstart on a project that already has some SBS files?

Yes. Quickstart skips files that already exist (unless `--force` is used). It also skips adding `import Dress` to files that already have it. This makes it safe to run on partially configured projects.

---

## General

### What are the 7 declaration statuses?

| Status | Description |
|--------|-------------|
| **notReady** | No Lean proof exists, or explicitly marked not ready for formalization |
| **wip** | Work in progress -- actively being formalized |
| **sorry** | Proof contains `sorryAx` (auto-detected) |
| **proven** | Complete Lean proof with no sorry, but has unproven ancestors |
| **fullyProven** | Complete proof AND all ancestors are proven/fullyProven/axiom |
| **axiom** | Lean `axiom` declaration -- intentionally has no proof |
| **mathlibReady** | Ready for upstream submission to Mathlib |

### What do the colors mean?

Each status has a fixed color used in the dependency graph SVG, status dots, and theorem headers:

| Status | Color | Hex |
|--------|-------|-----|
| notReady | Vivid Orange | `#E8820C` |
| wip | Deep Teal/Cyan | `#0097A7` |
| sorry | Vivid Red | `#C62828` |
| proven | Medium Green | `#66BB6A` |
| fullyProven | Deep Forest Green | `#1B5E20` |
| axiom | Vivid Purple | `#7E57C2` |
| mathlibReady | Vivid Blue | `#42A5F5` |

### Where is the color source of truth?

The canonical color definitions are in Lean:

- **`Dress/Graph/Svg.lean`** -- `SvgConfig` structure defines all 7 hex values
- **`common.css`** -- CSS variables (`--sbs-status-not-ready`, etc.) must match the Lean values exactly

Lean is the source of truth. If colors diverge between Lean and CSS, fix the CSS to match Lean.

---

## Manual vs Automatic

### Which statuses can I set manually?

Three statuses can be set via `@[blueprint]` attribute options:

| Option | Sets Status To |
|--------|----------------|
| `(notReady := true)` | notReady |
| `(wip := true)` | wip |
| `(mathlibReady := true)` | mathlibReady |

Example:

```lean
@[blueprint "thm:main" (wip := true)]
theorem main_thm : P := by sorry

@[blueprint "thm:upstream" (mathlibReady := true)]
theorem ready_for_mathlib : Q := proof
```

### Which statuses are computed automatically?

Four statuses are never set manually:

| Status | How It Is Determined |
|--------|---------------------|
| **sorry** | Auto-detected when the proof term contains `sorryAx` |
| **proven** | Auto-detected when a Lean declaration exists with no `sorryAx` |
| **fullyProven** | Computed after graph construction: `proven` + all ancestors are proven/fullyProven/axiom |
| **axiom** | Auto-detected when the Lean declaration uses the `axiom` keyword |

### How do I mark a declaration as work-in-progress?

```lean
@[blueprint "lem:helper" (wip := true)]
lemma helper : P := by sorry
```

Without `(wip := true)`, this declaration would show as `sorry` (because the proof contains `sorryAx`). The `wip` flag overrides that, signaling that the sorry is expected and the declaration is actively being worked on.

### Can I manually set `axiom` or `fullyProven`?

No. These statuses have no corresponding attribute options.

- **axiom** is auto-detected from the Lean environment. If the constant is declared with the `axiom` keyword, Dress assigns the axiom status.
- **fullyProven** is computed by `computeFullyProven` after graph construction. It cannot be forced.

### What happens if I set `(wip := true)` on a declaration that has a complete proof?

It stays `wip`. Manual flags `wip` and `mathlibReady` override auto-derived statuses. The priority order is:

```
mathlibReady > wip > explicit notReady > axiom > proven/sorry > default notReady
```

So `(wip := true)` wins over the auto-derived `proven` status. This is useful for declarations that technically compile but are not yet in their final form.

---

## Priority and Conflict Resolution

### What is the priority order?

Status determination follows this priority (highest to lowest):

1. **mathlibReady** -- if `(mathlibReady := true)` is set
2. **wip** -- if `(wip := true)` is set
3. **notReady** (explicit) -- if `(notReady := true)` is set, overrides auto-derive
4. **axiom** -- auto-detected from `axiom` keyword
5. **proven** -- has Lean code, no `sorryAx`
6. **sorry** -- has Lean code with `sorryAx`
7. **notReady** (default) -- no Lean code exists

This is implemented in `Dress/Graph/Build.lean` in the `getStatus` function.

### What happens when manual and automatic statuses conflict?

Manual flags always win over auto-derived statuses. The logic is:

```
1. Check mathlibReady flag -> if set, return mathlibReady
2. Check wip flag         -> if set, return wip
3. Check explicit notReady -> if statusExplicit && notReady, return notReady
4. Check axiom envType    -> if declaration is axiom, return axiom
5. Auto-derive from Lean  -> proven or sorry based on sorryAx presence
6. Default                -> notReady (no Lean code)
```

### If I set `(mathlibReady := true)` on a declaration with sorry, what status does it get?

**mathlibReady.** The `mathlibReady` flag has the highest priority and overrides everything, including auto-detected `sorry`. This is intentional -- you might mark something as mathlib-ready while a sorry exists in a helper lemma that is about to be replaced.

```lean
@[blueprint "thm:ready" (mathlibReady := true)]
theorem almost_there : P := by sorry  -- Status: mathlibReady (not sorry)
```

### What does `(notReady := true)` do on a declaration with a Lean proof?

It forces the status to **notReady**, overriding the auto-derived `proven` status. This is tracked via `statusExplicit = true` in the `Node` structure, which tells the status resolution to respect the explicit flag even when Lean code exists.

Use case: a declaration compiles but the LaTeX statement has not been written yet, or the formalization approach needs rethinking.

```lean
@[blueprint "lem:rethink" (notReady := true)]
lemma needs_rethink : P := proof  -- Status: notReady (not proven)
```

---

## fullyProven Promotion

### How does fullyProven work?

After the dependency graph is built, `computeFullyProven` runs a single O(V+E) pass over all nodes. A node is promoted from `proven` to `fullyProven` if and only if:

1. The node itself has status `proven`
2. **All** of its ancestors (transitive dependencies) have status `proven`, `fullyProven`, or `axiom`

This uses memoization with an iterative worklist algorithm. The implementation is in `Dress/Graph/Build.lean`.

### Do axiom ancestors block fullyProven?

**No.** Axioms are treated as "complete" for the purpose of fullyProven computation. The `isComplete` check in `computeFullyProven` accepts `proven`, `fullyProven`, and `axiom` as valid ancestor statuses.

This is correct because axioms are intentionally unproven -- they represent foundational assumptions that have no proof obligation.

### Can a sorry node become fullyProven?

**No.** Only nodes with status `proven` are candidates for promotion to `fullyProven`. A `sorry` node (or `notReady`, `wip`, `mathlibReady`) will never be promoted, regardless of its ancestors.

### What about cycles in the dependency graph?

Cycles are detected by `detectCycles` using DFS with gray/black coloring. If a cycle is found during `computeFullyProven`, the nodes involved are marked as incomplete (not promoted to fullyProven). Cycle detection results are also reported in `manifest.json` under `checkResults`.

---

## Axiom Status

### How are axioms detected?

Dress checks the Lean environment during graph construction (`fromEnvironment` in `Dress/Graph/Build.lean`). If `env.find?` returns `.axiomInfo`, the node's `envType` is set to `"axiom"`, which causes `getStatus` to return `.axiom`.

This is fully automatic -- no attribute flag is needed.

### What is the difference between an axiom declaration and a theorem with sorry?

| | Axiom | Theorem with sorry |
|-|-------|--------------------|
| **Lean keyword** | `axiom` | `theorem ... := by sorry` |
| **Status** | `axiom` (purple) | `sorry` (red) |
| **Proof expected?** | No | Yes |
| **Blocks fullyProven?** | No | Yes |
| **Graph shape** | Diamond | Ellipse |

An axiom is a deliberate foundational assumption. A theorem with sorry is an incomplete proof that needs to be filled in.

### Are axioms shown differently in the graph?

Yes. Axioms are rendered as **diamonds** in the SVG dependency graph (defined in `Dress/Graph/Svg.lean`). Theorems and lemmas use **ellipses**, and definitions use **rectangles**.

### Can I override an axiom's status?

Only `mathlibReady` and `wip` flags override the auto-detected axiom status (they have higher priority). Setting `(notReady := true)` on an axiom has no effect because `notReady` has lower priority than axiom in the resolution order.

---

## Visual Rendering

### How do statuses appear in the dependency graph SVG?

Each node is rendered with:
- **Fill color** matching the status hex value (see color table above)
- **Shape** based on declaration type: ellipse (theorems), rectangle (definitions), diamond (axioms)
- **Text color** is white for dark backgrounds (sorry, fullyProven, axiom, wip) and dark gray for light backgrounds
- **CSS class** for dark mode targeting (`status-not-ready`, `status-wip`, etc.)

### What does the dotted border mean?

A **dotted (dashed) stroke** on a graph node indicates that the node's status was **manually set** via an `@[blueprint]` attribute option (`notReady := true`, `wip := true`, or `mathlibReady := true`). This is controlled by the `isManuallyTagged` field on the graph `Node` type and rendered via `stroke-dasharray="2,2"` in the SVG.

Nodes with only auto-derived statuses (sorry, proven, fullyProven, axiom) have solid borders.

### How do statuses appear in HTML (theorem headers, status dots)?

Status dots are small colored circles that appear next to declaration names throughout the site:

| Context | CSS Class | Size |
|---------|-----------|------|
| Dashboard key declarations | `.status-dot` | 8px |
| Theorem headers (blueprint) | `.header-status-dot` | 10px |
| Paper theorem headers | `.paper-status-dot` | 10px |
| Dependency graph modals | `.modal-status-dot` | 12px |

The dot color comes from CSS variables (`--sbs-status-not-ready`, `--sbs-status-wip`, etc.) defined in `common.css`.

### Does dark mode change the colors?

Most status colors remain the same in dark mode. Two statuses get lighter variants for better visibility on dark backgrounds:

| Status | Light Mode | Dark Mode |
|--------|-----------|-----------|
| wip | `#0097A7` | `#4DD0E1` (lighter teal) |
| axiom | `#7E57C2` | `#B088E8` (lighter purple) |

All other status colors are unchanged. The SVG graph uses inline fill colors from Lean (not CSS variables), so graph node colors do not change with theme. Status dots in HTML do respond to dark mode via the CSS variable overrides.

---

## Backwards Compatibility

### What happened to the `ready` status?

The `ready` status was renamed to `wip` (work in progress) to better reflect its meaning. In the old 6-status model, `ready` meant "ready to formalize" which was confusing alongside `notReady`.

### What about old JSON files with `"ready"` or `"stated"`?

The `FromJson` instance for `NodeStatus` handles legacy values:

| Old Value | Maps To |
|-----------|---------|
| `"stated"` | `notReady` |
| `"ready"` | `wip` |
| `"inMathlib"` | `mathlibReady` |

Old `manifest.json` files will parse correctly.

### Will old `@[blueprint]` attributes with `(ready := true)` still work?

**No.** The `ready` syntax option has been removed from the attribute parser. You must update to `(wip := true)`. The Lean compiler will report an error if you use the old syntax.

---

## Troubleshooting

### My declaration shows as notReady even though it has a proof -- why?

Check for an explicit `(notReady := true)` flag:

```lean
-- This will show as notReady despite having a complete proof
@[blueprint "thm:stuck" (notReady := true)]
theorem my_thm : P := proof
```

When `statusExplicit` is `true` and status is `notReady`, it overrides the auto-derived `proven` status. Remove `(notReady := true)` to let auto-detection work.

### My declaration shows as proven but I expected fullyProven -- why?

A node is only promoted to `fullyProven` when ALL of its transitive dependencies are proven, fullyProven, or axiom. If any ancestor has status `sorry`, `notReady`, or `wip`, promotion is blocked.

To diagnose:
1. Open the dependency graph page
2. Click on the node to see its dependencies
3. Look for any ancestors with non-green status (orange notReady, teal wip, red sorry)
4. Those ancestors are blocking the fullyProven promotion

### Status colors look wrong in dark mode -- what should I check?

1. **CSS variables**: Verify `common.css` dark mode overrides at `@media (prefers-color-scheme: dark)` include the correct values for `--sbs-status-wip` and `--sbs-status-axiom`
2. **SVG vs HTML**: Graph SVG nodes use inline fill colors from Lean (not CSS variables), so they do not respond to dark mode. Only HTML elements (status dots, badges) use CSS variables
3. **Source of truth**: If Lean and CSS colors disagree, update CSS to match `Dress/Graph/Svg.lean`

---

## Quick Reference

### Attribute syntax summary

```lean
-- Minimal: just a label
@[blueprint "thm:main"]
theorem main_thm : P := proof

-- With manual status
@[blueprint "lem:wip" (wip := true)]
lemma work_in_progress : Q := by sorry

-- With metadata
@[blueprint "thm:key" (keyDeclaration := true, message := "Main result")]
theorem key_result : R := proof

-- Multiple options
@[blueprint "def:helper"
  (title := "Helper Function")
  (mathlibReady := true)
  (message := "PR #1234 submitted")]
def helper : S := value

-- Explicit notReady override
@[blueprint "thm:rethink" (notReady := true)]
theorem needs_work : T := proof
```

### Status resolution flowchart

```
Is (mathlibReady := true) set?  -->  YES: mathlibReady
                                     NO
                                     |
Is (wip := true) set?  ---------->  YES: wip
                                     NO
                                     |
Is (notReady := true) set?  ----->  YES: notReady
                                     NO
                                     |
Is Lean `axiom` keyword?  ------->  YES: axiom
                                     NO
                                     |
Has Lean code?  ------------------>  YES: has sorryAx? --> YES: sorry
                                     |                     NO: proven
                                     NO: notReady (default)
```

After graph construction, `proven` nodes with all ancestors complete are promoted to `fullyProven`.
