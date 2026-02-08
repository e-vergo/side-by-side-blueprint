"""Extract Claude Code interaction data from ~/.claude directory.

Enhanced to capture rich JSONL data including:
- Thinking blocks (reasoning traces)
- Token usage (cost analysis)
- Message threading (parentUuid chains)
- Full tool inputs/outputs
- Session metadata from index
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional
import shutil

from sls.archive.session_data import (
    SessionData, ToolCall, ClaudeDataSnapshot,
    ThinkingBlock, MessageUsage,
)
from sbs_core.utils import log

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


def parse_session_jsonl(session_path: Path, index_metadata: Optional[dict] = None) -> Optional[SessionData]:
    """Parse a session JSONL file into SessionData.

    Claude Code JSONL format:
    - Entries have `type` field: "user", "assistant", "system", "file-history-snapshot"
    - Messages have `message` object with `role`, `content`, etc.
    - Tool calls are in `message.content[]` with `type: "tool_use"`
    - Thinking blocks are in `message.content[]` with `type: "thinking"`
    - Token usage is in `message.usage`
    - Message threading via `parentUuid` field
    """
    if not session_path.exists():
        return None

    session_id = session_path.stem
    messages = []
    tool_calls = []
    tool_results = {}  # Map tool_use_id -> result data
    files_read = set()
    files_written = set()
    files_edited = set()
    subagent_ids = set()
    plan_files = set()

    # NEW: Rich data tracking
    thinking_blocks = []
    model_versions = set()
    parent_uuid_chain = []
    stop_reasons = []
    total_input_tokens = 0
    total_output_tokens = 0
    cache_creation_tokens = 0
    cache_read_tokens = 0

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

                # Track message threading
                if entry.get("parentUuid"):
                    parent_uuid_chain.append(entry["parentUuid"])

                # Track messages (user and assistant entries)
                if entry_type in ("user", "assistant"):
                    messages.append(entry)

                    msg = entry.get("message", {})

                    # Extract token usage from assistant messages
                    if entry_type == "assistant":
                        usage = msg.get("usage", {})
                        if usage:
                            total_input_tokens += usage.get("input_tokens", 0)
                            total_output_tokens += usage.get("output_tokens", 0)
                            cache_creation_tokens += usage.get("cache_creation_input_tokens", 0)
                            cache_read_tokens += usage.get("cache_read_input_tokens", 0)

                        # Track stop reason
                        stop_reason = msg.get("stop_reason")
                        if stop_reason:
                            stop_reasons.append(stop_reason)

                        # Track model version
                        model = msg.get("model")
                        if model:
                            model_versions.add(model)

                    # Process message content
                    content = msg.get("content", [])
                    if isinstance(content, list):
                        for item in content:
                            if not isinstance(item, dict):
                                continue

                            item_type = item.get("type")

                            # Extract thinking blocks
                            if item_type == "thinking":
                                thinking_text = item.get("thinking", "")
                                signature = item.get("signature")
                                if thinking_text:
                                    thinking_blocks.append(ThinkingBlock(
                                        content=thinking_text,
                                        signature=signature,
                                        timestamp=ts_str,
                                    ))
                                    # Model version from signature (signature encodes model info)
                                    if signature:
                                        model_versions.add(f"signature:{signature[:20]}...")

                            # Extract tool_use
                            elif item_type == "tool_use":
                                tool_name = item.get("name", "unknown")
                                tool_use_id = item.get("id")
                                input_data = item.get("input", {})

                                tool_call = ToolCall(
                                    tool_name=tool_name,
                                    timestamp=ts_str or "",
                                    duration_ms=None,
                                    success=True,  # Will update from tool_result
                                    error=None,
                                    input_summary=_truncate_input(input_data),
                                    input_full=input_data,  # NEW: Full input
                                    tool_use_id=tool_use_id,  # NEW: ID for linking
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
                                    subagent_ids.add(tool_use_id or "unknown")

                            # Extract tool_result
                            elif item_type == "tool_result":
                                tool_use_id = item.get("tool_use_id")
                                if tool_use_id:
                                    is_error = item.get("is_error", False)
                                    result_content = item.get("content", "")
                                    # Handle content that might be a list
                                    if isinstance(result_content, list):
                                        result_content = json.dumps(result_content)
                                    elif not isinstance(result_content, str):
                                        result_content = str(result_content)

                                    tool_results[tool_use_id] = {
                                        "content": result_content[:5000] if result_content else None,
                                        "is_error": is_error,
                                        "type": "error" if is_error else "text",
                                    }

                # Track plan file references in any entry
                entry_str = json.dumps(entry)
                if "plans/" in entry_str and ".md" in entry_str:
                    plan_matches = re.findall(r'["\']([^"\']*plans/[^"\']+\.md)["\']', entry_str)
                    for match in plan_matches:
                        if match.endswith(".md"):
                            plan_files.add(match)

        # Link tool_results back to tool_calls
        for tc in tool_calls:
            if tc.tool_use_id and tc.tool_use_id in tool_results:
                result = tool_results[tc.tool_use_id]
                tc.result_content = result.get("content")
                tc.result_type = result.get("type")
                tc.success = not result.get("is_error", False)
                if result.get("is_error"):
                    tc.error = result.get("content", "")[:500]  # Truncate error message

        # Count message types by entry type
        user_messages = sum(1 for m in messages if m.get("type") == "user")
        assistant_messages = sum(1 for m in messages if m.get("type") == "assistant")

        # Get unique tools used
        tools_used = list(set(tc.tool_name for tc in tool_calls))

        # Build message usage aggregate
        message_usage = None
        if total_input_tokens > 0 or total_output_tokens > 0:
            message_usage = MessageUsage(
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                cache_creation_input_tokens=cache_creation_tokens,
                cache_read_input_tokens=cache_read_tokens,
            )

        # Get session metadata from index
        slug = None
        first_prompt = None
        session_summary = None
        if index_metadata:
            slug = index_metadata.get("slug")
            first_prompt = index_metadata.get("firstPrompt")
            session_summary = index_metadata.get("summary")

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
            # NEW: Rich data fields
            slug=slug,
            first_prompt=first_prompt,
            session_summary=session_summary,
            model_versions=list(model_versions),
            thinking_blocks=thinking_blocks,
            message_usage=message_usage,
            parent_uuid_chain=parent_uuid_chain[:100],  # Limit chain length
            stop_reasons=stop_reasons,
        )

    except IOError as e:
        log.warning(f"Failed to parse session {session_path}: {e}")
        return None


def extract_ask_user_questions(session_path: Path) -> list[dict]:
    """Extract AskUserQuestion interactions from a session JSONL file.

    Reads the JSONL file line by line (no full-file load) and extracts
    structured data about AskUserQuestion tool calls and their answers.

    Returns list of dicts, each containing:
    - tool_use_id: str, for linking question to answer
    - timestamp: Optional[str], when the question was asked
    - questions: list of question dicts (question, header, options, multiSelect)
    - answers: dict mapping question text to selected answer(s)
    - context_before: Optional[str], summary of preceding assistant text
    """
    if not session_path.exists():
        return []

    # Pass 1: Collect AskUserQuestion tool_use blocks and tool_result blocks
    ask_blocks: list[dict] = []  # {tool_use_id, timestamp, questions_input, context_before}
    tool_results: dict[str, str] = {}  # tool_use_id -> result content string
    last_assistant_text = ""

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
                msg = entry.get("message", {})
                content = msg.get("content", [])
                if not isinstance(content, list):
                    continue

                # Extract timestamp
                ts = entry.get("timestamp") or entry.get("time")
                ts_str = None
                if ts:
                    if isinstance(ts, (int, float)):
                        ts_str = datetime.fromtimestamp(ts / 1000).isoformat()
                    else:
                        ts_str = str(ts)

                if entry_type == "assistant":
                    # Track last plain text for context_before
                    text_parts = []
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        if item.get("type") == "text":
                            text_parts.append(item.get("text", ""))

                    # Find AskUserQuestion tool_use blocks
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        if item.get("type") == "tool_use" and item.get("name") == "AskUserQuestion":
                            tool_use_id = item.get("id", "")
                            input_data = item.get("input", {})
                            context = " ".join(text_parts)[:300] if text_parts else None
                            ask_blocks.append({
                                "tool_use_id": tool_use_id,
                                "timestamp": ts_str,
                                "questions_input": input_data.get("questions", []),
                                "context_before": context,
                            })

                    if text_parts:
                        last_assistant_text = " ".join(text_parts)

                elif entry_type == "user":
                    # Find tool_result blocks matching AskUserQuestion
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        if item.get("type") == "tool_result":
                            tuid = item.get("tool_use_id", "")
                            result_content = item.get("content", "")
                            if isinstance(result_content, list):
                                # Sometimes content is a list of text blocks
                                parts = []
                                for rc in result_content:
                                    if isinstance(rc, dict):
                                        parts.append(rc.get("text", ""))
                                    elif isinstance(rc, str):
                                        parts.append(rc)
                                result_content = " ".join(parts)
                            elif not isinstance(result_content, str):
                                result_content = str(result_content)
                            if tuid:
                                tool_results[tuid] = result_content

    except IOError as e:
        log.warning(f"Failed to read session for AskUserQuestion extraction: {e}")
        return []

    # Link questions to answers
    interactions = []
    for block in ask_blocks:
        tuid = block["tool_use_id"]
        result_text = tool_results.get(tuid, "")
        answers = _parse_ask_user_answers(result_text)

        interactions.append({
            "tool_use_id": tuid,
            "timestamp": block["timestamp"],
            "questions": block["questions_input"],
            "answers": answers,
            "context_before": block["context_before"],
        })

    return interactions


def _parse_ask_user_answers(result_text: str) -> dict[str, str]:
    """Parse the answer text from an AskUserQuestion tool_result.

    The format is:
    'User has answered your questions: "Q1"="A1", "Q2"="A2". You can now continue...'

    Also handles:
    'User has answered your questions: "Q1"="A1". You can now continue...'

    Returns dict mapping question text to answer text.
    """
    answers: dict[str, str] = {}
    if not result_text:
        return answers

    # Find the prefix and strip it
    prefix = 'User has answered your questions: '
    idx = result_text.find(prefix)
    if idx == -1:
        return answers

    # Extract the Q=A portion (between prefix and ". You can now continue")
    qa_start = idx + len(prefix)
    suffix_marker = '. You can now continue'
    suffix_idx = result_text.find(suffix_marker, qa_start)
    if suffix_idx == -1:
        qa_text = result_text[qa_start:]
    else:
        qa_text = result_text[qa_start:suffix_idx]

    # Parse "Q"="A" pairs
    # Pattern: "question text"="answer text"
    # We need to handle commas inside quotes, so use a state machine approach
    pos = 0
    while pos < len(qa_text):
        # Skip whitespace and commas
        while pos < len(qa_text) and qa_text[pos] in (' ', ','):
            pos += 1
        if pos >= len(qa_text):
            break

        # Expect opening quote for question
        if qa_text[pos] != '"':
            break
        pos += 1

        # Read question text until closing quote
        q_start = pos
        while pos < len(qa_text) and qa_text[pos] != '"':
            pos += 1
        question = qa_text[q_start:pos]
        if pos < len(qa_text):
            pos += 1  # skip closing quote

        # Expect = sign
        if pos < len(qa_text) and qa_text[pos] == '=':
            pos += 1
        else:
            break

        # Expect opening quote for answer
        if pos < len(qa_text) and qa_text[pos] == '"':
            pos += 1
            # Read answer text until closing quote
            a_start = pos
            while pos < len(qa_text) and qa_text[pos] != '"':
                pos += 1
            answer = qa_text[a_start:pos]
            if pos < len(qa_text):
                pos += 1  # skip closing quote
        else:
            break

        answers[question] = answer

    return answers


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

            # Get index metadata for this session
            index_metadata = index_by_id.get(session_id)

            session_data = parse_session_jsonl(session_file, index_metadata)

            if session_data:
                # Enrich with index metadata
                if index_metadata:
                    session_data.project_path = index_metadata.get("projectPath", "")

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
                # NEW: Rich data summary
                "slug": s.slug,
                "first_prompt": s.first_prompt[:100] + "..." if s.first_prompt and len(s.first_prompt) > 100 else s.first_prompt,
                "thinking_block_count": len(s.thinking_blocks),
                "total_tokens": (s.message_usage.input_tokens + s.message_usage.output_tokens) if s.message_usage else 0,
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
    success_count = 0
    error_count = 0

    for session in sessions:
        for tc in session.tool_calls:
            total_calls += 1
            by_tool[tc.tool_name] = by_tool.get(tc.tool_name, 0) + 1
            if tc.success:
                success_count += 1
            else:
                error_count += 1
            if tc.error:
                errors.append({
                    "session_id": session.session_id,
                    "tool_name": tc.tool_name,
                    "error": tc.error[:200] if tc.error else None,
                    "timestamp": tc.timestamp,
                })

    summary = {
        "extracted_at": datetime.now().isoformat(),
        "total_calls": total_calls,
        "success_count": success_count,
        "error_count": error_count,
        "by_tool": dict(sorted(by_tool.items(), key=lambda x: -x[1])),
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

    # Collect all modified files (aggregate for backward compat)
    files_modified = set()
    per_session_files = []
    for s in sessions:
        files_modified.update(s.files_written)
        files_modified.update(s.files_edited)
        # Preserve per-session file lists for entry-level tagging
        session_files = sorted(set(s.files_written) | set(s.files_edited))
        per_session_files.append(session_files)

    # Calculate totals
    total_messages = sum(s.message_count for s in sessions)
    total_tool_calls = tool_summary["total_calls"]

    # NEW: Aggregate rich data
    total_input_tokens = 0
    total_output_tokens = 0
    cache_read_tokens = 0
    cache_creation_tokens = 0
    thinking_block_count = 0
    model_versions_used = set()
    unique_tools_used = set()

    for s in sessions:
        if s.message_usage:
            total_input_tokens += s.message_usage.input_tokens
            total_output_tokens += s.message_usage.output_tokens
            cache_read_tokens += s.message_usage.cache_read_input_tokens
            cache_creation_tokens += s.message_usage.cache_creation_input_tokens
        thinking_block_count += len(s.thinking_blocks)
        model_versions_used.update(s.model_versions)
        unique_tools_used.update(s.tools_used)

    # Save extraction state
    state = {
        "last_extraction": datetime.now().isoformat(),
        "session_count": len(sessions),
        "plan_count": len(plan_files),
        "tool_call_count": total_tool_calls,
        "message_count": total_messages,
        # NEW: Rich data stats
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_creation_tokens": cache_creation_tokens,
        "thinking_block_count": thinking_block_count,
        "model_versions_used": list(model_versions_used),
        "unique_tools_used": list(unique_tools_used),
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
        # NEW: Rich data aggregates
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_creation_tokens=cache_creation_tokens,
        thinking_block_count=thinking_block_count,
        model_versions_used=list(model_versions_used),
        unique_tools_used=list(unique_tools_used),
        per_session_files=per_session_files,
    )
