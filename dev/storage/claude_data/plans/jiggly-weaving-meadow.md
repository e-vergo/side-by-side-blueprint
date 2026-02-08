# MVP Validation Plan

## Phase 1: Test Suite (COMPLETE)
Created 125 tests. Current status: **123/125 passing** (test mode).

## Phase 2: Full Validation Run (THIS PLAN)

### Objective
Build all 3 projects, capture screenshots, run tests against real artifacts to achieve true MVP status.

---

## Gap Analysis Summary

**Implementation Status: 95% Complete**

| Feature | Status | Notes |
|---------|--------|-------|
| Side-by-Side Display | ✅ Complete | SideBySide.lean + blueprint.css |
| Dual Authoring (TeX) | ✅ Complete | \inputleannode, \inputleanmodule |
| Dual Authoring (Verso) | ✅ Complete | :::leanNode directive |
| Dependency Graph | ✅ Complete | JSON + SVG + interactive |
| Status Indicators | ✅ Complete | 6 colors in Lean + CSS |
| Dashboard | ✅ Complete | Stats, key theorems, navigation |
| Paper Generation | ✅ Complete | HTML + PDF (GCR configured) |
| CI/CD Integration | ✅ Complete | 433-line GitHub Action |
| Visual Quality | ✅ Complete | Theme, brackets, responsive |

**Known Gaps:**
- Verso LaTeX export not implemented (documented future work)
- PNT has no paper.tex configured (blueprint only)
- 2 tests skip on SBS-Test (Verso blueprint, paper.tex - both exist in GCR)

---

## Validation Run Plan

### Wave 1: Build All Projects (sbs-developer)

Build each project in order of complexity:

```bash
# 1. SBS-Test (~2 min) - Feature completeness
./dev/build-sbs-test.sh

# 2. GCR (~5 min) - Polished showcase
./dev/build-gcr.sh

# 3. PNT (~20 min) - Scale validation
./dev/build-pnt.sh
```

**Success criteria per project:**
- Build exits 0
- manifest.json generated
- dep-graph.json generated
- All HTML pages generated
- No Lean errors

### Wave 2: Capture Screenshots (sbs-developer)

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts

# Capture all projects with interactive states
python3 -m sbs capture --project SBSTest --interactive
python3 -m sbs capture --project GCR --interactive
python3 -m sbs capture --project PNT --interactive
```

**Pages to capture per project:**
- dashboard
- dep_graph
- chapter (first chapter with SBS content)
- paper_tex (if exists)
- pdf_tex (if exists)

### Wave 3: Run Full Test Suite (sbs-developer)

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
pytest sbs/tests/pytest/mvp/ -v --tb=short
```

**Expected results:**
- 123+ tests pass
- ≤5 tests skip (acceptable for missing optional features)
- 0 tests fail

### Wave 4: Visual Validation (agent evaluation)

For taste tests, agent reviews screenshots and provides scores:

1. Read each screenshot file
2. Evaluate against taste criteria (7/10 threshold)
3. Record findings

**Priority pages for taste evaluation:**
- SBSTest/dashboard.png - Overall impression
- SBSTest/dep_graph.png - Graph aesthetics
- GCR/paper_tex.png - Paper quality
- PNT/dep_graph.png - Scale handling

### Wave 5: Fix Issues (if needed)

If tests fail or taste scores are low:
1. Identify root cause
2. Fix CSS/JS/Lean as needed
3. Rebuild affected project
4. Re-capture screenshots
5. Re-run tests

---

## Gates

```yaml
gates:
  builds: all_pass          # All 3 projects build successfully
  tests: 120/125            # 96% pass rate
  taste: avg >= 7/10        # Aesthetic threshold
  regression: 0             # No regression in existing tests
```

---

## Verification Commands

```bash
# Full validation sequence
cd /Users/eric/GitHub/Side-By-Side-Blueprint

# 1. Build all projects
./dev/build-sbs-test.sh && ./dev/build-gcr.sh && ./dev/build-pnt.sh

# 2. Capture screenshots
cd dev/scripts
python3 -m sbs capture --project SBSTest --interactive
python3 -m sbs capture --project GCR --interactive
python3 -m sbs capture --project PNT --interactive

# 3. Run tests
pytest sbs/tests/pytest/mvp/ -v

# 4. Check results
pytest sbs/tests/pytest/mvp/ --tb=no -q | tail -5
```

**MVP is achieved when:** 120/125 tests pass against real build artifacts.

---

## Test Categories (Reference)

