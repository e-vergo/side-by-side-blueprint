#!/usr/bin/env python3
"""
Side-by-Side Blueprint Build Orchestrator

A robust Python replacement for build_blueprint.sh that handles multi-repo
coordination with proper dependency ordering.

Features:
- Git cycle management (commit -> push for all repos)
- Dependency graph from lakefile.toml/lakefile.lean
- Compliance enforcement (custom Mathlib version, main branch deps)
- Ordered operations respecting dependency levels
- Local caching (~/.sbs-cache/)
- Chrome window management (preserves MCP-connected window)

Usage:
    python build.py                  # Build current project
    python build.py --help           # Show help
    python build.py --dry-run        # Show what would be done
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Add venv site-packages to path if available (for toml on Python < 3.11)
SCRIPT_DIR = Path(__file__).parent
VENV_SITE_PACKAGES = SCRIPT_DIR / ".venv" / "lib"
if VENV_SITE_PACKAGES.exists():
    for p in VENV_SITE_PACKAGES.iterdir():
        site_pkg = p / "site-packages"
        if site_pkg.exists():
            sys.path.insert(0, str(site_pkg))
            break

# Try to import tomllib (Python 3.11+) or toml
try:
    import tomllib
except ImportError:
    try:
        import toml as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

# Import ledger types for metrics
try:
    from sbs.ledger import BuildMetrics, UnifiedLedger, get_or_create_unified_ledger
    HAS_LEDGER = True
except ImportError:
    HAS_LEDGER = False


# =============================================================================
# Constants
# =============================================================================

SBS_ROOT = Path("/Users/eric/GitHub/Side-By-Side-Blueprint")
CACHE_DIR = Path.home() / ".sbs-cache"

# Known repos in dependency order (used for git sync)
REPO_NAMES = [
    "subverso",
    "LeanArchitect",
    "Dress",
    "Runway",
    "verso",
    "dress-blueprint-action",
    "SBS-Test",
    "General_Crystallographic_Restriction",
    "PrimeNumberTheoremAnd",
]

# Required mathlib version (enforced across all projects)
REQUIRED_MATHLIB_VERSION = "v4.27.0"

# Toolchain build order
TOOLCHAIN_BUILD_ORDER = ["subverso", "LeanArchitect", "Dress", "Runway"]


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Repo:
    """Represents a repository in the build system."""

    name: str
    path: Path
    dependencies: list[str] = field(default_factory=list)
    is_toolchain: bool = False
    has_lakefile: bool = False
    lakefile_type: str = ""  # "toml" or "lean"

    def exists(self) -> bool:
        return self.path.exists()


@dataclass
class BuildConfig:
    """Configuration for a build run."""

    project_root: Path
    project_name: str
    module_name: str
    sbs_root: Path = field(default_factory=lambda: SBS_ROOT)
    cache_dir: Path = field(default_factory=lambda: CACHE_DIR)
    skip_cache: bool = False
    dry_run: bool = False
    verbose: bool = False
    capture: bool = False
    capture_url: str = "http://localhost:8000"


# =============================================================================
# Logging
# =============================================================================


class Logger:
    """Simple colored logger."""

    COLORS = {
        "reset": "\033[0m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "bold": "\033[1m",
    }

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._use_color = sys.stdout.isatty()

    def _color(self, text: str, color: str) -> str:
        if not self._use_color:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def step(self, message: str) -> None:
        print(f"\n{self._color('===', 'cyan')} {self._color(message, 'bold')} {self._color('===', 'cyan')}")

    def info(self, message: str) -> None:
        print(f"  {message}")

    def success(self, message: str) -> None:
        print(f"  {self._color('[OK]', 'green')} {message}")

    def warning(self, message: str) -> None:
        print(f"  {self._color('[WARN]', 'yellow')} {message}")

    def error(self, message: str) -> None:
        print(f"  {self._color('[ERROR]', 'red')} {message}")

    def debug(self, message: str) -> None:
        if self.verbose:
            print(f"  {self._color('[DEBUG]', 'magenta')} {message}")

    def dry_run(self, message: str) -> None:
        print(f"  {self._color('[DRY-RUN]', 'blue')} {message}")


log = Logger()


# =============================================================================
# Lakefile Parsing
# =============================================================================


def parse_lakefile_toml(path: Path) -> list[dict[str, Any]]:
    """Parse a lakefile.toml and return the list of requirements."""
    if tomllib is None:
        raise RuntimeError("tomllib not available. Install toml package: pip install toml")

    content = path.read_text()

    # Handle both tomllib (returns bytes) and toml (returns str)
    if hasattr(tomllib, 'loads'):
        data = tomllib.loads(content)
    else:
        data = tomllib.load(path.open('rb'))

    return data.get("require", [])


def parse_lakefile_lean(path: Path) -> list[dict[str, Any]]:
    """Parse a lakefile.lean and extract requirements.

    This is a simple regex-based parser that handles the common patterns:
    - require NAME from git "URL"@"REV"
    - require NAME from git "URL" @ "REV"
    """
    content = path.read_text()
    requirements = []

    # Pattern: require NAME from git "URL"@"REV" or "URL" @ "REV"
    pattern = r'require\s+(\w+)\s+from\s+git\s+"([^"]+)"(?:\s*@\s*|\s+@\s+)"([^"]+)"'

    for match in re.finditer(pattern, content):
        name, git, rev = match.groups()
        requirements.append({
            "name": name,
            "git": git,
            "rev": rev,
        })

    return requirements


def get_lakefile_path(repo_path: Path) -> tuple[Optional[Path], str]:
    """Find the lakefile in a repo and return its path and type."""
    toml_path = repo_path / "lakefile.toml"
    lean_path = repo_path / "lakefile.lean"

    if toml_path.exists():
        return toml_path, "toml"
    elif lean_path.exists():
        return lean_path, "lean"
    else:
        return None, ""


def parse_lakefile(repo_path: Path) -> list[dict[str, Any]]:
    """Parse the lakefile for a repo and return requirements."""
    lakefile_path, lakefile_type = get_lakefile_path(repo_path)

    if lakefile_path is None:
        return []

    if lakefile_type == "toml":
        return parse_lakefile_toml(lakefile_path)
    elif lakefile_type == "lean":
        return parse_lakefile_lean(lakefile_path)
    else:
        return []


# =============================================================================
# Git Operations
# =============================================================================


def run_cmd(
    cmd: list[str],
    cwd: Optional[Path] = None,
    capture: bool = False,
    check: bool = True,
    dry_run: bool = False,
) -> subprocess.CompletedProcess:
    """Run a command with proper error handling."""
    if dry_run:
        log.dry_run(f"Would run: {' '.join(cmd)}" + (f" in {cwd}" if cwd else ""))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    log.debug(f"Running: {' '.join(cmd)}" + (f" in {cwd}" if cwd else ""))

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture,
            text=True,
            check=check,
        )
        return result
    except subprocess.CalledProcessError as e:
        if capture:
            log.error(f"Command failed: {' '.join(cmd)}")
            if e.stdout:
                log.error(f"stdout: {e.stdout}")
            if e.stderr:
                log.error(f"stderr: {e.stderr}")
        raise


def git_has_changes(repo_path: Path) -> bool:
    """Check if a repo has uncommitted changes."""
    result = run_cmd(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture=True,
        check=False,
    )
    return bool(result.stdout.strip())


def git_commit_and_push(repo_path: Path, dry_run: bool = False) -> bool:
    """Commit and push changes in a repo. Returns True if changes were pushed."""
    if not git_has_changes(repo_path):
        return False

    if dry_run:
        log.dry_run(f"Would commit and push changes in {repo_path.name}")
        return True

    # Stage all changes
    run_cmd(["git", "add", "-A"], cwd=repo_path)

    # Commit
    run_cmd(
        ["git", "commit", "-m", "Auto-commit from build.py\n\nCo-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"],
        cwd=repo_path,
    )

    # Push
    run_cmd(["git", "push"], cwd=repo_path)

    return True


def git_pull(repo_path: Path, dry_run: bool = False) -> None:
    """Pull latest changes from remote."""
    if dry_run:
        log.dry_run(f"Would pull latest in {repo_path.name}")
        return

    # Try rebase first, fall back to regular pull
    result = run_cmd(
        ["git", "pull", "--rebase"],
        cwd=repo_path,
        check=False,
    )
    if result.returncode != 0:
        run_cmd(["git", "pull"], cwd=repo_path)


# =============================================================================
# Compliance Checks
# =============================================================================


def check_mathlib_version(requirements: list[dict[str, Any]], repo_name: str) -> list[str]:
    """Check that mathlib is at the required version. Returns list of errors."""
    errors = []

    for req in requirements:
        if req.get("name") == "mathlib":
            rev = req.get("rev", "")
            if rev != REQUIRED_MATHLIB_VERSION:
                errors.append(
                    f"{repo_name}: mathlib version {rev} != required {REQUIRED_MATHLIB_VERSION}"
                )

    return errors


def check_deps_point_to_main(requirements: list[dict[str, Any]], repo_name: str) -> list[str]:
    """Check that internal deps point to main branch. Returns list of errors."""
    errors = []

    # Internal repos that should point to main
    internal_repos = {"LeanArchitect", "Dress", "Runway", "subverso", "verso"}

    for req in requirements:
        name = req.get("name", "")
        if name in internal_repos:
            rev = req.get("rev", "")
            if rev != "main":
                errors.append(
                    f"{repo_name}: {name} points to '{rev}' instead of 'main'"
                )

    return errors


def run_compliance_checks(repos: dict[str, Repo]) -> list[str]:
    """Run all compliance checks across repos. Returns list of errors."""
    errors = []

    for name, repo in repos.items():
        if not repo.exists():
            continue

        requirements = parse_lakefile(repo.path)

        # Only check mathlib version for consumer projects (not toolchain)
        if not repo.is_toolchain:
            errors.extend(check_mathlib_version(requirements, name))

        # Check internal deps point to main
        errors.extend(check_deps_point_to_main(requirements, name))

    return errors


# =============================================================================
# Build Operations
# =============================================================================


def clean_build_artifacts(repo_path: Path, dry_run: bool = False) -> None:
    """Clean build artifacts for a repo."""
    build_dir = repo_path / ".lake" / "build"

    if build_dir.exists():
        if dry_run:
            log.dry_run(f"Would remove {build_dir}")
        else:
            shutil.rmtree(build_dir)


def lake_build(repo_path: Path, target: Optional[str] = None, dry_run: bool = False) -> None:
    """Run lake build in a repo."""
    cmd = ["lake", "build"]
    if target:
        cmd.append(target)

    if dry_run:
        log.dry_run(f"Would run: {' '.join(cmd)} in {repo_path}")
        return

    run_cmd(cmd, cwd=repo_path)


def lake_update(repo_path: Path, dep: Optional[str] = None, dry_run: bool = False) -> None:
    """Run lake update in a repo."""
    cmd = ["lake", "update"]
    if dep:
        cmd.append(dep)

    if dry_run:
        log.dry_run(f"Would run: {' '.join(cmd)} in {repo_path}")
        return

    run_cmd(cmd, cwd=repo_path, check=False)  # lake update can fail if already up to date


def fetch_mathlib_cache(project_root: Path, dry_run: bool = False) -> None:
    """Fetch mathlib cache for a project."""
    if dry_run:
        log.dry_run(f"Would fetch mathlib cache in {project_root}")
        return

    run_cmd(["lake", "exe", "cache", "get"], cwd=project_root, check=False)


# =============================================================================
# Caching
# =============================================================================


def get_cache_key(repo_path: Path) -> str:
    """Generate a cache key based on lakefile content and lean-toolchain."""
    hasher = hashlib.sha256()

    # Include lakefile content
    lakefile_path, _ = get_lakefile_path(repo_path)
    if lakefile_path and lakefile_path.exists():
        hasher.update(lakefile_path.read_bytes())

    # Include lean-toolchain
    toolchain_path = repo_path / "lean-toolchain"
    if toolchain_path.exists():
        hasher.update(toolchain_path.read_bytes())

    return hasher.hexdigest()[:16]


def get_cached_build(cache_dir: Path, repo_name: str, cache_key: str) -> Optional[Path]:
    """Check if a cached build exists and return its path."""
    cache_path = cache_dir / repo_name / cache_key
    if cache_path.exists():
        return cache_path
    return None


def save_to_cache(
    cache_dir: Path,
    repo_name: str,
    cache_key: str,
    build_dir: Path,
    dry_run: bool = False,
) -> None:
    """Save build artifacts to cache."""
    if dry_run:
        log.dry_run(f"Would cache {repo_name} build to {cache_dir / repo_name / cache_key}")
        return

    cache_path = cache_dir / repo_name / cache_key
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        shutil.rmtree(cache_path)

    if build_dir.exists():
        shutil.copytree(build_dir, cache_path)


def restore_from_cache(
    cache_path: Path,
    build_dir: Path,
    dry_run: bool = False,
) -> None:
    """Restore build artifacts from cache."""
    if dry_run:
        log.dry_run(f"Would restore from cache {cache_path} to {build_dir}")
        return

    if build_dir.exists():
        shutil.rmtree(build_dir)

    build_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(cache_path, build_dir)


# =============================================================================
# Chrome Window Management
# =============================================================================


def get_mcp_chrome_window_id() -> Optional[int]:
    """Try to identify the Chrome window connected to MCP.

    This is a heuristic - we look for Chrome windows that might be the MCP window.
    On macOS, we use AppleScript to query Chrome.
    """
    if sys.platform != "darwin":
        return None

    try:
        # Get list of Chrome window IDs and URLs
        script = '''
        tell application "Google Chrome"
            set windowInfo to {}
            repeat with w in windows
                set windowId to id of w
                set tabUrls to {}
                repeat with t in tabs of w
                    set end of tabUrls to URL of t
                end repeat
                set end of windowInfo to {windowId, tabUrls}
            end repeat
            return windowInfo
        end tell
        '''

        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return None

        # Parse output and look for localhost:8000 or similar patterns
        # that indicate the MCP window
        output = result.stdout.strip()

        # Simple heuristic: find window with localhost URL
        # The MCP extension typically opens localhost pages
        if "localhost" in output.lower():
            # Extract first window ID from output
            # AppleScript returns nested lists, parse roughly
            import re
            match = re.search(r'(\d+),', output)
            if match:
                return int(match.group(1))

        return None

    except Exception:
        return None


def cleanup_chrome_windows(preserve_window_id: Optional[int], dry_run: bool = False) -> None:
    """Kill Chrome windows except the MCP-connected one.

    On macOS, uses AppleScript to close specific windows.
    """
    if sys.platform != "darwin":
        log.warning("Chrome cleanup only supported on macOS")
        return

    if dry_run:
        log.dry_run(f"Would close Chrome windows except ID {preserve_window_id}")
        return

    try:
        # Get all window IDs
        script = '''
        tell application "Google Chrome"
            set windowIds to {}
            repeat with w in windows
                set end of windowIds to id of w
            end repeat
            return windowIds
        end tell
        '''

        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            log.warning("Could not get Chrome windows")
            return

        # Parse window IDs
        import re
        window_ids = [int(x) for x in re.findall(r'\d+', result.stdout)]

        # Close windows except preserved one
        for wid in window_ids:
            if preserve_window_id is not None and wid == preserve_window_id:
                log.info(f"Preserving Chrome window {wid} (MCP)")
                continue

            close_script = f'''
            tell application "Google Chrome"
                close (first window whose id is {wid})
            end tell
            '''

            subprocess.run(
                ["osascript", "-e", close_script],
                capture_output=True,
                check=False,
            )
            log.info(f"Closed Chrome window {wid}")

    except Exception as e:
        log.warning(f"Chrome cleanup failed: {e}")


# =============================================================================
# Project Detection
# =============================================================================


def detect_project(project_root: Path) -> tuple[str, str]:
    """Detect project name and module name from runway.json.

    Returns (project_name, module_name).
    """
    runway_json = project_root / "runway.json"

    if not runway_json.exists():
        raise RuntimeError(f"runway.json not found in {project_root}")

    data = json.loads(runway_json.read_text())
    project_name = data.get("projectName")

    if not project_name:
        raise RuntimeError("Could not extract projectName from runway.json")

    # Module name is same as project name
    return project_name, project_name


# =============================================================================
# Build Orchestrator
# =============================================================================


class BuildOrchestrator:
    """Orchestrates the multi-repo build process."""

    def __init__(self, config: BuildConfig):
        self.config = config
        self.repos: dict[str, Repo] = {}
        log.verbose = config.verbose

        # Timing tracking
        self._phase_start: Optional[float] = None
        self._phase_timings: dict[str, float] = {}
        self._build_start: Optional[float] = None
        self._run_id: str = ""
        self._commits_before: dict[str, str] = {}
        self._commits_after: dict[str, str] = {}
        self._build_success: bool = False
        self._error_message: Optional[str] = None

    def _generate_run_id(self) -> str:
        """Generate run_id as ISO timestamp + short hash."""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        short_hash = uuid.uuid4().hex[:6]
        return f"{timestamp}_{short_hash}"

    def _start_phase(self, name: str) -> None:
        """Mark start of a phase."""
        self._phase_start = time.time()

    def _end_phase(self, name: str) -> None:
        """Record phase duration."""
        if self._phase_start is not None:
            duration = time.time() - self._phase_start
            self._phase_timings[name] = round(duration, 3)
            self._phase_start = None

    def _collect_commits_before(self) -> None:
        """Collect git commits from all repos before build."""
        for name, repo in self.repos.items():
            if repo.exists():
                result = run_cmd(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo.path,
                    capture=True,
                    check=False,
                )
                if result.returncode == 0:
                    self._commits_before[name] = result.stdout.strip()[:12]

    def _collect_commits_after(self) -> None:
        """Collect git commits from all repos after build."""
        for name, repo in self.repos.items():
            if repo.exists():
                result = run_cmd(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo.path,
                    capture=True,
                    check=False,
                )
                if result.returncode == 0:
                    self._commits_after[name] = result.stdout.strip()[:12]

    def _save_metrics(self) -> None:
        """Save build metrics to unified ledger."""
        if not HAS_LEDGER:
            log.debug("Ledger module not available, skipping metrics save")
            return

        try:
            # Calculate total duration
            duration = 0.0
            if self._build_start is not None:
                duration = time.time() - self._build_start

            # Get current commit
            commit = ""
            result = run_cmd(
                ["git", "rev-parse", "HEAD"],
                cwd=self.config.project_root,
                capture=True,
                check=False,
            )
            if result.returncode == 0:
                commit = result.stdout.strip()[:12]

            # Determine which repos changed
            repos_changed = []
            for name in self._commits_before:
                before = self._commits_before.get(name, "")
                after = self._commits_after.get(name, "")
                if before and after and before != after:
                    repos_changed.append(name)

            # Create metrics
            metrics = BuildMetrics(
                run_id=self._run_id,
                project=self.config.project_name,
                commit=commit,
                started_at=datetime.fromtimestamp(self._build_start).isoformat() if self._build_start else "",
                completed_at=datetime.now().isoformat(),
                duration_seconds=round(duration, 2),
                phase_timings=self._phase_timings,
                repos_changed=repos_changed,
                commits_before=self._commits_before,
                commits_after=self._commits_after,
                success=self._build_success,
                error_message=self._error_message,
            )

            # Save to unified ledger
            stats_dir = SCRIPT_DIR / "stats"
            stats_dir.mkdir(parents=True, exist_ok=True)

            ledger = get_or_create_unified_ledger(stats_dir, self.config.project_name)
            ledger.add_build(metrics)
            ledger.save(stats_dir / "unified_ledger.json")

            log.success(f"Build metrics saved (run_id: {self._run_id})")
            log.info(f"  Duration: {duration:.1f}s across {len(self._phase_timings)} phases")

        except Exception as e:
            log.warning(f"Failed to save metrics: {e}")

    def discover_repos(self) -> None:
        """Discover all repos in the SBS workspace."""
        for name in REPO_NAMES:
            path = self.config.sbs_root / name
            lakefile_path, lakefile_type = get_lakefile_path(path)

            repo = Repo(
                name=name,
                path=path,
                is_toolchain=name in TOOLCHAIN_BUILD_ORDER,
                has_lakefile=lakefile_path is not None,
                lakefile_type=lakefile_type,
            )

            if path.exists() and lakefile_path:
                requirements = parse_lakefile(path)
                repo.dependencies = [
                    req["name"] for req in requirements
                    if req.get("name") in REPO_NAMES
                ]

            self.repos[name] = repo

        # Add the top-level monorepo
        self.repos["Side-By-Side-Blueprint"] = Repo(
            name="Side-By-Side-Blueprint",
            path=self.config.sbs_root,
            is_toolchain=False,
            has_lakefile=False,
        )

        # Add current project if not already in repos
        project_name = self.config.project_name
        if project_name not in self.repos:
            self.repos[project_name] = Repo(
                name=project_name,
                path=self.config.project_root,
                is_toolchain=False,
                has_lakefile=True,
            )

    def sync_repos(self) -> None:
        """Commit and push changes, then pull latest from all repos."""
        log.step("Syncing local repos to GitHub")

        # Commit and push all repos
        for name in REPO_NAMES + ["Side-By-Side-Blueprint"]:
            repo = self.repos.get(name)
            if not repo or not repo.exists():
                continue

            if git_commit_and_push(repo.path, self.config.dry_run):
                log.success(f"{name}: Committed and pushed changes")
            else:
                log.info(f"{name}: No changes to commit")

        # Also sync current project if different
        if self.config.project_root != self.config.sbs_root:
            if git_commit_and_push(self.config.project_root, self.config.dry_run):
                log.success(f"{self.config.project_name}: Committed and pushed changes")

        log.step("Pulling latest from GitHub")

        # Pull all repos
        for name in REPO_NAMES + ["Side-By-Side-Blueprint"]:
            repo = self.repos.get(name)
            if not repo or not repo.exists():
                continue

            git_pull(repo.path, self.config.dry_run)
            log.info(f"{name}: Pulled latest")

    def update_manifests(self) -> None:
        """Update lake manifests in dependency order."""
        log.step("Updating lake manifests")

        # Update toolchain repos
        updates = [
            ("LeanArchitect", "SubVerso"),
            ("Dress", "LeanArchitect"),
            ("Runway", "Dress"),
            ("verso", None),  # Full update
        ]

        for repo_name, dep in updates:
            repo = self.repos.get(repo_name)
            if not repo or not repo.exists():
                continue

            lake_update(repo.path, dep, self.config.dry_run)
            log.info(f"{repo_name}: Updated" + (f" {dep}" if dep else ""))

        # Update consumer projects
        for name in ["General_Crystallographic_Restriction", "PrimeNumberTheoremAnd"]:
            repo = self.repos.get(name)
            if repo and repo.exists():
                lake_update(repo.path, "Dress", self.config.dry_run)
                log.info(f"{name}: Updated Dress")

        # Update current project
        lake_update(self.config.project_root, "Dress", self.config.dry_run)
        log.info(f"{self.config.project_name}: Updated Dress")

        # Commit manifest changes
        for name in REPO_NAMES:
            repo = self.repos.get(name)
            if not repo or not repo.exists():
                continue

            manifest_path = repo.path / "lake-manifest.json"
            if manifest_path.exists():
                result = run_cmd(
                    ["git", "status", "--porcelain", "lake-manifest.json"],
                    cwd=repo.path,
                    capture=True,
                    check=False,
                )
                if result.stdout.strip():
                    if self.config.dry_run:
                        log.dry_run(f"Would commit manifest update in {name}")
                    else:
                        run_cmd(["git", "add", "lake-manifest.json"], cwd=repo.path)
                        run_cmd(
                            ["git", "commit", "-m", "Update lake-manifest.json from build.py\n\nCo-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"],
                            cwd=repo.path,
                        )
                        run_cmd(["git", "push"], cwd=repo.path)
                        log.success(f"{name}: Committed manifest update")

    def run_compliance_checks(self) -> None:
        """Run compliance checks and fail if issues found."""
        log.step("Running compliance checks")

        errors = run_compliance_checks(self.repos)

        if errors:
            log.error("Compliance check failed:")
            for error in errors:
                log.error(f"  - {error}")
            raise RuntimeError("Compliance check failed")

        log.success("All compliance checks passed")

    def clean_artifacts(self) -> None:
        """Clean build artifacts from toolchain and project."""
        log.step("Cleaning build artifacts")

        # Clean toolchain repos
        for name in TOOLCHAIN_BUILD_ORDER:
            repo = self.repos.get(name)
            if repo and repo.exists():
                clean_build_artifacts(repo.path, self.config.dry_run)
                log.info(f"{name}: Cleaned build artifacts")

        # Clean project artifacts
        build_dir = self.config.project_root / ".lake" / "build"
        for subdir in ["lib", "ir", "dressed", "runway"]:
            target = build_dir / subdir / self.config.module_name
            if target.exists():
                if self.config.dry_run:
                    log.dry_run(f"Would remove {target}")
                else:
                    shutil.rmtree(target)

        # Also clean dressed and runway dirs directly
        for subdir in ["dressed", "runway"]:
            target = build_dir / subdir
            if target.exists():
                if self.config.dry_run:
                    log.dry_run(f"Would remove {target}")
                else:
                    shutil.rmtree(target)

        log.success("Build artifacts cleaned")

    def build_toolchain(self) -> None:
        """Build the toolchain in dependency order with caching."""
        log.step("Building toolchain")

        for name in TOOLCHAIN_BUILD_ORDER:
            repo = self.repos.get(name)
            if not repo or not repo.exists():
                log.warning(f"{name}: Not found, skipping")
                continue

            # Check cache
            if not self.config.skip_cache:
                cache_key = get_cache_key(repo.path)
                cached = get_cached_build(self.config.cache_dir, name, cache_key)

                if cached:
                    log.info(f"{name}: Restoring from cache")
                    restore_from_cache(
                        cached,
                        repo.path / ".lake" / "build",
                        self.config.dry_run,
                    )
                    continue

            # Build
            log.info(f"{name}: Building...")
            lake_build(repo.path, dry_run=self.config.dry_run)
            log.success(f"{name}: Built")

            # Cache the build
            if not self.config.skip_cache:
                cache_key = get_cache_key(repo.path)
                save_to_cache(
                    self.config.cache_dir,
                    name,
                    cache_key,
                    repo.path / ".lake" / "build",
                    self.config.dry_run,
                )

    def build_project(self) -> None:
        """Build the project with dressed artifacts (legacy method for compatibility)."""
        log.step("Fetching mathlib cache")
        fetch_mathlib_cache(self.config.project_root, self.config.dry_run)

        self._build_project_internal()

        log.step("Building blueprint facet")
        lake_build(self.config.project_root, ":blueprint", self.config.dry_run)
        log.success("Blueprint facet built")

    def _build_project_internal(self) -> None:
        """Build the Lean project with dressed artifacts (without cache fetch or blueprint)."""
        log.step("Building Lean project with dressed artifacts")

        if self.config.dry_run:
            log.dry_run("Would run: BLUEPRINT_DRESS=1 lake build")
        else:
            env = os.environ.copy()
            env["BLUEPRINT_DRESS"] = "1"
            subprocess.run(
                ["lake", "build"],
                cwd=self.config.project_root,
                env=env,
                check=True,
            )

        log.success("Project built with dressed artifacts")

    def generate_dep_graph(self) -> None:
        """Generate the dependency graph."""
        log.step("Generating dependency graph")

        dress_path = self.repos["Dress"].path
        extract_exe = dress_path / ".lake" / "build" / "bin" / "extract_blueprint"

        if not extract_exe.exists() and not self.config.dry_run:
            log.error(f"extract_blueprint not found at {extract_exe}")
            raise RuntimeError("extract_blueprint executable not found")

        cmd = [
            "lake", "env",
            str(extract_exe),
            "graph",
            "--build", str(self.config.project_root / ".lake" / "build"),
            self.config.module_name,
        ]

        if self.config.dry_run:
            log.dry_run(f"Would run: {' '.join(cmd)}")
        else:
            subprocess.run(cmd, cwd=self.config.project_root, check=True)

        log.success("Dependency graph generated")

    def generate_site(self) -> None:
        """Generate the site with Runway."""
        log.step("Generating site with Runway")

        runway_path = self.repos["Runway"].path
        output_dir = self.config.project_root / ".lake" / "build" / "runway"

        cmd = [
            "lake", "exe", "runway",
            "--build-dir", str(self.config.project_root / ".lake" / "build"),
            "--output", str(output_dir),
            "build",
            str(self.config.project_root / "runway.json"),
        ]

        if self.config.dry_run:
            log.dry_run(f"Would run: {' '.join(cmd)}")
        else:
            subprocess.run(cmd, cwd=runway_path, check=True)

        log.success("Site generated")

        # Check for paper configuration
        runway_json = json.loads((self.config.project_root / "runway.json").read_text())
        has_paper = (
            runway_json.get("paperTexPath") or
            (runway_json.get("runwayDir") and
             (self.config.project_root / runway_json.get("runwayDir", "") / "src" / "paper.tex").exists())
        )

        if has_paper:
            log.step("Generating paper")

            cmd = [
                "lake", "exe", "runway",
                "--build-dir", str(self.config.project_root / ".lake" / "build"),
                "--output", str(output_dir),
                "paper",
                str(self.config.project_root / "runway.json"),
            ]

            if self.config.dry_run:
                log.dry_run(f"Would run: {' '.join(cmd)}")
            else:
                subprocess.run(cmd, cwd=runway_path, check=True)

            log.success("Paper generated")

    def start_server(self) -> int:
        """Start the HTTP server and return PID."""
        log.step("Starting server")

        output_dir = self.config.project_root / ".lake" / "build" / "runway"

        # Kill any existing servers on port 8000
        if self.config.dry_run:
            log.dry_run("Would kill processes on port 8000")
        else:
            subprocess.run(
                ["lsof", "-ti:8000"],
                capture_output=True,
            )
            result = subprocess.run(
                "lsof -ti:8000 | xargs kill -9 2>/dev/null || true",
                shell=True,
                capture_output=True,
            )

        if self.config.dry_run:
            log.dry_run(f"Would start server at {output_dir}")
            return 0

        # Start server in background
        proc = subprocess.Popen(
            ["python3", "-m", "http.server", "-d", str(output_dir), "8000"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        log.success(f"Server started at http://localhost:8000 (PID: {proc.pid})")

        # Open browser
        time.sleep(1)
        subprocess.Popen(["open", "http://localhost:8000"])

        return proc.pid

    def run_capture(self) -> None:
        """Run screenshot capture using the sbs CLI."""
        log.step("Capturing screenshots")

        if self.config.dry_run:
            log.dry_run("Would capture screenshots")
            return

        # Wait a bit for server to be ready
        time.sleep(2)

        try:
            # Run the sbs capture command
            cmd = [
                sys.executable, "-m", "sbs", "capture",
                "--url", self.config.capture_url,
                "--project", self.config.project_name,
            ]

            result = subprocess.run(
                cmd,
                cwd=SCRIPT_DIR,
                check=False,
            )

            if result.returncode == 0:
                log.success("Screenshots captured")
            else:
                log.warning("Screenshot capture failed (non-blocking)")

        except Exception as e:
            log.warning(f"Screenshot capture error: {e}")

    def run(self) -> None:
        """Run the full build process."""
        # Initialize timing
        self._build_start = time.time()
        self._run_id = self._generate_run_id()

        log.step(f"{self.config.project_name} Blueprint Builder")
        log.info(f"Run ID: {self._run_id}")

        try:
            # Discover repos
            self.discover_repos()

            # Collect commits before build
            self._collect_commits_before()

            # Chrome cleanup (before build to prevent interference)
            mcp_window = get_mcp_chrome_window_id()
            cleanup_chrome_windows(mcp_window, self.config.dry_run)

            # Git sync (mandatory - ensures reproducible builds)
            self._start_phase("sync_repos")
            self.sync_repos()
            self._end_phase("sync_repos")

            self._start_phase("update_manifests")
            self.update_manifests()
            self._end_phase("update_manifests")

            # Compliance checks
            self._start_phase("compliance_checks")
            self.run_compliance_checks()
            self._end_phase("compliance_checks")

            # Clean artifacts
            self._start_phase("clean_build")
            self.clean_artifacts()
            self._end_phase("clean_build")

            # Build toolchain (mandatory - ensures consistency)
            self._start_phase("build_toolchain")
            self.build_toolchain()
            self._end_phase("build_toolchain")

            # Fetch mathlib cache (extracted from build_project for granular timing)
            self._start_phase("fetch_mathlib_cache")
            fetch_mathlib_cache(self.config.project_root, self.config.dry_run)
            self._end_phase("fetch_mathlib_cache")

            # Build project
            self._start_phase("build_project")
            self._build_project_internal()
            self._end_phase("build_project")

            # Build blueprint facet
            self._start_phase("build_blueprint")
            lake_build(self.config.project_root, ":blueprint", self.config.dry_run)
            self._end_phase("build_blueprint")

            # Generate outputs
            self._start_phase("build_dep_graph")
            self.generate_dep_graph()
            self._end_phase("build_dep_graph")

            self._start_phase("generate_site")
            self.generate_site()
            self._end_phase("generate_site")

            # Final git sync (mandatory)
            self._start_phase("final_sync")
            if git_commit_and_push(self.config.project_root, self.config.dry_run):
                log.success("Final changes committed and pushed")
            self._end_phase("final_sync")

            # Collect commits after build
            self._collect_commits_after()

            # Start server
            self._start_phase("start_server")
            self.start_server()
            self._end_phase("start_server")

            # Capture screenshots if requested
            if self.config.capture:
                self._start_phase("capture")
                self.run_capture()
                self._end_phase("capture")

            # Mark build as successful
            self._build_success = True

            log.step("BUILD COMPLETE")
            log.info(f"Output: {self.config.project_root / '.lake' / 'build' / 'runway'}")
            log.info("Web: http://localhost:8000")

            # Print timing summary
            total = time.time() - self._build_start
            log.info(f"Total time: {total:.1f}s")
            if self.config.verbose:
                for phase, duration in self._phase_timings.items():
                    log.debug(f"  {phase}: {duration:.1f}s")

        except Exception as e:
            self._build_success = False
            self._error_message = str(e)
            raise

        finally:
            # Always save metrics (best-effort)
            self._save_metrics()


# =============================================================================
# CLI
# =============================================================================


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Side-by-Side Blueprint Build Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python build.py                  # Build current project
    python build.py --dry-run        # Show what would be done
    python build.py --verbose        # Enable debug output
        """,
    )

    parser.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        help="Project directory (default: current directory)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )

    parser.add_argument(
        "--skip-cache",
        action="store_true",
        help="Skip caching (always rebuild)",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose debug output",
    )

    parser.add_argument(
        "--capture",
        action="store_true",
        help="Capture screenshots after successful build",
    )

    parser.add_argument(
        "--capture-url",
        default="http://localhost:8000",
        help="URL to capture from (default: http://localhost:8000)",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Resolve project directory
    project_root = Path(args.project_dir).resolve()

    try:
        # Detect project
        project_name, module_name = detect_project(project_root)

        # Build config
        config = BuildConfig(
            project_root=project_root,
            project_name=project_name,
            module_name=module_name,
            skip_cache=args.skip_cache,
            dry_run=args.dry_run,
            verbose=args.verbose,
            capture=args.capture,
            capture_url=args.capture_url,
        )

        # Run build
        orchestrator = BuildOrchestrator(config)
        orchestrator.run()

        return 0

    except KeyboardInterrupt:
        log.warning("Build interrupted")
        return 130
    except Exception as e:
        log.error(str(e))
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
