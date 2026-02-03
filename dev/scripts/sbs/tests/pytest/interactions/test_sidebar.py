"""
Interactive test: Sidebar and navigation functionality.

This test verifies sidebar behavior including:
- Visibility on page load
- Theme toggle functionality
- Navigation link behavior
"""
import pytest


@pytest.mark.interactive
class TestSidebarVisibility:
    """Tests for sidebar visibility on page load."""

    def test_sidebar_visible_on_dashboard(self, page, base_url):
        """Sidebar should be visible on dashboard page."""
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        # Try multiple possible sidebar selectors
        sidebar = page.locator("nav.toc, .sidebar, #sidebar, nav.sidebar-main, .nav-wrapper")
        assert sidebar.count() > 0, "No sidebar element found"
        assert sidebar.first.is_visible(), "Sidebar should be visible on dashboard"

    def test_sidebar_has_navigation_links(self, page, base_url):
        """Sidebar should contain navigation links."""
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        # Look for sidebar links
        links = page.locator("nav a, .sidebar a, .toc a")
        assert links.count() > 0, "Sidebar should have navigation links"


@pytest.mark.interactive
class TestThemeToggle:
    """Tests for theme toggle functionality."""

    def test_theme_toggle_exists(self, page, base_url):
        """Theme toggle control should exist on page."""
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        toggle = page.locator(".theme-toggle, #theme-toggle, [aria-label*='theme']")
        # Theme toggle may not exist on all themes
        if toggle.count() == 0:
            pytest.skip("No theme toggle on this page/theme")

        assert toggle.first.is_visible(), "Theme toggle should be visible"

    def test_theme_toggle_changes_theme(self, page, base_url):
        """Clicking theme toggle should change the theme."""
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        toggle = page.locator(".theme-toggle, #theme-toggle")
        if toggle.count() == 0:
            pytest.skip("No theme toggle on this page")

        # Get initial theme state (check body or html class/data-attr)
        body = page.locator("body")
        initial_class = body.get_attribute("class") or ""
        initial_data = body.get_attribute("data-theme") or ""

        # Click toggle
        toggle.first.click()
        page.wait_for_timeout(300)  # Wait for theme transition

        # Check that something changed
        new_class = body.get_attribute("class") or ""
        new_data = body.get_attribute("data-theme") or ""

        # Either class or data-theme should have changed
        changed = (new_class != initial_class) or (new_data != initial_data)
        assert changed, "Theme should change after toggle click"


@pytest.mark.interactive
class TestNavigationLinks:
    """Tests for navigation link behavior."""

    def test_dashboard_link_is_active(self, page, base_url):
        """Dashboard link should be marked active when on dashboard."""
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        # Look for active link
        active = page.locator("a.active, a.sidebar-item.active, .nav-link.active")
        if active.count() == 0:
            # Some themes may use different patterns
            pytest.skip("No active link marker found")

        assert active.first.is_visible(), "Active link should be visible"

    def test_navigation_links_are_clickable(self, page, base_url):
        """Navigation links should be clickable and navigate."""
        page.goto(f"{base_url}/index.html")
        page.wait_for_load_state("networkidle")

        # Find a non-active navigation link
        links = page.locator("nav a:not(.active), .toc a:not(.active)")
        if links.count() == 0:
            pytest.skip("No non-active navigation links found")

        # Get href of first link
        first_link = links.first
        href = first_link.get_attribute("href")
        if not href:
            pytest.skip("Link has no href")

        # Click and verify navigation
        first_link.click()
        page.wait_for_load_state("networkidle")

        # URL should have changed
        assert href in page.url or page.url != f"{base_url}/index.html", \
            "Navigation should change the URL"
