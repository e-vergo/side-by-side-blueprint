"""
Screenshot capture for Side-by-Side Blueprint visual verification.

Captures key pages from a running blueprint site for visual diff testing.
"""

from __future__ import annotations

import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from sbs.core.utils import (
    ARCHIVE_DIR,
    IMAGES_DIR,  # Legacy alias
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
        # Exclusion patterns for non-chapter pages
        exclude_patterns = [
            "index", "dep_graph", "paper", "pdf", "verso",
            "introduction",
        ]

        # Try multiple starting points to find chapter links
        starting_pages = [
            "index.html",           # Dashboard
        ]

        candidates = []

        for start_page in starting_pages:
            try:
                page.goto(f"{base_url}/{start_page}", wait_until="networkidle", timeout=10000)

                # Look for chapter links in sidebar (.sidebar-chapter-panel) or any links
                all_links = page.query_selector_all(".sidebar-chapter-panel a[href$='.html'], a[href$='.html']")
                for link in all_links:
                    href = link.get_attribute("href")
                    if href and not any(x in href.lower() for x in exclude_patterns):
                        if not href.startswith("http"):
                            href = href.lstrip("./")
                        if href not in candidates:
                            candidates.append(href)

                if candidates:
                    break  # Found some candidates, no need to try other starting pages

            except Exception:
                continue

        # Try each candidate and pick one with theorem/proof content
        for candidate in candidates:
            try:
                page.goto(f"{base_url}/{candidate}", wait_until="networkidle", timeout=10000)
                # Look for theorem content indicators
                has_content = page.query_selector(
                    ".theorem-statement, .side-by-side, .lean-code, "
                    ".blueprint-theorem, .theorem_thmwrapper, .sbs-container"
                )
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
    log.info(f"Archived previous captures to: {archive_dir.relative_to(ARCHIVE_DIR)}")

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

    Includes timing_seconds for performance measurement.
    """
    log.info(f"Capturing {name}...")
    start_time = time.time()

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
                "timing_seconds": round(time.time() - start_time, 3),
            }

        if wait_for_load:
            page.wait_for_timeout(1000)

        page.screenshot(path=str(output_path), full_page=False)

        elapsed = time.time() - start_time
        return {
            "name": name,
            "path": str(output_path.name),
            "url": url,
            "status": "success",
            "timing_seconds": round(elapsed, 3),
        }
    except Exception as e:
        log.error(f"Error capturing {name}: {e}")
        return {
            "name": name,
            "path": None,
            "url": url,
            "status": "error",
            "error": str(e),
            "timing_seconds": round(time.time() - start_time, 3),
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
        Metadata dict with capture results including timing data
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("playwright not installed.")
        log.error("Run: scripts/.venv/bin/pip install playwright && scripts/.venv/bin/playwright install chromium")
        raise RuntimeError("playwright not available")

    capture_start = time.time()

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

    # Per-page timing aggregation
    page_timings: dict[str, float] = {}

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

            # Aggregate timing
            if "timing_seconds" in result:
                page_timings[f"capture_{name}"] = result["timing_seconds"]

        browser.close()

    # Total capture timing
    total_capture_time = time.time() - capture_start
    page_timings["capture_total"] = round(total_capture_time, 3)

    # Add timing summary to metadata
    metadata["timings"] = page_timings

    # Write metadata
    metadata_path = latest_dir / "capture.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

    return metadata


# =============================================================================
# Interactive Capture
# =============================================================================


def get_manifests_dir() -> Path:
    """Get path to interaction manifests directory."""
    from sbs.core.utils import get_sbs_root
    manifests_dir = get_sbs_root() / "archive" / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    return manifests_dir


def load_manifest(page_name: str) -> Optional[dict]:
    """Load interaction manifest for a page."""
    manifest_path = get_manifests_dir() / f"{page_name}_manifest.json"
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text())
        except Exception:
            return None
    return None


def save_manifest(page_name: str, manifest: dict) -> None:
    """Save interaction manifest for a page."""
    manifest_path = get_manifests_dir() / f"{page_name}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))


def discover_interactive_elements(page, page_name: str) -> list[dict]:
    """Discover interactive elements on a page.

    Returns list of discovered elements with selectors.
    """
    try:
        from sbs.tests.compliance.criteria import get_interactive_elements
        predefined = get_interactive_elements(page_name)
    except ImportError:
        predefined = []

    discovered = []

    for elem_def in predefined:
        selector = elem_def.get("selector", "")
        if not selector:
            continue

        try:
            elements = page.query_selector_all(selector)
            count = len(elements)

            if count > 0:
                discovered.append({
                    "id": elem_def.get("id", selector),
                    "selector": selector,
                    "type": elem_def.get("type", "click"),
                    "count": count,
                    "sample_count": elem_def.get("sample_count", 1),
                })
        except Exception:
            continue

    return discovered


def capture_interactive_states(
    page,
    base_url: str,
    page_config: dict,
    output_dir: Path,
    manifest: Optional[dict] = None,
) -> list[dict]:
    """Capture interactive states for a page.

    Args:
        page: Playwright page object
        base_url: Base URL of the site
        page_config: Page configuration dict
        output_dir: Directory to save screenshots
        manifest: Optional frozen manifest (if None, discover elements)

    Returns:
        List of interaction capture results
    """
    page_name = page_config["name"]
    page_path = page_config["path"]

    if page_path is None:
        return []

    results = []

    # Navigate to page
    try:
        page.goto(f"{base_url.rstrip('/')}/{page_path}", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(500)
    except Exception as e:
        log.warning(f"Could not load {page_name} for interactive capture: {e}")
        return []

    # Discover or use frozen manifest
    if manifest:
        elements = manifest.get("interactions", [])
    else:
        elements = discover_interactive_elements(page, page_name)

        # Save manifest for future runs
        if elements:
            save_manifest(page_name, {
                "page": page_name,
                "discovered_at": datetime.now().isoformat(),
                "interactions": elements,
            })

    # Capture each interactive state
    for elem in elements:
        elem_id = elem.get("id", "unknown")
        selector = elem.get("selector", "")
        elem_type = elem.get("type", "click")
        sample_count = elem.get("sample_count", 1)

        if not selector:
            continue

        try:
            targets = page.query_selector_all(selector)

            if not targets:
                continue

            # Limit to sample_count
            targets_to_capture = targets[:sample_count]

            for idx, target in enumerate(targets_to_capture):
                interaction_name = f"{elem_id}_{idx}" if len(targets_to_capture) > 1 else elem_id
                output_path = output_dir / f"{page_name}_{interaction_name}.png"

                try:
                    if elem_type == "click":
                        target.click()
                        page.wait_for_timeout(500)
                    elif elem_type == "hover":
                        target.hover()
                        page.wait_for_timeout(300)

                    page.screenshot(path=str(output_path), full_page=False)

                    results.append({
                        "page": page_name,
                        "interaction": interaction_name,
                        "selector": selector,
                        "type": elem_type,
                        "status": "success",
                        "path": str(output_path.name),
                    })

                    # Reset state for clicks (go back or re-navigate)
                    if elem_type == "click":
                        # Try to close any modals
                        try:
                            close_btn = page.query_selector(".dep-closebtn, .modal-close, .close")
                            if close_btn:
                                close_btn.click()
                                page.wait_for_timeout(300)
                        except Exception:
                            pass

                except Exception as e:
                    results.append({
                        "page": page_name,
                        "interaction": interaction_name,
                        "selector": selector,
                        "type": elem_type,
                        "status": "error",
                        "error": str(e),
                    })

        except Exception as e:
            log.warning(f"Error capturing {elem_id} on {page_name}: {e}")

    return results


def run_interactive_capture(
    base_url: str,
    project_name: str,
    project_root: Path,
    viewport: dict,
    pages: Optional[list[str]] = None,
    use_frozen_manifests: bool = True,
) -> dict:
    """Run capture including interactive states.

    Args:
        base_url: Base URL to capture from
        project_name: Name of the project
        project_root: Path to project root
        viewport: Dict with 'width' and 'height'
        pages: Optional list of page names to capture (default: all)
        use_frozen_manifests: If True, use saved manifests; if False, rediscover

    Returns:
        Metadata dict with capture results including interactions and timing data
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("playwright not installed.")
        raise RuntimeError("playwright not available")

    capture_start = time.time()

    # Setup directories
    project_dir = IMAGES_DIR / project_name
    latest_dir = project_dir / "latest"

    # Archive previous captures
    archive_previous_captures(project_dir, latest_dir)

    # Create fresh latest directory
    latest_dir.mkdir(parents=True, exist_ok=True)

    # Determine pages to capture
    if pages:
        pages_to_capture = [p for p in DEFAULT_PAGES if p["name"] in pages]
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
        "interactions": [],
    }

    # Per-page timing aggregation
    page_timings: dict[str, float] = {}

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
                page_config = dict(page_config)
                page_config["path"] = path

            url = f"{base_url.rstrip('/')}/{path}"
            output_path = latest_dir / f"{name}.png"

            # Capture static page (timing included in result)
            result = capture_page(page, url, output_path, name)
            metadata["pages"].append(result)

            # Aggregate page timing
            if "timing_seconds" in result:
                page_timings[f"capture_{name}"] = result["timing_seconds"]

            # Capture interactive states
            if result["status"] == "success":
                interactive_start = time.time()
                manifest = load_manifest(name) if use_frozen_manifests else None
                interactions = capture_interactive_states(
                    page, base_url, page_config, latest_dir, manifest
                )
                metadata["interactions"].extend(interactions)
                interactive_elapsed = time.time() - interactive_start
                page_timings[f"interactive_{name}"] = round(interactive_elapsed, 3)

        browser.close()

    # Total capture timing
    total_capture_time = time.time() - capture_start
    page_timings["capture_total"] = round(total_capture_time, 3)

    # Add timing summary to metadata
    metadata["timings"] = page_timings

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

        # Run capture (with or without interactive states)
        interactive = getattr(args, 'interactive', False)
        rediscover = getattr(args, 'rediscover', False)

        if interactive:
            metadata = run_interactive_capture(
                base_url=args.url,
                project_name=project_name,
                project_root=project_root,
                viewport=viewport,
                pages=pages,
                use_frozen_manifests=not rediscover,
            )
        else:
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
        log.info(f"Output: archive/{project_name}/latest/")
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

        # Report interactive captures
        interactions = metadata.get("interactions", [])
        if interactions:
            print()
            int_success = [i for i in interactions if i.get("status") == "success"]
            int_failed = [i for i in interactions if i.get("status") == "error"]

            log.info(f"Captured {len(int_success)} interactive states:")
            for i in int_success[:10]:  # Limit output
                log.info(f"  - {i['page']}_{i['interaction']}")
            if len(int_success) > 10:
                log.info(f"  ... and {len(int_success) - 10} more")

            if int_failed:
                log.warning(f"Failed {len(int_failed)} interactive captures")

        return 0

    except KeyboardInterrupt:
        log.warning("Capture interrupted")
        return 130
    except Exception as e:
        log.error(str(e))
        return 1
