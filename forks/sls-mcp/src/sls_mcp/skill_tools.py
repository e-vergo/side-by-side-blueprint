"""Skill tool implementations for MCP-based skill invocation.

This module contains MCP tools that serve as entry points for skills:
- sls_task: General-purpose agentic task execution
- sls_log: Quick capture of bugs, features, ideas to GitHub Issues
- sls_qa: Live interactive QA against running SBS blueprint site
- sls_introspect: Introspection and self-improvement
- sls_converge: Autonomous QA convergence loop
- sls_update_and_archive: Documentation refresh and porcelain state
- sls_divination: Codebase exploration and guidance

These tools are designed to be invoked by agents to drive skill lifecycles,
replacing the prompt-based SKILL.md approach with structured MCP tool calls.
"""

import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .duckdb_layer import DuckDBLayer
from .sls_models import (
    ConvergeResult,
    DivinationResult,
    IntrospectResult,
    LogResult,
    QAResult,
    SelfImproveContext,
    TaskResult,
    UpdateArchiveResult,
)
from .sls_utils import ARCHIVE_DIR, SBS_ROOT

# GitHub repo for issue creation
GITHUB_REPO = "e-vergo/Side-By-Side-Blueprint"


def _get_db(ctx: Context) -> DuckDBLayer:
    """Extract the DuckDBLayer from the MCP lifespan context."""
    return ctx.request_context.lifespan_context.duckdb_layer


def _run_archive_upload(
    trigger: str = "skill",
    global_state: Optional[Dict[str, Any]] = None,
    state_transition: Optional[str] = None,
    issue_refs: Optional[List[int]] = None,
) -> tuple[bool, Optional[str], Optional[str]]:
    """Run sbs archive upload and return (success, entry_id, error).

    Args:
        trigger: Trigger type for the archive entry
        global_state: New global state to set (None to clear)
        state_transition: Either "phase_start", "phase_end", or "phase_fail"
        issue_refs: List of GitHub issue numbers to associate

    Returns:
        Tuple of (success, entry_id, error_message)
    """
    scripts_dir = SBS_ROOT / "dev" / "scripts"

    cmd = ["python3", "-m", "sbs", "archive", "upload", "--trigger", trigger]

    if global_state:
        cmd.extend(["--global-state", json.dumps(global_state)])
    if state_transition:
        cmd.extend(["--state-transition", state_transition])
    if issue_refs:
        cmd.extend(["--issue-refs", ",".join(str(i) for i in issue_refs)])

    try:
        result = subprocess.run(
            cmd,
            cwd=str(scripts_dir),
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Parse entry ID from output
        entry_id = None
        for line in result.stdout.split("\n"):
            if "Entry ID:" in line:
                entry_id = line.split("Entry ID:")[1].strip()
                break
            # Also check for "entry_id:" in JSON output
            if '"entry_id":' in line:
                match = re.search(r'"entry_id":\s*"([^"]+)"', line)
                if match:
                    entry_id = match.group(1)
                    break

        if result.returncode != 0:
            return False, None, result.stderr.strip() or "Archive upload failed"

        return True, entry_id, None

    except subprocess.TimeoutExpired:
        return False, None, "Archive upload timed out after 60 seconds"
    except Exception as e:
        return False, None, str(e)


# Visual file patterns for detecting visual changes in task finalization
_VISUAL_FILE_PATTERNS = [
    "assets/",
    "common.css",
    "blueprint.css",
    "paper.css",
    "dep_graph.css",
    "plastex.js",
    "verso-code.js",
    "Theme.lean",
    "Render.lean",
    "DepGraph.lean",
    "SideBySide.lean",
    "Svg.lean",
]

# Tags that indicate visual changes
_VISUAL_TAGS = [
    "css",
    "visual",
    "layout",
    "template",
    "theme",
    "styling",
    "graph",
    "dashboard",
]


def _detect_visual_changes(db: "DuckDBLayer") -> bool:
    """Detect whether the current epoch contains visual changes.

    Checks two signals:
    1. Archive entry tags containing visual-related keywords
    2. repo_commits referencing visual file patterns

    Returns:
        True if visual changes were detected in the current epoch.
    """
    try:
        entries = db.get_epoch_entries()
    except Exception:
        return False

    for entry in entries:
        # Check tags
        tags = entry.get("tags", [])
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except (json.JSONDecodeError, TypeError):
                tags = []

        for tag in tags:
            tag_lower = str(tag).lower()
            if any(vt in tag_lower for vt in _VISUAL_TAGS):
                return True

        # Check repo_commits for visual file paths
        repo_commits = entry.get("repo_commits", {})
        if isinstance(repo_commits, str):
            try:
                repo_commits = json.loads(repo_commits)
            except (json.JSONDecodeError, TypeError):
                repo_commits = {}

        if isinstance(repo_commits, dict):
            for _repo, commit_info in repo_commits.items():
                files = []
                if isinstance(commit_info, dict):
                    files = commit_info.get("files", [])
                elif isinstance(commit_info, list):
                    files = commit_info

                for filepath in files:
                    filepath_str = str(filepath)
                    if any(pat in filepath_str for pat in _VISUAL_FILE_PATTERNS):
                        return True

    return False


def _run_visual_validators(project: str = "SBSTest") -> Dict[str, Any]:
    """Run T5 (status color match) and T6 (CSS variable coverage) validators.

    Returns:
        Dict with 'passed', 'failed', 'total', 'details' keys.
    """
    scripts_dir = SBS_ROOT / "dev" / "scripts"
    cmd = [
        "/opt/homebrew/bin/python3", "-m", "pytest",
        "sbs/tests/pytest/validators/test_color_match.py",
        "sbs/tests/pytest/validators/test_variable_coverage.py",
        "-v", "--tb=short", "-q",
    ]

    result_info: Dict[str, Any] = {
        "passed": 0,
        "failed": 0,
        "total": 0,
        "details": [],
    }

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(scripts_dir),
            timeout=120,
        )

        output = result.stdout + result.stderr

        # Parse pytest summary line: "X passed, Y failed in Z.ZZs"
        summary_match = re.search(
            r"(\d+) passed(?:.*?(\d+) failed)?",
            output,
        )
        if summary_match:
            result_info["passed"] = int(summary_match.group(1) or 0)
            result_info["failed"] = int(summary_match.group(2) or 0)

        result_info["total"] = result_info["passed"] + result_info["failed"]

        # Extract FAILED lines for details
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("FAILED") or ("FAILED" in line and "::" in line):
                result_info["details"].append(line)

    except subprocess.TimeoutExpired:
        result_info["details"].append("T5/T6 validators timed out after 120s")
    except Exception as e:
        result_info["details"].append(f"T5/T6 validator error: {str(e)}")

    return result_info


def _parse_l3_findings(summary_content: str) -> List[Dict[str, str]]:
    """Extract actionable findings from L3+ meta-analysis markdown.

    Looks for structured patterns:
    - Numbered lists under "## Findings", "## Actions", "## Recommendations"
    - Lines starting with "- **" or "- [ ]" as action items
    - Bold text as titles followed by description

    Returns:
        List of dicts with 'title' and 'body' keys, max 5 findings.
    """
    findings: List[Dict[str, str]] = []
    if not summary_content:
        return findings

    # Split into sections by ## headers
    sections = re.split(r"^##\s+", summary_content, flags=re.MULTILINE)

    # Look for actionable sections
    actionable_headers = [
        "finding", "action", "recommend", "issue", "improvement",
        "observation", "concern", "suggestion",
    ]

    for section in sections:
        lines = section.strip().split("\n")
        if not lines:
            continue

        header = lines[0].lower().strip()
        is_actionable = any(ah in header for ah in actionable_headers)
        if not is_actionable:
            continue

        # Parse numbered or bulleted items from the section body
        current_title = ""
        current_body_lines: List[str] = []

        for line in lines[1:]:
            stripped = line.strip()
            if not stripped:
                continue

            # Match numbered items: "1. Title" or "1. **Title**: description"
            num_match = re.match(r"^\d+\.\s+(.+)", stripped)
            # Match bullet items: "- **Title**: description" or "- [ ] Title"
            bullet_match = re.match(r"^[-*]\s+(.+)", stripped)

            if num_match or bullet_match:
                # Save previous finding
                if current_title:
                    body = "\n".join(current_body_lines).strip()
                    findings.append({"title": current_title, "body": body})

                content = (num_match or bullet_match).group(1)  # type: ignore[union-attr]

                # Extract title from bold: "**Title**: rest"
                bold_match = re.match(r"\*\*(.+?)\*\*[:\s]*(.*)", content)
                checkbox_match = re.match(r"\[[ x]\]\s*(.*)", content)

                if bold_match:
                    current_title = bold_match.group(1).strip()
                    current_body_lines = [bold_match.group(2).strip()] if bold_match.group(2).strip() else []
                elif checkbox_match:
                    current_title = checkbox_match.group(1).strip()
                    current_body_lines = []
                else:
                    # Use the whole line as title (truncate if too long)
                    current_title = content[:120].strip()
                    current_body_lines = []
            elif current_title:
                # Continuation line for current item
                current_body_lines.append(stripped)

        # Save the last finding
        if current_title:
            body = "\n".join(current_body_lines).strip()
            findings.append({"title": current_title, "body": body})

    # Deduplicate by title similarity and limit to 5
    seen_titles: set = set()
    unique_findings: List[Dict[str, str]] = []
    for f in findings:
        title_key = f["title"].lower().strip()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_findings.append(f)

    return unique_findings[:5]


