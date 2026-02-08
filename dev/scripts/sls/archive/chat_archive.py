"""
Chat session archiving for Claude Code sessions.

Archives:
- Session transcripts from ~/.claude/projects/
- Plan files from ~/.claude/plans/
- Auto-generated session summaries
"""

from pathlib import Path
from typing import Optional
import json
import logging
from datetime import datetime

log = logging.getLogger(__name__)

# Claude data paths
CLAUDE_ROOT = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_ROOT / "projects"
PLANS_DIR = CLAUDE_ROOT / "plans"

# SBS workspace path pattern
SBS_WORKSPACE_PREFIX = "-Users-eric-GitHub-Side-By-Side-Blueprint"


def get_sbs_sessions_dir() -> Optional[Path]:
    """Get the Claude sessions directory for SBS workspace."""
    sbs_dir = PROJECTS_DIR / SBS_WORKSPACE_PREFIX
    return sbs_dir if sbs_dir.exists() else None


def parse_jsonl_session(session_path: Path) -> dict:
    """
    Parse a .jsonl session file.

    Returns dict with:
    {
        "session_id": str,
        "messages": list of {role, content, timestamp},
        "tool_calls": list of tool names used,
        "files_modified": list of file paths,
        "start_time": str,
        "end_time": str,
        "message_count": int,
    }
    """
    result = {
        "session_id": session_path.stem,
        "messages": [],
        "tool_calls": [],
        "files_modified": set(),
        "start_time": None,
        "end_time": None,
        "message_count": 0,
    }

    try:
        with open(session_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)

                    # Track timestamps
                    if "timestamp" in entry:
                        ts = entry["timestamp"]
                        if not result["start_time"] or ts < result["start_time"]:
                            result["start_time"] = ts
                        if not result["end_time"] or ts > result["end_time"]:
                            result["end_time"] = ts

                    # Track messages
                    if entry.get("type") == "message":
                        role = entry.get("role", "unknown")
                        content = entry.get("content", "")
                        result["messages"].append({
                            "role": role,
                            "content": content[:500],  # Truncate for summary
                            "timestamp": entry.get("timestamp", ""),
                        })
                        result["message_count"] += 1

                    # Track tool calls
                    if entry.get("type") == "tool_use":
                        tool_name = entry.get("name", "unknown")
                        if tool_name not in result["tool_calls"]:
                            result["tool_calls"].append(tool_name)

                        # Track file modifications from Edit/Write tools
                        if tool_name in ("Edit", "Write"):
                            file_path = entry.get("input", {}).get("file_path", "")
                            if file_path:
                                result["files_modified"].add(file_path)

                except json.JSONDecodeError:
                    continue

    except Exception as e:
        log.warning(f"Error parsing session {session_path}: {e}")

    result["files_modified"] = list(result["files_modified"])
    return result


def generate_session_summary(session_data: dict) -> str:
    """
    Generate a markdown summary of a session.

    Returns markdown string.
    """
    lines = []
    lines.append(f"# Session Summary: {session_data['session_id'][:8]}...")
    lines.append("")

    # Time range
    if session_data["start_time"] and session_data["end_time"]:
        lines.append(f"**Time:** {session_data['start_time'][:19]} to {session_data['end_time'][:19]}")

    # Stats
    lines.append(f"**Messages:** {session_data['message_count']}")
    lines.append("")

    # Tools used
    if session_data["tool_calls"]:
        lines.append("## Tools Used")
        for tool in sorted(set(session_data["tool_calls"])):
            lines.append(f"- {tool}")
        lines.append("")

    # Files modified
    if session_data["files_modified"]:
        lines.append("## Files Modified")
        for f in sorted(session_data["files_modified"]):
            # Shorten paths - handle SLS, SBS submodule, and legacy paths
            short = f
            for prefix in [
                "/Users/eric/GitHub/SLS-Strange-Loop-Station/SBS/",
                "/Users/eric/GitHub/SLS-Strange-Loop-Station/",
                "/Users/eric/GitHub/Side-By-Side-Blueprint/",
            ]:
                if short.startswith(prefix):
                    short = short[len(prefix):]
                    break
            # Normalize paths from old structure
            for old_prefix, new_prefix in [
                ("scripts/", "dev/scripts/"),
                ("archive/", "storage/"),
                ("Dress/", "toolchain/Dress/"),
                ("Runway/", "toolchain/Runway/"),
                ("SBS-Test/", "toolchain/SBS-Test/"),
                ("dress-blueprint-action/", "toolchain/dress-blueprint-action/"),
                ("LeanArchitect/", "forks/LeanArchitect/"),
                ("subverso/", "forks/subverso/"),
                ("verso/", "forks/verso/"),
                ("General_Crystallographic_Restriction/", "showcase/General_Crystallographic_Restriction/"),
                ("PrimeNumberTheoremAnd/", "showcase/PrimeNumberTheoremAnd/"),
            ]:
                if short.startswith(old_prefix):
                    short = new_prefix + short[len(old_prefix):]
                    break
            lines.append(f"- `{short}`")
        lines.append("")

    # Recent messages (last 5 user messages)
    user_messages = [m for m in session_data["messages"] if m["role"] == "user"]
    if user_messages:
        lines.append("## Recent User Requests")
        for msg in user_messages[-5:]:
            content = msg["content"][:200] + "..." if len(msg["content"]) > 200 else msg["content"]
            lines.append(f"- {content}")
        lines.append("")

    return "\n".join(lines)