| Category | Count | Type |
|----------|-------|------|
| Side-by-Side Display | 15 | Deterministic (HTML parsing) |
| Dual Authoring Modes | 15 | Deterministic (artifact comparison) |
| Dependency Graph | 20 | Deterministic (JSON + HTML) |
| Status Indicators | 12 | Deterministic (CSS + JSON) |
| Dashboard | 13 | Deterministic (HTML + manifest) |
| Paper Generation | 12 | Deterministic (file existence + structure) |
| CI/CD Integration | 8 | Deterministic (action.yml + workflow) |
| Visual Quality | 5 | Deterministic (CSS + screenshots) |
| Taste | 25 | Agent-validated (subjective) |
| **Total** | **125** | |

---

## Implementation Waves

### Wave 1: Test Infrastructure (sbs-developer)
Create base fixtures and helpers for MVP tests.

**Files to create:**
- `dev/scripts/sbs/tests/pytest/mvp/conftest.py` - MVP-specific fixtures
- `dev/scripts/sbs/tests/pytest/mvp/helpers.py` - HTML/JSON parsing utilities

**Key fixtures:**
```python
@pytest.fixture
def sbstest_site() -> SiteArtifacts:
    """Load SBS-Test generated site artifacts."""

@pytest.fixture
def gcr_site() -> SiteArtifacts:
    """Load GCR generated site artifacts."""

@pytest.fixture
def pnt_site() -> SiteArtifacts:
    """Load PNT generated site artifacts."""

class SiteArtifacts:
    manifest: dict          # manifest.json
    dep_graph: dict         # dep-graph.json
    pages: dict[str, str]   # page_name -> HTML content
    css: str                # common.css content
    screenshots: dict       # page_name -> path
```

### Wave 2: Deterministic Tests (sbs-developer)
Create 100 deterministic tests across 8 categories.

**Files to create:**
```
dev/scripts/sbs/tests/pytest/mvp/
├── __init__.py
├── conftest.py
├── helpers.py
├── test_side_by_side.py      # 15 tests
├── test_authoring_modes.py   # 15 tests
├── test_dependency_graph.py  # 20 tests
├── test_status_indicators.py # 12 tests
├── test_dashboard.py         # 13 tests
├── test_paper_generation.py  # 12 tests
├── test_cicd.py              # 8 tests
└── test_visual_quality.py    # 5 tests
```

**Test implementation pattern:**
```python
@pytest.mark.evergreen
class TestSideBySideDisplay:
    def test_sbs_columns_present(self, sbstest_site: SiteArtifacts):
        """LaTeX and Lean columns both render."""
        html = sbstest_site.pages["chapter"]
        soup = BeautifulSoup(html, "html.parser")
        containers = soup.select(".sbs-container")
        assert len(containers) > 0
        for container in containers:
            assert container.select_one(".sbs-latex-column")
            assert container.select_one(".sbs-lean-column")
```

### Wave 3: Taste Tests (sbs-developer)
Create 25 agent-validated subjective tests.

**File to create:**
- `dev/scripts/sbs/tests/pytest/mvp/test_taste.py`

**Taste test pattern:**
```python
@pytest.mark.evergreen
class TestTaste:
    """
    Subjective aesthetic tests validated by agent vision.

    These tests generate prompts that an agent evaluates against
    screenshots. Each test asks a specific aesthetic question.
    """

    @pytest.fixture
    def taste_validator(self) -> TasteValidator:
        return TasteValidator()

    def test_taste_whitespace_breathing_room(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """Does the layout have appropriate whitespace?"""
        result = taste_validator.evaluate(
            screenshot=sbstest_site.screenshots["dashboard"],
            question="Does the layout have appropriate whitespace and breathing room, or does it feel cramped?",
            criteria="Margins between sections, padding inside containers, line spacing in text",
        )
        assert result.score >= 7, f"Whitespace score {result.score}/10: {result.reasoning}"
```

**TasteValidator implementation:**
- Generates structured prompts with screenshot paths
- Returns `TasteResult(score: int, reasoning: str, passed: bool)`
- Score threshold: 7/10 for pass
- Stores prompts in `result.details["prompt"]` for agent evaluation

### Wave 4: Validation & Fixes (sbs-developer)
Run full test suite, fix failing tests, iterate until 120/125 pass.

**Validation command:**
```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
pytest sbs/tests/pytest/mvp/ -v --tb=short
```

---

## Critical Files

**Artifacts to test against:**
- `toolchain/SBS-Test/.lake/build/dressed/manifest.json`
- `toolchain/SBS-Test/.lake/build/dressed/dep-graph.json`
- `toolchain/SBS-Test/.lake/build/runway/*.html`
- `toolchain/SBS-Test/.lake/build/runway/assets/common.css`
- `dev/storage/SBSTest/latest/*.png`

