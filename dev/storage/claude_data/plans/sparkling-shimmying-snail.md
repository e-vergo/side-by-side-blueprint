# Plan: Fix Lean Code Overflow in Blueprint View

**Issue:** #3 - Lean code overflows container in blueprint view
**Approach:** Option A - Allow horizontal scrolling within the Lean column

## Problem Summary

The `.sbs-lean-column` uses `white-space: pre-wrap` with `word-wrap: break-word`, but long Lean tokens (identifiers, type signatures) don't break naturally, causing overflow outside the container.

## Solution

Change from wrapping to horizontal scrolling:
1. Use `white-space: pre` (no wrapping) instead of `pre-wrap`
2. Ensure `overflow-x: auto` creates scrollbar within the column bounds
3. Add `max-width: 100%` to constrain to grid cell

## Files to Modify

### Primary: `toolchain/dress-blueprint-action/assets/blueprint.css`

**Lines 243-259** - Modify `.sbs-lean-column` and `.sbs-lean-column pre.lean-code`:

```css
.sbs-lean-column {
  min-width: 0;
  max-width: 100%;           /* ADD: Constrain to grid cell */
  overflow-x: auto;          /* KEEP: Horizontal scroll */
  overflow-wrap: normal;     /* CHANGE: Don't break words */
  word-wrap: normal;         /* CHANGE: Don't break words */
  position: relative;
}

.sbs-lean-column pre.lean-code {
  margin: 0;
  padding: 0;
  background: transparent;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.85rem;
  line-height: 1.5;
  white-space: pre;          /* CHANGE: from pre-wrap */
  /* REMOVE: word-wrap: break-word */
}
```

### Secondary: `toolchain/dress-blueprint-action/assets/common.css`

**Lines 336-339** - Verify/update base `.sbs-lean-column`:

```css
.sbs-lean-column {
  min-width: 0;
  max-width: 100%;           /* ADD if not present */
  overflow-x: auto;
}
```

## Execution Steps

1. **Edit CSS** - Apply changes to `blueprint.css` (primary fix)
2. **Build SBS-Test** - Run `./dev/build-sbs-test.sh`
3. **Verify SBS-Test** - Check built site for overflow fix
4. **Build GCR** - Run `./dev/build-gcr.sh`
5. **Verify GCR** - Confirm fix works on production-like project
6. **Commit** - Commit to feature branch

## Validation

### Gates
```yaml
gates:
  tests: all_pass
  quality:
    T6: >= 0.9   # CSS variable coverage (shouldn't regress)
  regression: >= 0
```

### Manual Verification
1. Open SBS-Test chapter page in browser
2. Find a theorem with long Lean code
3. Verify horizontal scrollbar appears within Lean column
4. Verify no content overflows container bounds
5. Repeat for GCR

### Automated Validation
```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs validate-project --project SBSTest --validators T5,T6
python3 -m sbs validate-project --project GCR --validators T5,T6
```

## Risk Assessment

**Low risk** - This is a CSS-only change affecting layout behavior:
- No Lean code changes
- No build pipeline changes
- Easy to revert if issues arise
- Limited scope: only affects `.sbs-lean-column` overflow behavior

## Notes

- Playwright not available for automated screenshots, will rely on manual browser verification
- The fix should be universal (affects all projects using the shared CSS)
