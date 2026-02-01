"""Extract Claude Code interaction data from ~/.claude directory."""

from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import shutil

from sbs.archive.session_data import SessionData, ToolCall, ClaudeDataSnapshot
from sbs.core.utils import log

# Constants
CLAUDE_DIR = Path.home() / ".claude"
SBS_PATH_PATTERN = "Side-By-Side-Blueprint"


def get_sbs_project_dirs() -> list[Path]:
    """Get all ~/.claude/projects directories related to SBS monorepo."""
    projects_dir = CLAUDE_DIR / "projects"
    if not projects_dir.exists():
        return []

    sbs_dirs = []
    for d in projects_dir.iterdir():
        if d.is_dir() and SBS_PATH_PATTERN in d.name:
            sbs_dirs.append(d)
    return sbs_dirs


def parse_session_index(project_dir: Path) -> list[dict]:
    """Parse sessions-index.json from a project directory."""
    index_path = project_dir / "sessions-index.json"
    if not index_path.exists():
        return []

    try:
        with open(index_path) as f:
            data = json.load(f)
            # Handle v1 format with 'entries' key
            if isinstance(data, dict) and "entries" in data:
                return data["entries"]
            # Handle direct array format
            if isinstance(data, list):
                return data
            return []
    except (json.JSONDecodeError, IOError) as e:
        log.warning(f"Failed to parse {index_path}: {e}")
        return []