**Test infrastructure:**
- `dev/scripts/sbs/tests/pytest/conftest.py` (existing fixtures)
- `dev/scripts/sbs/tests/validators/base.py` (validator protocol)

---

## Gates

```yaml
gates:
  tests: 120/125           # 96% pass rate required
  regression: >= 0         # No regression in existing 283 tests

validators:
  - pytest: mvp/           # All 125 MVP tests
  - pytest: validators/    # Existing validator tests
```

---

## Test List Reference

### Side-by-Side Display (1-15)
1. `test_sbs_columns_present` - Both columns render
2. `test_sbs_latex_left_lean_right` - Correct column order
3. `test_sbs_synchronized_expand` - Expand syncs both sides
4. `test_sbs_synchronized_collapse` - Collapse syncs both
5. `test_sbs_latex_mathjax_renders` - MathJax works
6. `test_sbs_lean_syntax_highlighted` - Syntax highlighting applied
7. `test_sbs_hover_shows_type` - Type tooltips work
8. `test_sbs_hover_shows_docstring` - Docstrings in hovers
9. `test_sbs_multiline_proof_aligned` - Multi-line alignment
10. `test_sbs_complex_latex_renders` - Complex LaTeX (matrices, align)
11. `test_sbs_nested_structures_render` - Nested proofs
12. `test_sbs_no_horizontal_overflow` - No overflow
13. `test_sbs_mobile_stacks_vertical` - Responsive layout
14. `test_sbs_print_layout_clean` - Print stylesheet
15. `test_sbs_all_nodes_have_sbs` - Every node has SBS

### Dual Authoring Modes (16-30)
16. `test_tex_inputleannode_resolves` - \inputleannode works
17. `test_tex_inputleanmodule_works` - \inputleanmodule works
18. `test_tex_chapter_structure_preserved` - Chapters → sections
19. `test_tex_section_numbering_correct` - Section numbers match
20. `test_tex_cross_references_work` - \ref links work
21. `test_tex_bibliography_renders` - Bibliography displays
22. `test_verso_leannode_resolves` - :::leanNode works
23. `test_verso_markdown_renders` - Markdown → HTML
24. `test_verso_code_blocks_highlighted` - Code highlighting
25. `test_verso_links_work` - Internal links
26. `test_tex_and_verso_output_equivalent` - Same node, same output
27. `test_tex_special_chars_escaped` - Special chars safe
28. `test_verso_unicode_renders` - Unicode math
29. `test_tex_missing_node_error_graceful` - Graceful missing node error
30. `test_verso_missing_node_error_graceful` - Graceful missing node error

### Dependency Graph (31-50)
31. `test_graph_renders_svg` - SVG element present
32. `test_graph_all_nodes_present` - All nodes in graph
33. `test_graph_edges_match_deps` - Edge count correct
34. `test_graph_solid_edges_proof_deps` - Solid = proof deps
35. `test_graph_dashed_edges_stmt_deps` - Dashed = stmt deps
36. `test_graph_node_click_opens_modal` - Modal on click
37. `test_graph_modal_shows_sbs` - Modal has SBS
38. `test_graph_modal_has_source_link` - Modal links to source
39. `test_graph_pan_works` - Pan gesture
40. `test_graph_zoom_works` - Zoom gesture
41. `test_graph_zoom_buttons_work` - +/- buttons
42. `test_graph_reset_view_works` - Reset button
43. `test_graph_filter_by_status` - Status filter
44. `test_graph_search_highlights_node` - Search highlighting
45. `test_graph_node_shapes_correct` - Correct shapes
46. `test_graph_node_colors_match_status` - Colors match
47. `test_graph_no_overlapping_nodes` - No collisions
48. `test_graph_no_overlapping_edges` - Edges don't cross nodes
49. `test_graph_pnt_renders_under_30s` - PNT performance
50. `test_graph_pnt_zoom_responsive` - PNT zoom <500ms

### Status Indicators (51-62)
51. `test_status_notready_shows_sandy_brown` - #F4A460
52. `test_status_ready_shows_sea_green` - #20B2AA
53. `test_status_sorry_shows_dark_red` - #8B0000
54. `test_status_proven_shows_light_green` - #90EE90
55. `test_status_fullyproven_shows_forest_green` - #228B22
56. `test_status_mathlibready_shows_light_blue` - #87CEEB
57. `test_status_auto_infers_sorry` - sorry auto-detected
58. `test_status_auto_infers_proven` - proven auto-detected
59. `test_status_fullyproven_computed` - fullyProven computed
60. `test_status_manual_override_works` - Manual override
61. `test_status_priority_order_correct` - Priority order
62. `test_status_legend_present` - Legend on graph

