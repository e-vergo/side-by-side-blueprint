"""
Build orchestrator for Side-by-Side Blueprint.

Coordinates multi-repo builds with timing, caching, and metrics.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from sbs.core.utils import (
    log,
    run_cmd,
    parse_lakefile,
    git_has_changes,
    SBS_ROOT,
)
from sbs.build.config import (
    BuildConfig,
    Repo,
    REPO_NAMES,
    REPO_PATHS,
    TOOLCHAIN_BUILD_ORDER,
    detect_project,
    get_lakefile_path,
)
from sbs.build.caching import (
    get_cache_key,
    get_cached_build,
    save_to_cache,
    restore_from_cache,
    has_dressed_artifacts,
    has_lean_changes,
    save_lean_hash,
    get_lean_sources_hash,
)
from sbs.build.compliance import run_compliance_checks
from sbs.tests.validators.runner import run_validators
from sbs.build.phases import (
    clean_build_artifacts,
    lake_build,
    lake_update,
    fetch_mathlib_cache,
    build_project_with_dress,
    git_commit_and_push,
    git_pull,
    get_mcp_chrome_window_id,
    cleanup_chrome_windows,
    kill_processes_on_port,
    start_http_server,
    open_browser,
)

# Import ledger types for metrics
try:
    from sbs.core.ledger import BuildMetrics, get_or_create_unified_ledger
    HAS_LEDGER = True
except ImportError:
    HAS_LEDGER = False

# Import archive types for iCloud sync
try:
    from sbs.archive import ArchiveEntry, ArchiveIndex, full_sync
    HAS_ARCHIVE = True
except ImportError:
    HAS_ARCHIVE = False

# Import archive upload for build integration
try:
    from sbs.archive.upload import archive_upload
    HAS_ARCHIVE_UPLOAD = True
except ImportError:
    HAS_ARCHIVE_UPLOAD = False

# Script directory for capture commands
SCRIPT_DIR = Path(__file__).parent.parent


# =============================================================================
# Build Orchestrator
# =============================================================================


class BuildOrchestrator:
    """Orchestrates the multi-repo build process."""

    def __init__(self, config: BuildConfig):
        self.config = config
        self.repos: dict[str, Repo] = {}

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

    def _validate_project_structure(self) -> None:
        """Pre-flight checks before expensive operations.

        Catches configuration errors early to avoid wasting 2+ minutes
        before discovering missing files or bad state.

        Raises:
            RuntimeError: If critical configuration is missing or invalid.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Check required files exist
        runway_json = self.config.project_root / "runway.json"
        if not runway_json.exists():
            errors.append(
                f"runway.json not found at {runway_json}\n"
                f"  Fix: Create runway.json with projectName and assetsDir fields"
            )
        else:
            # Validate runway.json is parseable and has required fields
            try:
                data = json.loads(runway_json.read_text())
                if not data.get("projectName"):
                    errors.append(
                        f"runway.json missing required 'projectName' field\n"
                        f"  Fix: Add \"projectName\": \"YourProject\" to runway.json"
                    )
                # Check assetsDir exists if specified
                assets_dir = data.get("assetsDir")
                if assets_dir:
                    assets_path = (self.config.project_root / assets_dir).resolve()
                    if not assets_path.exists():
                        errors.append(
                            f"assetsDir not found: {assets_path}\n"
                            f"  Fix: Create the assets directory or update assetsDir in runway.json"
                        )
            except json.JSONDecodeError as e:
                errors.append(
                    f"runway.json is not valid JSON: {e}\n"
                    f"  Fix: Validate JSON syntax in runway.json"
                )

        # Check lakefile exists
        lakefile_toml = self.config.project_root / "lakefile.toml"
        lakefile_lean = self.config.project_root / "lakefile.lean"
        if not lakefile_toml.exists() and not lakefile_lean.exists():
            errors.append(
                f"No lakefile found in {self.config.project_root}\n"
                f"  Fix: Create lakefile.toml or lakefile.lean"
            )

        # 2. Check Lake manifests parseable (catches corruption early)
        manifest_path = self.config.project_root / "lake-manifest.json"
        if manifest_path.exists():
            try:
                json.loads(manifest_path.read_text())
            except json.JSONDecodeError as e:
                errors.append(
                    f"lake-manifest.json is corrupted: {e}\n"
                    f"  Fix: Run 'lake update' to regenerate the manifest"
                )

        # 3. Check git status in toolchain repos (warn if dirty)
        for name in TOOLCHAIN_BUILD_ORDER:
            repo_path = self.config.sbs_root / REPO_PATHS.get(name, name)
            if repo_path.exists():
                if git_has_changes(repo_path):
                    warnings.append(f"{name}: Has uncommitted changes")

        # Report warnings (non-blocking)
        if warnings:
            log.header("Pre-flight warnings")
            for warning in warnings:
                log.warning(f"  {warning}")

        # Report errors and fail if any critical issues
        if errors:
            log.header("Pre-flight validation failed")
            for error in errors:
                log.error(f"  {error}")
            raise RuntimeError(
                f"Pre-flight validation failed with {len(errors)} error(s). "
                f"Fix the issues above before building."
            )

        log.success("Pre-flight validation passed")

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
            log.info("Ledger module not available, skipping metrics save")
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

            # Save to unified ledger (in dev/storage/)
            archive_dir = SBS_ROOT / "dev" / "storage"
            archive_dir.mkdir(parents=True, exist_ok=True)

            ledger = get_or_create_unified_ledger(archive_dir, self.config.project_name)
            ledger.add_build(metrics)
            ledger.save(archive_dir / "unified_ledger.json")

            log.success(f"Build metrics saved (run_id: {self._run_id})")
            log.info(f"  Duration: {duration:.1f}s across {len(self._phase_timings)} phases")

        except Exception as e:
            log.warning(f"Failed to save metrics: {e}")

    def _create_archive_entry(self) -> Optional["ArchiveEntry"]:
        """Create an archive entry for this build."""
        if not HAS_ARCHIVE:
            log.info("Archive module not available, skipping entry creation")
            return None

        return ArchiveEntry(
            entry_id=str(int(time.time())),
            created_at=datetime.now().isoformat(),
            project=self.config.project_name,
            build_run_id=self._run_id,
            repo_commits=self._commits_after,
        )

    def _finalize_archive(self, entry: Optional["ArchiveEntry"]) -> None:
        """Finalize archive entry and sync to iCloud."""
        if not HAS_ARCHIVE or entry is None:
            return

        try:
            archive_root = SBS_ROOT / "dev" / "storage"
            index_path = archive_root / "archive_index.json"

            # Load or create index
            if index_path.exists():
                index = ArchiveIndex.load(index_path)
            else:
                index = ArchiveIndex()

            # Add screenshots reference
            project_dir = SBS_ROOT / "dev" / "storage" / self.config.project_name / "latest"
            if project_dir.exists():
                entry.screenshots = [str(p.name) for p in project_dir.glob("*.png")]

            # Add entry to index
            index.add_entry(entry)
            index.save(index_path)

            # Sync to iCloud (non-blocking)
            sync_result = full_sync(archive_root, index)
            if sync_result["success"]:
                log.success("Archive synced to iCloud")
            else:
                log.warning(f"iCloud sync partial: {sync_result['errors']}")

        except Exception as e:
            log.warning(f"iCloud sync skipped: {e}")

        # Run archive upload with build context
        if HAS_ARCHIVE_UPLOAD:
            try:
                # Calculate build duration
                build_duration = sum(self._phase_timings.values()) if self._phase_timings else None

                # Determine repos that changed
                repos_changed = []
                for repo, after_commit in self._commits_after.items():
                    before_commit = self._commits_before.get(repo)
                    if before_commit and after_commit != before_commit:
                        repos_changed.append(repo)

                archive_upload(
                    project=self.config.project_name,
                    build_run_id=self._run_id,
                    trigger="build",
                    dry_run=self.config.dry_run,
                    build_success=self._build_success,
                    build_duration_seconds=build_duration,
                    repos_changed=repos_changed,
                )
            except Exception as e:
                log.warning(f"Archive upload failed: {e}")

    def discover_repos(self) -> None:
        """Discover all repos in the SBS workspace."""
        for name in REPO_NAMES:
            rel_path = REPO_PATHS.get(name, name)
            path = self.config.sbs_root / rel_path
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
        log.header("Syncing local repos to GitHub")

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

        log.header("Pulling latest from GitHub")

        # Pull all repos
        for name in REPO_NAMES + ["Side-By-Side-Blueprint"]:
            repo = self.repos.get(name)
            if not repo or not repo.exists():
                continue

            git_pull(repo.path, self.config.dry_run)
            log.info(f"{name}: Pulled latest")

    def update_manifests(self) -> None:
        """Update lake manifests in dependency order."""
        log.header("Updating lake manifests")

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
                        log.info(f"[DRY-RUN] Would commit manifest update in {name}")
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
        log.header("Running compliance checks")

        errors = run_compliance_checks(self.repos)

        if errors:
            log.error("Compliance check failed:")
            for error in errors:
                log.error(f"  - {error}")
            raise RuntimeError("Compliance check failed")

        log.success("All compliance checks passed")

    def run_quality_validators(self) -> None:
        """Run deterministic quality validators (non-blocking)."""
        log.header("Running quality validators")
        try:
            result = run_validators(
                project=self.config.project_name,
                project_root=self.config.project_root,
                metric_ids=[
                    "t1-cli-execution",
                    "t2-ledger-population",
                    "t5-color-match",
                    "t6-css-coverage",
                ],
                update_ledger=True,
                skip_heuristic=True,
            )
            passed = sum(1 for r in result.results.values() if r.passed)
            total = len(result.results)
            if result.overall_passed:
                log.success(f"Quality validators: {passed}/{total} passed")
            else:
                log.warning(f"Quality validators: {passed}/{total} passed (non-blocking)")
                for metric_id, r in result.results.items():
                    if not r.passed:
                        log.warning(f"  - {metric_id}: {'; '.join(r.findings[:3])}")
            if result.errors:
                for err in result.errors:
                    log.warning(f"  Validator error: {err}")
        except Exception as e:
            log.warning(f"Quality validators skipped: {e}")

    def clean_artifacts(self) -> None:
        """Clean build artifacts from toolchain and project."""
        log.header("Cleaning build artifacts")

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
                    log.info(f"[DRY-RUN] Would remove {target}")
                else:
                    shutil.rmtree(target)

        # Also clean dressed and runway dirs directly
        for subdir in ["dressed", "runway"]:
            target = build_dir / subdir
            if target.exists():
                if self.config.dry_run:
                    log.info(f"[DRY-RUN] Would remove {target}")
                else:
                    shutil.rmtree(target)

        log.success("Build artifacts cleaned")

    def build_toolchain(self) -> None:
        """Build the toolchain in dependency order with caching."""
        log.header("Building toolchain")

        for name in TOOLCHAIN_BUILD_ORDER:
            repo = self.repos.get(name)
            if not repo or not repo.exists():
                log.warning(f"{name}: Not found, skipping")
                continue

            # Check if Lean sources changed (skip if stable)
            if not self.config.force_lake and not has_lean_changes(repo.path, self.config.cache_dir, name):
                log.info(f"Skipping {name}: Lean sources unchanged")
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

            # Record Lean hash for future skip detection
            lean_hash = get_lean_sources_hash(repo.path)
            if lean_hash:
                save_lean_hash(self.config.cache_dir, name, lean_hash)

    def build_project(self) -> None:
        """Build the project with dressed artifacts (legacy method for compatibility)."""
        log.header("Fetching mathlib cache")
        fetch_mathlib_cache(self.config.project_root, self.config.dry_run)

        self._build_project_internal()

        log.header("Building blueprint facet")
        lake_build(self.config.project_root, ":blueprint", self.config.dry_run)
        log.success("Blueprint facet built")

    def _needs_project_build(self) -> bool:
        """Check if the project needs a (re)build.

        Returns True when any of:
        - force_lake is set
        - Lean sources changed since last build
        - Per-declaration dressed artifacts are missing (e.g. after clean_artifacts)
        """
        if self.config.force_lake:
            return True
        if has_lean_changes(
            self.config.project_root, self.config.cache_dir, self.config.project_name
        ):
            return True
        if not has_dressed_artifacts(self.config.project_root):
            log.info("Per-declaration dressed artifacts missing — forcing rebuild")
            return True
        return False

    def _lake_manifests_changed(self) -> bool:
        """Check if Lake manifests changed since last successful build.

        Compares lakefile.lean/toml and lake-manifest.json timestamps against
        the last recorded build timestamp to detect dependency changes.
        """
        # Check for manifest timestamp file
        timestamp_file = self.config.cache_dir / f"{self.config.project_name}_manifest_ts"

        # Get current manifest files
        lakefile_toml = self.config.project_root / "lakefile.toml"
        lakefile_lean = self.config.project_root / "lakefile.lean"
        lake_manifest = self.config.project_root / "lake-manifest.json"

        manifest_files = [f for f in [lakefile_toml, lakefile_lean, lake_manifest] if f.exists()]

        if not manifest_files:
            return False  # No manifests to check

        # Get latest modification time of manifest files
        latest_mtime = max(f.stat().st_mtime for f in manifest_files)

        # If no timestamp file exists, this is first run - don't force clean
        if not timestamp_file.exists():
            # Save current timestamp for future comparisons
            timestamp_file.parent.mkdir(parents=True, exist_ok=True)
            timestamp_file.write_text(str(latest_mtime))
            return False

        # Compare with last recorded timestamp
        try:
            last_mtime = float(timestamp_file.read_text().strip())
            manifests_changed = latest_mtime > last_mtime

            if manifests_changed:
                log.info("Lake manifests changed since last build")
                # Update timestamp for next run
                timestamp_file.write_text(str(latest_mtime))

            return manifests_changed
        except (ValueError, OSError):
            # Corrupt timestamp file - don't force clean, just update
            timestamp_file.write_text(str(latest_mtime))
            return False

    def _build_project_internal(self) -> None:
        """Build the Lean project with dressed artifacts (without cache fetch or blueprint)."""
        if not self._needs_project_build():
            log.info("Skipping project build: Lean sources unchanged")
            return

        log.header("Building Lean project with dressed artifacts")
        build_project_with_dress(self.config.project_root, self.config.dry_run)
        log.success("Project built with dressed artifacts")

        # Record Lean hash for future skip detection
        lean_hash = get_lean_sources_hash(self.config.project_root)
        if lean_hash:
            save_lean_hash(self.config.cache_dir, self.config.project_name, lean_hash)

    def generate_verso_documents(self) -> None:
        """Run Verso document generators (paper, blueprint) if executables exist."""
        log.header("Generating Verso documents")

        generators = ["generate-paper-verso", "generate-blueprint-verso"]
        generated = False

        for gen_name in generators:
            cmd = ["lake", "exe", gen_name]

            if self.config.dry_run:
                log.info(f"[DRY-RUN] Would run: {' '.join(cmd)}")
                generated = True
                continue

            result = subprocess.run(
                cmd,
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                log.success(f"{gen_name}: Generated")
                generated = True
            else:
                # Not all projects have all generators -- this is expected
                if "unknown executable" in result.stderr.lower() or "unknown target" in result.stderr.lower():
                    log.info(f"{gen_name}: Not configured for this project, skipping")
                else:
                    log.warning(f"{gen_name}: Failed ({result.stderr.strip()[:200]})")

        if not generated:
            log.info("No Verso generators found for this project")

    def generate_dep_graph(self) -> None:
        """Generate the dependency graph."""
        log.header("Generating dependency graph")

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
            log.info(f"[DRY-RUN] Would run: {' '.join(cmd)}")
        else:
            subprocess.run(cmd, cwd=self.config.project_root, check=True)

        log.success("Dependency graph generated")

    def generate_site(self) -> None:
        """Generate the site with Runway."""
        log.header("Generating site with Runway")

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
            log.info(f"[DRY-RUN] Would run: {' '.join(cmd)}")
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
            log.header("Generating paper")

            cmd = [
                "lake", "exe", "runway",
                "--build-dir", str(self.config.project_root / ".lake" / "build"),
                "--output", str(output_dir),
                "paper",
                str(self.config.project_root / "runway.json"),
            ]

            if self.config.dry_run:
                log.info(f"[DRY-RUN] Would run: {' '.join(cmd)}")
            else:
                subprocess.run(cmd, cwd=runway_path, check=True)

            log.success("Paper generated")

    def start_server(self) -> int:
        """Start the HTTP server and return PID."""
        log.header("Starting server")

        output_dir = self.config.project_root / ".lake" / "build" / "runway"

        # Kill any existing servers on port 8000
        kill_processes_on_port(8000, self.config.dry_run)

        if self.config.dry_run:
            log.info(f"[DRY-RUN] Would start server at {output_dir}")
            return 0

        # Start server in background
        pid = start_http_server(output_dir, 8000, self.config.dry_run)

        log.success(f"Server started at http://localhost:8000 (PID: {pid})")

        # Open browser
        time.sleep(1)
        open_browser("http://localhost:8000", self.config.dry_run)

        return pid or 0

    def run_capture(self) -> None:
        """Run screenshot capture using the sbs CLI."""
        log.header("Capturing screenshots")

        if self.config.dry_run:
            log.info("[DRY-RUN] Would capture screenshots")
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

        log.header(f"{self.config.project_name} Blueprint Builder")
        log.info(f"Run ID: {self._run_id}")

        try:
            # Pre-flight validation (catches missing files before expensive ops)
            if not self.config.skip_validation:
                self._start_phase("validation")
                self._validate_project_structure()
                self._end_phase("validation")
            else:
                log.info("Skipping pre-flight validation (--skip-validation)")

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

            # Update manifests only if Lean sources changed
            if self.config.force_lake or has_lean_changes(
                self.config.project_root, self.config.cache_dir, self.config.project_name
            ):
                self._start_phase("update_manifests")
                self.update_manifests()
                self._end_phase("update_manifests")
            else:
                log.info("Skipping manifest update: Lean sources unchanged")

            # Compliance checks
            self._start_phase("compliance_checks")
            self.run_compliance_checks()
            self._end_phase("compliance_checks")

            # Quality validators (non-blocking)
            self._start_phase("quality_validators")
            self.run_quality_validators()
            self._end_phase("quality_validators")

            # Clean artifacts only if explicitly requested or manifests changed
            # This preserves dressed/ artifacts for skip logic when Lean unchanged
            if self.config.force_clean or self._lake_manifests_changed():
                self._start_phase("clean_build")
                self.clean_artifacts()
                self._end_phase("clean_build")
            else:
                log.info("Skipping artifact cleanup: manifests unchanged (use --clean to force)")

            # Build toolchain (mandatory - ensures consistency)
            self._start_phase("build_toolchain")
            self.build_toolchain()
            self._end_phase("build_toolchain")

            # Fetch mathlib cache (extracted from build_project for granular timing)
            if self._needs_project_build():
                self._start_phase("fetch_mathlib_cache")
                fetch_mathlib_cache(self.config.project_root, self.config.dry_run)
                self._end_phase("fetch_mathlib_cache")
            else:
                log.info("Skipping mathlib cache fetch: Lean sources unchanged")

            # Build project
            self._start_phase("build_project")
            self._build_project_internal()
            self._end_phase("build_project")

            # Build blueprint facet
            if self._needs_project_build():
                self._start_phase("build_blueprint")
                lake_build(self.config.project_root, ":blueprint", self.config.dry_run)
                self._end_phase("build_blueprint")
            else:
                log.info("Skipping blueprint build: Lean sources unchanged")

            # Generate Verso documents (paper_verso, blueprint_verso)
            self._start_phase("generate_verso")
            self.generate_verso_documents()
            self._end_phase("generate_verso")

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

            log.header("BUILD COMPLETE")
            log.info(f"Output: {self.config.project_root / '.lake' / 'build' / 'runway'}")
            log.info("Web: http://localhost:8000")

            # Print timing summary
            total = time.time() - self._build_start
            log.info(f"Total time: {total:.1f}s")
            if self.config.verbose:
                for phase, duration in self._phase_timings.items():
                    log.info(f"  {phase}: {duration:.1f}s")

        except Exception as e:
            self._build_success = False
            self._error_message = str(e)
            raise

        finally:
            # Always save metrics (best-effort)
            self._save_metrics()

            # Archive finalization (best-effort)
            entry = self._create_archive_entry()
            self._finalize_archive(entry)


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
        "--skip-validation",
        action="store_true",
        help="Skip pre-flight validation checks",
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

    parser.add_argument(
        "--force-lake",
        action="store_true",
        help="Force Lake builds even if Lean sources are unchanged",
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Force full cleanup of build artifacts before building",
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
            skip_validation=args.skip_validation,
            dry_run=args.dry_run,
            verbose=args.verbose,
            capture=args.capture,
            capture_url=args.capture_url,
            force_lake=args.force_lake,
            force_clean=args.clean,
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
