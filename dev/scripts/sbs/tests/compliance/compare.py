"""
Image comparison for Side-by-Side Blueprint visual verification.

Compares latest screenshots to previous captures to detect visual changes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sbs.core.utils import ARCHIVE_DIR, IMAGES_DIR, detect_project, log


# =============================================================================
# Data Types
# =============================================================================


@dataclass
class ComparisonResult:
    """Result of comparing two images."""

    page_name: str
    latest_path: Optional[Path]
    baseline_path: Optional[Path]
    status: str  # "identical", "different", "missing_latest", "missing_baseline", "new"
    difference_percent: Optional[float] = None
    error: Optional[str] = None


# =============================================================================
# Image Comparison
# =============================================================================


def get_most_recent_archive(project_dir: Path) -> Optional[Path]:
    """Get the most recent archive directory.

    Returns None if no archives exist.
    """
    archive_dir = project_dir / "archive"
    if not archive_dir.exists():
        return None

    archives = sorted(archive_dir.iterdir(), reverse=True)
    for archive in archives:
        if archive.is_dir() and (archive / "capture.json").exists():
            return archive

    return None


def compare_images(image1: Path, image2: Path) -> tuple[bool, float]:
    """Compare two images and return (are_identical, difference_percent).

    Uses PIL to perform pixel-by-pixel comparison.
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        # Without PIL/numpy, just compare file sizes as a rough check
        size1 = image1.stat().st_size
        size2 = image2.stat().st_size
        if size1 == size2:
            # Could be same, check bytes
            if image1.read_bytes() == image2.read_bytes():
                return True, 0.0
            return False, 1.0  # Unknown difference
        return False, abs(size1 - size2) / max(size1, size2) * 100

    img1 = Image.open(image1).convert("RGB")
    img2 = Image.open(image2).convert("RGB")

    # If sizes differ, resize to match (and mark as different)
    if img1.size != img2.size:
        # Significant size difference
        return False, 100.0

    arr1 = np.array(img1)
    arr2 = np.array(img2)

    # Calculate pixel differences
    diff = np.abs(arr1.astype(float) - arr2.astype(float))
    total_pixels = arr1.size
    changed_pixels = np.sum(diff > 0) / 3  # Divide by 3 for RGB channels

    difference_percent = (changed_pixels / (total_pixels / 3)) * 100

    # Consider identical if less than 0.1% difference (accounts for compression artifacts)
    is_identical = difference_percent < 0.1

    return is_identical, difference_percent


def compare_captures(
    latest_dir: Path,
    baseline_dir: Path,
) -> list[ComparisonResult]:
    """Compare all pages between latest and baseline.

    Returns list of ComparisonResult for each page.
    """
    results = []

    # Get page lists from both captures
    latest_pages = set()
    baseline_pages = set()

    latest_metadata = latest_dir / "capture.json"
    baseline_metadata = baseline_dir / "capture.json"

    if latest_metadata.exists():
        data = json.loads(latest_metadata.read_text())
        for page in data.get("pages", []):
            if page.get("status") == "success" and page.get("path"):
                latest_pages.add(page["name"])

    if baseline_metadata.exists():
        data = json.loads(baseline_metadata.read_text())
        for page in data.get("pages", []):
            if page.get("status") == "success" and page.get("path"):
                baseline_pages.add(page["name"])

    # Also check for PNG files directly
    for png in latest_dir.glob("*.png"):
        latest_pages.add(png.stem)
    for png in baseline_dir.glob("*.png"):
        baseline_pages.add(png.stem)

    all_pages = latest_pages | baseline_pages

    for page_name in sorted(all_pages):
        latest_path = latest_dir / f"{page_name}.png"
        baseline_path = baseline_dir / f"{page_name}.png"

        if not latest_path.exists():
            results.append(ComparisonResult(
                page_name=page_name,
                latest_path=None,
                baseline_path=baseline_path,
                status="missing_latest",
            ))
        elif not baseline_path.exists():
            results.append(ComparisonResult(
                page_name=page_name,
                latest_path=latest_path,
                baseline_path=None,
                status="new",
            ))
        else:
            try:
                is_identical, diff_percent = compare_images(latest_path, baseline_path)
                results.append(ComparisonResult(
                    page_name=page_name,
                    latest_path=latest_path,
                    baseline_path=baseline_path,
                    status="identical" if is_identical else "different",
                    difference_percent=diff_percent,
                ))
            except Exception as e:
                results.append(ComparisonResult(
                    page_name=page_name,
                    latest_path=latest_path,
                    baseline_path=baseline_path,
                    status="error",
                    error=str(e),
                ))

    return results


