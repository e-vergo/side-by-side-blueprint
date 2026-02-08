# Task: MVP Sync + Verso Surface Removal + Implementation Fixes

**Issues:** #68 (design language consistency), #109 (desktop-only + verso removal)

## Scope Summary

1. **MVP.md rewrite** -- align document with reality (desktop-only, drop verso/filter claims, fix theme claim, add #68 items)
2. **Verso surface removal** -- sidebar, compliance, tests, docs
3. **System theme preference** -- `prefers-color-scheme` fallback in JS + CSS
4. **Verification badges** -- investigate why existing Lean code isn't rendering badges in paper HTML
5. **No horizontal scrollbars** -- side-by-side content must fit viewport width, never overflow
6. **Hover popup styling** -- limit max-width of Lean hover tooltips, match design language
7. **Design language audit** -- visual pass to fix color mismatches, link styling artifacts, etc.
8. **CLAUDE.md fix** -- correct known limitations section

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  quality:
    T5: >= 1.0
    T6: >= 0.9
  regression: >= 0
```

## Wave Structure

### Wave 1: Documentation + Verso Removal (2 parallel agents)

**Agent 1A: MVP.md + CLAUDE.md updates**
- Files: `dev/markdowns/living/MVP.md`, `CLAUDE.md`
- Changes to MVP.md:
  - Section 2 (Dual Authoring): Reframe Verso as future capability, TeX as primary MVP mode
  - Section 3 (Dependency Graph): Remove "filter controls" -- keep "pan, zoom, and fit controls"
  - Visual Standards: Replace "responsive layout for various screen sizes" with "desktop/landscape layout"
  - Visual Standards: Replace "system preference detection" with "manual dark/light toggle with system preference fallback"
  - Add new section for #68: "Interactive Components & Design Consistency" covering toggles, modals, navigation, design language
  - Add explicit requirement: **no horizontal scrollbars** -- all content (especially side-by-side displays) must fit within the viewport width
  - Add explicit requirement: **hover tooltips must be bounded** -- max-width constraint, consistent styling with overall design language
  - Success Criteria: Update criterion 2 (both authoring modes) to reflect TeX-primary
  - Add to "What MVP Does NOT Include": mobile/responsive layout, verso-native document generation (future)
- Changes to CLAUDE.md:
  - Known Limitations > Verso LaTeX Export: Clarify that `paper_verso`, `blueprint_verso`, and `pdf_verso` are all removed from active surfaces (not just `pdf_verso`)
  - Update sidebar description if it references verso

**Agent 1B: Verso removal from code**
- Files (all in `dev/scripts/sbs/`):
  - `tests/compliance/mapping.py`: Remove `"verso"` from REPO_PAGE_MAPPING (line 39), REPO_VALIDATOR_MAPPING (line 64), and `paper_verso`/`blueprint_verso` from ALL_PAGES (lines 93-94)
  - `tests/compliance/criteria.py`: Delete PAPER_VERSO_CRITERIA (lines 372-390), BLUEPRINT_VERSO_CRITERIA (lines 393-434), remove from PAGE_CRITERIA dict (lines 565-566)
  - `tests/compliance/capture.py`: Remove verso from DEFAULT_PAGES (lines 37-38), exclude_patterns (lines 61-62), starting_pages (line 69)
  - `tests/validators/design/toggle_discoverability.py`: Remove `blueprint_verso` from DEFAULT_PAGES (line 98)
  - `tests/validators/design/jarring_check.py`: Remove `blueprint_verso` from DEFAULT_PAGES (line 84)
  - `tests/validators/design/professional_score.py`: Remove `blueprint_verso` from DEFAULT_PAGES (line 95)

### Wave 2: Sidebar + Theme (2 parallel agents)

**Agent 2A: Remove verso from sidebar (Lean)**
- File: `toolchain/Runway/Runway/Theme.lean`
- Change: Remove the verso section from the `navItems` array (line 198):
  - Delete: `++ #[sectionHeader "Verso", separator, versoBlueprint, versoPaperRow]`
  - Keep the variable definitions (lines 168-171) but unused -- or delete them too for cleanliness
- Also remove the TeX section header label since there's no longer a distinction needed:
  - Change `sectionHeader "TeX"` to just remove the section header, OR keep it if the user wants explicit "TeX" labeling
- Verify: `lean_diagnostic_messages` after edit to confirm no compilation errors

**Agent 2B: System theme preference detection**
- File: `toolchain/dress-blueprint-action/assets/plastex.js`
  - Replace `getPreferredTheme()` (lines 3-11) to check `window.matchMedia('(prefers-color-scheme: dark)')` when no localStorage preference exists
  - Add `matchMedia` change listener (after line 38) that applies system preference changes only when no saved preference
- File: `toolchain/dress-blueprint-action/assets/common.css`
  - Add `@media (prefers-color-scheme: dark) { html:not([data-theme]) { ... } }` block reusing existing dark mode variable definitions as fallback for initial page load before JS runs

### Wave 3: Badges Investigation + Design Language (2 parallel agents)

**Agent 3A: Verification badge investigation**
- Paper.lean already has `renderBadge` (line 72-82), `VerificationLevel` (lines 49-63), and badge insertion in `renderStatement` (line 134)
- **Investigation needed:** Why aren't badges appearing in generated paper HTML?
  - Check if `\paperstatement` LaTeX command actually calls `renderStatement` during HTML generation
  - Check if the paper generation path uses `PaperNodeInfo` with populated status
  - Check if the manifest/artifacts HashMap is being passed correctly to `blockToHtmlString`
  - Build SBS-Test and inspect `paper_tex.html` for `.verification-badge` elements
- If code path is broken: fix the plumbing (likely in `blockToHtmlString` or `replacePlaceholders`)
- If code works but CSS isn't rendering: fix CSS in `paper.css` or `common.css`

**Agent 3B: Design language consistency + overflow fixes**
- Build SBS-Test, capture screenshots with `sbs capture --project SBSTest --interactive`
- **Priority fix 1: No horizontal scrollbars**
  - Side-by-side displays (`.decl-container`, `.sbs-display`, or similar) must not overflow viewport
  - Investigate CSS causing horizontal overflow -- likely fixed-width columns or `pre` blocks without `overflow-wrap`
  - Fix: ensure `max-width: 100%`, `overflow-x: auto` on code blocks (not the page), `word-break: break-word` where needed
  - Apply to chapter pages and any page with side-by-side content
- **Priority fix 2: Hover tooltip max-width**
  - Lean hover tooltips (Tippy.js, `.tippy-box` or `.lean-hover`) are unbounded in width
  - Fix: add `max-width` constraint (e.g., `max-width: 600px` or `max-width: 50vw`)
  - Ensure long type signatures wrap properly within the tooltip
  - Match tooltip styling (border, background, font) to overall design language
  - Files: likely `common.css` or `verso-code.js` (Tippy.js config) in `dress-blueprint-action/assets/`
- **Visual audit:**
  - Color mismatches (elements that should use CSS variables but don't)
  - Link styling artifacts (hooks/serifs on links in key declarations)
  - Inconsistent spacing, font sizes, or padding between page types
- Fix identified issues in `common.css`, `blueprint.css`, `paper.css`
- Re-capture and verify fixes

### Wave 4: Build + Validate

- Build SBS-Test: `python build.py`
- Capture screenshots: `sbs capture --project SBSTest --interactive`
- Run evergreen tests: `sbs_run_tests(tier="evergreen")`
- Run validators: `sbs_validate_project("SBSTest", ["T5", "T6"])`
- Verify: no verso in sidebar screenshots, badges in paper, theme respects system preference

## Files Modified (by repo)

| Repo | Files | Agent |
|------|-------|-------|
| Side-By-Side-Blueprint (main) | `dev/markdowns/living/MVP.md`, `CLAUDE.md` | 1A |
| Side-By-Side-Blueprint (scripts) | 6 files in `dev/scripts/sbs/tests/` | 1B |
| Runway | `Runway/Theme.lean` | 2A |
| Runway | `Runway/Paper.lean` (if fix needed) | 3A |
| dress-blueprint-action | `assets/plastex.js`, `assets/common.css` | 2B, 3B |

No file overlaps between parallel agents within a wave.

## Verification

1. **Verso removed:** Sidebar screenshots show no "Verso" section
2. **Theme preference:** Open site with system dark mode → should render dark without manual toggle
3. **Badges:** `paper_tex.html` contains `.verification-badge` elements with correct status classes
4. **No horizontal scrollbars:** All pages render without horizontal overflow at desktop width
5. **Hover tooltips:** Lean hovers are bounded in width, text wraps cleanly
6. **Design consistency:** Visual audit confirms no color mismatches or styling artifacts
7. **Tests pass:** Evergreen tier at 100%
6. **T5 >= 1.0, T6 >= 0.9:** Quality validators pass gates
