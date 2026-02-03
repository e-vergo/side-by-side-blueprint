"""
MVP test fixtures for Side-by-Side Blueprint.

Provides fixtures to load generated site artifacts for testing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pytest


# Project root paths
MONOREPO_ROOT = Path("/Users/eric/GitHub/Side-By-Side-Blueprint")
SBSTEST_ROOT = MONOREPO_ROOT / "toolchain" / "SBS-Test"
GCR_ROOT = MONOREPO_ROOT / "showcase" / "General_Crystallographic_Restriction"
PNT_ROOT = MONOREPO_ROOT / "showcase" / "PrimeNumberTheoremAnd"
STORAGE_ROOT = MONOREPO_ROOT / "dev" / "storage"


@dataclass
class SiteArtifacts:
    """Container for generated site artifacts."""

    project: str
    project_root: Path

    # Lazy-loaded cached data
    _manifest: Optional[dict] = field(default=None, repr=False)
    _dep_graph: Optional[dict] = field(default=None, repr=False)
    _pages: dict[str, str] = field(default_factory=dict, repr=False)
    _css: Optional[str] = field(default=None, repr=False)

    @property
    def dressed_dir(self) -> Path:
        return self.project_root / ".lake" / "build" / "dressed"

    @property
    def runway_dir(self) -> Path:
        return self.project_root / ".lake" / "build" / "runway"

    @property
    def screenshots_dir(self) -> Path:
        return STORAGE_ROOT / self.project / "latest"

    @property
    def manifest(self) -> dict:
        if self._manifest is None:
            manifest_path = self.dressed_dir / "manifest.json"
            if manifest_path.exists():
                self._manifest = json.loads(manifest_path.read_text())
            else:
                self._manifest = {}
        return self._manifest

    @property
    def dep_graph(self) -> dict:
        if self._dep_graph is None:
            graph_path = self.dressed_dir / "dep-graph.json"
            if graph_path.exists():
                self._dep_graph = json.loads(graph_path.read_text())
            else:
                self._dep_graph = {"nodes": [], "edges": []}
        return self._dep_graph

    @property
    def css(self) -> str:
        if self._css is None:
            css_path = self.runway_dir / "assets" / "common.css"
            if css_path.exists():
                self._css = css_path.read_text()
            else:
                self._css = ""
        return self._css

    @property
    def all_css(self) -> dict[str, str]:
        """Load all CSS files from assets directory, keyed by filename."""
        css_files: dict[str, str] = {}
        assets_dir = self.runway_dir / "assets"
        if assets_dir.exists():
            for css_path in assets_dir.glob("*.css"):
                css_files[css_path.name] = css_path.read_text()
        return css_files

    @property
    def js_assets(self) -> dict[str, str]:
        """Load all JS files from assets directory, keyed by filename."""
        js_files: dict[str, str] = {}
        assets_dir = self.runway_dir / "assets"
        if assets_dir.exists():
            for js_path in assets_dir.glob("*.js"):
                js_files[js_path.name] = js_path.read_text()
        return js_files

    @property
    def assets_dir(self) -> Path:
        return self.runway_dir / "assets"

    def get_page(self, name: str) -> str:
        """Get HTML content for a page by name."""
        if name not in self._pages:
            # Map page names to file paths
            page_map = {
                "dashboard": "index.html",
                "dep_graph": "dep_graph.html",
                "paper_tex": "paper_tex.html",
                "pdf_tex": "pdf_tex.html",
                "paper_verso": "paper_verso.html",
                "blueprint_verso": "blueprint_verso.html",
            }
            filename = page_map.get(name, f"{name}.html")
            page_path = self.runway_dir / filename

            # Also check for chapter pages
            if not page_path.exists():
                # Try finding chapter files
                for p in self.runway_dir.glob("*.html"):
                    if name in p.name:
                        page_path = p
                        break

            if page_path.exists():
                self._pages[name] = page_path.read_text()
            else:
                self._pages[name] = ""
        return self._pages[name]

    def get_screenshot(self, name: str) -> Optional[Path]:
        """Get screenshot path for a page."""
        screenshot_path = self.screenshots_dir / f"{name}.png"
        return screenshot_path if screenshot_path.exists() else None

    def list_pages(self) -> list[str]:
        """List all available HTML pages."""
        return [p.stem for p in self.runway_dir.glob("*.html")]

    def list_screenshots(self) -> list[str]:
        """List all available screenshots."""
        return [p.stem for p in self.screenshots_dir.glob("*.png")]


@pytest.fixture
def sbstest_site() -> SiteArtifacts:
    """Load SBS-Test generated site artifacts."""
    return SiteArtifacts(project="SBSTest", project_root=SBSTEST_ROOT)


@pytest.fixture
def gcr_site() -> SiteArtifacts:
    """Load GCR generated site artifacts."""
    return SiteArtifacts(project="GCR", project_root=GCR_ROOT)


@pytest.fixture
def pnt_site() -> SiteArtifacts:
    """Load PNT generated site artifacts."""
    return SiteArtifacts(project="PNT", project_root=PNT_ROOT)


@pytest.fixture
def all_sites(sbstest_site, gcr_site, pnt_site) -> dict[str, SiteArtifacts]:
    """All project site artifacts."""
    return {
        "SBSTest": sbstest_site,
        "GCR": gcr_site,
        "PNT": pnt_site,
    }
