# Plan: Fix Sidebar Disabled Item Font-Size Alignment

**Issue:** #2 - Sidebar disabled items have misaligned text due to font-size change

## Problem

In `blueprint.css`, the sidebar item styling targets `.toc ul a` which sets `font-size: 1.125rem`. However, disabled items are rendered as `<span class="sidebar-item disabled">` instead of `<a class="sidebar-item">`. The span doesn't match the `a` selector, so it inherits a smaller default font-size.

## Solution

Change selectors from targeting `a` elements to targeting the `.sidebar-item` class, which both enabled and disabled items share.

## Changes

**File:** `toolchain/dress-blueprint-action/assets/blueprint.css`

| Line | Current | New |
|------|---------|-----|
| 178 | `.toc ul a` | `.toc ul .sidebar-item` |
| 188 | `.sub-toc-0 a` | `.sub-toc-0 .sidebar-item` |
| 189 | `.sub-toc-1 a` | `.sub-toc-1 .sidebar-item` |
| 190 | `.sub-toc-2 a` | `.sub-toc-2 .sidebar-item` |
| 191 | `.sub-toc-3 a` | `.sub-toc-3 .sidebar-item` |
| 192 | `.sub-toc-4 a` | `.sub-toc-4 .sidebar-item` |

## Gates

```yaml
gates:
  tests: all_pass
  regression: >= 0
```

## Execution

1. **Wave 1:** CSS edit in `blueprint.css` (6 selector changes)
2. **Wave 2:** Build SBSTest project
3. **Wave 3:** Capture before/after screenshots, verify alignment

## Verification

1. Build SBSTest: `python ../../dev/scripts/build.py`
2. Capture screenshots: `python3 -m sbs capture --project SBSTest`
3. Visual inspection: Disabled "Paper_pdf [Verso]" item should align with adjacent items
4. Run tests: `python3 -m sbs.tests.pytest` (ensure no regressions)
