# Task #119: MVP Test Suite Expansion

## Objective

Expand the test suite by ~102 new tests, each mapped directly to one of the 10 MVP success criteria. All new tests are `@pytest.mark.evergreen`, deterministic, and read-only against existing build artifacts. Phase 1: SBS-Test only.

## Baseline

- **Evergreen:** 629/629 (100%)
- **MVP tests:** 200 existing (structural checks -- element existence, file size, CSS containment)
- **Gap:** Tests verify "does it exist?" but not "is it correct?"
- **New tests add:** content correctness, link resolution, data accuracy, cross-page consistency

## MVP Criteria → Test File Mapping

| MVP Criterion | Test File | New Tests |
|---------------|-----------|-----------|
| 1. Side-by-side works | `test_sbs_content.py` | 18 |
| 3. Dependency graph works + 9. Interactive components | `test_graph_navigation.py` | 18 |
| 5. Dashboard works | `test_dashboard_accuracy.py` | 16 |
| 6. Paper generation works | `test_paper_quality.py` | 14 |
| 9. Theme toggle + 10. Design consistency | `test_theme_and_dark_mode.py` | 16 |
| 8. Visual quality + 10. Design consistency | `test_cross_page_consistency.py` | 20 |
| **Total** | **6 files** | **102** |

## Verified Data Structures

Manually reviewed from actual SBS-Test build artifacts.

**manifest.json:** `{stats, projectNotes, nodes, messages, keyDeclarations, checks}`
- `nodes`: `dict[str, str]` -- values are `"#node_id"`
- `keyDeclarations`: `list[str]` (can contain colons: `"bracket:deep"`)
- `messages`: `list[{message, label, id}]`

**dep-graph.json:** `{width, height, nodes: list, edges: list}`
- Nodes: 18 fields all always present (`id, status, label, url, x, y, width, height, envType, moduleName, leanDecls, keyDeclaration, message, blocked, technicalDebt, potentialIssue, misc, priorityItem`)
- Edges: `{from, to, points}`

**HTML IDs:** Underscores matching node IDs (`id="proven_leaf"`). Bracket nodes use colons in manifest (`bracket:complex`).

**CSS:** Dark mode via `html[data-theme="dark"]` in common.css. ~45 root vars, ~30 have dark overrides. Status colors intentionally constant across themes.

**Theme toggle:** `plastex.js` sets `document.documentElement.setAttribute('data-theme', 'dark')`, persists via `localStorage('sbs-theme')`.

---

## New Test Files

### 1. `test_sbs_content.py` (~18 tests) -- MVP Criteria 1, 2

Side-by-side display has real content, not just containers.

**`TestSideBySideContent`** (8):
- `test_latex_columns_have_math_content`: every `.sbs-latex-column` contains math (`$`, `\(`, or MathJax span)
- `test_lean_columns_have_code`: every `.sbs-lean-column` has `pre.lean-code` with actual code text
- `test_lean_code_has_keywords`: code blocks contain at least one of `theorem|def|lemma|example|instance`
- `test_hover_data_is_valid_json`: `data-lean-hovers` attributes parse as valid JSON dicts
- `test_hover_data_has_entries`: hover JSON dicts have `>= 1` entry (not empty `{}`)
- `test_proof_content_not_empty`: `.proof_content` elements have text > 10 chars
- `test_latex_statements_not_empty`: `.theorem_thmcontent` paragraphs have text > 10 chars
- `test_sbs_containers_have_both_columns`: every `.sbs-container` has both `.sbs-latex-column` and `.sbs-lean-column`

**`TestDeclarationArtifactContent`** (6):
- `test_every_node_has_decl_html`: for each manifest node, `decl.html` exists in dressed/ tree and > 50 bytes
- `test_every_node_has_decl_json`: `decl.json` present for every node
- `test_every_node_has_decl_tex`: `decl.tex` present, > 10 bytes
- `test_every_node_has_hovers_json`: `decl.hovers.json` present
- `test_decl_json_has_name`: `"name"` key with non-empty string
- `test_decl_json_has_highlighting`: `"highlighting"` key with `"seq"` sub-key

