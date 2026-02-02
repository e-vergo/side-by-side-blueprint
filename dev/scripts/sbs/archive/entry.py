"""Archive entry data structures for SBS project snapshots."""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
import json
from pathlib import Path

if TYPE_CHECKING:
    from .session_data import ClaudeDataSnapshot


@dataclass
class ArchiveEntry:
    """A single archive entry representing a project snapshot."""

    # Identity
    entry_id: str  # Unix timestamp: "1738340279"
    created_at: str  # ISO timestamp

    # Linkage
    project: str
    build_run_id: Optional[str] = None

    # User annotations
    notes: str = ""
    tags: list[str] = field(default_factory=list)

    # Content references
    screenshots: list[str] = field(default_factory=list)

    # Git state
    repo_commits: dict[str, str] = field(default_factory=dict)

    # Sync status
    synced_to_icloud: bool = False
    sync_timestamp: Optional[str] = None
    sync_error: Optional[str] = None

    # Rubric evaluation
    rubric_id: Optional[str] = None  # Links to a rubric in archive/rubrics/
    rubric_evaluation: Optional[dict] = None  # Snapshot of evaluation results

    # Claude data extraction
    claude_data: Optional[dict] = None  # Serialized ClaudeDataSnapshot
    auto_tags: list[str] = field(default_factory=list)  # Tags from rules/hooks
    trigger: str = "manual"  # "build", "manual", "skill"

    # Quality scores snapshot
    quality_scores: Optional[dict] = None  # {overall: float, scores: {metric_id: {value, passed, stale}}}
    quality_delta: Optional[dict] = None  # Delta from previous entry if available

    # State machine fields
    global_state: Optional[dict] = None  # {skill: str, substate: str} or null when idle
    state_transition: Optional[str] = None  # "phase_start" | "phase_end" | null
    epoch_summary: Optional[dict] = None  # Computed on skill-triggered entries that close epochs

    # Gate validation
    gate_validation: Optional[dict] = None  # {passed: bool, findings: list[str]} if gates were checked

    # GitHub issue references
    issue_refs: list[str] = field(default_factory=list)  # Issue numbers, e.g., ["42", "57"]

    # PR references
    pr_refs: list[int] = field(default_factory=list)  # PR numbers, e.g., [42, 57]

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "entry_id": self.entry_id,
            "created_at": self.created_at,
            "project": self.project,
            "build_run_id": self.build_run_id,
            "notes": self.notes,
            "tags": self.tags,
            "screenshots": self.screenshots,
            "repo_commits": self.repo_commits,
            "synced_to_icloud": self.synced_to_icloud,
            "sync_timestamp": self.sync_timestamp,
            "sync_error": self.sync_error,
            "rubric_id": self.rubric_id,
            "rubric_evaluation": self.rubric_evaluation,
            "claude_data": self.claude_data,
            "auto_tags": self.auto_tags,
            "trigger": self.trigger,
            "quality_scores": self.quality_scores,
            "quality_delta": self.quality_delta,
            "global_state": self.global_state,
            "state_transition": self.state_transition,
            "epoch_summary": self.epoch_summary,
            "gate_validation": self.gate_validation,
            "issue_refs": self.issue_refs,
            "pr_refs": self.pr_refs,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ArchiveEntry":
        """Create an ArchiveEntry from a dict.

        Note: Ignores legacy fields (compliance_run_id, stats_snapshot,
        chat_summary) for backward compatibility with old entries.
        """
        return cls(
            entry_id=data["entry_id"],
            created_at=data["created_at"],
            project=data["project"],
            build_run_id=data.get("build_run_id"),
            notes=data.get("notes", ""),
            tags=data.get("tags", []),
            screenshots=data.get("screenshots", []),
            repo_commits=data.get("repo_commits", {}),
            synced_to_icloud=data.get("synced_to_icloud", False),
            sync_timestamp=data.get("sync_timestamp"),
            sync_error=data.get("sync_error"),
            rubric_id=data.get("rubric_id"),
            rubric_evaluation=data.get("rubric_evaluation"),
            claude_data=data.get("claude_data"),
            auto_tags=data.get("auto_tags", []),
            trigger=data.get("trigger", "manual"),
            quality_scores=data.get("quality_scores"),
            quality_delta=data.get("quality_delta"),
            global_state=data.get("global_state"),
            state_transition=data.get("state_transition"),
            epoch_summary=data.get("epoch_summary"),
            gate_validation=data.get("gate_validation"),
            issue_refs=data.get("issue_refs", []),
            pr_refs=data.get("pr_refs", []),
        )


