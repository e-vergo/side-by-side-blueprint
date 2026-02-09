# Sidebar Styling Fixes - Issue #208

**Issue:** #208
**Scope:** Fix 4 related sidebar styling issues via CSS changes
**Files:** `common.css` (3 sections), `blueprint.css` (1 section)
**Strategy:** Single-wave CSS-only fixes

---

## Problem Summary

1. **Color mismatch** - Active sidebar item background doesn't match content area (breaks "contiguous tab" effect)
2. **Text wrapping** - Long navigation labels wrap to multiple lines
3. **Spacing inconsistencies** - Uneven padding across sidebar items
4. **Visual hierarchy** - Active state hard to distinguish (will be fixed by #1)

---

## Implementation

### File 1: `toolchain/dress-blueprint-action/assets/common.css`

**Change 1: Line 118 (Light Mode Color Variable)**
```css
/* BEFORE */
--sidebar-active-bg: var(--sbs-bg-surface);

/* AFTER */
--sidebar-active-bg: var(--sbs-bg-page);
```

**Change 2: Line 314 (Dark Mode Color Variable)**
```css
/* BEFORE */
--sidebar-active-bg: var(--sbs-bg-surface);

/* AFTER */
--sidebar-active-bg: var(--sbs-bg-page);
```

**Change 3: Line 1107 (Chapter Item Padding & Truncation)**
```css
/* BEFORE */
padding: 0.3rem 0.8rem 0.3rem 1.8rem;

/* AFTER */
padding: 0.35rem 0.8rem 0.35rem 1.8rem;
white-space: nowrap;
overflow: hidden;
text-overflow: ellipsis;
```

Add after line 1111 (after `transition` property):
```css
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
```

---

### File 2: `toolchain/dress-blueprint-action/assets/blueprint.css`

**Change 4: Line 178 (Sidebar Item - Minified)**

Current (single line):
```css
.toc ul .sidebar-item{display:inline-block;max-width:90%;padding-top:.35rem;padding-right:.5rem;padding-bottom:.35rem;transition:all .1s ease;text-align:left;text-decoration:none;font-size:0.9375rem;line-height:1.5;color:#fff;flex-grow:1}
```

Replace with:
```css
.toc ul .sidebar-item{display:inline-block;padding:.35rem .8rem;transition:all .1s ease;text-align:left;text-decoration:none;font-size:0.9375rem;line-height:1.5;color:#fff;flex-grow:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
```

Changes:
- Removed `max-width:90%;`
- Changed `padding-top:.35rem;padding-right:.5rem;padding-bottom:.35rem;` to `padding:.35rem .8rem;`
- Added `white-space:nowrap;overflow:hidden;text-overflow:ellipsis`

---

## Validation

### Manual Testing
1. **Build:** `./dev/build-sbs-test.sh`
2. **Serve:** `cd toolchain/SBS-Test && python3 -m http.server 8000 -d _site`
3. **Visual checks:**
   - Active item background matches content area (both themes)
   - Long labels show ellipsis instead of wrapping
   - Consistent padding across all sidebar items
   - Active state clearly visible

### Screenshot Validation
```bash
cd dev/scripts
python3 -m sbs capture --project SBSTest --interactive
```

Check:
- Light mode: dashboard, chapter, dep_graph pages
- Dark mode: same pages
- Interactive states: hover, active

### Automated Tests
```bash
# Evergreen suite
pytest dev/scripts/sbs/tests/pytest -m evergreen --tb=short

# CSS variable test
python3 -m sbs validate --project SBSTest --validators T6
```

---

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  validation:
    - Visual compliance (before/after screenshots)
    - Interactive state testing (hover, active work correctly)
    - Both themes tested (light and dark mode)
    - T6 CSS variable coverage
  quality:
    T6: >= 0.9
  regression: >= 0
```

---

## Critical Files

- `/Users/eric/GitHub/Side-By-Side-Blueprint/toolchain/dress-blueprint-action/assets/common.css`
  Lines 118, 314, 1107-1111

- `/Users/eric/GitHub/Side-By-Side-Blueprint/toolchain/dress-blueprint-action/assets/blueprint.css`
  Line 178

---

## Execution

**Single agent, sequential changes:**
1. Edit `common.css` (lines 118, 314, 1107-1111)
2. Edit `blueprint.css` (line 178)
3. Build SBSTest
4. Visual verification
5. Screenshot capture & comparison
6. Run validation gates

**Total changes:** 2 files, ~8 lines modified
