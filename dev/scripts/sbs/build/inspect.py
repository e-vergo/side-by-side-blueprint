"""
Build inspection for Side-by-Side Blueprint.

Shows build state, artifact locations, and manifest contents.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from sbs.core.utils import get_git_commit, get_git_branch, log
from sbs.core import detect_project


# =============================================================================
# Build State Inspection
# =============================================================================


def get_dressed_artifacts(build_dir: Path) -> dict[str, int]:
    """Count dressed artifacts by module.

    Returns dict mapping module name to artifact count.
    """
    dressed_dir = build_dir / "dressed"
    if not dressed_dir.exists():
        return {}

    counts = {}
    for module_dir in dressed_dir.iterdir():
        if module_dir.is_dir():
            # Count label directories in each module
            labels = [d for d in module_dir.iterdir() if d.is_dir()]
            if labels:
                counts[module_dir.name] = len(labels)

    return counts


def get_manifest_summary(manifest_path: Path) -> Optional[dict[str, Any]]:
    """Get summary of manifest.json contents.

    Returns dict with node_count, edge_count, status_counts, etc.
    """
    if not manifest_path.exists():
        return None

    try:
        data = json.loads(manifest_path.read_text())

        summary = {
            "node_count": len(data.get("nodes", [])),
            "edge_count": len(data.get("edges", [])),
            "modules": list(set(n.get("module", "") for n in data.get("nodes", []))),
        }

        # Count statuses
        status_counts = {}
        for node in data.get("nodes", []):
            status = node.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        summary["status_counts"] = status_counts

        # Check results if present
        if "checkResults" in data:
            summary["check_results"] = data["checkResults"]

        return summary

    except Exception as e:
        return {"error": str(e)}


def get_runway_config(runway_json_path: Path) -> Optional[dict[str, Any]]:
    """Get runway configuration summary."""
    if not runway_json_path.exists():
        return None

    try:
        data = json.loads(runway_json_path.read_text())
        return {
            "title": data.get("title", ""),
            "projectName": data.get("projectName", ""),
            "githubUrl": data.get("githubUrl", ""),
            "baseUrl": data.get("baseUrl", ""),
            "hasDocgen": data.get("docgen4Url") is not None,
            "hasPaper": data.get("paperTexPath") is not None,
        }
    except Exception as e:
        return {"error": str(e)}


def get_site_pages(site_dir: Path) -> list[str]:
    """Get list of generated HTML pages."""
    if not site_dir.exists():
        return []

    return sorted([p.name for p in site_dir.glob("*.html")])


# =============================================================================
# Validation
# =============================================================================


def validate_site(site_dir: Path, config: dict) -> list[str]:
    """Validate generated site for issues.

    Returns list of issue descriptions.
    """
    issues = []

    if not site_dir.exists():
        issues.append("Site directory does not exist")
        return issues

    # Check required files
    required_files = ["index.html", "dep_graph.html"]
    for f in required_files:
        if not (site_dir / f).exists():
            issues.append(f"Missing required file: {f}")

    # Check manifest
    manifest_path = site_dir / "manifest.json"
    if not manifest_path.exists():
        issues.append("Missing manifest.json")
    else:
        try:
            data = json.loads(manifest_path.read_text())
            if not data.get("nodes"):
                issues.append("manifest.json has no nodes")
        except json.JSONDecodeError as e:
            issues.append(f"Invalid manifest.json: {e}")

    # Check assets
    for asset in ["common.css", "blueprint.css", "verso-code.js"]:
        if not (site_dir / asset).exists():
            issues.append(f"Missing asset: {asset}")

    # Check for paper if configured
    if config.get("hasPaper"):
        if not (site_dir / "paper.html").exists():
            issues.append("Paper configured but paper.html missing")

    # Check for broken internal links
    for html_file in site_dir.glob("*.html"):
        try:
            content = html_file.read_text()
            # Simple check for href to other .html files
            import re
            for match in re.finditer(r'href="([^"]+\.html)"', content):
                href = match.group(1)
                if not href.startswith("http") and not href.startswith("#"):
                    target = site_dir / href.lstrip("./")
                    if not target.exists():
                        issues.append(f"Broken link in {html_file.name}: {href}")
        except Exception:
            pass

    return issues


# =============================================================================
# CLI Entry Points
# =============================================================================


def cmd_inspect(args) -> int:
    """Main entry point for the inspect command."""
    log.header("Side-by-Side Blueprint Build Inspection")

    try:
        # Detect project
        project_name, project_root = detect_project()

        log.info(f"Project: {project_name}")
        log.info(f"Root: {project_root}")
        log.info(f"Branch: {get_git_branch(project_root)}")
        log.info(f"Commit: {get_git_commit(project_root)}")
        print()

        # Build directory
        build_dir = project_root / ".lake" / "build"
        site_dir = build_dir / "runway"

        # Runway config
        log.header("Configuration")
        config = get_runway_config(project_root / "runway.json")
        if config:
            if "error" in config:
                log.error(f"runway.json: {config['error']}")
            else:
                log.table_row("Title:", config.get("title", ""))
                log.table_row("Base URL:", config.get("baseUrl", ""))
                log.table_row("GitHub:", config.get("githubUrl", ""))
                log.table_row("DocGen4:", "Yes" if config.get("hasDocgen") else "No")
                log.table_row("Paper:", "Yes" if config.get("hasPaper") else "No")
        else:
            log.error("runway.json not found")

        print()

        # Dressed artifacts
        log.header("Build Artifacts")
        log.table_row("Build directory:", str(build_dir))

        dressed = get_dressed_artifacts(build_dir)
        if dressed:
            total = sum(dressed.values())
            log.table_row("Dressed artifacts:", f"{total} total")
            for module, count in sorted(dressed.items()):
                log.dim(f"  {module}: {count}")
        else:
            log.warning("No dressed artifacts found")

        # Site output
        if site_dir.exists():
            pages = get_site_pages(site_dir)
            log.table_row("Site directory:", str(site_dir))
            log.table_row("HTML pages:", str(len(pages)))
            if args.verbose:
                for page in pages:
                    log.dim(f"  {page}")
        else:
            log.warning("Site not generated yet")

        print()

        # Manifest
        log.header("Manifest")
        manifest_path = site_dir / "manifest.json"
        manifest = get_manifest_summary(manifest_path)
        if manifest:
            if "error" in manifest:
                log.error(f"manifest.json: {manifest['error']}")
            else:
                log.table_row("Nodes:", str(manifest.get("node_count", 0)))
                log.table_row("Edges:", str(manifest.get("edge_count", 0)))
                log.table_row("Modules:", str(len(manifest.get("modules", []))))

                if manifest.get("status_counts"):
                    log.info("Status breakdown:")
                    for status, count in sorted(manifest["status_counts"].items()):
                        log.dim(f"  {status}: {count}")

                if manifest.get("check_results"):
                    results = manifest["check_results"]
                    log.info("Validation:")
                    log.dim(f"  Connected: {results.get('isConnected', 'unknown')}")
                    log.dim(f"  Acyclic: {results.get('isAcyclic', 'unknown')}")
        else:
            log.warning("No manifest.json found")

        return 0

    except KeyboardInterrupt:
        log.warning("Interrupted")
        return 130
    except Exception as e:
        log.error(str(e))
        return 1


def cmd_validate(args) -> int:
    """Main entry point for the validate command."""
    log.header("Side-by-Side Blueprint Site Validation")

    try:
        # Detect project
        project_name, project_root = detect_project()

        log.info(f"Project: {project_name}")
        print()

        # Get config and site dir
        build_dir = project_root / ".lake" / "build"
        site_dir = build_dir / "runway"
        config = get_runway_config(project_root / "runway.json") or {}

        # Run validation
        issues = validate_site(site_dir, config)

        if not issues:
            log.success("All validation checks passed")
            return 0
        else:
            log.error(f"Found {len(issues)} issues:")
            for issue in issues:
                log.warning(f"  - {issue}")
            return 1

    except KeyboardInterrupt:
        log.warning("Interrupted")
        return 130
    except Exception as e:
        log.error(str(e))
        return 1