**`TestChapterContent`** (4):
- `test_chapter_pages_have_substantial_text`: each chapter page > 500 chars visible text
- `test_chapter_pages_have_theorem_wrappers`: each chapter page has `.theorem_thmwrapper` elements
- `test_tex_generates_multiple_chapters`: at least 3 chapter pages generated
- `test_sbs_container_count_reasonable`: total sbs-containers across chapters >= `stats["total"] / 2` (not every node has LaTeX)

### 2. `test_graph_navigation.py` (~18 tests) -- MVP Criteria 3, 9

Graph nodes link to real pages, modals have content, controls work.

**`TestGraphNodeNavigation`** (7):
- `test_node_urls_are_fragment_links`: every `node["url"]` starts with `#`
- `test_node_urls_resolve_to_page_ids`: for each `node["url"]` `#X`, ID `X` exists as `id=` attribute on some chapter page
- `test_all_manifest_nodes_have_page_anchor`: every manifest node key maps to an `id=` on a chapter page
- `test_graph_and_manifest_nodes_match`: `set(graph node IDs) == set(manifest node keys)`
- `test_no_duplicate_ids_in_chapters`: each chapter page has unique `id` attribute values
- `test_edges_reference_valid_nodes`: every edge `from`/`to` is a valid node ID
- `test_clickable_nodes_have_urls`: every node has non-empty `url` field

**`TestGraphModals`** (5) -- "Graph node modals with status, statement, and proof details":
- `test_modal_container_in_dep_graph`: dep_graph.html has modal container element
- `test_graph_nodes_have_status`: every node has `status` in `{notReady, ready, sorry, proven, fullyProven, mathlibReady}`
- `test_graph_nodes_have_label`: every node has non-empty `label`
- `test_graph_nodes_have_env_type`: every node has non-empty `envType`
- `test_graph_nodes_carry_lean_decls`: every node has `leanDecls` with `>= 1` entry

**`TestGraphControls`** (6) -- "Pan, zoom, and fit controls":
- `test_pan_zoom_controls_present`: dep_graph.html has zoom/pan control elements
- `test_fit_to_window_available`: "fitToWindow" or "fit" in dep_graph page
- `test_graph_svg_or_container_present`: SVG element or `.graph-container` exists
- `test_graph_dimensions_positive`: `width > 0`, `height > 0` in dep-graph.json
- `test_node_coordinates_non_negative`: all nodes `x >= 0`, `y >= 0`
- `test_node_dimensions_positive`: all nodes `width > 0`, `height > 0`

### 3. `test_dashboard_accuracy.py` (~16 tests) -- MVP Criterion 5

Dashboard stats are accurate, key declarations valid, navigation works.

**`TestDashboardStats`** (6) -- "Aggregate statistics (proven/total, sorry count, etc.)":
- `test_stats_total_displayed`: `stats["total"]` value appears in dashboard HTML
- `test_stats_proven_count_displayed`: proven count appears in `.stats-value` elements
- `test_stats_sorry_count_displayed`: hasSorry count appears in dashboard
- `test_legend_has_all_status_types`: legend covers all 6 status type names
- `test_pie_chart_present`: SVG circle or `.stats-pie` element exists
- `test_stats_values_match_manifest`: all numeric `.stats-value` elements match a manifest stat value

**`TestKeyDeclarations`** (5) -- "Key theorems highlighted":
- `test_key_declarations_section_present`: `.key-declarations` section exists
- `test_key_declarations_listed`: at least 1 `.key-declaration-item` present
- `test_key_declarations_are_valid_nodes`: every `keyDeclarations[]` ID exists in `manifest["nodes"]`
- `test_key_declaration_items_have_links`: `.key-declaration-link` elements have `href`
- `test_key_declarations_have_preview`: `.key-declaration-preview` elements exist

**`TestDashboardNavigation`** (5) -- "Navigation to all sections":
- `test_sidebar_links_resolve`: all `href="./X.html"` in `nav.toc` map to existing runway/ files
- `test_dep_graph_link_present`: link to `dep_graph.html` in dashboard sidebar
- `test_all_chapter_pages_linked`: every chapter page has a corresponding sidebar link
- `test_navigation_link_count_matches`: sidebar chapter link count matches chapter page count
- `test_dashboard_links_to_paper`: link to `paper_tex.html` present (if paper exists)

### 4. `test_paper_quality.py` (~14 tests) -- MVP Criterion 6

