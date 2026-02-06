"""
Watch mode for Side-by-Side Blueprint.

Monitors file changes and triggers incremental site regeneration.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import threading
import time
from enum import Enum, auto
from pathlib import Path
from typing import Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from sbs.core.utils import log, SBS_ROOT


# =============================================================================
# Constants
# =============================================================================

# Known project paths relative to monorepo root
PROJECT_PATHS: dict[str, str] = {
    "SBSTest": "toolchain/SBS-Test",
    "GCR": "showcase/General_Crystallographic_Restriction",
    "PNT": "showcase/PrimeNumberTheoremAnd",
}

DEBOUNCE_SECONDS = 0.5


# =============================================================================
# Change Classification
# =============================================================================


class ChangeAction(Enum):
    """What kind of regeneration is needed."""
    COPY_ASSETS = auto()      # CSS/JS changed -> copy to _site
    REGEN_PAGES = auto()      # Artifact changed -> regenerate affected pages
    REGEN_GRAPH = auto()      # Graph topology changed -> re-layout graph
    RECOLOR_GRAPH = auto()    # Status-only change -> recolor nodes in SVG
    FULL_SITE_REGEN = auto()  # Template changed -> full page regeneration
    FULL_REBUILD = auto()     # Config changed -> full rebuild


class ChangeClassifier:
    """Classifies file change events into regeneration actions."""

    def __init__(
        self,
        project_root: Path,
        assets_dir: Path,
        dressed_dir: Path,
    ):
        self.project_root = project_root
        self.assets_dir = assets_dir
        self.dressed_dir = dressed_dir
        self._previous_manifest: Optional[dict] = None
        self._load_manifest()

    def _load_manifest(self) -> None:
        """Load the current manifest for topology comparison."""
        manifest_path = (
            self.project_root / ".lake" / "build" / "runway" / "manifest.json"
        )
        if manifest_path.exists():
            try:
                self._previous_manifest = json.loads(manifest_path.read_text())
            except (json.JSONDecodeError, OSError):
                self._previous_manifest = None

    def classify(self, path: Path) -> Optional[ChangeAction]:
        """Classify a changed file into a regeneration action.

        Returns None if the change should be ignored.
        """
        path_str = str(path)

        # Ignore hidden files, __pycache__, .lake internals (not dressed)
        if any(
            part.startswith(".")
            for part in path.parts
            if part not in (".lake",)
        ):
            return None
        if "__pycache__" in path_str:
            return None

        # CSS/JS assets
        if self._is_asset(path):
            return ChangeAction.COPY_ASSETS

        # Dressed artifacts (JSON files from Lean elaboration)
        if self._is_dressed_artifact(path):
            return self._classify_artifact_change(path)

        # Runway templates (Lean source in Runway repo)
        if self._is_runway_template(path):
            return ChangeAction.FULL_SITE_REGEN

        # runway.json config
        if path.name == "runway.json" and path.parent == self.project_root:
            return ChangeAction.FULL_REBUILD

        return None

    def _is_asset(self, path: Path) -> bool:
        """Check if the path is a CSS/JS asset file."""
        try:
            path.relative_to(self.assets_dir)
            return path.suffix in (".css", ".js")
        except ValueError:
            return False

    def _is_dressed_artifact(self, path: Path) -> bool:
        """Check if the path is a dressed artifact."""
        try:
            path.relative_to(self.dressed_dir)
            return path.suffix == ".json"
        except ValueError:
            return False

    def _is_runway_template(self, path: Path) -> bool:
        """Check if the path is a Runway Lean template file."""
        runway_path = SBS_ROOT / "toolchain" / "Runway"
        try:
            path.relative_to(runway_path)
            return path.suffix == ".lean"
        except ValueError:
            return False

    def _classify_artifact_change(self, path: Path) -> ChangeAction:
        """Determine if an artifact change affects graph topology or just status.

        For now, we conservatively treat all artifact changes as page regen.
        A more sophisticated version could diff the manifest to detect
        topology vs. status-only changes.
        """
        # Check if this is a manifest.json (graph data)
        if path.name == "manifest.json":
            return self._check_topology_change(path)

        # Individual declaration artifacts -> page regen
        return ChangeAction.REGEN_PAGES

    def _check_topology_change(self, manifest_path: Path) -> ChangeAction:
        """Compare new manifest against previous to detect topology changes."""
        if self._previous_manifest is None:
            return ChangeAction.REGEN_GRAPH

        try:
            new_manifest = json.loads(manifest_path.read_text())
        except (json.JSONDecodeError, OSError):
            return ChangeAction.REGEN_GRAPH

        old_nodes = {n.get("id") for n in self._previous_manifest.get("nodes", [])}
        new_nodes = {n.get("id") for n in new_manifest.get("nodes", [])}

        old_edges = {
            (e.get("from"), e.get("to"))
            for e in self._previous_manifest.get("edges", [])
        }
        new_edges = {
            (e.get("from"), e.get("to"))
            for e in new_manifest.get("edges", [])
        }

        # Topology changed if nodes or edges differ
        if old_nodes != new_nodes or old_edges != new_edges:
            self._previous_manifest = new_manifest
            return ChangeAction.REGEN_GRAPH

        # Only status/metadata changed
        self._previous_manifest = new_manifest
        return ChangeAction.RECOLOR_GRAPH


# =============================================================================
# Debouncer
# =============================================================================


class Debouncer:
    """Batches rapid file change events into a single action.

    Collects events for `delay` seconds after the last event,
    then fires the highest-priority action from the batch.
    """

    # Priority: higher number = more work = takes precedence
    _PRIORITY = {
        ChangeAction.COPY_ASSETS: 1,
        ChangeAction.RECOLOR_GRAPH: 2,
        ChangeAction.REGEN_PAGES: 3,
        ChangeAction.REGEN_GRAPH: 4,
        ChangeAction.FULL_SITE_REGEN: 5,
        ChangeAction.FULL_REBUILD: 6,
    }

    def __init__(self, delay: float, callback):
        self.delay = delay
        self.callback = callback
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._pending_actions: list[ChangeAction] = []
        self._pending_paths: list[Path] = []

    def trigger(self, action: ChangeAction, path: Path) -> None:
        """Register a change event. Resets the debounce timer."""
        with self._lock:
            self._pending_actions.append(action)
            self._pending_paths.append(path)

            if self._timer is not None:
                self._timer.cancel()

            self._timer = threading.Timer(self.delay, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        """Called after debounce period. Fires the highest-priority action."""
        with self._lock:
            if not self._pending_actions:
                return

            # Get highest priority action
            best_action = max(
                self._pending_actions,
                key=lambda a: self._PRIORITY.get(a, 0),
            )
            paths = list(self._pending_paths)

            self._pending_actions.clear()
            self._pending_paths.clear()
            self._timer = None

        self.callback(best_action, paths)

    def cancel(self) -> None:
        """Cancel any pending debounce timer."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._pending_actions.clear()
            self._pending_paths.clear()