def _deduplicate_against_open_issues(
    findings: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """Filter findings that match existing open GitHub issues by title similarity.

    Queries open issues and removes findings whose titles closely match
    existing issue titles (case-insensitive substring match).

    Returns:
        Filtered list of findings that don't duplicate existing issues.
    """
    if not findings:
        return findings

    # Fetch open issues
    try:
        result = subprocess.run(
            [
                "gh", "issue", "list",
                "--repo", GITHUB_REPO,
                "--json", "title",
                "--limit", "100",
                "--state", "open",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            # Cannot check for duplicates -- allow all through
            return findings

        existing = json.loads(result.stdout)
        existing_titles = [
            item.get("title", "").lower().strip()
            for item in existing
            if isinstance(item, dict)
        ]
    except Exception:
        # Cannot check -- allow all through
        return findings

    novel: List[Dict[str, str]] = []
    for finding in findings:
        title_lower = finding["title"].lower().strip()
        is_duplicate = False
        for existing_title in existing_titles:
            # Check substring match in both directions
            if (
                title_lower in existing_title
                or existing_title in title_lower
                # Also check word overlap > 60%
                or _word_overlap(title_lower, existing_title) > 0.6
            ):
                is_duplicate = True
                break
        if not is_duplicate:
            novel.append(finding)

    return novel


def _word_overlap(a: str, b: str) -> float:
    """Calculate word overlap ratio between two strings."""
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    return len(intersection) / min(len(words_a), len(words_b))


def _create_l3_issues(
    findings: List[Dict[str, str]],
    level: int,
) -> tuple[List[int], Optional[int]]:
    """Create GitHub issues for L3+ findings and an epic linking them.

    Args:
        findings: List of {title, body} dicts to create issues for.
        level: Introspection level (3, 4, etc.)

    Returns:
        (issue_numbers, epic_number) - list of created issue numbers and epic issue number.
    """
    created_numbers: List[int] = []

    for finding in findings:
        title = f"[L{level}] {finding['title']}"
        body = finding.get("body", "") or "(No details provided)"
        body += f"\n\n---\nOrigin: L{level} meta-analysis finding\nLabel: `origin:self-improve`"

        try:
            result = subprocess.run(
                [
                    "gh", "issue", "create",
                    "--repo", GITHUB_REPO,
                    "--title", title,
                    "--body", body,
                    "--label", "origin:self-improve,ai-authored",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                url = result.stdout.strip()
                if "/issues/" in url:
                    try:
                        num = int(url.split("/issues/")[-1])
                        created_numbers.append(num)
                    except ValueError:
                        pass
        except Exception:
            continue

    # Create epic issue linking all child issues
    epic_number: Optional[int] = None
    if len(created_numbers) >= 2:
        epic_title = f"[L{level}] Meta-analysis findings ({datetime.now().strftime('%Y-%m-%d')})"
        issue_links = "\n".join(f"- #{num}" for num in created_numbers)
        epic_body = (
            f"## L{level} Meta-Analysis Findings\n\n"
            f"Auto-created from L{level} introspection.\n\n"
            f"### Linked Issues\n{issue_links}\n\n"
            f"---\nOrigin: L{level} meta-analysis epic\n"
            f"Label: `origin:self-improve`"
        )

        try:
            result = subprocess.run(
                [
                    "gh", "issue", "create",
                    "--repo", GITHUB_REPO,
                    "--title", epic_title,
                    "--body", epic_body,
                    "--label", "origin:self-improve,ai-authored",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                url = result.stdout.strip()
                if "/issues/" in url:
                    try:
                        epic_number = int(url.split("/issues/")[-1])
                    except ValueError:
                        pass
        except Exception:
            pass

    return created_numbers, epic_number


# Project name normalization map
_PROJECT_MAP = {
    "SBSTest": "SBSTest",
    "sbs-test": "SBSTest",
    "sls_test": "SBSTest",
    "GCR": "GCR",
    "gcr": "GCR",
    "General_Crystallographic_Restriction": "GCR",
    "PNT": "PNT",
    "pnt": "PNT",
    "PrimeNumberTheoremAnd": "PNT",
}

# Project paths
_PROJECT_PATHS = {
    "SBSTest": SBS_ROOT / "toolchain" / "SBS-Test",
    "GCR": SBS_ROOT / "showcase" / "General_Crystallographic_Restriction",
    "PNT": SBS_ROOT / "showcase" / "PrimeNumberTheoremAnd",
}

# Default QA pages
_DEFAULT_QA_PAGES = ["dashboard", "dep_graph", "chapter"]

# Page URL mappings
_PAGE_URLS = {
    "dashboard": "/",
    "dep_graph": "/dep_graph.html",
    "paper_tex": "/paper.html",
    "pdf_tex": "/pdf.html",
    "chapter": None,  # Auto-detect
}


def _normalize_project(project: str) -> Optional[str]:
    """Normalize project name to canonical form."""
    return _PROJECT_MAP.get(project)


def _get_project_path(project: str) -> Optional[Path]:
    """Get the filesystem path for a project."""
    normalized = _normalize_project(project)
    if normalized:
        return _PROJECT_PATHS.get(normalized)
    return None


def _build_project(project: str, dry_run: bool = False) -> tuple[bool, str]:
    """Build a project using build.py. Returns (success, output)."""
    project_path = _get_project_path(project)
    if not project_path or not project_path.exists():
        return False, f"Project path does not exist: {project_path}"

    scripts_dir = SBS_ROOT / "dev" / "scripts"
    cmd = ["python3", str(scripts_dir / "build.py")]

    if dry_run:
        cmd.append("--dry-run")

    try:
        result = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minute timeout
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Build timed out after 30 minutes"
    except Exception as e:
        return False, str(e)


def _start_server(project: str, port: int = 8000) -> tuple[bool, Optional[int], str]:
    """Start dev server for project. Returns (success, pid, error)."""
    normalized = _normalize_project(project)
    if not normalized:
        return False, None, f"Unknown project: {project}"

    site_path = _get_project_path(project)
    if not site_path:
        return False, None, f"Project path not found: {project}"

    site_dir = site_path / ".lake" / "build" / "runway"
    if not site_dir.exists():
        return False, None, f"Site directory not found at {site_dir}. Run build first."

    # Check if port is already in use
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            result = s.connect_ex(("localhost", port))
            if result == 0:
                # Port in use - assume server is already running
                return True, None, ""
    except Exception:
        pass

    try:
        process = subprocess.Popen(
            ["python3", "-m", "http.server", str(port)],
            cwd=site_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        time.sleep(0.5)

        # Check if process is still running
        if process.poll() is None:
            return True, process.pid, ""
        else:
            stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
            return False, None, f"Server exited immediately: {stderr}"
    except Exception as e:
        return False, None, str(e)


def _stop_server(port: int = 8000) -> bool:
    """Stop server on given port. Returns success."""
    import signal
    import os

    # Find process using the port
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid_str in pids:
                try:
                    pid = int(pid_str)
                    os.kill(pid, signal.SIGTERM)
                except (ValueError, ProcessLookupError):
                    pass
            return True
    except Exception:
        pass
    return False


def _check_server_running(port: int = 8000) -> bool:
    """Check if server is running on port."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(("localhost", port)) == 0
    except Exception:
        return False


def _get_all_repos() -> List[Path]:
    """Get list of all repos (main + submodules) for porcelain check."""
    return [
        SBS_ROOT,  # Main repo
        SBS_ROOT / "forks" / "verso",
        SBS_ROOT / "forks" / "subverso",
        SBS_ROOT / "forks" / "LeanArchitect",
        SBS_ROOT / "forks" / "sls-mcp",
        SBS_ROOT / "toolchain" / "Dress",
        SBS_ROOT / "toolchain" / "Runway",
        SBS_ROOT / "toolchain" / "SBS-Test",
        SBS_ROOT / "toolchain" / "dress-blueprint-action",
        SBS_ROOT / "showcase" / "General_Crystallographic_Restriction",
        SBS_ROOT / "showcase" / "PrimeNumberTheoremAnd",
        SBS_ROOT / "dev" / "storage",
    ]


def _commit_and_push_repo(repo_path: Path, message: str) -> tuple[bool, str]:
    """Commit any changes in repo and push. Returns (had_changes, error)."""
    if not repo_path.exists():
        return False, ""

    try:
        # Check for changes
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if not status_result.stdout.strip():
            # No changes
            return False, ""

        # Stage all changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=repo_path,
            capture_output=True,
            timeout=30,
        )

        # Commit
        commit_result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if commit_result.returncode != 0:
            return False, commit_result.stderr

        # Push via subprocess (bypasses Claude Code hook)
        push_result = subprocess.run(
            ["git", "push"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if push_result.returncode != 0:
            return True, push_result.stderr  # Had changes but push failed

        return True, ""

    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


def _infer_type_label(text: str) -> Optional[str]:
    """Infer type label from text keywords.

    Returns the most specific matching type label, or None if no match.
    Priority: More specific multi-word patterns are checked before single-word patterns.
    """
    text_lower = text.lower()

    # Multi-word patterns first (most specific), then single-word patterns
    # The order within each category matters - more specific should come first
    type_keywords = [
        # Multi-word patterns (check these first - they're more specific)
        ("bug:build", ["build fail", "lake error", "compile error", "lakefile", "build broken"]),
        ("bug:regression", ["regression", "worked before", "used to work", "was working"]),
        ("bug:data", ["data wrong", "archive corrupt", "missing data"]),
        ("bug:visual", ["looks wrong", "look wrong", "broken layout", "misaligned"]),
        ("idea:architecture", ["redesign system"]),
        ("idea:design", ["layout concept"]),
        ("idea:exploration", ["what if"]),
        ("behavior", ["workflow rule", "meta-cognitive", "how claude", "claude should"]),
        ("housekeeping:migration", ["format change"]),
        ("housekeeping:debt", ["tech debt"]),
        ("housekeeping:tooling", ["cli command"]),
        ("housekeeping:cleanup", ["dead code"]),
        ("investigation", ["figure out", "look into", "root cause"]),

        # Single-word patterns (less specific, check after multi-word)
        # Idea/exploration first - "idea" and "explore" are strong signals
        ("idea:exploration", ["idea", "explore", "wonder", "consider"]),
        ("idea:architecture", ["architecture", "restructure", "rethink"]),
        ("idea:design", ["design", "mockup", "wireframe", "ux"]),

        # Bug subtypes - visual keywords before generic ones
        ("bug:build", ["lakefile"]),
        ("bug:regression", ["regression", "broke"]),
        ("bug:data", ["ledger", "manifest"]),
        ("bug:visual", ["visual", "display", "render", "css", "style", "misaligned", "ugly"]),
        ("bug:functional", ["bug", "broken", "error", "crash", "fail", "wrong", "doesn't work", "incorrect"]),

        # Feature subtypes
        ("feature:integration", ["integrate", "connect", "bridge", "combine", "link"]),
        ("feature:enhancement", ["improve", "enhance", "better", "upgrade", "optimize", "refine"]),
        ("feature:new", ["add", "implement", "new", "create", "support", "enable", "introduce"]),

        # Other types
        ("behavior", ["personality", "tone", "communication"]),
        ("housekeeping:migration", ["migrate", "migration", "schema"]),
        ("housekeeping:debt", ["debt", "shortcut", "hack", "workaround"]),
        ("housekeeping:tooling", ["tooling", "script", "maintenance"]),
        ("housekeeping:cleanup", ["cleanup", "refactor", "tidy", "organize"]),
        ("housekeeping:docs", ["document", "readme", "docs", "documentation"]),
        ("investigation", ["investigate", "debug", "understand", "profile"]),
    ]

    for label, keywords in type_keywords:
        for keyword in keywords:
            if keyword in text_lower:
                return label

    return None


def _infer_area_labels(text: str) -> List[str]:
    """Infer area labels from text keywords.

    Returns all matching area labels (multi-area is encouraged).
    """
    text_lower = text.lower()
    areas = []

    area_keywords = [
        # SBS areas
        ("area:sbs:graph", ["graph", "dep graph", "dependency graph", "node", "edge", "layout"]),
        ("area:sbs:dashboard", ["dashboard", "stats panel", "key theorems", "project notes"]),
        ("area:sbs:paper", ["paper", "ar5iv", "verification badge"]),
        ("area:sbs:pdf", ["pdf", "tectonic", "pdflatex"]),
        ("area:sbs:sidebar", ["sidebar", "navigation", "chapter panel"]),
        ("area:sbs:modal", ["modal", "popup", "detail view"]),
        ("area:sbs:theme", ["theme", "dark mode", "light mode", "toggle theme"]),
        ("area:sbs:css", ["css", "stylesheet", "variable", "common.css"]),
        ("area:sbs:js", ["javascript", "js", "plastex.js", "verso-code.js", "tippy"]),
        ("area:sbs:blueprint", ["blueprint attribute", "@[blueprint]", "metadata field"]),
        ("area:sbs:color-model", ["status color", "color model", "notready", "fullyproven"]),
        ("area:sbs:tooltips", ["tooltip", "hover", "tippy", "type signature popup"]),
        ("area:sbs:latex", ["latex", "plastex", "inputleanmodule", "tex"]),
        ("area:sbs:highlighting", ["highlighting", "syntax", "rainbow bracket", "subverso"]),
        ("area:sbs:chapter", ["chapter", "side-by-side", "proof toggle"]),
        ("area:sbs:ci", ["ci", "github action", "deployment", "ci/cd"]),
        # Devtools areas
        ("area:devtools:archive", ["archive", "entry", "epoch", "upload"]),
        ("area:devtools:cli", ["cli", "sbs command", "subcommand"]),
        ("area:devtools:mcp", ["mcp", "mcp tool", "mcp server"]),
        ("area:devtools:validators", ["validator", "t1", "t2", "t5", "t6", "quality score"]),
        ("area:devtools:oracle", ["oracle", "concept index", "knowledge base"]),
        ("area:devtools:skills", ["skill", "skill definition", "skill.md"]),
        ("area:devtools:tagging", ["tag", "auto-tag", "tagging rule"]),
        ("area:devtools:gates", ["gate", "gate failure", "threshold"]),
        ("area:devtools:session-data", ["session", "jsonl", "session data", "extraction"]),
        ("area:devtools:quality-ledger", ["quality ledger", "score ledger", "staleness"]),
        ("area:devtools:compliance", ["compliance", "compliance ledger", "page criteria"]),
        ("area:devtools:capture", ["screenshot", "capture", "playwright"]),
        ("area:devtools:porcelain", ["porcelain", "git push", "submodule commit"]),
        ("area:devtools:state-machine", ["state machine", "global_state", "skill state", "handoff"]),
        ("area:devtools:self-improve", ["self-improve", "self-improvement", "introspect", "pillar", "finding"]),
        ("area:devtools:question-analysis", ["question analysis", "askuserquestion"]),
        ("area:devtools:test-suite", ["test", "pytest", "evergreen", "test tier"]),
        # Lean areas
        ("area:lean:architect", ["leanarchitect", "lean architect", "blueprint attribute"]),
        ("area:lean:dress", ["dress", "artifact generation", "dressed"]),
        ("area:lean:runway", ["runway", "site generation", "runway.json"]),
        ("area:lean:verso", ["verso", "genre", "sbsblueprint"]),
        ("area:lean:subverso", ["subverso", "syntax highlighting"]),
        ("area:lean:lakefile", ["lakefile", "lake", "lake build", "lake update"]),
        ("area:lean:manifest", ["manifest", "manifest.json"]),
        ("area:lean:dressed-artifacts", ["dressed artifact", "decl.html", "decl.json"]),
    ]

    for label, keywords in area_keywords:
        for keyword in keywords:
            if keyword in text_lower:
                if label not in areas:
                    areas.append(label)
                break  # Found match for this area, move to next

    return areas


def register_skill_tools(mcp: FastMCP) -> None:
    """Register skill-level MCP tools with the server.

    These tools provide structured entry points for skill invocation,
    replacing prompt-based SKILL.md files with MCP tool implementations.

    Args:
        mcp: The FastMCP server instance to register tools on.
    """

    @mcp.tool(
        "sls_task",
        annotations=ToolAnnotations(
            title="SBS Task Skill",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    def sls_task(
        ctx: Context,
        phase: Annotated[
            Literal["start", "plan", "execute", "finalize"],
            Field(description="Task phase: start (alignment), plan, execute, or finalize"),
        ],
        issue_refs: Annotated[
            Optional[List[int]],
            Field(description="GitHub issue numbers this task relates to"),
        ] = None,
        plan_content: Annotated[
            Optional[str],
            Field(description="Plan markdown content (required for plan phase)"),
        ] = None,
        pr_number: Annotated[
            Optional[int],
            Field(description="PR number created during planning"),
        ] = None,
        agents_to_spawn: Annotated[
            Optional[List[Dict[str, Any]]],
            Field(description="Agent spawn specs for execution phase"),
        ] = None,
        auto_mode: Annotated[
            bool,
            Field(description="Skip alignment/planning, go direct to execution"),
        ] = False,
        task_description: Annotated[
            Optional[str],
            Field(description="Task description for freeform invocation"),
        ] = None,
    ) -> TaskResult:
        """Execute a phase of the /task skill workflow.

        The task skill follows: start (alignment) -> plan -> execute -> finalize

        Args:
            phase: Which phase to execute
            issue_refs: GitHub issue numbers this task relates to
            plan_content: Plan markdown (required for plan phase, used for gate extraction)
            pr_number: PR number if one was created during planning
            agents_to_spawn: Agent spawn specifications for execution phase
            auto_mode: If True, skip alignment/planning phases
            task_description: Task description for freeform tasks

        Returns:
            TaskResult with success, next_action, gate_results, etc.
        """
        from .gate_validation import GateSpec, parse_gate_spec_from_plan, validate_gates

        db = _get_db(ctx)

        # =====================================================================
        # START PHASE (Alignment)
        # =====================================================================
        if phase == "start":
            # Check current state - must be idle or resuming this skill
            current_skill, current_substate = db.get_global_state()

            if current_skill and current_skill != "task":
                return TaskResult(
                    success=False,
                    error=f"Cannot start task: skill '{current_skill}' is already active",
                    phase_completed=None,
                    next_action=None,
                    issue_refs=issue_refs or [],
                )

            # Load issue context if issue_refs provided
            issue_context = []
            if issue_refs:
                for issue_num in issue_refs:
                    try:
                        result = subprocess.run(
                            ["gh", "issue", "view", str(issue_num), "--repo", GITHUB_REPO, "--json", "title,body,labels"],
                            capture_output=True,
                            text=True,
                            timeout=15,
                        )
                        if result.returncode == 0:
                            issue_data = json.loads(result.stdout)
                            issue_context.append(issue_data)
                    except Exception:
                        pass

            # Determine initial substate based on auto_mode
            initial_substate = "execution" if auto_mode else "alignment"

            # Start the skill
            new_state = {"skill": "task", "substate": initial_substate}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
                state_transition="phase_start",
                issue_refs=issue_refs,
            )

            if not success:
                return TaskResult(
                    success=False,
                    error=f"Failed to start task skill: {error}",
                    phase_completed=None,
                    next_action=None,
                    issue_refs=issue_refs or [],
                )
            db.invalidate()

            # Determine next action
            if auto_mode:
                next_action = "execute"
            else:
                next_action = "plan"

            return TaskResult(
                success=True,
                error=None,
                phase_completed="start",
                next_action=next_action,
                issue_refs=issue_refs or [],
            )

        # =====================================================================
        # PLAN PHASE
        # =====================================================================
        elif phase == "plan":
            # Verify we're in task skill
            current_skill, current_substate = db.get_global_state()
            if current_skill != "task":
                return TaskResult(
                    success=False,
                    error=f"Cannot plan: task skill not active (current: {current_skill or 'none'})",
                    phase_completed=None,
                    next_action=None,
                    issue_refs=issue_refs or [],
                )

            # Transition to planning phase
            new_state = {"skill": "task", "substate": "planning"}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
                state_transition="phase_start",
                issue_refs=issue_refs,
            )
            if not success:
                return TaskResult(
                    success=False,
                    error=f"Failed to transition to planning: {error}",
                    phase_completed=None,
                    next_action=None,
                    issue_refs=issue_refs or [],
                )
            db.invalidate()

            # Parse gate spec from plan content
            gate_spec = None
            if plan_content:
                gate_spec = parse_gate_spec_from_plan(plan_content)

            # If PR number provided or we should create one, track it
            result_pr_number = pr_number

            return TaskResult(
                success=True,
                error=None,
                phase_completed="plan",
                next_action="execute",
                pr_number=result_pr_number,
                issue_refs=issue_refs or [],
            )

        # =====================================================================
        # EXECUTE PHASE
        # =====================================================================
        elif phase == "execute":
            # Verify we're in task skill
            current_skill, current_substate = db.get_global_state()
            if current_skill != "task":
                return TaskResult(
                    success=False,
                    error=f"Cannot execute: task skill not active (current: {current_skill or 'none'})",
                    phase_completed=None,
                    next_action=None,
                    issue_refs=issue_refs or [],
                )

            # Transition to execution phase
            new_state = {"skill": "task", "substate": "execution"}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
                state_transition="phase_start",
                issue_refs=issue_refs,
            )
            if not success:
                return TaskResult(
                    success=False,
                    error=f"Failed to transition to execution: {error}",
                    phase_completed=None,
                    next_action=None,
                    issue_refs=issue_refs or [],
                )
            db.invalidate()

            # Return execution phase completed - orchestrator spawns agents
            return TaskResult(
                success=True,
                error=None,
                phase_completed="execute",
                next_action="finalize",
                agents_to_spawn=agents_to_spawn,
                pr_number=pr_number,
                issue_refs=issue_refs or [],
            )

        # =====================================================================
        # FINALIZE PHASE
        # =====================================================================
        elif phase == "finalize":
            # Verify we're in task skill
            current_skill, current_substate = db.get_global_state()
            if current_skill != "task":
                return TaskResult(
                    success=False,
                    error=f"Cannot finalize: task skill not active (current: {current_skill or 'none'})",
                    phase_completed=None,
                    next_action=None,
                    issue_refs=issue_refs or [],
                )

            # Transition to finalization phase
            new_state = {"skill": "task", "substate": "finalization"}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
                state_transition="phase_start",
                issue_refs=issue_refs,
            )
            if not success:
                return TaskResult(
                    success=False,
                    error=f"Failed to transition to finalization: {error}",
                    phase_completed=None,
                    next_action=None,
                    issue_refs=issue_refs or [],
                )
            db.invalidate()

            # Validate gates if plan content provided
            gate_results: List[str] = []
            gate_failures: List[str] = []
            requires_approval = False

            if plan_content:
                gate_spec = parse_gate_spec_from_plan(plan_content)
                if gate_spec:
                    # Default to SBSTest for validation
                    project = "SBSTest"
                    gate_result = validate_gates(ctx, gate_spec, project)
                    gate_results = gate_result.results
                    gate_failures = gate_result.failures

                    if not gate_result.all_pass:
                        requires_approval = True

            # Auto-run T5/T6 validators if visual changes detected (soft gate)
            visual_validator_results: Optional[Dict[str, Any]] = None
            if _detect_visual_changes(db):
                visual_validator_results = _run_visual_validators()
                if visual_validator_results["failed"] > 0:
                    # Soft gate: warn but don't block
                    for detail in visual_validator_results.get("details", []):
                        gate_results.append(f"[WARN] Visual validator: {detail}")
                    gate_results.append(
                        f"[WARN] T5/T6 visual validators: "
                        f"{visual_validator_results['passed']} passed, "
                        f"{visual_validator_results['failed']} failed "
                        f"(soft gate - not blocking finalization)"
                    )
                elif visual_validator_results["total"] > 0:
                    gate_results.append(
                        f"T5/T6 visual validators: "
                        f"{visual_validator_results['passed']}/{visual_validator_results['total']} passed"
                    )
                else:
                    gate_results.append(
                        "T5/T6 visual validators: no tests collected (check test paths)"
                    )

            # If gates pass (or no gates), proceed to handoff
            if not requires_approval:
                # Merge PR if one exists
                if pr_number:
                    try:
                        merge_result = subprocess.run(
                            ["gh", "pr", "merge", str(pr_number), "--repo", GITHUB_REPO,
                             "--squash", "--delete-branch"],
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )
                        if merge_result.returncode != 0:
                            gate_failures.append(f"PR merge failed: {merge_result.stderr}")
                    except Exception as e:
                        gate_failures.append(f"PR merge error: {str(e)}")

                # Close issues if specified
                if issue_refs:
                    for issue_num in issue_refs:
                        try:
                            subprocess.run(
                                ["gh", "issue", "close", str(issue_num), "--repo", GITHUB_REPO],
                                capture_output=True,
                                timeout=15,
                            )
                        except Exception:
                            pass

                # Handoff to update-and-archive
                new_state = {"skill": "update-and-archive", "substate": "retrospective"}
                success, entry_id, error = _run_archive_upload(
                    trigger="skill",
                    global_state=new_state,
                    state_transition="phase_start",
                    issue_refs=issue_refs,
                )
                db.invalidate()

                return TaskResult(
                    success=True,
                    error=None,
                    phase_completed="finalize",
                    next_action="update-and-archive",
                    gate_results=gate_results,
                    gate_failures=gate_failures,
                    requires_approval=False,
                    pr_number=pr_number,
                    issue_refs=issue_refs or [],
                )
            else:
                # Gates failed - require approval
                return TaskResult(
                    success=True,
                    error=None,
                    phase_completed="finalize",
                    next_action="await_approval",
                    gate_results=gate_results,
                    gate_failures=gate_failures,
                    requires_approval=True,
                    pr_number=pr_number,
                    issue_refs=issue_refs or [],
                )

        else:
            return TaskResult(
                success=False,
                error=f"Unknown phase: {phase}",
                phase_completed=None,
                next_action=None,
                issue_refs=issue_refs or [],
            )

    @mcp.tool(
        "sls_log",
        annotations=ToolAnnotations(
            title="SBS Log Skill",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    def sls_log(
        ctx: Context,
        title: Annotated[
            str,
            Field(description="Issue title"),
        ],
        body: Annotated[
            Optional[str],
            Field(description="Issue body/description"),
        ] = None,
        labels: Annotated[
            Optional[List[str]],
            Field(description="Labels from taxonomy dimensions"),
        ] = None,
    ) -> LogResult:
        """Quick capture of bugs, features, and ideas to GitHub Issues.

        Atomic skill that creates a GitHub issue with label inference.
        Always applies origin:agent and ai-authored labels.

        If labels are not provided, infers type and area from the title/body text.

        Args:
            title: Issue title
            body: Issue body/description
            labels: Labels from taxonomy (bug:*, feature:*, idea:*, area:*, etc.)

        Returns:
            LogResult with success, issue_number, issue_url, labels_applied
        """
        # Build label set - always include these base labels
        resolved_labels = ["origin:agent", "ai-authored"]

        if labels:
            # User provided explicit labels
            resolved_labels.extend(labels)
        else:
            # Infer labels from title and body text
            search_text = title + " " + (body or "")

            # Infer type
            type_label = _infer_type_label(search_text)
            if type_label:
                resolved_labels.append(type_label)

            # Infer areas (can be multiple)
            area_labels = _infer_area_labels(search_text)
            resolved_labels.extend(area_labels)

        # Attribution footer for AI transparency
        attribution = "\n\n---\n🤖 Created with [Claude Code](https://claude.ai/code)"
        full_body = (body or "") + attribution

        # Create issue via gh CLI
        cmd = ["gh", "issue", "create", "--repo", GITHUB_REPO, "--title", title]
        cmd.extend(["--body", full_body])
        cmd.extend(["--label", ",".join(resolved_labels)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return LogResult(
                    success=False,
                    error=result.stderr.strip() or "Failed to create issue",
                    issue_number=None,
                    issue_url=None,
                    labels_applied=[],
                )

            # Parse URL from output (e.g., "https://github.com/e-vergo/Side-By-Side-Blueprint/issues/123")
            url = result.stdout.strip()
            number = None
            if url and "/issues/" in url:
                try:
                    number = int(url.split("/issues/")[-1])
                except ValueError:
                    pass

            # Archive with issue reference
            if number:
                _run_archive_upload(trigger="skill", issue_refs=[number])

            return LogResult(
                success=True,
                error=None,
                issue_number=number,
                issue_url=url,
                labels_applied=resolved_labels,
            )

        except subprocess.TimeoutExpired:
            return LogResult(
                success=False,
                error="Command timed out after 30 seconds",
                issue_number=None,
                issue_url=None,
                labels_applied=[],
            )
        except Exception as e:
            return LogResult(
                success=False,
                error=str(e),
                issue_number=None,
                issue_url=None,
                labels_applied=[],
            )

    @mcp.tool(
        "sls_qa",
        annotations=ToolAnnotations(
            title="SBS QA Skill",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    def sls_qa(
        ctx: Context,
        phase: Annotated[
            Literal["setup", "review", "report"],
            Field(description="QA phase: setup (server/navigation), review (per-page checks), report"),
        ],
        project: Annotated[
            str,
            Field(description="Project name: SBSTest, GCR, or PNT"),
        ],
        pages: Annotated[
            Optional[List[str]],
            Field(description="Specific pages to QA, or all if omitted"),
        ] = None,
    ) -> QAResult:
        """Live interactive QA against a running SBS blueprint site.

        Browser-driven visual and interactive verification using compliance
        criteria and the test catalog.

        Phases:
        - setup: Build project, start server, claim skill state
        - review: Per-page visual checks (page loads = pass)
        - report: Write ledger, stop server, release state

        Args:
            phase: Which QA phase to execute
            project: Project name (SBSTest, GCR, PNT)
            pages: Specific pages to check, or all if omitted

        Returns:
            QAResult with page_status, issues_logged, etc.
        """
        normalized_project = _normalize_project(project)
        if not normalized_project:
            return QAResult(
                success=False,
                error=f"Unknown project: {project}. Valid: SBSTest, GCR, PNT",
                phase_completed=None,
                page_status={},
                issues_logged=[],
            )

        target_pages = pages if pages else _DEFAULT_QA_PAGES
        db = _get_db(ctx)

        # =====================================================================
        # SETUP PHASE
        # =====================================================================
        if phase == "setup":
            # 1. Start the skill, claim global state
            current_skill, _ = db.get_global_state()
            if current_skill and current_skill != "qa":
                return QAResult(
                    success=False,
                    error=f"Cannot start QA: skill '{current_skill}' is already active",
                    phase_completed=None,
                    page_status={},
                    issues_logged=[],
                )

            # Start skill if not already started
            if current_skill != "qa":
                new_state = {"skill": "qa", "substate": "setup"}
                success, entry_id, error = _run_archive_upload(
                    trigger="skill",
                    global_state=new_state,
                    state_transition="phase_start",
                )
                if not success:
                    return QAResult(
                        success=False,
                        error=f"Failed to start QA skill: {error}",
                        phase_completed=None,
                        page_status={},
                        issues_logged=[],
                    )
                db.invalidate()

            # 2. Build project
            build_success, build_output = _build_project(normalized_project)
            if not build_success:
                # Record failure and release state
                _run_archive_upload(
                    trigger="skill",
                    global_state=None,
                    state_transition="phase_fail",
                )
                db.invalidate()
                return QAResult(
                    success=False,
                    error=f"Build failed: {build_output[:500]}",
                    phase_completed=None,
                    page_status={},
                    issues_logged=[],
                )

            # 3. Start dev server
            server_success, server_pid, server_error = _start_server(normalized_project)
            if not server_success:
                _run_archive_upload(
                    trigger="skill",
                    global_state=None,
                    state_transition="phase_fail",
                )
                db.invalidate()
                return QAResult(
                    success=False,
                    error=f"Server failed to start: {server_error}",
                    phase_completed=None,
                    page_status={},
                    issues_logged=[],
                )

            return QAResult(
                success=True,
                error=None,
                phase_completed="setup",
                page_status={},
                issues_logged=[],
            )

        # =====================================================================
        # REVIEW PHASE
        # =====================================================================
        elif phase == "review":
            # Verify we're in QA skill
            current_skill, current_substate = db.get_global_state()
            if current_skill != "qa":
                return QAResult(
                    success=False,
                    error=f"Cannot review: QA skill not active (current: {current_skill or 'none'})",
                    phase_completed=None,
                    page_status={},
                    issues_logged=[],
                )

            # Transition to review phase
            new_state = {"skill": "qa", "substate": "review"}
            success, _, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
            )
            if not success:
                return QAResult(
                    success=False,
                    error=f"Failed to transition to review: {error}",
                    phase_completed=None,
                    page_status={},
                    issues_logged=[],
                )
            db.invalidate()

            # Check server is running
            if not _check_server_running():
                return QAResult(
                    success=False,
                    error="Server not running. Run setup phase first.",
                    phase_completed=None,
                    page_status={},
                    issues_logged=[],
                )

            # Perform simplified review: check if pages load
            # Note: Full browser-based review would use async browser tools
            # This is a simplified synchronous implementation
            page_status: Dict[str, str] = {}
            import urllib.request
            import urllib.error

            for page in target_pages:
                url_path = _PAGE_URLS.get(page)
                if url_path is None and page == "chapter":
                    # Auto-detect chapter: try /SBSChapter1.html or first chapter
                    url_path = "/SBSChapter1.html"

                if url_path is None:
                    url_path = f"/{page}.html"

                full_url = f"http://localhost:8000{url_path}"

                try:
                    with urllib.request.urlopen(full_url, timeout=10) as response:
                        if response.status == 200:
                            page_status[page] = "pass"
                        else:
                            page_status[page] = "fail"
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        page_status[page] = "warn"  # Page not found, skip
                    else:
                        page_status[page] = "fail"
                except Exception:
                    page_status[page] = "fail"

            return QAResult(
                success=True,
                error=None,
                phase_completed="review",
                page_status=page_status,
                issues_logged=[],
            )

        # =====================================================================
        # REPORT PHASE
        # =====================================================================
        elif phase == "report":
            # Verify we're in QA skill
            current_skill, _ = db.get_global_state()
            if current_skill != "qa":
                return QAResult(
                    success=False,
                    error=f"Cannot report: QA skill not active (current: {current_skill or 'none'})",
                    phase_completed=None,
                    page_status={},
                    issues_logged=[],
                )

            # Transition to report phase
            new_state = {"skill": "qa", "substate": "report"}
            success, _, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
            )
            if not success:
                return QAResult(
                    success=False,
                    error=f"Failed to transition to report: {error}",
                    phase_completed=None,
                    page_status={},
                    issues_logged=[],
                )
            db.invalidate()

            # Write QA ledger
            ledger_dir = ARCHIVE_DIR / normalized_project
            ledger_dir.mkdir(parents=True, exist_ok=True)
            ledger_path = ledger_dir / "qa_ledger.json"

            run_id = datetime.now().strftime("%Y%m%d%H%M%S")
            timestamp = datetime.now().isoformat()

            # Note: page_status would come from previous review phase
            # In a real implementation, this would be persisted between phases
            # For now, create a minimal ledger entry
            ledger_data = {
                "version": "1.0",
                "project": normalized_project,
                "run_id": run_id,
                "timestamp": timestamp,
                "pages": {},
                "summary": {
                    "pages_reviewed": len(target_pages),
                    "total_criteria": 0,
                    "passed": 0,
                    "failed": 0,
                    "warnings": 0,
                    "issues_logged": [],
                },
            }

            try:
                with open(ledger_path, "w") as f:
                    json.dump(ledger_data, f, indent=2)
            except Exception as e:
                return QAResult(
                    success=False,
                    error=f"Failed to write ledger: {e}",
                    phase_completed=None,
                    page_status={},
                    issues_logged=[],
                )

            # Stop server
            _stop_server()

            # End skill (clear global state)
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=None,
                state_transition="phase_end",
            )
            db.invalidate()

            return QAResult(
                success=True,
                error=None,
                phase_completed="report",
                page_status={},
                issues_logged=[],
            )

        else:
            return QAResult(
                success=False,
                error=f"Unknown phase: {phase}",
                phase_completed=None,
                page_status={},
                issues_logged=[],
            )

    @mcp.tool(
        "sls_introspect",
        annotations=ToolAnnotations(
            title="SBS Introspect Skill",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    def sls_introspect(
        ctx: Context,
        level: Annotated[
            int,
            Field(description="Introspection level: 2 for L2 self-improvement, 3+ for meta-analysis", ge=2),
        ],
        phase: Annotated[
            str,
            Field(description="Phase within introspect: discovery, selection, dialogue, logging, archive (L2) or ingestion, synthesis, archive (L3+)"),
        ],
        dry_run: Annotated[
            bool,
            Field(description="Discovery only, no issue creation"),
        ] = False,
        selected_findings: Annotated[
            Optional[List[int]],
            Field(description="Indices of findings selected for refinement (for selection phase)"),
        ] = None,
        refined_issues: Annotated[
            Optional[List[Dict[str, Any]]],
            Field(description="Issue specs refined through dialogue (for logging phase)"),
        ] = None,
        summary_content: Annotated[
            Optional[str],
            Field(description="Summary document content (for archive phase)"),
        ] = None,
    ) -> IntrospectResult:
        """Introspection and self-improvement across hierarchy levels.

        L2 workflow: Discovery -> Selection -> Dialogue -> Logging -> Archive
        L3+ workflow: Ingestion -> Synthesis -> Archive

        Args:
            level: Introspection level (2 for self-improve, 3+ for meta-analysis)
            phase: Which phase to execute
            dry_run: If True, discovery only without creating issues
            selected_findings: Indices of findings user selected (selection phase)
            refined_issues: Issue specifications from dialogue (logging phase)
            summary_content: Final summary document (archive phase)

        Returns:
            IntrospectResult with findings_count, issues_created, etc.
        """
        db = _get_db(ctx)

        # Dispatch based on level: L2 vs L3+
        if level >= 3:
            return _introspect_l3_plus(ctx, db, level, phase, summary_content, dry_run)
        else:  # level == 2
            return _introspect_l2(ctx, db, phase, dry_run, selected_findings, refined_issues, summary_content)

    @mcp.tool(
        "sls_self_improve",
        annotations=ToolAnnotations(
            title="SBS Self-Improve Context",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def sls_self_improve(
        ctx: Context,
        multiplier: Annotated[
            int,
            Field(description="Geometric decay multiplier (default 4)"),
        ] = 4,
    ) -> SelfImproveContext:
        """Compute introspection level and assemble context for the sbs-self-improve agent.

        Called by the sbs-self-improve agent at the start of each run.
        Computes the appropriate level based on geometric 4x decay,
        then assembles the context blob with session transcripts,
        lower-level findings, open issues, and improvement captures.
        """
        db = _get_db(ctx)

        # Compute level
        level = db.compute_self_improve_level(multiplier=multiplier)

        # Get archive state
        metadata = db.get_metadata()
        archive_state = metadata

        # For L0: find the latest session transcript (JSONL)
        session_transcript_path = None
        if level == 0:
            sessions_dir = SBS_ROOT / "dev" / "storage" / "claude_data" / "sessions"
            if sessions_dir.exists():
                jsonl_files = sorted(
                    sessions_dir.glob("*.jsonl"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if jsonl_files:
                    session_transcript_path = str(jsonl_files[0])

        # Get entries since last self-improve at this level
        entries_result = db.entries_since_self_improve()
        entries = entries_result.entries_since

        # For L1+: get lower-level findings
        lower_findings: List[str] = []
        if level >= 1:
            lower_findings = db.get_self_improve_findings(level - 1)

        # Get open issues for correlation
        open_issues: List[Dict[str, Any]] = []
        try:
            result = subprocess.run(
                [
                    "gh", "issue", "list", "--repo", GITHUB_REPO, "--state", "open",
                    "--json", "number,title,labels", "--limit", "50",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                open_issues = json.loads(result.stdout)
        except Exception:
            pass

        # Get improvement captures
        improvement_captures = db.get_improvement_captures()

        return SelfImproveContext(
            level=level,
            multiplier=multiplier,
            session_transcript_path=session_transcript_path,
            entries_since_last_level=[
                {
                    "entry_id": e.entry_id,
                    "notes": (e.notes or "")[:200],
                    "tags": e.tags,
                    "created_at": str(e.created_at),
                }
                for e in entries[:50]
            ],
            lower_level_findings=lower_findings,
            open_issues=open_issues,
            improvement_captures=[
                {
                    "entry_id": e.get("entry_id", ""),
                    "notes": (e.get("notes") or "")[:200],
                }
                for e in improvement_captures[:20]
            ],
            archive_state=archive_state,
        )

    def _introspect_l2(
        ctx: Context,
        db: "DuckDBLayer",
        phase: str,
        dry_run: bool,
        selected_findings: Optional[List[int]],
        refined_issues: Optional[List[Dict[str, Any]]],
        summary_content: Optional[str],
    ) -> IntrospectResult:
        """L2 self-improvement workflow: discovery -> selection -> dialogue -> logging -> archive."""

        # =====================================================================
        # DISCOVERY PHASE
        # =====================================================================
        if phase == "discovery":
            # Check current state
            current_skill, current_substate = db.get_global_state()

            if current_skill and current_skill != "introspect":
                return IntrospectResult(
                    success=False,
                    error=f"Cannot start introspect: skill '{current_skill}' is already active",
                    level=2,
                    phase_completed=None,
                )

            # Start skill if not already started
            if current_skill != "introspect":
                new_state = {"skill": "introspect", "substate": "discovery"}
                success, entry_id, error = _run_archive_upload(
                    trigger="skill",
                    global_state=new_state,
                    state_transition="phase_start",
                )
                if not success:
                    return IntrospectResult(
                        success=False,
                        error=f"Failed to start introspect skill: {error}",
                        level=2,
                        phase_completed=None,
                    )
                db.invalidate()

            # Query analysis tools for findings
            # The actual analysis is delegated to the orchestrator/agent
            # We just signal that discovery phase is ready
            return IntrospectResult(
                success=True,
                error=None,
                level=2,
                phase_completed="discovery",
                findings_count=0,  # Orchestrator will populate via analysis tools
            )

        # =====================================================================
        # SELECTION PHASE
        # =====================================================================
        elif phase == "selection":
            current_skill, current_substate = db.get_global_state()
            if current_skill != "introspect":
                return IntrospectResult(
                    success=False,
                    error=f"Cannot run selection: introspect skill not active (current: {current_skill or 'none'})",
                    level=2,
                    phase_completed=None,
                )

            # Transition to selection phase
            new_state = {"skill": "introspect", "substate": "selection"}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
            )
            if not success:
                return IntrospectResult(
                    success=False,
                    error=f"Failed to transition to selection: {error}",
                    level=2,
                    phase_completed=None,
                )
            db.invalidate()

            return IntrospectResult(
                success=True,
                error=None,
                level=2,
                phase_completed="selection",
            )

        # =====================================================================
        # DIALOGUE PHASE
        # =====================================================================
        elif phase == "dialogue":
            current_skill, _ = db.get_global_state()
            if current_skill != "introspect":
                return IntrospectResult(
                    success=False,
                    error=f"Cannot run dialogue: introspect skill not active",
                    level=2,
                    phase_completed=None,
                )

            # Transition to dialogue phase
            new_state = {"skill": "introspect", "substate": "dialogue"}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
            )
            if not success:
                return IntrospectResult(
                    success=False,
                    error=f"Failed to transition to dialogue: {error}",
                    level=2,
                    phase_completed=None,
                )
            db.invalidate()

            return IntrospectResult(
                success=True,
                error=None,
                level=2,
                phase_completed="dialogue",
            )

        # =====================================================================
        # LOGGING PHASE
        # =====================================================================
        elif phase == "logging":
            if dry_run:
                return IntrospectResult(
                    success=True,
                    error=None,
                    level=2,
                    phase_completed="logging",
                    issues_created=[],
                )

            current_skill, _ = db.get_global_state()
            if current_skill != "introspect":
                return IntrospectResult(
                    success=False,
                    error=f"Cannot run logging: introspect skill not active",
                    level=2,
                    phase_completed=None,
                )

            # Transition to logging phase
            new_state = {"skill": "introspect", "substate": "logging"}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
            )
            if not success:
                return IntrospectResult(
                    success=False,
                    error=f"Failed to transition to logging: {error}",
                    level=2,
                    phase_completed=None,
                )
            db.invalidate()

            # Create issues from refined_issues if provided
            issues_created: List[int] = []
            if refined_issues:
                for issue_spec in refined_issues:
                    title = issue_spec.get("title", "Improvement from introspection")
                    body = issue_spec.get("body", "")
                    labels = issue_spec.get("labels", [])

                    # Always include self-improve origin
                    if "origin:self-improve" not in labels:
                        labels.append("origin:self-improve")
                    if "ai-authored" not in labels:
                        labels.append("ai-authored")

                    # Attribution footer
                    attribution = "\n\n---\n🤖 Created with [Claude Code](https://claude.ai/code) via /introspect"
                    full_body = body + attribution

                    cmd = ["gh", "issue", "create", "--repo", GITHUB_REPO, "--title", title]
                    cmd.extend(["--body", full_body])
                    cmd.extend(["--label", ",".join(labels)])

                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                        if result.returncode == 0:
                            url = result.stdout.strip()
                            if url and "/issues/" in url:
                                try:
                                    issue_num = int(url.split("/issues/")[-1])
                                    issues_created.append(issue_num)
                                except ValueError:
                                    pass
                    except Exception:
                        pass

            return IntrospectResult(
                success=True,
                error=None,
                level=2,
                phase_completed="logging",
                issues_created=issues_created,
            )

        # =====================================================================
        # ARCHIVE PHASE
        # =====================================================================
        elif phase == "archive":
            current_skill, _ = db.get_global_state()
            if current_skill != "introspect":
                return IntrospectResult(
                    success=False,
                    error=f"Cannot run archive: introspect skill not active",
                    level=2,
                    phase_completed=None,
                )

            # Transition to archive phase
            new_state = {"skill": "introspect", "substate": "archive"}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
            )
            if not success:
                return IntrospectResult(
                    success=False,
                    error=f"Failed to transition to archive: {error}",
                    level=2,
                    phase_completed=None,
                )
            db.invalidate()

            # Write L2 summary document
            summary_dir = ARCHIVE_DIR / "archive" / "summaries"
            summary_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            summary_path = summary_dir / f"{timestamp}.md"

            content = summary_content or f"# L2 Self-Improvement Summary\n\nGenerated: {datetime.now().isoformat()}\n\n(No content provided)"

            try:
                with open(summary_path, "w") as f:
                    f.write(content)
            except Exception as e:
                return IntrospectResult(
                    success=False,
                    error=f"Failed to write summary: {e}",
                    level=2,
                    phase_completed=None,
                )

            # End the skill
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=None,
                state_transition="phase_end",
            )
            db.invalidate()

            return IntrospectResult(
                success=True,
                error=None,
                level=2,
                phase_completed="archive",
            )

        else:
            return IntrospectResult(
                success=False,
                error=f"Unknown L2 phase: {phase}. Valid: discovery, selection, dialogue, logging, archive",
                level=2,
                phase_completed=None,
            )


    def _introspect_l3_plus(
        ctx: Context,
        db: "DuckDBLayer",
        level: int,
        phase: str,
        summary_content: Optional[str],
        dry_run: bool = False,
    ) -> IntrospectResult:
        """L3+ meta-analysis workflow: ingestion -> synthesis -> archive."""

        # =====================================================================
        # INGESTION PHASE
        # =====================================================================
        if phase == "ingestion":
            current_skill, current_substate = db.get_global_state()

            if current_skill and current_skill != "introspect":
                return IntrospectResult(
                    success=False,
                    error=f"Cannot start introspect: skill '{current_skill}' is already active",
                    level=level,
                    phase_completed=None,
                )

            # Determine input directory based on level
            if level == 3:
                input_dir = ARCHIVE_DIR / "archive" / "summaries"
                glob_pattern = "*.md"
            else:
                input_dir = ARCHIVE_DIR / "archive" / "meta-summaries"
                glob_pattern = f"L{level-1}-*.md"

            # Check for sufficient input documents
            if input_dir.exists():
                input_files = list(input_dir.glob(glob_pattern))
                # Exclude .gitkeep
                input_files = [f for f in input_files if f.name != ".gitkeep"]
            else:
                input_files = []

            if len(input_files) < 2:
                # Fail gracefully - insufficient data
                return IntrospectResult(
                    success=False,
                    error=f"Insufficient data: need >= 2 L{level-1} documents, found {len(input_files)}",
                    level=level,
                    phase_completed=None,
                )

            # Start skill if not already started
            if current_skill != "introspect":
                new_state = {"skill": "introspect", "substate": "ingestion"}
                success, entry_id, error = _run_archive_upload(
                    trigger="skill",
                    global_state=new_state,
                    state_transition="phase_start",
                )
                if not success:
                    return IntrospectResult(
                        success=False,
                        error=f"Failed to start introspect skill: {error}",
                        level=level,
                        phase_completed=None,
                    )
                db.invalidate()

            return IntrospectResult(
                success=True,
                error=None,
                level=level,
                phase_completed="ingestion",
                findings_count=len(input_files),  # Number of documents to analyze
            )

        # =====================================================================
        # SYNTHESIS PHASE
        # =====================================================================
        elif phase == "synthesis":
            current_skill, _ = db.get_global_state()
            if current_skill != "introspect":
                return IntrospectResult(
                    success=False,
                    error=f"Cannot run synthesis: introspect skill not active",
                    level=level,
                    phase_completed=None,
                )

            # Transition to synthesis phase
            new_state = {"skill": "introspect", "substate": "synthesis"}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
            )
            if not success:
                return IntrospectResult(
                    success=False,
                    error=f"Failed to transition to synthesis: {error}",
                    level=level,
                    phase_completed=None,
                )
            db.invalidate()

            # Synthesis is done by the orchestrator/agent
            # This tool just tracks the phase transition
            return IntrospectResult(
                success=True,
                error=None,
                level=level,
                phase_completed="synthesis",
            )

        # =====================================================================
        # ARCHIVE PHASE
        # =====================================================================
        elif phase == "archive":
            current_skill, _ = db.get_global_state()
            if current_skill != "introspect":
                return IntrospectResult(
                    success=False,
                    error=f"Cannot run archive: introspect skill not active",
                    level=level,
                    phase_completed=None,
                )

            # Transition to archive phase
            new_state = {"skill": "introspect", "substate": "archive"}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
            )
            if not success:
                return IntrospectResult(
                    success=False,
                    error=f"Failed to transition to archive: {error}",
                    level=level,
                    phase_completed=None,
                )
            db.invalidate()

            # Write L(N) document
            meta_dir = ARCHIVE_DIR / "archive" / "meta-summaries"
            meta_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            output_path = meta_dir / f"L{level}-{timestamp}.md"

            content = summary_content or f"# L{level} Meta-Analysis\n\nGenerated: {datetime.now().isoformat()}\n\n(No content provided)"

            try:
                with open(output_path, "w") as f:
                    f.write(content)
            except Exception as e:
                return IntrospectResult(
                    success=False,
                    error=f"Failed to write meta-summary: {e}",
                    level=level,
                    phase_completed=None,
                )

            # Auto-create GitHub issues for actionable L3+ findings
            issues_created: List[int] = []
            if not dry_run and content:
                findings = _parse_l3_findings(content)
                if findings:
                    novel_findings = _deduplicate_against_open_issues(findings)
                    if novel_findings:
                        created, epic = _create_l3_issues(novel_findings, level)
                        issues_created = created
                        if epic:
                            issues_created.append(epic)

            # End the skill
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=None,
                state_transition="phase_end",
            )
            db.invalidate()

            return IntrospectResult(
                success=True,
                error=None,
                level=level,
                phase_completed="archive",
                issues_created=issues_created,
            )

        else:
            return IntrospectResult(
                success=False,
                error=f"Unknown L{level} phase: {phase}. Valid: ingestion, synthesis, archive",
                level=level,
                phase_completed=None,
            )

    @mcp.tool(
        "sls_converge",
        annotations=ToolAnnotations(
            title="SBS Converge Skill",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    def sls_converge(
        ctx: Context,
        phase: Annotated[
            str,
            Field(description="Phase: setup, eval-N, fix-N, introspect-N, rebuild-N, report"),
        ],
        project: Annotated[
            str,
            Field(description="Project name: SBSTest, GCR, or PNT"),
        ],
        max_iter: Annotated[
            int,
            Field(description="Maximum convergence iterations", ge=1),
        ] = 3,
        hardcore: Annotated[
            bool,
            Field(description="Hardcore mode: no plateau bail, tick-tock introspect"),
        ] = False,
        iteration: Annotated[
            int,
            Field(description="Current iteration number (for eval-N, fix-N, etc.)"),
        ] = 1,
        pass_rate_history: Annotated[
            Optional[List[float]],
            Field(description="Pass rates from previous iterations"),
        ] = None,
        goal: Annotated[
            str,
            Field(description="Convergence goal: 'qa' (default), 'tests', or custom thresholds"),
        ] = "qa",
        single_mode: Annotated[
            bool,
            Field(description="Sequential mode: one category at a time instead of crush"),
        ] = False,
    ) -> ConvergeResult:
        """Autonomous QA convergence loop with in-loop introspection.

        Runs QA evaluation, fixes failures, reflects on outcomes, rebuilds,
        and repeats until 100% pass rate or max iterations.

        Workflow: Setup -> [Eval -> Fix -> Introspect -> Rebuild]xN -> Report

        Args:
            phase: Which phase to execute (setup, eval-N, fix-N, introspect-N, rebuild-N, report)
            project: Project name (SBSTest, GCR, PNT)
            max_iter: Maximum iterations before giving up
            hardcore: If True, disables plateau detection and max iterations
            iteration: Current iteration number
            pass_rate_history: History of pass rates for tracking convergence
            goal: Convergence goal ('qa', 'tests', or custom validator thresholds)
            single_mode: If True, process one failure category at a time

        Returns:
            ConvergeResult with pass_rate, iteration, exit_reason, etc.
        """
        db = _get_db(ctx)
        normalized_project = _normalize_project(project)

        if not normalized_project:
            return ConvergeResult(
                success=False,
                error=f"Unknown project: {project}. Valid: SBSTest, GCR, PNT",
                phase_completed=None,
                iteration=iteration,
                pass_rate=0.0,
                pass_rate_history=pass_rate_history or [],
            )

        history = pass_rate_history or []

        # =====================================================================
        # SETUP PHASE
        # =====================================================================
        if phase == "setup":
            # Check current state
            current_skill, current_substate = db.get_global_state()

            if current_skill and current_skill != "converge":
                return ConvergeResult(
                    success=False,
                    error=f"Cannot start converge: skill '{current_skill}' is already active",
                    phase_completed=None,
                    iteration=1,
                    pass_rate=0.0,
                    pass_rate_history=[],
                )

            # Start skill
            new_state = {"skill": "converge", "substate": "setup"}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
                state_transition="phase_start",
            )
            if not success:
                return ConvergeResult(
                    success=False,
                    error=f"Failed to start converge skill: {error}",
                    phase_completed=None,
                    iteration=1,
                    pass_rate=0.0,
                    pass_rate_history=[],
                )
            db.invalidate()

            # Build project
            build_success, build_output = _build_project(normalized_project)
            if not build_success:
                # Record failure
                _run_archive_upload(
                    trigger="skill",
                    global_state=None,
                    state_transition="phase_fail",
                )
                db.invalidate()
                return ConvergeResult(
                    success=False,
                    error=f"Build failed: {build_output[:500]}",
                    phase_completed=None,
                    iteration=1,
                    pass_rate=0.0,
                    pass_rate_history=[],
                    exit_reason="build_failure",
                )

            # Start dev server
            server_success, server_pid, server_error = _start_server(normalized_project)
            if not server_success:
                _run_archive_upload(
                    trigger="skill",
                    global_state=None,
                    state_transition="phase_fail",
                )
                db.invalidate()
                return ConvergeResult(
                    success=False,
                    error=f"Server failed to start: {server_error}",
                    phase_completed=None,
                    iteration=1,
                    pass_rate=0.0,
                    pass_rate_history=[],
                    exit_reason="build_failure",
                )

            # Clear adaptation notes
            storage_dir = SBS_ROOT / "dev" / "storage" / normalized_project
            storage_dir.mkdir(parents=True, exist_ok=True)
            adaptation_path = storage_dir / "adaptation_notes.json"
            try:
                with open(adaptation_path, "w") as f:
                    json.dump([], f)
            except Exception:
                pass

            return ConvergeResult(
                success=True,
                error=None,
                phase_completed="setup",
                iteration=1,
                pass_rate=0.0,
                pass_rate_history=[],
            )

        # =====================================================================
        # EVAL PHASE
        # =====================================================================
        elif phase.startswith("eval"):
            current_skill, _ = db.get_global_state()
            if current_skill != "converge":
                return ConvergeResult(
                    success=False,
                    error=f"Cannot eval: converge skill not active",
                    phase_completed=None,
                    iteration=iteration,
                    pass_rate=0.0,
                    pass_rate_history=history,
                )

            # Transition to eval-N
            new_state = {"skill": "converge", "substate": f"eval-{iteration}"}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
            )
            if not success:
                return ConvergeResult(
                    success=False,
                    error=f"Failed to transition to eval: {error}",
                    phase_completed=None,
                    iteration=iteration,
                    pass_rate=0.0,
                    pass_rate_history=history,
                )
            db.invalidate()

            # Evaluate based on goal type
            pass_rate = 0.0

            if goal == "tests":
                # Run tests and calculate pass rate
                from .gate_validation import GateSpec
                spec = GateSpec(tests="all", test_tier="all")
                passed, total, _ = _run_tests(spec)
                pass_rate = (passed / total) if total > 0 else 0.0

            elif goal.startswith("T") or ">=" in goal:
                # Custom validator thresholds
                # Parse format like "T5 >= 0.9, T6 >= 0.95"
                thresholds = {}
                for part in goal.split(","):
                    part = part.strip()
                    match = re.match(r"(T\d+)\s*>=\s*([\d.]+)", part)
                    if match:
                        thresholds[match.group(1)] = float(match.group(2))

                if thresholds:
                    from .gate_validation import GateSpec, _run_validators
                    spec = GateSpec(quality=thresholds)
                    scores = _run_validators(spec, normalized_project)
                    # Pass rate = validators meeting threshold / total
                    passed = sum(1 for v, t in thresholds.items() if scores.get(v, 0) >= t)
                    pass_rate = passed / len(thresholds) if thresholds else 0.0

            else:
                # QA goal (default) - check pages load
                pages_passed = 0
                pages_total = len(_DEFAULT_QA_PAGES)

                if _check_server_running():
                    import urllib.request
                    import urllib.error

                    for page in _DEFAULT_QA_PAGES:
                        url_path = _PAGE_URLS.get(page, f"/{page}.html")
                        if url_path is None and page == "chapter":
                            url_path = "/SBSChapter1.html"
                        if url_path is None:
                            url_path = f"/{page}.html"

                        full_url = f"http://localhost:8000{url_path}"

                        try:
                            with urllib.request.urlopen(full_url, timeout=10) as response:
                                if response.status == 200:
                                    pages_passed += 1
                        except urllib.error.HTTPError as e:
                            if e.code == 404:
                                pages_passed += 1  # Skip as passing (page not found is ok)
                        except Exception:
                            pass

                pass_rate = pages_passed / pages_total if pages_total > 0 else 0.0

            # Update history
            history = history + [pass_rate]

            # Check exit conditions
            exit_reason = None

            # 1. 100% pass rate
            if pass_rate >= 1.0:
                exit_reason = "converged"

            # 2. Plateau detection (normal mode only)
            elif not hardcore and iteration > 1 and pass_rate <= history[-2]:
                exit_reason = "plateau"

            # 3. Max iterations (normal mode only)
            elif not hardcore and iteration >= max_iter:
                exit_reason = "max_iterations"

            if exit_reason:
                return ConvergeResult(
                    success=True,
                    error=None,
                    phase_completed=f"eval-{iteration}",
                    iteration=iteration,
                    pass_rate=pass_rate,
                    pass_rate_history=history,
                    exit_reason=exit_reason,
                )

            return ConvergeResult(
                success=True,
                error=None,
                phase_completed=f"eval-{iteration}",
                iteration=iteration,
                pass_rate=pass_rate,
                pass_rate_history=history,
            )

        # =====================================================================
        # FIX PHASE
        # =====================================================================
        elif phase.startswith("fix"):
            current_skill, _ = db.get_global_state()
            if current_skill != "converge":
                return ConvergeResult(
                    success=False,
                    error=f"Cannot fix: converge skill not active",
                    phase_completed=None,
                    iteration=iteration,
                    pass_rate=0.0,
                    pass_rate_history=history,
                )

            # Transition to fix-N
            new_state = {"skill": "converge", "substate": f"fix-{iteration}"}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
            )
            if not success:
                return ConvergeResult(
                    success=False,
                    error=f"Failed to transition to fix: {error}",
                    phase_completed=None,
                    iteration=iteration,
                    pass_rate=0.0,
                    pass_rate_history=history,
                )
            db.invalidate()

            # Fix phase completed - orchestrator spawns fix agents
            return ConvergeResult(
                success=True,
                error=None,
                phase_completed=f"fix-{iteration}",
                iteration=iteration,
                pass_rate=history[-1] if history else 0.0,
                pass_rate_history=history,
            )

        # =====================================================================
        # INTROSPECT PHASE
        # =====================================================================
        elif phase.startswith("introspect"):
            # In hardcore mode, only run introspect on odd iterations
            if hardcore and iteration % 2 == 0:
                # Skip introspect on even iterations
                return ConvergeResult(
                    success=True,
                    error=None,
                    phase_completed=f"introspect-{iteration}",
                    iteration=iteration,
                    pass_rate=history[-1] if history else 0.0,
                    pass_rate_history=history,
                )

            current_skill, _ = db.get_global_state()
            if current_skill != "converge":
                return ConvergeResult(
                    success=False,
                    error=f"Cannot introspect: converge skill not active",
                    phase_completed=None,
                    iteration=iteration,
                    pass_rate=0.0,
                    pass_rate_history=history,
                )

            # Transition to introspect-N
            new_state = {"skill": "converge", "substate": f"introspect-{iteration}"}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
            )
            if not success:
                return ConvergeResult(
                    success=False,
                    error=f"Failed to transition to introspect: {error}",
                    phase_completed=None,
                    iteration=iteration,
                    pass_rate=0.0,
                    pass_rate_history=history,
                )
            db.invalidate()

            # In-loop introspection - orchestrator handles the reflection
            return ConvergeResult(
                success=True,
                error=None,
                phase_completed=f"introspect-{iteration}",
                iteration=iteration,
                pass_rate=history[-1] if history else 0.0,
                pass_rate_history=history,
            )

        # =====================================================================
        # REBUILD PHASE
        # =====================================================================
        elif phase.startswith("rebuild"):
            current_skill, _ = db.get_global_state()
            if current_skill != "converge":
                return ConvergeResult(
                    success=False,
                    error=f"Cannot rebuild: converge skill not active",
                    phase_completed=None,
                    iteration=iteration,
                    pass_rate=0.0,
                    pass_rate_history=history,
                )

            # Transition to rebuild-N
            new_state = {"skill": "converge", "substate": f"rebuild-{iteration}"}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
            )
            if not success:
                return ConvergeResult(
                    success=False,
                    error=f"Failed to transition to rebuild: {error}",
                    phase_completed=None,
                    iteration=iteration,
                    pass_rate=0.0,
                    pass_rate_history=history,
                )
            db.invalidate()

            # Rebuild project
            build_success, build_output = _build_project(normalized_project)
            if not build_success:
                _run_archive_upload(
                    trigger="skill",
                    global_state=None,
                    state_transition="phase_fail",
                )
                db.invalidate()
                return ConvergeResult(
                    success=False,
                    error=f"Build failed: {build_output[:500]}",
                    phase_completed=None,
                    iteration=iteration,
                    pass_rate=0.0,
                    pass_rate_history=history,
                    exit_reason="build_failure",
                )

            # Increment iteration for next eval
            return ConvergeResult(
                success=True,
                error=None,
                phase_completed=f"rebuild-{iteration}",
                iteration=iteration + 1,  # Next iteration
                pass_rate=history[-1] if history else 0.0,
                pass_rate_history=history,
            )

        # =====================================================================
        # REPORT PHASE
        # =====================================================================
        elif phase == "report":
            current_skill, _ = db.get_global_state()
            if current_skill != "converge":
                return ConvergeResult(
                    success=False,
                    error=f"Cannot report: converge skill not active",
                    phase_completed=None,
                    iteration=iteration,
                    pass_rate=0.0,
                    pass_rate_history=history,
                )

            # Transition to report
            new_state = {"skill": "converge", "substate": "report"}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
            )
            if not success:
                return ConvergeResult(
                    success=False,
                    error=f"Failed to transition to report: {error}",
                    phase_completed=None,
                    iteration=iteration,
                    pass_rate=0.0,
                    pass_rate_history=history,
                )
            db.invalidate()

            # Stop server
            _stop_server()

            # Check for L3 handoff possibility
            summary_dir = ARCHIVE_DIR / "archive" / "summaries"
            l2_docs = []
            if summary_dir.exists():
                l2_docs = [f for f in summary_dir.glob("*.md") if f.name != ".gitkeep"]

            exit_reason = "converged" if (history and history[-1] >= 1.0) else "plateau"

            if len(l2_docs) >= 2:
                # Handoff to introspect L3
                new_state = {"skill": "introspect", "substate": "ingestion"}
                success, entry_id, error = _run_archive_upload(
                    trigger="skill",
                    global_state=new_state,
                    state_transition="phase_start",
                )
                db.invalidate()

                return ConvergeResult(
                    success=True,
                    error=None,
                    phase_completed="report",
                    iteration=iteration,
                    pass_rate=history[-1] if history else 0.0,
                    pass_rate_history=history,
                    exit_reason=exit_reason,
                )
            else:
                # End converge skill
                success, entry_id, error = _run_archive_upload(
                    trigger="skill",
                    global_state=None,
                    state_transition="phase_end",
                )
                db.invalidate()

                return ConvergeResult(
                    success=True,
                    error=None,
                    phase_completed="report",
                    iteration=iteration,
                    pass_rate=history[-1] if history else 0.0,
                    pass_rate_history=history,
                    exit_reason=exit_reason,
                )

        else:
            return ConvergeResult(
                success=False,
                error=f"Unknown phase: {phase}. Valid: setup, eval-N, fix-N, introspect-N, rebuild-N, report",
                phase_completed=None,
                iteration=iteration,
                pass_rate=0.0,
                pass_rate_history=history,
            )


    def _run_tests(spec: "GateSpec") -> tuple[int, int, List[str]]:
        """Run pytest tests according to spec. Returns (passed, total, failures)."""
        from .gate_validation import _run_tests as run_tests_impl
        return run_tests_impl(spec)

    @mcp.tool(
        "sls_update_and_archive",
        annotations=ToolAnnotations(
            title="SBS Update and Archive Skill",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    def sls_update_and_archive(
        ctx: Context,
        phase: Annotated[
            Literal["retrospective", "porcelain", "upload"],
            Field(description="Phase: retrospective (write retro), porcelain (git state), upload (archive)"),
        ],
        retrospective_content: Annotated[
            Optional[str],
            Field(description="Retrospective content to write (required for retrospective phase)"),
        ] = None,
    ) -> UpdateArchiveResult:
        """Documentation refresh and porcelain state management.

        Simplified 3-phase workflow (per #213):
        - retrospective: Write retrospective document
        - porcelain: Ensure all repos committed and pushed
        - upload: Archive upload with validation

        Args:
            phase: Which phase to execute
            retrospective_content: Content for retrospective document (required for retrospective phase)

        Returns:
            UpdateArchiveResult with repos_committed, archive_entry_id, etc.
        """
        db = _get_db(ctx)

        # =====================================================================
        # RETROSPECTIVE PHASE
        # =====================================================================
        if phase == "retrospective":
            # Check current state - may already be set via handoff from /task
            current_skill, current_substate = db.get_global_state()

            # If not already in update-and-archive, start the skill
            if current_skill != "update-and-archive":
                if current_skill:
                    return UpdateArchiveResult(
                        success=False,
                        error=f"Cannot start update-and-archive: skill '{current_skill}' is already active",
                        phase_completed=None,
                        retrospective_written=False,
                        repos_committed=[],
                        archive_entry_id=None,
                    )

                # Start skill
                new_state = {"skill": "update-and-archive", "substate": "retrospective"}
                success, entry_id, error = _run_archive_upload(
                    trigger="skill",
                    global_state=new_state,
                    state_transition="phase_start",
                )
                if not success:
                    return UpdateArchiveResult(
                        success=False,
                        error=f"Failed to start skill: {error}",
                        phase_completed=None,
                        retrospective_written=False,
                        repos_committed=[],
                        archive_entry_id=None,
                    )
                db.invalidate()

            # Write retrospective document
            retro_dir = ARCHIVE_DIR / "archive" / "retrospectives"
            retro_dir.mkdir(parents=True, exist_ok=True)

            entry_id = datetime.now().strftime("%Y%m%d%H%M%S")
            retro_path = retro_dir / f"{entry_id}.md"

            content = retrospective_content or "# Session Retrospective\n\n(No content provided)"

            try:
                with open(retro_path, "w") as f:
                    f.write(content)
            except Exception as e:
                return UpdateArchiveResult(
                    success=False,
                    error=f"Failed to write retrospective: {e}",
                    phase_completed=None,
                    retrospective_written=False,
                    repos_committed=[],
                    archive_entry_id=None,
                )

            return UpdateArchiveResult(
                success=True,
                error=None,
                phase_completed="retrospective",
                retrospective_written=True,
                repos_committed=[],
                archive_entry_id=None,
            )

        # =====================================================================
        # PORCELAIN PHASE
        # =====================================================================
        elif phase == "porcelain":
            # Verify we're in update-and-archive skill
            current_skill, _ = db.get_global_state()
            if current_skill != "update-and-archive":
                return UpdateArchiveResult(
                    success=False,
                    error=f"Cannot run porcelain: update-and-archive skill not active (current: {current_skill or 'none'})",
                    phase_completed=None,
                    retrospective_written=False,
                    repos_committed=[],
                    archive_entry_id=None,
                )

            # Transition to porcelain phase
            new_state = {"skill": "update-and-archive", "substate": "porcelain"}
            success, _, error = _run_archive_upload(
                trigger="skill",
                global_state=new_state,
            )
            if not success:
                return UpdateArchiveResult(
                    success=False,
                    error=f"Failed to transition to porcelain: {error}",
                    phase_completed=None,
                    retrospective_written=False,
                    repos_committed=[],
                    archive_entry_id=None,
                )
            db.invalidate()

            # Commit and push each repo with changes
            repos_committed: List[str] = []
            commit_message = "docs: update-and-archive refresh"

            for repo_path in _get_all_repos():
                had_changes, error = _commit_and_push_repo(repo_path, commit_message)
                if had_changes:
                    repos_committed.append(str(repo_path.relative_to(SBS_ROOT)))
                if error:
                    # Log error but continue with other repos
                    pass

            return UpdateArchiveResult(
                success=True,
                error=None,
                phase_completed="porcelain",
                retrospective_written=False,
                repos_committed=repos_committed,
                archive_entry_id=None,
            )

        # =====================================================================
        # UPLOAD PHASE
        # =====================================================================
        elif phase == "upload":
            # Verify we're in update-and-archive skill
            current_skill, _ = db.get_global_state()
            if current_skill != "update-and-archive":
                return UpdateArchiveResult(
                    success=False,
                    error=f"Cannot upload: update-and-archive skill not active (current: {current_skill or 'none'})",
                    phase_completed=None,
                    retrospective_written=False,
                    repos_committed=[],
                    archive_entry_id=None,
                )

            # Transition to upload phase and end skill (is_final=True clears state)
            new_state = {"skill": "update-and-archive", "substate": "archive-upload"}
            success, entry_id, error = _run_archive_upload(
                trigger="skill",
                global_state=None,  # Clear state since this is final
                state_transition="phase_end",
            )
            db.invalidate()

            if not success:
                return UpdateArchiveResult(
                    success=False,
                    error=f"Failed to upload: {error}",
                    phase_completed=None,
                    retrospective_written=False,
                    repos_committed=[],
                    archive_entry_id=None,
                )

            return UpdateArchiveResult(
                success=True,
                error=None,
                phase_completed="upload",
                retrospective_written=False,
                repos_committed=[],
                archive_entry_id=entry_id,
            )

        else:
            return UpdateArchiveResult(
                success=False,
                error=f"Unknown phase: {phase}",
                phase_completed=None,
                retrospective_written=False,
                repos_committed=[],
                archive_entry_id=None,
            )

    @mcp.tool(
        "sls_divination",
        annotations=ToolAnnotations(
            title="SBS Divination Tool",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def sls_divination(
        ctx: Context,
        query: Annotated[
            str,
            Field(description="Natural language query about the codebase"),
        ],
        scope: Annotated[
            Optional[str],
            Field(description="Limit exploration to repo/area, e.g. 'Dress', 'Runway', 'CSS'"),
        ] = None,
        depth: Annotated[
            Literal["quick", "medium", "thorough"],
            Field(description="Exploration depth: quick (oracle only), medium (+archive), thorough (+archive+issues)"),
        ] = "quick",
    ) -> DivinationResult:
        """Codebase exploration and guidance tool.

        Combines oracle queries, archive context, and optional deeper exploration
        to provide guidance on where to find things and how they work.

        Depth levels:
        - quick: Oracle query only, fastest response
        - medium: Oracle + archive context for recent activity
        - thorough: Oracle + archive + related GitHub issues

        Args:
            query: Natural language query about the codebase
            scope: Optional scope restriction (repo name, subsystem, etc.)
            depth: How deep to explore (quick/medium/thorough)

        Returns:
            DivinationResult with files_explored, patterns, suggestions, etc.
        """
        try:
            db = _get_db(ctx)

            # Query oracle with options based on depth
            include_archive = depth in ("medium", "thorough")
            include_issues = depth == "thorough"

            oracle_result = db.oracle_query(
                query=query,
                max_results=10,
                result_type="all",
                scope=scope,
                min_relevance=0.0,
                fuzzy=False,
                include_archive=include_archive,
                include_quality=False,
            )

            # Extract file matches
            files_explored = []
            for match in oracle_result.file_matches:
                files_explored.append({
                    "path": match.file,
                    "relevance": str(match.relevance),
                    "summary": match.context[:100] if match.context else "",
                })

            # Extract concept patterns
            patterns = [c.name for c in oracle_result.concepts]

            # Build archive context dict if available
            archive_context = None
            if include_archive and oracle_result.archive_context:
                archive_context = oracle_result.archive_context

            # Generate suggestions based on results
            suggestions = []

            if files_explored:
                top_file = files_explored[0]
                suggestions.append(f"Start exploration at: {top_file['path']}")

                # Suggest related files if we have multiple
                if len(files_explored) > 1:
                    related = [f["path"] for f in files_explored[1:4]]
                    suggestions.append(f"Also check: {', '.join(related)}")

            if patterns:
                top_patterns = patterns[:5]
                suggestions.append(f"Key concepts: {', '.join(top_patterns)}")

            if archive_context:
                suggestions.append("Recent archive activity found - check archive_context for details")

            # For thorough depth, search for related issues
            related_issues = None
            if include_issues:
                try:
                    gh_result = subprocess.run(
                        ["gh", "issue", "list", "--repo", GITHUB_REPO,
                         "--search", query, "--json", "number,title,state,labels",
                         "--limit", "5"],
                        capture_output=True, text=True, timeout=15,
                    )
                    if gh_result.returncode == 0:
                        import json
                        issues = json.loads(gh_result.stdout)
                        if issues:
                            related_issues = issues
                            suggestions.append(f"Found {len(issues)} related GitHub issues")
                except Exception:
                    pass

            # If no results at all, suggest broader search
            if not files_explored and not patterns:
                suggestions.append("No direct matches found. Try broader search terms or remove scope filter.")

            return DivinationResult(
                success=True,
                error=None,
                query=query,
                files_explored=files_explored,
                patterns=patterns,
                archive_context=archive_context,
                suggestions=suggestions,
            )

        except Exception as e:
            return DivinationResult(
                success=False,
                error=str(e),
                query=query,
                files_explored=[],
                patterns=[],
                archive_context=None,
                suggestions=[],
            )
