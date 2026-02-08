# Plan: SBS Visual Alignment + Toggle Removal (#230)

## Summary

Four changes to the side-by-side view: remove the Lean column toggle, and fix three vertical alignment issues between the LaTeX and Lean columns.

## Files Modified

| File | Changes |
|------|---------|
| `toolchain/dress-blueprint-action/assets/plastex.js` | Remove toggle JS (lines 118-150) |
| `toolchain/dress-blueprint-action/assets/common.css` | Remove toggle CSS (lines 483-495) |
| `toolchain/dress-blueprint-action/assets/blueprint.css` | Add alignment padding |

## Changes

### 1. Remove Lean column toggle (issue #230)

**JS (`plastex.js`):** Delete the entire "SBS container expand/collapse toggle" block (lines 118-150). This removes:
- The `sbs-toggle-indicator` chevron injection
- The `sbs-expanded` / `sbs-collapsed` class toggling
- The `cursor: pointer` on headings
- The `slideUp`/`slideDown` on `.sbs-lean-column`

**CSS (`common.css`):** Delete lines 483-495:
- `.sbs-toggle-indicator` styles
- `.sbs-collapsed .sbs-toggle-indicator` rotation

### 2. Proof content spacing (LaTeX side)

**CSS (`common.css`):** Reduce `.proof_content` margin-top from `0.5rem` to `0.25rem` (line 413). This equalizes the gap above and below `[hide]`.

### 3. Lean declaration alignment

**CSS (`blueprint.css`):** Add `padding-top: 0.35rem` to `.sbs-lean-column pre.lean-code` to nudge the Lean declaration code down so its first line aligns with the LaTeX statement text.

### 4. Lean proof body alignment

**CSS (`common.css`):** Add `margin-top: 0.25rem` to `.lean-proof-body` (line 434) so the Lean proof body text aligns with the LaTeX proof content below `[hide]`.

## Verification

1. Build SBS-Test: `sbs_build_project(project="SBSTest")`
2. Serve and screenshot before/after for visual comparison
3. Specifically verify:
   - No toggle chevron on theorem headers
   - Heading is NOT clickable (no cursor change)
   - Lean declaration first line aligns with LaTeX statement first line
   - Lean proof body first line aligns with LaTeX proof body first line
   - Equal gap above and below `[hide]`
4. Run evergreen tests: `sbs_run_tests(tier="evergreen")`

## Notes

- Padding/margin values (0.35rem, 0.25rem) are initial estimates. Visual verification will confirm or require fine-tuning.
- The proof body toggle (lines 69-85 in plastex.js) is NOT touched -- that functionality is kept.
