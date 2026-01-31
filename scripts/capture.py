#!/usr/bin/env python3
"""
Screenshot capture script for Side-by-Side Blueprint visual verification.

Captures key pages from a running blueprint site for visual diff testing.

Usage:
    python capture.py                    # Capture from http://localhost:8000
    python capture.py --url http://...   # Capture from custom URL
    python capture.py --help             # Show help
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add venv to path if running directly
SCRIPT_DIR = Path(__file__).parent
VENV_SITE_PACKAGES = SCRIPT_DIR / ".venv" / "lib"
if VENV_SITE_PACKAGES.exists():
    # Find the python version directory
    for p in VENV_SITE_PACKAGES.iterdir():
        site_pkg = p / "site-packages"
        if site_pkg.exists():
            sys.path.insert(0, str(site_pkg))
            break

try:
    from playwright.sync_api import sync_playwright, Page
except ImportError:
    print("Error: playwright not installed.")
    print("Run: scripts/.venv/bin/pip install playwright && scripts/.venv/bin/playwright install chromium")
    sys.exit(1)


# =============================================================================
# Constants
# =============================================================================

SBS_ROOT = Path("/Users/eric/GitHub/Side-By-Side-Blueprint")
IMAGES_DIR = SBS_ROOT / "images"
DEFAULT_URL = "http://localhost:8000"
DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}

# Pages to capture (relative to base URL)
PAGES_TO_CAPTURE = [
    {"name": "dashboard", "path": "index.html", "description": "Dashboard homepage"},
    {"name": "dep_graph", "path": "dep_graph.html", "description": "Dependency graph"},
    {"name": "chapter", "path": None, "description": "First chapter page"},  # Will be detected
]


# =============================================================================
# Utilities
# =============================================================================


def get_git_commit(directory: Path) -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=directory,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()[:12]
    except Exception:
        return "unknown"


def detect_project() -> tuple[str, Path]:
    """Detect project from runway.json in current directory.

    Returns (project_name, project_root).
    """
    cwd = Path.cwd()
    runway_json = cwd / "runway.json"

    if not runway_json.exists():
        raise RuntimeError(f"runway.json not found in {cwd}")

    data = json.loads(runway_json.read_text())
    project_name = data.get("projectName", cwd.name)

    return project_name, cwd


def archive_previous_captures(project_dir: Path, latest_dir: Path) -> None:
    """Archive previous captures if they exist."""
    if not latest_dir.exists():
        return

    # Read metadata to get timestamp
    metadata_path = latest_dir / "capture.json"
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text())
            timestamp = metadata.get("timestamp", datetime.now().isoformat())
            # Convert to filesystem-safe format
            archive_name = timestamp.replace(":", "-").replace("T", "_").split(".")[0]
        except Exception:
            archive_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    else:
        archive_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    archive_dir = project_dir / "archive" / archive_name
    archive_dir.parent.mkdir(parents=True, exist_ok=True)

    # Move latest to archive
    shutil.move(str(latest_dir), str(archive_dir))
    print(f"  Archived previous captures to: {archive_dir.relative_to(IMAGES_DIR)}")


def find_chapter_page(page: Page, base_url: str) -> Optional[str]:
    """Find the first blueprint chapter page with actual content (side-by-side displays)."""
    try:
        # Navigate to dashboard first
        page.goto(f"{base_url}/index.html", wait_until="networkidle")

        # Exclusion patterns for non-chapter pages
        exclude_patterns = [
            "index", "dep_graph", "paper", "pdf", "verso",
            "blueprint_verso", "pdf_verso", "paper_verso",
            "introduction",  # Skip intro pages - they often lack side-by-side content
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
                # Check for side-by-side content markers
                has_content = page.query_selector(".theorem-statement, .side-by-side, .lean-code, .blueprint-theorem")
                if has_content:
                    return candidate
            except Exception:
                continue

        # Fallback to first candidate if none have content markers
        if candidates:
            return candidates[0]

        return None
    except Exception as e:
        print(f"  Warning: Could not find chapter page: {e}")
        return None


# =============================================================================
# Capture Logic
# =============================================================================


def capture_page(
    page: Page,
    url: str,
    output_path: Path,
    name: str,
    wait_for_load: bool = True,
) -> dict:
    """Capture a single page screenshot.

    Returns metadata dict for this capture.
    """
    print(f"  Capturing {name}...")

    try:
        # Navigate with timeout
        page.goto(url, wait_until="networkidle", timeout=30000)

        if wait_for_load:
            # Additional wait for any JavaScript rendering
            page.wait_for_timeout(1000)

        # Take screenshot
        page.screenshot(path=str(output_path), full_page=False)

        return {
            "name": name,
            "path": str(output_path.name),
            "url": url,
            "status": "success",
        }
    except Exception as e:
        print(f"    Error capturing {name}: {e}")
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
) -> dict:
    """Run the full capture process.

    Returns metadata dict.
    """
    # Setup directories
    project_dir = IMAGES_DIR / project_name
    latest_dir = project_dir / "latest"

    # Archive previous captures
    archive_previous_captures(project_dir, latest_dir)

    # Create fresh latest directory
    latest_dir.mkdir(parents=True, exist_ok=True)

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

        # Capture each page
        for page_config in PAGES_TO_CAPTURE:
            name = page_config["name"]
            path = page_config["path"]

            # Special handling for chapter page detection
            if path is None and name == "chapter":
                path = find_chapter_page(page, base_url)
                if path is None:
                    print(f"  Skipping {name}: no chapter page found")
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
# CLI
# =============================================================================


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Capture screenshots of Side-by-Side Blueprint site",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python capture.py                    # Capture from localhost:8000
    python capture.py --url http://...   # Capture from custom URL
    python capture.py --width 1280       # Custom viewport width
        """,
    )

    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Base URL to capture from (default: {DEFAULT_URL})",
    )

    parser.add_argument(
        "--width",
        type=int,
        default=DEFAULT_VIEWPORT["width"],
        help=f"Viewport width (default: {DEFAULT_VIEWPORT['width']})",
    )

    parser.add_argument(
        "--height",
        type=int,
        default=DEFAULT_VIEWPORT["height"],
        help=f"Viewport height (default: {DEFAULT_VIEWPORT['height']})",
    )

    parser.add_argument(
        "--project",
        default=None,
        help="Project name (default: detect from runway.json)",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    print("Side-by-Side Blueprint Screenshot Capture")
    print("=" * 45)

    try:
        # Detect project
        if args.project:
            project_name = args.project
            project_root = Path.cwd()
        else:
            project_name, project_root = detect_project()

        print(f"Project: {project_name}")
        print(f"URL: {args.url}")

        viewport = {"width": args.width, "height": args.height}

        # Run capture
        metadata = run_capture(
            base_url=args.url,
            project_name=project_name,
            project_root=project_root,
            viewport=viewport,
        )

        # Report results
        print()
        print("Capture complete!")
        print(f"  Output: images/{project_name}/latest/")
        print(f"  Commit: {metadata['commit']}")
        print()

        successful = [p for p in metadata["pages"] if p["status"] == "success"]
        failed = [p for p in metadata["pages"] if p["status"] == "error"]

        print(f"Captured {len(successful)} pages:")
        for p in successful:
            print(f"  - {p['name']}: {p['path']}")

        if failed:
            print(f"\nFailed {len(failed)} pages:")
            for p in failed:
                print(f"  - {p['name']}: {p.get('error', 'unknown error')}")
            return 1

        return 0

    except KeyboardInterrupt:
        print("\nCapture interrupted")
        return 130
    except Exception as e:
        print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
