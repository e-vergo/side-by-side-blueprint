"""Session data structures for Claude Code interaction tracking."""

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class ToolCall:
    """Single tool invocation from a Claude session."""

    tool_name: str
    timestamp: str  # ISO format
    duration_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    input_summary: Optional[str] = None  # Truncated input for pattern detection

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "input_summary": self.input_summary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ToolCall":
        return cls(
            tool_name=data["tool_name"],
            timestamp=data["timestamp"],
            duration_ms=data.get("duration_ms"),
            success=data.get("success", True),
            error=data.get("error"),
            input_summary=data.get("input_summary"),
        )


@dataclass
class SessionData:
    """Parsed data from a single Claude Code session."""

    session_id: str
    project_path: str  # The workspace path
    started_at: str  # ISO timestamp
    ended_at: str  # ISO timestamp

    # Message stats
    message_count: int = 0
    user_messages: int = 0
    assistant_messages: int = 0

    # Tool usage
    tool_calls: list[ToolCall] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)  # Unique tool names

    # File operations
    files_read: list[str] = field(default_factory=list)
    files_written: list[str] = field(default_factory=list)
    files_edited: list[str] = field(default_factory=list)

    # Subagents
    subagent_ids: list[str] = field(default_factory=list)

    # Plan references
    plan_files: list[str] = field(default_factory=list)

    # Analysis hooks can add findings here
    analysis_findings: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "project_path": self.project_path,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "message_count": self.message_count,
            "user_messages": self.user_messages,
            "assistant_messages": self.assistant_messages,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "tools_used": self.tools_used,
            "files_read": self.files_read,
            "files_written": self.files_written,
            "files_edited": self.files_edited,
            "subagent_ids": self.subagent_ids,
            "plan_files": self.plan_files,
            "analysis_findings": self.analysis_findings,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionData":
        return cls(
            session_id=data["session_id"],
            project_path=data["project_path"],
            started_at=data["started_at"],
            ended_at=data["ended_at"],
            message_count=data.get("message_count", 0),
            user_messages=data.get("user_messages", 0),
            assistant_messages=data.get("assistant_messages", 0),
            tool_calls=[ToolCall.from_dict(tc) for tc in data.get("tool_calls", [])],
            tools_used=data.get("tools_used", []),
            files_read=data.get("files_read", []),
            files_written=data.get("files_written", []),
            files_edited=data.get("files_edited", []),
            subagent_ids=data.get("subagent_ids", []),
            plan_files=data.get("plan_files", []),
            analysis_findings=data.get("analysis_findings", {}),
        )


@dataclass
class ClaudeDataSnapshot:
    """Snapshot of extracted ~/.claude data for an archive entry."""

    session_ids: list[str] = field(default_factory=list)
    plan_files: list[str] = field(default_factory=list)
    tool_call_count: int = 0
    message_count: int = 0
    files_modified: list[str] = field(default_factory=list)
    extraction_timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "session_ids": self.session_ids,
            "plan_files": self.plan_files,
            "tool_call_count": self.tool_call_count,
            "message_count": self.message_count,
            "files_modified": self.files_modified,
            "extraction_timestamp": self.extraction_timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClaudeDataSnapshot":
        return cls(
            session_ids=data.get("session_ids", []),
            plan_files=data.get("plan_files", []),
            tool_call_count=data.get("tool_call_count", 0),
            message_count=data.get("message_count", 0),
            files_modified=data.get("files_modified", []),
            extraction_timestamp=data.get("extraction_timestamp", ""),
        )