@dataclass
class ArchiveIndex:
    """Index of all archive entries with lookup indices."""

    version: str = "1.1"
    entries: dict[str, ArchiveEntry] = field(default_factory=dict)
    by_tag: dict[str, list[str]] = field(default_factory=dict)
    by_project: dict[str, list[str]] = field(default_factory=dict)
    latest_by_project: dict[str, str] = field(default_factory=dict)

    # Global orchestration state
    global_state: Optional[dict] = None  # Current {skill, substate} or null when idle
    last_epoch_entry: Optional[str] = None  # Entry ID of last epoch close

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "version": self.version,
            "entries": {k: v.to_dict() for k, v in self.entries.items()},
            "by_tag": self.by_tag,
            "by_project": self.by_project,
            "latest_by_project": self.latest_by_project,
            "global_state": self.global_state,
            "last_epoch_entry": self.last_epoch_entry,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ArchiveIndex":
        """Create an ArchiveIndex from a dict."""
        entries = {
            k: ArchiveEntry.from_dict(v) for k, v in data.get("entries", {}).items()
        }
        return cls(
            version=data.get("version", "1.0"),
            entries=entries,
            by_tag=data.get("by_tag", {}),
            by_project=data.get("by_project", {}),
            latest_by_project=data.get("latest_by_project", {}),
            global_state=data.get("global_state"),
            last_epoch_entry=data.get("last_epoch_entry"),
        )

    def add_entry(self, entry: ArchiveEntry) -> None:
        """Add entry and update indices."""
        entry_id = entry.entry_id

        # Add to main entries dict
        self.entries[entry_id] = entry

        # Update by_tag index (include both manual tags and auto_tags)
        all_tags = list(entry.tags) + list(entry.auto_tags)
        for tag in all_tags:
            if tag not in self.by_tag:
                self.by_tag[tag] = []
            if entry_id not in self.by_tag[tag]:
                self.by_tag[tag].append(entry_id)

        # Update by_project index
        project = entry.project
        if project not in self.by_project:
            self.by_project[project] = []
        if entry_id not in self.by_project[project]:
            self.by_project[project].append(entry_id)

        # Update latest_by_project
        current_latest = self.latest_by_project.get(project)
        if current_latest is None or entry_id > current_latest:
            self.latest_by_project[project] = entry_id

    def get_entries_by_tag(self, tag: str) -> list[ArchiveEntry]:
        """Get all entries with a given tag."""
        entry_ids = self.by_tag.get(tag, [])
        return [self.entries[eid] for eid in entry_ids if eid in self.entries]

    def get_entries_by_project(self, project: str) -> list[ArchiveEntry]:
        """Get all entries for a given project."""
        entry_ids = self.by_project.get(project, [])
        return [self.entries[eid] for eid in entry_ids if eid in self.entries]

    def get_latest_entry(self, project: str) -> Optional[ArchiveEntry]:
        """Get the latest entry for a given project."""
        entry_id = self.latest_by_project.get(project)
        if entry_id is None:
            return None
        return self.entries.get(entry_id)

    def save(self, path: Path) -> None:
        """Save index to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "ArchiveIndex":
        """Load index from JSON file."""
        if not path.exists():
            return cls()
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)
