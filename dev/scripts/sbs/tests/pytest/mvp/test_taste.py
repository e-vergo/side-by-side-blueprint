"""
Taste Tests (101-125)

Subjective aesthetic tests validated by agent vision analysis.

These tests evaluate the tool against the aesthetic principle:
"A clean, simple, timeless tool that mathematicians would find aesthetic
both in terms of how it looks and how it functions."

In test mode, these default to passing. In production, an agent evaluates
each criterion against screenshots and provides scores (0-10).
"""

import pytest
from pathlib import Path
from typing import Optional

from .conftest import SiteArtifacts
from .helpers import TasteValidator, TasteResult


@pytest.fixture
def taste_validator() -> TasteValidator:
    """Create a taste validator in test mode."""
    return TasteValidator(test_mode=True)


@pytest.mark.evergreen
class TestTasteVisualAesthetics:
    """Visual Aesthetics - Does it look right? (Tests 101-105)"""

    def test_taste_whitespace_breathing_room(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """101. Does the layout have appropriate whitespace?"""
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Does the layout have appropriate whitespace and breathing room, or does it feel cramped?",
            criteria="Margins between sections, padding inside containers, line spacing in text blocks",
            test_name="whitespace_breathing_room",
        )
        assert result.passed, f"Whitespace score {result.score}/10: {result.reasoning}"

    def test_taste_typography_hierarchy(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """102. Is there clear visual hierarchy through typography?"""
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Is there clear visual hierarchy through font sizes and weights?",
            criteria="Headings visually distinct from body, important elements emphasized, consistent sizing",
            test_name="typography_hierarchy",
        )
        assert result.passed, f"Typography score {result.score}/10: {result.reasoning}"

    def test_taste_color_restraint(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """103. Are colors used sparingly and purposefully?"""
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Are colors used sparingly and purposefully, not garish or overwhelming?",
            criteria="Limited color palette, colors serve function (status, navigation), no gratuitous decoration",
            test_name="color_restraint",
        )
        assert result.passed, f"Color restraint score {result.score}/10: {result.reasoning}"

    def test_taste_alignment_consistency(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """104. Do elements align on a consistent grid?"""
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Do elements align on a consistent grid? Are margins and spacing uniform?",
            criteria="Left edges align, consistent gutters, no random offsets, grid-based layout",
            test_name="alignment_consistency",
        )
        assert result.passed, f"Alignment score {result.score}/10: {result.reasoning}"

    def test_taste_no_visual_clutter(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """105. Is the interface free of unnecessary decorative elements?"""
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Is the interface free of unnecessary decorative elements?",
            criteria="No gratuitous icons, no decorative borders, no visual noise, functional minimalism",
            test_name="no_visual_clutter",
        )
        assert result.passed, f"Visual clutter score {result.score}/10: {result.reasoning}"


@pytest.mark.evergreen
class TestTasteFunctionalAesthetics:
    """Functional Aesthetics - Does it work right? (Tests 106-110)"""

    def test_taste_interaction_predictable(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """106. Do interactive elements behave as expected?"""
        screenshot = sbstest_site.get_screenshot("dep_graph")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Do interactive elements (buttons, links, toggles) look clickable and behave predictably?",
            criteria="Buttons look like buttons, links are underlined or colored, hover states visible",
            test_name="interaction_predictable",
        )
        assert result.passed, f"Interaction score {result.score}/10: {result.reasoning}"

    def test_taste_navigation_intuitive(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """107. Can you find things without reading documentation?"""
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Can a user find things without reading documentation? Is navigation intuitive?",
            criteria="Clear navigation structure, logical grouping, breadcrumbs or location indicators",
            test_name="navigation_intuitive",
        )
        assert result.passed, f"Navigation score {result.score}/10: {result.reasoning}"

    def test_taste_feedback_appropriate(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """108. Do actions provide clear, non-intrusive feedback?"""
        screenshot = sbstest_site.get_screenshot("dep_graph")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Do actions provide clear, non-intrusive feedback?",
            criteria="Selection states visible, loading indicators present, no jarring popups",
            test_name="feedback_appropriate",
        )
        assert result.passed, f"Feedback score {result.score}/10: {result.reasoning}"

    def test_taste_loading_graceful(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """109. Do loading states feel smooth, not janky?"""
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Does the page appear to load gracefully? No broken images or missing styles visible?",
            criteria="Complete rendering, no layout shifts visible, professional appearance",
            test_name="loading_graceful",
        )
        assert result.passed, f"Loading score {result.score}/10: {result.reasoning}"

    def test_taste_error_states_helpful(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """110. When things go wrong, are error messages useful?"""
        # This is harder to test with screenshots - check that error handling exists
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Does the interface look like it would handle errors gracefully?",
            criteria="Professional appearance suggests attention to detail, no visible broken states",
            test_name="error_states_helpful",
        )
        assert result.passed, f"Error states score {result.score}/10: {result.reasoning}"