Paper content, PDF validity, verification badges.

**`TestPaperContent`** (6) -- "ar5iv-style HTML rendering":
- `test_paper_has_math_content`: paper_tex.html contains math (`$`, `\(`, or MathJax rendered elements)
- `test_paper_has_multiple_sections`: paper has `> 1` heading (h2 or h3)
- `test_paper_has_substantial_text`: paper page > 2000 chars of content
- `test_paper_mathjax_loads`: MathJax script tag present
- `test_paper_title_present`: `h1` or `.paper-title` element with text
- `test_paper_has_theorem_environments`: paper has theorem-style elements

**`TestPdfValidity`** (4) -- "PDF generation via LaTeX":
- `test_pdf_has_valid_header`: `paper.pdf` starts with `%PDF-`
- `test_pdf_has_eof_marker`: `paper.pdf` contains `%%EOF`
- `test_pdf_minimum_size`: `paper.pdf` > 10KB (actual: ~127KB)
- `test_pdf_embed_page_references_file`: `pdf_tex.html` contains `"paper.pdf"`

**`TestVerificationBadges`** (4) -- "Verification badges showing formalization status":
- `test_paper_has_verification_indicators`: paper page has badge elements or "verified"/"progress" text
- `test_badge_css_variables_defined`: `--sbs-badge-verified-bg`, `--sbs-badge-progress-bg` etc. in common.css
- `test_badge_verified_and_progress_variants`: both verified and progress badge styles exist in CSS
- `test_badges_link_to_blueprint`: badge elements have `href` linking to blueprint chapter sections

### 5. `test_theme_and_dark_mode.py` (~16 tests) -- MVP Criteria 9, 10

"Manual dark/light theme toggle with system preference fallback"

**`TestThemeToggle`** (5):
- `test_theme_toggle_on_all_pages`: `.theme-toggle` present on every runway page
- `test_theme_toggle_js_sets_data_theme`: plastex.js contains `setAttribute('data-theme'` or `data-theme`
- `test_theme_persists_to_localstorage`: plastex.js references `localStorage` and `sbs-theme`
- `test_system_preference_fallback`: `prefers-color-scheme` in CSS or JS
- `test_pages_no_hardcoded_theme`: no page HTML has `data-theme=` in static source

**`TestDarkModeCSSCoverage`** (8):
- `test_dark_mode_block_exists`: `html[data-theme="dark"]` in common.css
- `test_dark_overrides_backgrounds`: `--sbs-bg-page` and `--sbs-bg-surface` overridden in dark block
- `test_dark_overrides_text`: `--sbs-text` and `--sbs-text-muted` overridden
- `test_dark_overrides_borders`: `--sbs-border` overridden
- `test_dark_overrides_links`: `--sbs-link` and `--sbs-link-hover` overridden
- `test_dark_overrides_heading`: `--sbs-heading` overridden
- `test_dark_overrides_accent`: `--sbs-accent` overridden
- `test_dark_overrides_graph_vars`: `--sbs-graph-bg`, `--sbs-graph-edge`, `--sbs-graph-edge-hover` overridden

**`TestDarkModeDesign`** (3):
- `test_status_colors_constant_across_themes`: `--sbs-status-*` NOT in dark block (intentionally constant)
- `test_prefers_color_scheme_media_fallback`: `@media (prefers-color-scheme: dark)` block in common.css
- `test_dark_mode_badge_vars_overridden`: `--sbs-badge-verified-bg` etc overridden in dark block

### 6. `test_cross_page_consistency.py` (~20 tests) -- MVP Criteria 8, 10

"No horizontal scrollbars", "cohesive design language", "design consistency across all page types"

**`TestNoHorizontalScrollbars`** (4) -- "all content must fit within viewport width":
- `test_css_overflow_handling`: CSS has `overflow-x: hidden` or `auto` or `overflow-wrap` on body/main
- `test_sbs_container_bounded_width`: `.sbs-container` has `max-width` or `width` constraint in CSS
- `test_code_blocks_overflow_wrap`: `pre` or `code` elements have `overflow-wrap`, `word-break`, or `overflow-x` in CSS
- `test_no_fixed_width_exceeding_viewport`: no CSS rule sets `width` to a fixed value > `100vw` or `1920px`

