"""
Screenshot capture for Side-by-Side Blueprint visual verification.

Captures key pages from a running blueprint site for visual diff testing.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .utils import (
    IMAGES_DIR,
    detect_project,
    get_git_commit,
    log,
)

# =============================================================================
# Constants
# =============================================================================

DEFAULT_URL = "http://localhost:8000"
DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}

# Pages to capture (relative to base URL)
# Some pages may not exist in all projects (e.g., Verso docs require extra setup)
DEFAULT_PAGES = [
    {"name": "dashboard", "path": "index.html", "description": "Dashboard homepage"},
    {"name": "dep_graph", "path": "dep_graph.html", "description": "Dependency graph"},
    {"name": "paper_tex", "path": "paper_tex.html", "description": "Paper [TeX]"},
    {"name": "pdf_tex", "path": "pdf_tex.html", "description": "PDF [TeX]"},
    {"name": "paper_verso", "path": "paper_verso.html", "description": "Paper [Verso]"},
    {"name": "pdf_verso", "path": "pdf_verso.html", "description": "PDF [Verso]"},
    {"name": "blueprint_verso", "path": "blueprint_verso.html", "description": "Blueprint [Verso]"},
    {"name": "chapter", "path": None, "description": "First chapter page"},
]


# =============================================================================
# Page Detection
# =============================================================================


def find_chapter_page(page, base_url: str) -> Optional[str]:
    """Find the first blueprint chapter page with actual content (side-by-side displays).

    Args:
        page: Playwright page object
        base_url: Base URL of the site

    Returns:
        Relative path to chapter page, or None if not found
    """
    try:
        # Navigate to dashboard first
        page.goto(f"{base_url}/index.html", wait_until="networkidle")

        # Exclusion patterns for non-chapter pages
        exclude_patterns = [
            "index", "dep_graph", "paper", "pdf", "verso",
            "blueprint_verso", "pdf_verso", "paper_verso",
            "introduction",
        ]

        # Collect candidate pages
        candidates = []
        all_links = page.query_selector_all("a[href$='.html']")
        for link in all_links:
            href = link.get_attribute("href")
            if href and not any(x in href.lower() for x in exclude_patterns):
                if not href.startswith("http"):
                    href = href.lstrip("./")
                if href not in candidates:
                    candidates.append(href)

        # Try each candidate and pick one with theorem/proof content
        for candidate in candidates:
            try:
                page.goto(f"{base_url}/{candidate}", wait_until="networkidle", timeout=10000)
                has_content = page.query_selector(".theorem-statement, .side-by-side, .lean-code, .blueprint-theorem")
                if has_content:
                    return candidate
            except Exception:
                continue

        # Fallback to first candidate
        if candidates:
            return candidates[0]

        return None
    except Exception as e:
        log.warning(f"Could not find chapter page: {e}")
        return None


# =============================================================================
# Archive Management
# =============================================================================


def archive_previous_captures(project_dir: Path, latest_dir: Path) -> Optional[Path]:
    """Archive previous captures if they exist.

    Returns the archive path if archiving occurred, None otherwise.
    """
    if not latest_dir.exists():
        return None

    # Read metadata to get timestamp
    metadata_path = latest_dir / "capture.json"
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text())
            timestamp = metadata.get("timestamp", datetime.now().isoformat())
            archive_name = timestamp.replace(":", "-").replace("T", "_").split(".")[0]
        except Exception:
            archive_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    else:
        archive_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    archive_dir = project_dir / "archive" / archive_name
    archive_dir.parent.mkdir(parents=True, exist_ok=True)

    # Move latest to archive
    shutil.move(str(latest_dir), str(archive_dir))
    log.info(f"Archived previous captures to: {archive_dir.relative_to(IMAGES_DIR)}")

    return archive_dir


def get_archive_history(project_dir: Path) -> list[dict]:
    """Get list of archived captures with metadata.

    Returns list of dicts with: timestamp, path, page_count, commit
    """
    archive_dir = project_dir / "archive"
    if not archive_dir.exists():
        return []

    archives = []
    for item in sorted(archive_dir.iterdir(), reverse=True):
        if item.is_dir():
            metadata_path = item / "capture.json"
            if metadata_path.exists():
                try:
                    metadata = json.loads(metadata_path.read_text())
                    archives.append({
                        "path": item,
                        "timestamp": metadata.get("timestamp", "unknown"),
                        "commit": metadata.get("commit", "unknown"),
                        "page_count": len(metadata.get("pages", [])),
                    })
                except Exception:
                    archives.append({
                        "path": item,
                        "timestamp": item.name,
                        "commit": "unknown",
                        "page_count": len(list(item.glob("*.png"))),
                    })

    return archives


# =============================================================================
# Capture Logic
# =============================================================================


def capture_page(
    page,
    url: str,
    output_path: Path,
    name: str,
    wait_for_load: bool = True,
) -> dict:
    """Capture a single page screenshot.

    Returns metadata dict for this capture.
    Status will be:
    - "success": Page loaded and captured
    - "skipped": Page doesn't exist (404) - not an error, just not available
    - "error": Actual error during capture
    """
    log.info(f"Capturing {name}...")

    try:
        response = page.goto(url, wait_until="networkidle", timeout=30000)

        # Check for 404 or other client/server errors
        if response and response.status >= 400:
            log.warning(f"Skipping {name}: page not found (HTTP {response.status})")
            return {
                "name": name,
                "path": None,
                "url": url,
                "status": "skipped",
                "reason": f"HTTP {response.status}",
            }

        if wait_for_load:
            page.wait_for_timeout(1000)

        page.screenshot(path=str(output_path), full_page=False)

        return {
            "name": name,
            "path": str(output_path.name),
            "url": url,
            "status": "success",
        }
    except Exception as e:
        log.error(f"Error capturing {name}: {e}")
        return {
            "name": name,
            "path": None,
            "url": url,
            "status": "error",
            "error": str(e),
        }


def run_capture(
    base_url: str,
    project_name: str,
    project_root: Path,
    viewport: dict,
    pages: Optional[list[str]] = None,
) -> dict:
    """Run the full capture process.

    Args:
        base_url: Base URL to capture from
        project_name: Name of the project
        project_root: Path to project root
        viewport: Dict with 'width' and 'height'
        pages: Optional list of page names to capture (default: all)

    Returns:
        Metadata dict with capture results
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("playwright not installed.")
        log.error("Run: scripts/.venv/bin/pip install playwright && scripts/.venv/bin/playwright install chromium")
        raise RuntimeError("playwright not available")

    # Setup directories
    project_dir = IMAGES_DIR / project_name
    latest_dir = project_dir / "latest"

    # Archive previous captures
    archive_previous_captures(project_dir, latest_dir)

    # Create fresh latest directory
    latest_dir.mkdir(parents=True, exist_ok=True)

    # Determine pages to capture
    if pages:
        pages_to_capture = []
        for p in DEFAULT_PAGES:
            if p["name"] in pages:
                pages_to_capture.append(p)
    else:
        pages_to_capture = DEFAULT_PAGES

    # Metadata
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "project": project_name,
        "commit": get_git_commit(project_root),
        "base_url": base_url,
        "viewport": viewport,
        "pages": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=viewport)
        page = context.new_page()

        for page_config in pages_to_capture:
            name = page_config["name"]
            path = page_config["path"]

            # Special handling for chapter page detection
            if path is None and name == "chapter":
                path = find_chapter_page(page, base_url)
                if path is None:
                    log.warning(f"Skipping {name}: no chapter page found")
                    continue

            url = f"{base_url.rstrip('/')}/{path}"
            output_path = latest_dir / f"{name}.png"

            result = capture_page(page, url, output_path, name)
            metadata["pages"].append(result)

        browser.close()

    # Write metadata
    metadata_path = latest_dir / "capture.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

    return metadata