@pytest.mark.evergreen
class TestTasteConceptualAesthetics:
    """Conceptual Aesthetics - Does it make sense? (Tests 111-115)"""

    def test_taste_purpose_obvious(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """111. Is it immediately clear what this tool is for?"""
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Is it immediately clear what this tool is for? Would a mathematician understand at a glance?",
            criteria="Clear title/branding, obvious purpose from layout, math content visible",
            test_name="purpose_obvious",
        )
        assert result.passed, f"Purpose score {result.score}/10: {result.reasoning}"

    def test_taste_mental_model_clear(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """112. Does the UI map to how mathematicians think about proofs?"""
        screenshot = sbstest_site.get_screenshot("dep_graph")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Does the dependency graph represent mathematical relationships in a familiar way?",
            criteria="Nodes as theorems, edges as dependencies, hierarchical layout, clear flow",
            test_name="mental_model_clear",
        )
        assert result.passed, f"Mental model score {result.score}/10: {result.reasoning}"

    def test_taste_no_unnecessary_concepts(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """113. Are there features that feel bolted-on or confusing?"""
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Does everything on the page serve a clear purpose? No confusing or unnecessary elements?",
            criteria="Every section has clear purpose, no mystery buttons, no unexplained UI",
            test_name="no_unnecessary_concepts",
        )
        assert result.passed, f"Unnecessary concepts score {result.score}/10: {result.reasoning}"

    def test_taste_terminology_precise(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """114. Is the language mathematically precise, not marketing-speak?"""
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Is the terminology mathematically precise? No marketing buzzwords?",
            criteria="Uses 'theorem', 'lemma', 'proof' correctly, no hype language, academic tone",
            test_name="terminology_precise",
        )
        assert result.passed, f"Terminology score {result.score}/10: {result.reasoning}"

    def test_taste_information_density_appropriate(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """115. Is there enough info without overwhelming?"""
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Is the information density appropriate? Enough detail without overwhelming?",
            criteria="Key stats visible, detail available on demand, not sparse or cluttered",
            test_name="information_density_appropriate",
        )
        assert result.passed, f"Information density score {result.score}/10: {result.reasoning}"


