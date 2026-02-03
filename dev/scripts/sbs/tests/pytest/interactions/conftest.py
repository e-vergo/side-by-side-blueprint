"""
Fixtures for interactive (Playwright-based) tests.

These tests require:
1. A built project in _site/
2. A running dev server (spawned by fixture)
3. playwright installed with chromium

Usage:
    @pytest.mark.interactive
    def test_sidebar_toggle(page, base_url):
        page.goto(f"{base_url}/index.html")
        ...
"""
import pytest
from pathlib import Path
from typing import Generator
import subprocess
import time
import socket


def find_free_port() -> int:
    """Find an available port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get SBS-Test project root."""
    return Path(__file__).parents[6] / "toolchain" / "SBS-Test"


@pytest.fixture(scope="session")
def site_dir(project_root: Path) -> Path:
    """Get built site directory."""
    site = project_root / "_site"
    if not site.exists():
        pytest.skip("_site not built. Run build.py first.")
    return site


@pytest.fixture(scope="session")
def server_port() -> int:
    """Get a free port for the test server."""
    return find_free_port()


@pytest.fixture(scope="session")
def base_url(site_dir: Path, server_port: int) -> Generator[str, None, None]:
    """Start a local server and yield its URL."""
    # Start simple HTTP server
    proc = subprocess.Popen(
        ["python3", "-m", "http.server", str(server_port)],
        cwd=site_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for server to start
    time.sleep(1)

    yield f"http://localhost:{server_port}"

    # Cleanup
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def browser():
    """Launch Playwright browser for session."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright not installed. Run: pip install playwright && playwright install chromium")

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    yield browser
    browser.close()
    pw.stop()


@pytest.fixture
def page(browser):
    """Create a new page for each test."""
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    yield page
    page.close()
    context.close()