**`TestCrossPageUniformity`** (8) -- "Design language consistency across all page types":
- `test_all_pages_load_common_css`: every page references `common.css`
- `test_all_pages_have_theme_toggle`: `.theme-toggle` on every page
- `test_all_pages_have_sidebar_nav`: `nav.toc` or sidebar element on every page
- `test_all_pages_have_html_title`: every page has `<title>` with non-empty text
- `test_chapter_pages_share_layout_classes`: all chapter pages use consistent wrapper class names
- `test_all_pages_load_plastex_js`: every page references `plastex.js`
- `test_all_pages_have_header`: every page has `nav.header` or `.nav-wrapper`
- `test_consistent_page_structure`: every page has `<html>`, `<head>`, `<body>` in correct order

**`TestDesignLanguage`** (4) -- "unified colors, typography, spacing":
- `test_rainbow_brackets_six_colors`: `.lean-bracket-1` through `.lean-bracket-6` defined in CSS
- `test_monospace_font_for_code`: CSS specifies `monospace` font-family for `code` or `.lean-code`
- `test_status_dot_is_circle`: `.status-dot` has `border-radius` in CSS
- `test_heading_hierarchy_defined`: CSS defines distinct font-size for `h1`, `h2`, `h3`

**`TestBuildOutputComplete`** (4) -- all expected build outputs present:
- `test_all_expected_html_pages_exist`: 12 expected HTML files in runway/
- `test_all_css_assets_bundled`: 4 CSS files (common, blueprint, dep_graph, paper)
- `test_all_js_assets_bundled`: 2 JS files (plastex.js, verso-code.js)
- `test_no_zero_byte_output_files`: every HTML/CSS/JS file > 50 bytes

---

## Helper Additions (`helpers.py`)

```python
def collect_all_ids(html: str) -> set[str]:
    """Extract all id= attribute values from HTML using BeautifulSoup."""

def collect_fragment_links(html: str) -> set[str]:
    """Extract all href='#...' fragment targets (without the #)."""

def collect_relative_links(html: str) -> set[str]:
    """Extract all href='./X.html' relative page link targets."""

def extract_css_block_variables(css: str, selector: str) -> set[str]:
    """Extract CSS variable names defined within a specific selector block."""

def get_dressed_decl_paths(site, node_id: str) -> dict[str, Path]:
    """Resolve paths to dressed declaration artifacts (decl.json, decl.html, etc.) for a node."""
```

## Execution Waves

| Wave | Agents | Files | Notes |
|------|--------|-------|-------|
| 1 | A, B | A: `helpers.py` + `test_sbs_content.py`; B: `test_graph_navigation.py` | Core features + helpers |
| 2 | C, D | C: `test_dashboard_accuracy.py`; D: `test_paper_quality.py` | Dashboard + paper |
| 3 | E, F | E: `test_theme_and_dark_mode.py`; F: `test_cross_page_consistency.py` | Visual/design |
| 4 | G | Run full suite, fix failures | Validation pass |

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  regression: >= 0
  custom:
    new_test_count: ">= 100"
    all_new_tests_evergreen: true
    no_network_access: true
```

## Branch

`task/119-mvp-test-expansion`

## Critical Files

**Read (reference patterns):**
- [conftest.py](dev/scripts/sbs/tests/pytest/mvp/conftest.py) -- SiteArtifacts API, fixtures
- [helpers.py](dev/scripts/sbs/tests/pytest/mvp/helpers.py) -- existing helpers to extend
- [test_dependency_graph.py](dev/scripts/sbs/tests/pytest/mvp/test_dependency_graph.py) -- graph JSON test patterns
- [test_visual_quality.py](dev/scripts/sbs/tests/pytest/mvp/test_visual_quality.py) -- CSS analysis patterns

**Write (new/modified):**
- [helpers.py](dev/scripts/sbs/tests/pytest/mvp/helpers.py) -- add 5 helper functions
- 6 new test files in `dev/scripts/sbs/tests/pytest/mvp/`

## Verification

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
pytest sbs/tests/pytest/mvp/ -v -m evergreen
pytest sbs/tests/pytest/mvp/ --collect-only | tail -1  # verify count >= 300
pytest sbs/tests/pytest/ -v  # full suite regression check
```