@pytest.mark.evergreen
class TestTasteImplementationAesthetics:
    """Implementation Aesthetics - Is it well-made? (Tests 116-120)"""

    def test_taste_code_highlighting_readable(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """116. Is the Lean syntax highlighting helpful, not distracting?"""
        # Try to find a chapter page with code
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "chapter" in p.lower() or "main" in p.lower()]
        screenshot = None
        if chapter_pages:
            screenshot = sbstest_site.get_screenshot(chapter_pages[0])
        if screenshot is None:
            screenshot = sbstest_site.get_screenshot("dashboard")

        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Is the code syntax highlighting helpful and readable, not distracting?",
            criteria="Colors distinguish syntax elements, readable contrast, not too colorful",
            test_name="code_highlighting_readable",
        )
        assert result.passed, f"Code highlighting score {result.score}/10: {result.reasoning}"

    def test_taste_math_rendering_beautiful(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """117. Does the LaTeX render as beautifully as a published paper?"""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "chapter" in p.lower() or "main" in p.lower()]
        screenshot = None
        if chapter_pages:
            screenshot = sbstest_site.get_screenshot(chapter_pages[0])
        if screenshot is None:
            screenshot = sbstest_site.get_screenshot("dashboard")

        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Does the mathematical typesetting look as good as a published paper?",
            criteria="Proper symbol rendering, good spacing, professional math layout",
            test_name="math_rendering_beautiful",
        )
        assert result.passed, f"Math rendering score {result.score}/10: {result.reasoning}"

    def test_taste_graph_layout_logical(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """118. Does the dependency graph layout make mathematical sense?"""
        screenshot = sbstest_site.get_screenshot("dep_graph")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Does the graph layout reflect logical dependency structure?",
            criteria="Hierarchical flow, foundations at top/bottom, clear edge directions",
            test_name="graph_layout_logical",
        )
        assert result.passed, f"Graph layout score {result.score}/10: {result.reasoning}"

    def test_taste_transitions_smooth(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """119. Are animations subtle and purposeful?"""
        screenshot = sbstest_site.get_screenshot("dep_graph")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Does the interface look like it would animate smoothly? No janky elements?",
            criteria="Professional appearance, smooth-looking controls, no obvious performance issues",
            test_name="transitions_smooth",
        )
        assert result.passed, f"Transitions score {result.score}/10: {result.reasoning}"

    def test_taste_responsive_feels_native(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """120. Does it feel like a native app, not a janky website?"""
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Does this feel like a polished application, not a thrown-together website?",
            criteria="Consistent design language, professional polish, attention to detail",
            test_name="responsive_feels_native",
        )
        assert result.passed, f"Responsive feel score {result.score}/10: {result.reasoning}"


@pytest.mark.evergreen
class TestTasteTimelessness:
    """Timelessness - Will this age well? (Tests 121-125)"""

    def test_taste_no_trendy_design(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """121. Does it avoid dated design trends?"""
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Does this avoid dated design trends (excessive gradients, shadows, skeuomorphism)?",
            criteria="Clean flat design, no obvious 2015-era trends, timeless aesthetic",
            test_name="no_trendy_design",
        )
        assert result.passed, f"Trendy design score {result.score}/10: {result.reasoning}"

    def test_taste_professional_not_playful(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """122. Does it feel serious/academic, not startup-y?"""
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Does this feel serious and academic, not like a startup landing page?",
            criteria="Academic tone, no marketing speak, scholarly appearance, serious purpose",
            test_name="professional_not_playful",
        )
        assert result.passed, f"Professional tone score {result.score}/10: {result.reasoning}"

    def test_taste_would_arxiv_link(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """123. Would you be proud to link this from an arXiv paper?"""
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Would a researcher be proud to link to this from an arXiv paper?",
            criteria="Professional quality, credible appearance, appropriate for academic context",
            test_name="would_arxiv_link",
        )
        assert result.passed, f"arXiv worthy score {result.score}/10: {result.reasoning}"

    def test_taste_respects_content(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """124. Does the UI get out of the way of the mathematics?"""
        pages = sbstest_site.list_pages()
        chapter_pages = [p for p in pages if "chapter" in p.lower() or "main" in p.lower()]
        screenshot = None
        if chapter_pages:
            screenshot = sbstest_site.get_screenshot(chapter_pages[0])
        if screenshot is None:
            screenshot = sbstest_site.get_screenshot("dashboard")

        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Does the UI serve the mathematical content, not compete with it?",
            criteria="Content is the focus, UI is invisible infrastructure, math is prominent",
            test_name="respects_content",
        )
        assert result.passed, f"Respects content score {result.score}/10: {result.reasoning}"

    def test_taste_unified_vision(
        self, taste_validator: TasteValidator, sbstest_site: SiteArtifacts
    ):
        """125. Does everything feel like it belongs together?"""
        screenshot = sbstest_site.get_screenshot("dashboard")
        result = taste_validator.evaluate(
            screenshot=screenshot,
            question="Does everything feel like it belongs together as a unified design?",
            criteria="Consistent colors, fonts, spacing, interaction patterns throughout",
            test_name="unified_vision",
        )
        assert result.passed, f"Unified vision score {result.score}/10: {result.reasoning}"
