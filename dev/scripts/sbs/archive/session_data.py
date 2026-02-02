"""Session data structures for Claude Code interaction tracking.

Extended to capture rich JSONL data including:
- Thinking blocks (reasoning traces)
- Token usage (cost analysis)
- Message threading (session reconstruction)
- Full tool inputs/outputs
"""

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class ThinkingBlock:
    """Claude's reasoning trace from extended thinking."""

    content: str
    signature: Optional[str] = None  # Model version signature (e.g., "ErAAntoP...")
    timestamp: Optional[str] = None  # When this thinking block was generated

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ThinkingBlock":
        return cls(
            content=data["content"],
            signature=data.get("signature"),
            timestamp=data.get("timestamp"),
        )


@dataclass
class MessageUsage:
    """Token usage for messages (aggregated across session)."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MessageUsage":
        return cls(
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            cache_creation_input_tokens=data.get("cache_creation_input_tokens", 0),
            cache_read_input_tokens=data.get("cache_read_input_tokens", 0),
        )


@dataclass
class ToolCall:
    """Single tool invocation from a Claude session."""

    tool_name: str
    timestamp: str  # ISO format

    # Existing fields
    duration_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    input_summary: Optional[str] = None  # Truncated input for pattern detection

    # NEW: Rich data fields
    input_full: Optional[dict] = None  # Complete input (not truncated)
    result_content: Optional[str] = None  # Tool result content
    result_type: Optional[str] = None  # "text", "image", "error"
    tool_use_id: Optional[str] = None  # For linking tool_use to tool_result

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "input_summary": self.input_summary,
            "input_full": self.input_full,
            "result_content": self.result_content,
            "result_type": self.result_type,
            "tool_use_id": self.tool_use_id,
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
            input_full=data.get("input_full"),
            result_content=data.get("result_content"),
            result_type=data.get("result_type"),
            tool_use_id=data.get("tool_use_id"),
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

    # NEW: Rich data fields
    slug: Optional[str] = None  # Human-readable session name from index
    first_prompt: Optional[str] = None  # Initial user intent
    session_summary: Optional[str] = None  # From sessions-index.json
    model_versions: list[str] = field(default_factory=list)  # Models used (from thinking signatures)
    thinking_blocks: list[ThinkingBlock] = field(default_factory=list)  # Reasoning traces
    message_usage: Optional[MessageUsage] = None  # Aggregated token usage
    parent_uuid_chain: list[str] = field(default_factory=list)  # Message threading
    stop_reasons: list[str] = field(default_factory=list)  # Completion reasons

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
            # New fields
            "slug": self.slug,
            "first_prompt": self.first_prompt,
            "session_summary": self.session_summary,
            "model_versions": self.model_versions,
            "thinking_blocks": [tb.to_dict() for tb in self.thinking_blocks],
            "message_usage": self.message_usage.to_dict() if self.message_usage else None,
            "parent_uuid_chain": self.parent_uuid_chain,
            "stop_reasons": self.stop_reasons,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionData":
        # Parse thinking blocks
        thinking_blocks = []
        for tb in data.get("thinking_blocks", []):
            thinking_blocks.append(ThinkingBlock.from_dict(tb))

        # Parse message usage
        message_usage = None
        if data.get("message_usage"):
            message_usage = MessageUsage.from_dict(data["message_usage"])

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
            # New fields
            slug=data.get("slug"),
            first_prompt=data.get("first_prompt"),
            session_summary=data.get("session_summary"),
            model_versions=data.get("model_versions", []),
            thinking_blocks=thinking_blocks,
            message_usage=message_usage,
            parent_uuid_chain=data.get("parent_uuid_chain", []),
            stop_reasons=data.get("stop_reasons", []),
        )


@dataclass
class ClaudeDataSnapshot:
    """Snapshot of extracted ~/.claude data for an archive entry."""

    # Existing fields
    session_ids: list[str] = field(default_factory=list)
    plan_files: list[str] = field(default_factory=list)
    tool_call_count: int = 0
    message_count: int = 0
    files_modified: list[str] = field(default_factory=list)
    extraction_timestamp: str = ""

    # NEW: Rich data aggregates
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    thinking_block_count: int = 0
    model_versions_used: list[str] = field(default_factory=list)
    unique_tools_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "session_ids": self.session_ids,
            "plan_files": self.plan_files,
            "tool_call_count": self.tool_call_count,
            "message_count": self.message_count,
            "files_modified": self.files_modified,
            "extraction_timestamp": self.extraction_timestamp,
            # New fields
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "thinking_block_count": self.thinking_block_count,
            "model_versions_used": self.model_versions_used,
            "unique_tools_used": self.unique_tools_used,
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
            # New fields
            total_input_tokens=data.get("total_input_tokens", 0),
            total_output_tokens=data.get("total_output_tokens", 0),
            cache_read_tokens=data.get("cache_read_tokens", 0),
            cache_creation_tokens=data.get("cache_creation_tokens", 0),
            thinking_block_count=data.get("thinking_block_count", 0),
            model_versions_used=data.get("model_versions_used", []),
            unique_tools_used=data.get("unique_tools_used", []),
        )
