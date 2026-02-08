# Task #49: Visual Differentiation for TeX Blueprint Pages

## Goal
Make TeX-driven blueprint chapter pages look like typeset math papers (serif, justified, paper-like), while Verso pages retain their modern web aesthetic. The visual contrast makes the two modes immediately distinguishable.

## Approach: CSS-Only Scoped Styling

All changes target `.chapter-page` (TeX blueprint chapters) and `.ar5iv-paper` (TeX paper view) via CSS selectors. No template or JavaScript changes required.

## Changes

### File: `toolchain/dress-blueprint-action/assets/blueprint.css`

**1. Paper-like typography for `.chapter-page`**
- Font family: `Georgia, "Palatino Linotype", "Book Antiqua", Palatino, serif`
- Body text: justified, line-height 1.7
- Headings: serif (same family), slightly smaller weight
- Prose max-width: reduce from 100ch to 80ch for narrower, paper-like column
- Paragraph spacing: more generous (matching paper conventions)

**2. Theorem environment styling**
- Theorem headings (`div[class$=_thmheading]`): italic label style (e.g., *Theorem 1.2.1*)
- Theorem content (`div[class$=_thmcontent]`): italic body (standard math paper convention for theorem statements)
- Definition content: roman (upright) body

**3. Simplified proof toggle (scoped to `.chapter-page`)**
- Strip the modern button styling (background, border, border-radius, padding)
- Replace chevron indicator with plain text `[show]`/`[hide]` via CSS `::before` pseudo-elements
- Toggle text: underlined, black (not link-colored), matching issue spec
- Override `transform: rotate` so text doesn't flip

### File: `toolchain/dress-blueprint-action/assets/common.css`

No changes. Proof toggle base styles remain for Verso and other contexts.

### Preserved elements (explicitly NOT changed)
- Status indicator dots (colors, positioning, sizing)
- Lean code panels (monospace font, syntax highlighting)
- Sidebar navigation and chapter panel
- SBS grid layout (100ch + 100ch columns)
- KaTeX math rendering
- Dark mode variables for colors

### Dark mode support
- Scoped dark mode overrides for `.chapter-page` typography
- Proof toggle text stays readable in dark mode (use `var(--sbs-text)` instead of hardcoded black)

## Wave Structure

**Single wave** - one `sbs-developer` agent:
1. Add paper-like typography section to `blueprint.css`
2. Add scoped proof toggle overrides to `blueprint.css`
3. Add dark mode overrides for new styles
4. Build SBS-Test and GCR
5. Capture before/after screenshots

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  quality:
    T5: ">= current"
    T6: ">= current"
  regression: ">= 0"
```

## Validation

1. Build SBS-Test: `./dev/build-sbs-test.sh`
2. Build GCR: `./dev/build-gcr.sh`
3. Capture screenshots: `python3 -m sbs capture --project SBSTest --interactive` and same for GCR
4. Run evergreen tests: `pytest sbs/tests/pytest -m evergreen --tb=short`
5. Run T5/T6 validators: `sbs_validate_project(project="SBSTest")` and `sbs_validate_project(project="GCR")`
6. Visual comparison of chapter pages (serif, justified, paper feel)
7. Visual comparison of paper_tex pages (should look consistent)
8. Verify status dots unchanged
9. Verify proof toggle shows `[show]`/`[hide]` text on chapter pages
10. Verify dark mode works for new styles

## Files Modified
- `toolchain/dress-blueprint-action/assets/blueprint.css`