def parse_session_jsonl(session_path: Path) -> Optional[SessionData]:
    """Parse a session JSONL file into SessionData.

    Claude Code JSONL format:
    - Entries have `type` field: "user", "assistant", "system", "file-history-snapshot"
    - Messages have `message` object with `role`, `content`, etc.
    - Tool calls are in `message.content[]` with `type: "tool_use"`
    """
    if not session_path.exists():
        return None

    session_id = session_path.stem
    messages = []
    tool_calls = []
    files_read = set()
    files_written = set()
    files_edited = set()
    subagent_ids = set()
    plan_files = set()

    started_at = None
    ended_at = None

    try:
        with open(session_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entry_type = entry.get("type", "")

                # Track timestamps
                ts = entry.get("timestamp") or entry.get("time")
                ts_str = None
                if ts:
                    if isinstance(ts, (int, float)):
                        ts_str = datetime.fromtimestamp(ts / 1000).isoformat()
                    else:
                        ts_str = str(ts)
                    if started_at is None:
                        started_at = ts_str
                    ended_at = ts_str

                # Track messages (user and assistant entries)
                if entry_type in ("user", "assistant"):
                    messages.append(entry)

                    # Extract tool calls from assistant message content
                    if entry_type == "assistant":
                        msg = entry.get("message", {})
                        content = msg.get("content", [])
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "tool_use":
                                    tool_name = item.get("name", "unknown")
                                    input_data = item.get("input", {})

                                    tool_call = ToolCall(
                                        tool_name=tool_name,
                                        timestamp=ts_str or "",
                                        duration_ms=None,  # Not available in this format
                                        success=True,  # Assume success; errors tracked separately
                                        error=None,
                                        input_summary=_truncate_input(input_data),
                                    )
                                    tool_calls.append(tool_call)

                                    # Track file operations
                                    if tool_name == "Read":
                                        path = input_data.get("file_path") or input_data.get("path")
                                        if path:
                                            files_read.add(path)
                                    elif tool_name == "Write":
                                        path = input_data.get("file_path") or input_data.get("path")
                                        if path:
                                            files_written.add(path)
                                    elif tool_name == "Edit":
                                        path = input_data.get("file_path") or input_data.get("path")
                                        if path:
                                            files_edited.add(path)
                                    elif tool_name == "Task":
                                        # Track subagent spawns
                                        subagent_ids.add(item.get("id", "unknown"))

                # Track plan file references in any entry
                entry_str = json.dumps(entry)
                if "plans/" in entry_str and ".md" in entry_str:
                    # Look for plan file paths
                    import re
                    plan_matches = re.findall(r'["\']([^"\']*plans/[^"\']+\.md)["\']', entry_str)
                    for match in plan_matches:
                        if match.endswith(".md"):
                            plan_files.add(match)

        # Count message types by entry type
        user_messages = sum(1 for m in messages if m.get("type") == "user")
        assistant_messages = sum(1 for m in messages if m.get("type") == "assistant")

        # Get unique tools used
        tools_used = list(set(tc.tool_name for tc in tool_calls))

        return SessionData(
            session_id=session_id,
            project_path="",  # Will be set by caller
            started_at=started_at or "",
            ended_at=ended_at or "",
            message_count=len(messages),
            user_messages=user_messages,
            assistant_messages=assistant_messages,
            tool_calls=tool_calls,
            tools_used=tools_used,
            files_read=list(files_read),
            files_written=list(files_written),
            files_edited=list(files_edited),
            subagent_ids=list(subagent_ids),
            plan_files=list(plan_files),
        )

    except IOError as e:
        log.warning(f"Failed to parse session {session_path}: {e}")
        return None


def _truncate_input(input_data: dict, max_len: int = 200) -> Optional[str]:
    """Truncate input data for storage."""
    if not input_data:
        return None
    try:
        s = json.dumps(input_data)
        if len(s) > max_len:
            return s[:max_len] + "..."
        return s
    except (TypeError, ValueError):
        return None


def extract_sessions(output_dir: Path) -> tuple[list[SessionData], list[str]]:
    """Extract all SBS-related sessions from ~/.claude/projects/."""
    sessions_dir = output_dir / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    sessions = []
    session_ids = []

    for project_dir in get_sbs_project_dirs():
        # Get session index for metadata
        index_entries = parse_session_index(project_dir)
        index_by_id = {e.get("sessionId", ""): e for e in index_entries}

        # Find all session JSONL files
        for session_file in project_dir.glob("*.jsonl"):
            session_id = session_file.stem
            session_data = parse_session_jsonl(session_file)

            if session_data:
                # Enrich with index metadata
                if session_id in index_by_id:
                    meta = index_by_id[session_id]
                    session_data.project_path = meta.get("projectPath", "")

                sessions.append(session_data)
                session_ids.append(session_id)

                # Save parsed session
                session_out = sessions_dir / f"{session_id}.json"
                with open(session_out, "w") as f:
                    json.dump(session_data.to_dict(), f, indent=2)

    # Create session index
    index_path = sessions_dir / "index.json"
    index_data = {
        "extracted_at": datetime.now().isoformat(),
        "session_count": len(sessions),
        "sessions": [
            {
                "session_id": s.session_id,
                "project_path": s.project_path,
                "started_at": s.started_at,
                "ended_at": s.ended_at,
                "message_count": s.message_count,
                "tool_call_count": len(s.tool_calls),
            }
            for s in sessions
        ],
    }
    with open(index_path, "w") as f:
        json.dump(index_data, f, indent=2)

    log.info(f"Extracted {len(sessions)} sessions to {sessions_dir}")
    return sessions, session_ids


def extract_plans(output_dir: Path) -> list[str]:
    """Extract plan files from ~/.claude/plans/."""
    plans_src = CLAUDE_DIR / "plans"
    plans_dst = output_dir / "plans"

    if not plans_src.exists():
        return []

    plans_dst.mkdir(parents=True, exist_ok=True)
    plan_files = []

    for plan_file in plans_src.glob("*.md"):
        # Copy plan file
        dst = plans_dst / plan_file.name
        shutil.copy2(plan_file, dst)
        plan_files.append(plan_file.name)

    log.info(f"Extracted {len(plan_files)} plan files to {plans_dst}")
    return plan_files


def extract_tool_call_summary(sessions: list[SessionData], output_dir: Path) -> dict:
    """Create aggregated tool call summary."""
    tool_calls_dir = output_dir / "tool_calls"
    tool_calls_dir.mkdir(parents=True, exist_ok=True)

    # Aggregate stats
    total_calls = 0
    by_tool = {}
    errors = []

    for session in sessions:
        for tc in session.tool_calls:
            total_calls += 1
            by_tool[tc.tool_name] = by_tool.get(tc.tool_name, 0) + 1
            if tc.error:
                errors.append({
                    "session_id": session.session_id,
                    "tool_name": tc.tool_name,
                    "error": tc.error,
                    "timestamp": tc.timestamp,
                })

    summary = {
        "extracted_at": datetime.now().isoformat(),
        "total_calls": total_calls,
        "by_tool": dict(sorted(by_tool.items(), key=lambda x: -x[1])),
        "error_count": len(errors),
        "recent_errors": errors[:20],  # Keep last 20 errors
    }

    summary_path = tool_calls_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    log.info(f"Tool call summary: {total_calls} calls across {len(by_tool)} tools")
    return summary


def extract_claude_data(output_dir: Path) -> ClaudeDataSnapshot:
    """
    Main extraction entry point.

    Extracts all SBS-relevant data from ~/.claude and saves to output_dir.
    Returns a ClaudeDataSnapshot for inclusion in archive entry.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    log.header("Extracting Claude Code data")

    # Extract sessions
    sessions, session_ids = extract_sessions(output_dir)

    # Extract plans
    plan_files = extract_plans(output_dir)

    # Extract tool call summary
    tool_summary = extract_tool_call_summary(sessions, output_dir)

    # Collect all modified files
    files_modified = set()
    for s in sessions:
        files_modified.update(s.files_written)
        files_modified.update(s.files_edited)

    # Calculate totals
    total_messages = sum(s.message_count for s in sessions)
    total_tool_calls = tool_summary["total_calls"]

    # Save extraction state
    state = {
        "last_extraction": datetime.now().isoformat(),
        "session_count": len(sessions),
        "plan_count": len(plan_files),
        "tool_call_count": total_tool_calls,
        "message_count": total_messages,
    }
    state_path = output_dir / "extraction_state.json"
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)

    log.success(f"Extraction complete: {len(sessions)} sessions, {len(plan_files)} plans, {total_tool_calls} tool calls")

    return ClaudeDataSnapshot(
        session_ids=session_ids,
        plan_files=plan_files,
        tool_call_count=total_tool_calls,
        message_count=total_messages,
        files_modified=list(files_modified)[:100],  # Limit to 100 files
        extraction_timestamp=datetime.now().isoformat(),
    )