### Dashboard (63-75)
63. `test_dashboard_loads` - 200 response
64. `test_dashboard_stats_total_count` - Total count
65. `test_dashboard_stats_proven_count` - Proven count
66. `test_dashboard_stats_sorry_count` - Sorry count
67. `test_dashboard_stats_percentage` - Completion %
68. `test_dashboard_key_theorems_listed` - Key theorems
69. `test_dashboard_key_theorems_clickable` - Clickable links
70. `test_dashboard_messages_shown` - Messages display
71. `test_dashboard_nav_to_chapters` - Chapter nav
72. `test_dashboard_nav_to_graph` - Graph nav
73. `test_dashboard_nav_to_paper` - Paper nav
74. `test_dashboard_gcr_no_sorries` - GCR 0 sorries
75. `test_dashboard_pnt_stats_accurate` - PNT stats accurate

### Paper Generation (76-87)
76. `test_paper_html_exists` - paper_tex.html exists
77. `test_paper_pdf_exists` - paper.pdf exists
78. `test_paper_title_matches_tex` - Title matches
79. `test_paper_authors_listed` - Authors displayed
80. `test_paper_abstract_present` - Abstract present
81. `test_paper_sections_structured` - Section hierarchy
82. `test_paper_math_renders` - MathJax works
83. `test_paper_verification_badges` - Badges present
84. `test_paper_badge_links_to_proof` - Badge links work
85. `test_paper_bibliography_present` - References
86. `test_pdf_viewer_loads` - PDF viewer
87. `test_pdf_downloadable` - PDF downloadable

### CI/CD Integration (88-95)
88. `test_action_yaml_valid` - Valid YAML
89. `test_action_inputs_documented` - Inputs documented
90. `test_action_builds_sbstest` - Builds SBS-Test
91. `test_action_builds_gcr` - Builds GCR
92. `test_action_deploys_artifact` - Uploads artifact
93. `test_action_cache_works` - Cache speeds rebuild
94. `test_action_docgen4_skip_mode` - Skip mode works
95. `test_action_under_60min` - <60min build

### Visual Quality (96-100)
96. `test_theme_toggle_switches` - Toggle works
97. `test_theme_system_pref_detected` - System pref
98. `test_rainbow_brackets_colored` - Bracket colors
99. `test_no_console_errors` - No JS errors
100. `test_fonts_load` - Fonts render

### Taste (101-125)
101. `test_taste_whitespace_breathing_room` - Appropriate whitespace
102. `test_taste_typography_hierarchy` - Clear visual hierarchy
103. `test_taste_color_restraint` - Colors used sparingly
104. `test_taste_alignment_consistency` - Consistent grid
105. `test_taste_no_visual_clutter` - No unnecessary decoration
106. `test_taste_interaction_predictable` - Predictable interactions
107. `test_taste_navigation_intuitive` - Intuitive navigation
108. `test_taste_feedback_appropriate` - Clear feedback
109. `test_taste_loading_graceful` - Smooth loading
110. `test_taste_error_states_helpful` - Helpful errors
111. `test_taste_purpose_obvious` - Clear purpose
112. `test_taste_mental_model_clear` - Maps to math thinking
113. `test_taste_no_unnecessary_concepts` - No bolted-on features
114. `test_taste_terminology_precise` - Precise language
115. `test_taste_information_density_appropriate` - Right info density
116. `test_taste_code_highlighting_readable` - Readable highlighting
117. `test_taste_math_rendering_beautiful` - Beautiful LaTeX
118. `test_taste_graph_layout_logical` - Logical graph layout
119. `test_taste_transitions_smooth` - Smooth animations
120. `test_taste_responsive_feels_native` - Native feel
121. `test_taste_no_trendy_design` - No dated trends
122. `test_taste_professional_not_playful` - Academic tone
123. `test_taste_would_arxiv_link` - Proud to link from arXiv
124. `test_taste_respects_content` - UI serves math
125. `test_taste_unified_vision` - Everything belongs together

---

## Verification

After implementation:

```bash
# Run all MVP tests
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
pytest sbs/tests/pytest/mvp/ -v

# Check pass count
pytest sbs/tests/pytest/mvp/ --tb=no -q | tail -5

# Run existing tests to verify no regression
pytest sbs/tests/pytest/ -v --ignore=sbs/tests/pytest/mvp/
```

**Success criteria:** 120/125 MVP tests pass, 0 regressions in existing 283 tests.
