"""Archive entry data structures for SBS project snapshots."""

from dataclasses import dataclass, field
from typing import Optional
import json
from pathlib import Path


@dataclass
class ArchiveEntry:
    """A single archive entry representing a project snapshot."""

    # Identity
    entry_id: str  # Unix timestamp: "1738340279"
    created_at: str  # ISO timestamp

    # Linkage
    project: str
    build_run_id: Optional[str] = None
    compliance_run_id: Optional[str] = None

    # User annotations
    notes: str = ""
    tags: list[str] = field(default_factory=list)

    # Content references
    screenshots: list[str] = field(default_factory=list)
    stats_snapshot: Optional[str] = None
    chat_summary: Optional[str] = None

    # Git state
    repo_commits: dict[str, str] = field(default_factory=dict)

    # Sync status
    synced_to_icloud: bool = False
    sync_timestamp: Optional[str] = None
    sync_error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "entry_id": self.entry_id,
            "created_at": self.created_at,
            "project": self.project,
            "build_run_id": self.build_run_id,
            "compliance_run_id": self.compliance_run_id,
            "notes": self.notes,
            "tags": self.tags,
            "screenshots": self.screenshots,
            "stats_snapshot": self.stats_snapshot,
            "chat_summary": self.chat_summary,
            "repo_commits": self.repo_commits,
            "synced_to_icloud": self.synced_to_icloud,
            "sync_timestamp": self.sync_timestamp,
            "sync_error": self.sync_error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ArchiveEntry":
        """Create an ArchiveEntry from a dict."""
        return cls(
            entry_id=data["entry_id"],
            created_at=data["created_at"],
            project=data["project"],
            build_run_id=data.get("build_run_id"),
            compliance_run_id=data.get("compliance_run_id"),
            notes=data.get("notes", ""),
            tags=data.get("tags", []),
            screenshots=data.get("screenshots", []),
            stats_snapshot=data.get("stats_snapshot"),
            chat_summary=data.get("chat_summary"),
            repo_commits=data.get("repo_commits", {}),
            synced_to_icloud=data.get("synced_to_icloud", False),
            sync_timestamp=data.get("sync_timestamp"),
            sync_error=data.get("sync_error"),
        )


@dataclass
class ArchiveIndex:
    """Index of all archive entries with lookup indices."""

    version: str = "1.0"
    entries: dict[str, ArchiveEntry] = field(default_factory=dict)
    by_tag: dict[str, list[str]] = field(default_factory=dict)
    by_project: dict[str, list[str]] = field(default_factory=dict)
    latest_by_project: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "version": self.version,
            "entries": {k: v.to_dict() for k, v in self.entries.items()},
            "by_tag": self.by_tag,
            "by_project": self.by_project,
            "latest_by_project": self.latest_by_project,
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
        )

    def add_entry(self, entry: ArchiveEntry) -> None:
        """Add entry and update indices."""
        entry_id = entry.entry_id

        # Add to main entries dict
        self.entries[entry_id] = entry

        # Update by_tag index
        for tag in entry.tags:
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