# =============================================================================
# Regenerator
# =============================================================================


class Regenerator:
    """Executes regeneration actions."""

    def __init__(self, project_root: Path, project_name: str, assets_dir: Path):
        self.project_root = project_root
        self.project_name = project_name
        self.assets_dir = assets_dir
        self.site_dir = project_root / ".lake" / "build" / "runway"
        self._regen_count = 0

    @property
    def regen_count(self) -> int:
        return self._regen_count

    def execute(self, action: ChangeAction, paths: list[Path]) -> None:
        """Execute a regeneration action."""
        self._regen_count += 1
        start = time.time()

        try:
            if action == ChangeAction.COPY_ASSETS:
                self._copy_assets(paths)
            elif action == ChangeAction.RECOLOR_GRAPH:
                self._regen_graph()
            elif action == ChangeAction.REGEN_PAGES:
                self._regen_site()
            elif action == ChangeAction.REGEN_GRAPH:
                self._regen_dep_graph()
                self._regen_site()
            elif action == ChangeAction.FULL_SITE_REGEN:
                self._regen_site()
            elif action == ChangeAction.FULL_REBUILD:
                self._full_rebuild()

            elapsed = time.time() - start
            log.success(
                f"[{self._regen_count}] {action.name} completed in {elapsed:.1f}s"
            )
        except Exception as e:
            elapsed = time.time() - start
            log.error(
                f"[{self._regen_count}] {action.name} failed after {elapsed:.1f}s: {e}"
            )

    def _copy_assets(self, paths: list[Path]) -> None:
        """Copy changed CSS/JS files to the site output directory."""
        site_assets = self.site_dir / "assets"
        if not site_assets.exists():
            log.warning("Site assets directory not found, falling back to full regen")
            self._regen_site()
            return

        copied = 0
        for path in paths:
            if path.suffix in (".css", ".js") and path.exists():
                dest = site_assets / path.name
                shutil.copy2(path, dest)
                copied += 1
                log.info(f"  Copied {path.name} -> {dest}")

        if copied == 0:
            log.info("  No asset files to copy")

    def _regen_dep_graph(self) -> None:
        """Regenerate the dependency graph."""
        log.info("  Regenerating dependency graph...")

        dress_path = SBS_ROOT / "toolchain" / "Dress"
        extract_exe = dress_path / ".lake" / "build" / "bin" / "extract_blueprint"

        if not extract_exe.exists():
            log.warning("extract_blueprint not found, skipping graph regen")
            return

        cmd = [
            "lake", "env",
            str(extract_exe),
            "graph",
            "--build", str(self.project_root / ".lake" / "build"),
            self.project_name,
        ]

        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            log.error(f"  Graph generation failed: {result.stderr[:200]}")
        else:
            log.info("  Dependency graph regenerated")

    def _regen_graph(self) -> None:
        """Recolor graph nodes (status-only change).

        For now, this delegates to full graph regeneration since
        the SVG is generated from Lean code. A future optimization
        could do in-place SVG edits.
        """
        self._regen_dep_graph()
        self._regen_site()

    def _regen_site(self) -> None:
        """Regenerate the site with Runway."""
        log.info("  Regenerating site...")

        runway_path = SBS_ROOT / "toolchain" / "Runway"
        output_dir = self.project_root / ".lake" / "build" / "runway"

        cmd = [
            "lake", "exe", "runway",
            "--build-dir", str(self.project_root / ".lake" / "build"),
            "--output", str(output_dir),
            "build",
            str(self.project_root / "runway.json"),
        ]

        result = subprocess.run(
            cmd,
            cwd=runway_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            log.error(f"  Site generation failed: {result.stderr[:300]}")
        else:
            log.info("  Site regenerated")

            # Also generate paper if configured
            self._regen_paper()

    def _regen_paper(self) -> None:
        """Regenerate paper if the project has one configured."""
        runway_json_path = self.project_root / "runway.json"
        if not runway_json_path.exists():
            return

        try:
            config = json.loads(runway_json_path.read_text())
        except (json.JSONDecodeError, OSError):
            return

        has_paper = bool(config.get("paperTexPath"))
        if not has_paper:
            return

        runway_path = SBS_ROOT / "toolchain" / "Runway"
        output_dir = self.project_root / ".lake" / "build" / "runway"

        cmd = [
            "lake", "exe", "runway",
            "--build-dir", str(self.project_root / ".lake" / "build"),
            "--output", str(output_dir),
            "paper",
            str(self.project_root / "runway.json"),
        ]

        result = subprocess.run(
            cmd,
            cwd=runway_path,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            log.info("  Paper regenerated")

    def _full_rebuild(self) -> None:
        """Trigger a full rebuild via build.py."""
        log.info("  Triggering full rebuild...")

        cmd = [
            sys.executable,
            str(SBS_ROOT / "dev" / "scripts" / "build.py"),
        ]

        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            log.error(f"  Full rebuild failed: {result.stderr[:300]}")
        else:
            log.info("  Full rebuild complete")


# =============================================================================
# File System Event Handler
# =============================================================================


class SBSEventHandler(FileSystemEventHandler):
    """Handles file system events and classifies them for regeneration."""

    def __init__(self, classifier: ChangeClassifier, debouncer: Debouncer):
        super().__init__()
        self.classifier = classifier
        self.debouncer = debouncer

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle(event)

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle(event)

    def _handle(self, event: FileSystemEvent) -> None:
        path = Path(event.src_path)
        action = self.classifier.classify(path)
        if action is not None:
            log.info(f"  Change detected: {path.name} -> {action.name}")
            self.debouncer.trigger(action, path)


# =============================================================================
# Watch Command
# =============================================================================


def resolve_project(project: str) -> tuple[str, Path]:
    """Resolve project name to (project_name, project_root).

    Handles both short names (SBSTest, GCR, PNT) and directory paths.
    """
    # Check known project names
    if project in PROJECT_PATHS:
        project_root = SBS_ROOT / PROJECT_PATHS[project]
        return project, project_root

    # Try as a path
    project_path = Path(project).resolve()
    if project_path.exists():
        runway_json = project_path / "runway.json"
        if runway_json.exists():
            data = json.loads(runway_json.read_text())
            return data.get("projectName", project_path.name), project_path

    raise ValueError(
        f"Unknown project: {project}. "
        f"Known projects: {', '.join(sorted(PROJECT_PATHS.keys()))}"
    )


def get_assets_dir(project_root: Path) -> Path:
    """Resolve the assets directory from runway.json config."""
    runway_json = project_root / "runway.json"
    if not runway_json.exists():
        raise ValueError(f"runway.json not found in {project_root}")

    data = json.loads(runway_json.read_text())
    assets_rel = data.get("assetsDir")
    if not assets_rel:
        raise ValueError("No assetsDir configured in runway.json")

    return (project_root / assets_rel).resolve()


def cmd_watch(args: argparse.Namespace) -> int:
    """Execute the watch command."""
    try:
        project_name, project_root = resolve_project(args.project)
    except ValueError as e:
        log.error(str(e))
        return 1

    try:
        assets_dir = get_assets_dir(project_root)
    except ValueError as e:
        log.error(str(e))
        return 1

    dressed_dir = project_root / ".lake" / "build" / "dressed"
    site_dir = project_root / ".lake" / "build" / "runway"
    port = args.port

    # Validate site exists
    if not site_dir.exists():
        log.error(
            f"Site directory not found at {site_dir}\n"
            f"Run a build first: python build.py"
        )
        return 1

    # Start HTTP server
    log.header(f"SBS Watch Mode: {project_name}")

    from sbs.build.phases import kill_processes_on_port, start_http_server
    kill_processes_on_port(port)

    pid = start_http_server(site_dir, port)
    log.success(f"Server started at http://localhost:{port} (PID: {pid})")

    # Set up components
    classifier = ChangeClassifier(project_root, assets_dir, dressed_dir)
    regenerator = Regenerator(project_root, project_name, assets_dir)

    def on_regen(action: ChangeAction, paths: list[Path]) -> None:
        regenerator.execute(action, paths)

    debouncer = Debouncer(DEBOUNCE_SECONDS, on_regen)
    handler = SBSEventHandler(classifier, debouncer)

    # Set up watchers
    observer = Observer()

    watch_targets: list[tuple[str, Path, bool]] = []

    # Watch assets directory
    if assets_dir.exists():
        watch_targets.append(("Assets", assets_dir, False))
    else:
        log.warning(f"Assets directory not found: {assets_dir}")

    # Watch dressed artifacts
    if dressed_dir.exists():
        watch_targets.append(("Artifacts", dressed_dir, True))
    else:
        log.info(f"Dressed artifacts dir not found (yet): {dressed_dir}")

    # Watch runway.json
    watch_targets.append(("Config", project_root, False))

    # Watch Runway templates
    runway_lean_dir = SBS_ROOT / "toolchain" / "Runway"
    if runway_lean_dir.exists():
        watch_targets.append(("Templates", runway_lean_dir, True))

    # Schedule watches
    for label, path, recursive in watch_targets:
        try:
            observer.schedule(handler, str(path), recursive=recursive)
            log.info(f"  Watching: {label} ({path})")
        except Exception as e:
            log.warning(f"  Could not watch {label}: {e}")

    if not watch_targets:
        log.error("No valid watch targets found")
        return 1

    # Start watching
    observer.start()

    log.info("")
    log.info(f"Watching for changes... (Ctrl+C to stop)")
    log.info(f"Server: http://localhost:{port}")
    log.info("")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("")
        log.header("Shutting down")

        debouncer.cancel()
        observer.stop()
        observer.join(timeout=5)

        kill_processes_on_port(port)

        log.info(f"Regenerations performed: {regenerator.regen_count}")
        log.success("Watch mode stopped")

    return 0