def list_recent_sessions(hours: int = 24) -> list[Path]:
    """
    List session files modified in the last N hours.

    Returns list of session .jsonl paths.
    """
    sbs_dir = get_sbs_sessions_dir()
    if not sbs_dir:
        return []

    from datetime import timedelta
    cutoff = datetime.now() - timedelta(hours=hours)

    sessions = []
    for jsonl in sbs_dir.glob("*.jsonl"):
        mtime = datetime.fromtimestamp(jsonl.stat().st_mtime)
        if mtime > cutoff:
            sessions.append(jsonl)

    return sorted(sessions, key=lambda p: p.stat().st_mtime, reverse=True)


def archive_chat_sessions(entry_id: str, output_dir: Path, hours: int = 24) -> dict:
    """
    Archive recent chat sessions for a build entry.

    Steps:
    1. Scan relevant .jsonl files (SBS workspace sessions)
    2. Parse: session ID, timestamps, messages, tool calls
    3. Generate summary (key decisions, files modified, commits)
    4. Save to output_dir/{entry_id}.md

    Returns dict with:
    {
        "sessions_processed": int,
        "summary_path": str or None,
        "error": str or None,
    }
    """
    result = {
        "sessions_processed": 0,
        "summary_path": None,
        "error": None,
    }

    try:
        sessions = list_recent_sessions(hours=hours)
        if not sessions:
            result["error"] = "No recent sessions found"
            return result

        # Parse all sessions
        all_data = []
        for session_path in sessions:
            data = parse_jsonl_session(session_path)
            all_data.append(data)
            result["sessions_processed"] += 1

        # Generate combined summary
        lines = []
        lines.append(f"# Archive Entry: {entry_id}")
        lines.append(f"**Generated:** {datetime.now().isoformat()}")
        lines.append(f"**Sessions Analyzed:** {len(all_data)}")
        lines.append("")
        lines.append("---")
        lines.append("")

        for data in all_data:
            lines.append(generate_session_summary(data))
            lines.append("---")
            lines.append("")

        # Save summary
        output_dir.mkdir(parents=True, exist_ok=True)
        summary_path = output_dir / f"{entry_id}.md"
        summary_path.write_text("\n".join(lines))
        result["summary_path"] = str(summary_path)

        log.info(f"Archived {len(all_data)} sessions to {summary_path}")

    except Exception as e:
        log.error(f"Error archiving sessions: {e}")
        result["error"] = str(e)

    return result


def list_plan_files() -> list[Path]:
    """List all plan files in ~/.claude/plans/."""
    if not PLANS_DIR.exists():
        return []
    return sorted(PLANS_DIR.glob("*.md"))


def copy_active_plans(output_dir: Path) -> list[str]:
    """
    Copy active plan files to archive.

    Returns list of copied plan filenames.
    """
    copied = []
    plans_output = output_dir / "plans"
    plans_output.mkdir(parents=True, exist_ok=True)

    for plan in list_plan_files():
        try:
            dest = plans_output / plan.name
            dest.write_text(plan.read_text())
            copied.append(plan.name)
        except Exception as e:
            log.warning(f"Could not copy plan {plan.name}: {e}")

    return copied