# =============================================================================
# CLI Entry Point
# =============================================================================


def cmd_capture(args) -> int:
    """Main entry point for the capture command."""
    log.header("Side-by-Side Blueprint Screenshot Capture")

    try:
        # Detect project
        if args.project:
            project_name = args.project
            project_root = Path.cwd()
        else:
            project_name, project_root = detect_project()

        log.info(f"Project: {project_name}")
        log.info(f"URL: {args.url}")

        # Parse viewport
        if "x" in args.viewport.lower():
            w, h = args.viewport.lower().split("x")
            viewport = {"width": int(w), "height": int(h)}
        else:
            viewport = DEFAULT_VIEWPORT

        # Parse pages
        pages = None
        if args.pages:
            pages = [p.strip() for p in args.pages.split(",")]

        # Run capture
        metadata = run_capture(
            base_url=args.url,
            project_name=project_name,
            project_root=project_root,
            viewport=viewport,
            pages=pages,
        )

        # Report results
        print()
        log.success("Capture complete!")
        log.info(f"Output: images/{project_name}/latest/")
        log.info(f"Commit: {metadata['commit']}")
        print()

        successful = [p for p in metadata["pages"] if p["status"] == "success"]
        skipped = [p for p in metadata["pages"] if p["status"] == "skipped"]
        failed = [p for p in metadata["pages"] if p["status"] == "error"]

        log.info(f"Captured {len(successful)} pages:")
        for p in successful:
            log.info(f"  - {p['name']}: {p['path']}")

        if skipped:
            print()
            log.warning(f"Skipped {len(skipped)} pages (not available in this project):")
            for p in skipped:
                log.warning(f"  - {p['name']}: {p.get('reason', 'not found')}")

        if failed:
            print()
            log.error(f"Failed {len(failed)} pages:")
            for p in failed:
                log.error(f"  - {p['name']}: {p.get('error', 'unknown error')}")
            return 1

        return 0

    except KeyboardInterrupt:
        log.warning("Capture interrupted")
        return 130
    except Exception as e:
        log.error(str(e))
        return 1
