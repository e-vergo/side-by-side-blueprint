"""
Build phases for Side-by-Side Blueprint.

Individual build operations that can be orchestrated together.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from sbs.core.utils import log, run_cmd, parse_lakefile, git_has_changes


# =============================================================================
# Lakefile Parsing (Extended)
# =============================================================================


def parse_lakefile_toml(path: Path) -> list[dict[str, Any]]:
    """Parse a lakefile.toml and return the list of requirements."""
    try:
        import tomllib
    except ImportError:
        try:
            import toml as tomllib  # type: ignore
        except ImportError:
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


# =============================================================================
# Git Operations (Build-specific)
# =============================================================================


def run_cmd_with_dry_run(
    cmd: list[str],
    cwd: Optional[Path] = None,
    capture: bool = False,
    check: bool = True,
    dry_run: bool = False,
) -> subprocess.CompletedProcess:
    """Run a command with proper error handling and dry-run support."""
    if dry_run:
        log.info(f"[DRY-RUN] Would run: {' '.join(cmd)}" + (f" in {cwd}" if cwd else ""))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    return run_cmd(cmd, cwd=cwd, capture=capture, check=check)


def git_commit_and_push(repo_path: Path, dry_run: bool = False) -> bool:
    """Commit and push changes in a repo. Returns True if changes were pushed."""
    if not git_has_changes(repo_path):
        return False

    if dry_run:
        log.info(f"[DRY-RUN] Would commit and push changes in {repo_path.name}")
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
        log.info(f"[DRY-RUN] Would pull latest in {repo_path.name}")
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
# Build Operations
# =============================================================================


def clean_build_artifacts(repo_path: Path, dry_run: bool = False) -> None:
    """Clean build artifacts for a repo."""
    build_dir = repo_path / ".lake" / "build"

    if build_dir.exists():
        if dry_run:
            log.info(f"[DRY-RUN] Would remove {build_dir}")
        else:
            shutil.rmtree(build_dir)


def lake_build(repo_path: Path, target: Optional[str] = None, dry_run: bool = False) -> None:
    """Run lake build in a repo."""
    cmd = ["lake", "build"]
    if target:
        cmd.append(target)

    if dry_run:
        log.info(f"[DRY-RUN] Would run: {' '.join(cmd)} in {repo_path}")
        return

    run_cmd(cmd, cwd=repo_path)


def lake_update(repo_path: Path, dep: Optional[str] = None, dry_run: bool = False) -> None:
    """Run lake update in a repo."""
    cmd = ["lake", "update"]
    if dep:
        cmd.append(dep)

    if dry_run:
        log.info(f"[DRY-RUN] Would run: {' '.join(cmd)} in {repo_path}")
        return

    run_cmd(cmd, cwd=repo_path, check=False)  # lake update can fail if already up to date


def fetch_mathlib_cache(project_root: Path, dry_run: bool = False) -> None:
    """Fetch mathlib cache for a project."""
    if dry_run:
        log.info(f"[DRY-RUN] Would fetch mathlib cache in {project_root}")
        return

    run_cmd(["lake", "exe", "cache", "get"], cwd=project_root, check=False)


def build_project_with_dress(project_root: Path, dry_run: bool = False) -> None:
    """Build the Lean project with dressed artifacts (BLUEPRINT_DRESS=1)."""
    if dry_run:
        log.info("[DRY-RUN] Would run: BLUEPRINT_DRESS=1 lake build")
        return

    env = os.environ.copy()
    env["BLUEPRINT_DRESS"] = "1"
    subprocess.run(
        ["lake", "build"],
        cwd=project_root,
        env=env,
        check=True,
    )


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
        log.info(f"[DRY-RUN] Would close Chrome windows except ID {preserve_window_id}")
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
# Server Management
# =============================================================================


def kill_processes_on_port(port: int, dry_run: bool = False) -> None:
    """Kill any processes listening on a port."""
    if dry_run:
        log.info(f"[DRY-RUN] Would kill processes on port {port}")
        return

    subprocess.run(
        f"lsof -ti:{port} | xargs kill -9 2>/dev/null || true",
        shell=True,
        capture_output=True,
    )


def start_http_server(directory: Path, port: int = 8000, dry_run: bool = False) -> Optional[int]:
    """Start an HTTP server in the background. Returns PID or None."""
    if dry_run:
        log.info(f"[DRY-RUN] Would start server at {directory}")
        return 0

    proc = subprocess.Popen(
        ["python3", "-m", "http.server", "-d", str(directory), str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return proc.pid


def open_browser(url: str, dry_run: bool = False) -> None:
    """Open a URL in the default browser."""
    if dry_run:
        log.info(f"[DRY-RUN] Would open {url}")
        return

    subprocess.Popen(["open", url])
