# Task #55: Remove pdf_verso from Active Surfaces

## Objective
Disable `pdf_verso` from all user-facing surfaces (sidebar, compliance framework) while preserving the underlying Lean infrastructure for future use.

## Scope
- **Remove from**: Sidebar navigation, compliance/capture framework, documentation
- **Preserve**: Lean code in Theme.lean (`renderVersoPdfPage`), Main.lean build logic, `AvailableDocuments.paperPdfVerso` field
- **MVP.md**: No changes needed (no pdf_verso references found)

## Wave 1: Lean Sidebar Removal (Runway)

### Files Modified
- `toolchain/Runway/Runway/Theme.lean`
  - **Line 146**: Remove `versoPaperPdf` doc item creation
  - **Line ~160-170** (sidebar items list): Remove `versoPaperPdf` from the rendered sidebar items array
  - **Line 78**: Keep `| some "pdf_verso" => false` in `isBlueprintPage` (defensive, costs nothing)
  - Keep `renderVersoPdfPage` function untouched (disable-only)

### Verification
- `lean_diagnostic_messages` on Theme.lean — no errors
- Build SBS-Test — sidebar should not show "Paper_pdf [Verso]"

## Wave 2: Python Compliance Cleanup

### Files Modified
- `dev/scripts/sbs/tests/compliance/mapping.py`
  - Remove `"pdf_verso"` from `ALL_PAGES` list (line ~93)

- `dev/scripts/sbs/tests/compliance/capture.py`
  - Remove `pdf_verso` entry from `DEFAULT_PAGES` list (line ~38)
  - Remove `"pdf_verso"` from `exclude_patterns` in `find_chapter_page` (line ~63)

- `dev/scripts/sbs/tests/compliance/criteria.py`
  - Remove `"pdf_verso"` entry from `PAGE_CRITERIA` dict (line ~566)

### Verification
- `sbs_run_tests(tier="evergreen")` — all pass
- `sbs capture --project SBSTest` — no pdf_verso in output

## Wave 3: Documentation Updates

### Files Modified
- `CLAUDE.md` — Update "Known Limitations" section (line ~339)
- `.claude/agents/sbs-developer.md` — Remove pdf_verso from page type list, update limitation notes
- `.claude/agents/sbs-oracle.md` — Update limitation notes
- `dev/.refs/ARCHITECTURE.md` — Remove from page type table
- `dev/markdowns/permanent/GOALS.md` — Update known limitations
- `dev/storage/README.md` — Remove from page types table
- `dev/storage/COMPLIANCE_STATUS.md` — Remove pdf_verso row

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  quality:
    T5: >= current  # No regression
    T6: >= current  # No regression
  regression: >= 0
  visual:
    - SBS-Test sidebar: pdf_verso item absent
    - GCR sidebar: pdf_verso item absent
    - Both projects build successfully
```

## Verification Plan
1. Build SBS-Test — clean build, no pdf_verso in sidebar
2. Build GCR — clean build, no pdf_verso in sidebar
3. Screenshot comparison (before/after) for both projects
4. Evergreen tests pass
5. No Lean compilation errors in Runway
