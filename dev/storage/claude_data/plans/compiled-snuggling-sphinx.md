# Task: Sidebar Restructure + Contrast Fix (#69, #70)

## Root Cause Analysis (#69)

**Specificity bug:** `blueprint.css:178` sets `.toc ul .sidebar-item { color: #fff }` at specificity (0,2,1). `common.css:917` sets `.sidebar-item.active { color: var(--sidebar-active-text) }` at specificity (0,2,0). The white color wins, making active items invisible in light mode where the active background is white.

**Fix:** Change `.sidebar-item.active` to `.toc .sidebar-item.active` (specificity 0,3,0).

## Files to Modify

| File | Repo | Changes |
|------|------|---------|
| `toolchain/Runway/Runway/Theme.lean` | Runway | Restructure `renderSidebar` (lines 103-181) |
| `toolchain/Runway/Runway/Config.lean` | Runway | Add `faqUrl`, `zulipUrl` optional fields |
| `toolchain/dress-blueprint-action/assets/common.css` | dress-blueprint-action | Fix contrast specificity, add external links row styles, Paper inline link styles |

## Implementation

### Wave 1: All changes (single agent)

#### 1. Config.lean - Add URL fields

Add to `Config` structure:
```lean
faqUrl : Option String := some "https://leanprover-community.github.io/blueprint/faq.html"
zulipUrl : Option String := some "https://leanprover.zulipchat.com/"
```

Add to `ToJson`/`FromJson` instances (same pattern as `githubUrl`/`docgen4Url`).

#### 2. Theme.lean - Restructure renderSidebar

Replace the `renderSidebar` function body (lines 103-181) with new layout:

**New structure:**
```
<nav class="toc">
  <ul class="sub-toc-0">
    <li class="sidebar-top-spacer"></li>     <!-- breathing room -->
    <li><a class="sidebar-item [active]">Dashboard</a></li>
    <li><a class="sidebar-item [active]">Dependency Graph</a></li>
    <li class="sidebar-top-spacer"></li>     <!-- breathing room -->

    <li class="nav-section-header">TeX</li>  <!-- existing CSS class -->
    <li class="nav-separator"></li>           <!-- existing divider -->
    <li><a class="sidebar-item">Blueprint</a></li>
    <li class="sidebar-doc-row">             <!-- new: inline links row -->
      <span class="sidebar-item-label">Paper</span>
      <a class="sidebar-doc-link [disabled]">[web]</a>
      <a class="sidebar-doc-link [disabled]">[pdf]</a>
    </li>

    <li class="nav-section-header">Verso</li>
    <li class="nav-separator"></li>
    <li><a class="sidebar-item">Blueprint</a></li>
    <li class="sidebar-doc-row">
      <span class="sidebar-item-label">Paper</span>
      <a class="sidebar-doc-link [disabled]">[web]</a>
    </li>

    <li class="sidebar-spacer"></li>         <!-- flex grow -->
  </ul>

  <div class="theme-toggle">...</div>
  <div class="sidebar-external-links">       <!-- new: bottom links row -->
    <a href="..." target="_blank">GH</a>
    <a href="..." target="_blank">API</a>
    <a href="..." target="_blank">FAQ</a>
    <a href="..." target="_blank">Zulip</a>
  </div>
</nav>
```

Key changes to `renderSidebar`:
- Add `sidebar-top-spacer` items for breathing room
- Add `nav-section-header` items for "TEX" and "VERSO" labels (CSS class already exists in common.css:951-966)
- Blueprint items come before Paper items in each section
- Paper uses new `sidebar-doc-row` with inline `[web]`/`[pdf]` links
- External links move to a new `sidebar-external-links` div after theme toggle
- Add FAQ and Zulip links using config fields (with hardcoded defaults)

#### 3. common.css - Fix contrast + new styles

**Contrast fix (line 916):**
```css
/* Change selector from: */
.sidebar-item.active {
/* To: */
.toc .sidebar-item.active {
```
Also update the `::before` pseudo-element selector to `.toc .sidebar-item.active::before`.

**New styles to add:**

```css
/* Top spacer for breathing room */
.sidebar-top-spacer {
  height: 0.5rem;
  pointer-events: none;
}

/* Paper inline links row */
.sidebar-doc-row {
  display: flex;
  align-items: center;
  padding: 0.35rem 0.8rem;
  gap: 0.35rem;
}

.sidebar-item-label {
  color: #fff;
  font-size: 0.875rem;
}

.sidebar-doc-link {
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.8rem;
  text-decoration: none;
}

.sidebar-doc-link:hover {
  color: #fff;
}

.sidebar-doc-link.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

/* External links row at bottom */
.sidebar-external-links {
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  padding: 0.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}

.sidebar-external-links a {
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.75rem;
  text-decoration: none;
}

.sidebar-external-links a:hover {
  color: #fff;
}
```

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  quality:
    T5: >= 0.8
    T6: >= 0.9
  regression: >= 0
```

## Verification

1. Build SBS-Test: `python ../../dev/scripts/build.py` from SBS-Test dir
2. Capture screenshots: `python3 -m sbs capture --project SBSTest --interactive`
3. Visual check: Light mode active item contrast is readable
4. Visual check: Sidebar layout matches agreed structure
5. Visual check: Grey-out works for unavailable Verso documents
6. Visual check: External links row renders at bottom with all 4 links
7. Run evergreen tests: `sbs_run_tests(tier="evergreen")`
8. Run validators: `sbs_validate_project("SBSTest")`