# =============================================================================
# CLI Entry Point
# =============================================================================


def cmd_compare(args) -> int:
    """Main entry point for the compare command."""
    log.header("Side-by-Side Blueprint Image Comparison")

    try:
        # Detect project
        if args.project:
            project_name = args.project
        else:
            project_name, _ = detect_project()

        log.info(f"Project: {project_name}")

        # Setup paths
        project_dir = IMAGES_DIR / project_name
        latest_dir = project_dir / "latest"

        if not latest_dir.exists():
            log.error(f"No latest captures found at {latest_dir}")
            log.info("Run 'sbs capture' first to create captures")
            return 1

        # Find baseline
        if args.baseline:
            baseline_dir = project_dir / "archive" / args.baseline
            if not baseline_dir.exists():
                log.error(f"Baseline not found: {args.baseline}")
                return 1
        else:
            baseline_dir = get_most_recent_archive(project_dir)
            if baseline_dir is None:
                log.error("No previous captures to compare against")
                log.info("This appears to be the first capture for this project")
                return 0

        log.info(f"Comparing: latest vs {baseline_dir.name}")
        print()

        # Run comparison
        results = compare_captures(latest_dir, baseline_dir)

        # Report results
        has_differences = False
        has_errors = False

        for result in results:
            if result.status == "identical":
                log.success(f"{result.page_name}: identical")
            elif result.status == "different":
                has_differences = True
                diff_str = f"{result.difference_percent:.2f}%" if result.difference_percent else "unknown"
                log.warning(f"{result.page_name}: DIFFERENT ({diff_str} changed)")
            elif result.status == "new":
                has_differences = True
                log.info(f"{result.page_name}: NEW (no baseline)")
            elif result.status == "missing_latest":
                has_differences = True
                log.warning(f"{result.page_name}: MISSING in latest")
            elif result.status == "error":
                has_errors = True
                log.error(f"{result.page_name}: error - {result.error}")

        print()

        # Summary
        identical = len([r for r in results if r.status == "identical"])
        different = len([r for r in results if r.status in ("different", "new", "missing_latest")])
        errors = len([r for r in results if r.status == "error"])

        log.info(f"Summary: {identical} identical, {different} different, {errors} errors")

        if has_differences:
            return 1
        elif has_errors:
            return 2
        else:
            return 0

    except KeyboardInterrupt:
        log.warning("Comparison interrupted")
        return 130
    except Exception as e:
        log.error(str(e))
        return 1


def cmd_history(args) -> int:
    """Main entry point for the history command."""
    log.header("Capture History")

    try:
        # Detect project
        if args.project:
            project_name = args.project
        else:
            project_name, _ = detect_project()

        log.info(f"Project: {project_name}")
        print()

        # Get history
        project_dir = IMAGES_DIR / project_name

        # Check latest
        latest_dir = project_dir / "latest"
        if latest_dir.exists():
            metadata_path = latest_dir / "capture.json"
            if metadata_path.exists():
                metadata = json.loads(metadata_path.read_text())
                timestamp = metadata.get("timestamp", "unknown")
                commit = metadata.get("commit", "unknown")
                pages = len([p for p in metadata.get("pages", []) if p.get("status") == "success"])
                log.info(f"[latest] {timestamp} (commit: {commit}, {pages} pages)")
            else:
                pages = len(list(latest_dir.glob("*.png")))
                log.info(f"[latest] ({pages} pages)")
        else:
            log.info("[latest] No current captures")

        print()

        # Get archives
        archive_dir = project_dir / "archive"
        if archive_dir.exists():
            archives = sorted(archive_dir.iterdir(), reverse=True)
            if archives:
                log.info("Archives:")
                for archive in archives[:20]:  # Show last 20
                    if archive.is_dir():
                        metadata_path = archive / "capture.json"
                        if metadata_path.exists():
                            metadata = json.loads(metadata_path.read_text())
                            timestamp = metadata.get("timestamp", archive.name)
                            commit = metadata.get("commit", "unknown")
                            pages = len([p for p in metadata.get("pages", []) if p.get("status") == "success"])
                            log.info(f"  {archive.name} (commit: {commit}, {pages} pages)")
                        else:
                            pages = len(list(archive.glob("*.png")))
                            log.info(f"  {archive.name} ({pages} pages)")

                if len(archives) > 20:
                    log.dim(f"  ... and {len(archives) - 20} more")
            else:
                log.info("No archives yet")
        else:
            log.info("No archives yet")

        return 0

    except KeyboardInterrupt:
        log.warning("Interrupted")
        return 130
    except Exception as e:
        log.error(str(e))
        return 1
