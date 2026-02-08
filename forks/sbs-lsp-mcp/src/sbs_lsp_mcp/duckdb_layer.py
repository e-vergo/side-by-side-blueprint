"""DuckDB-backed data layer for the SBS MCP server.

Replaces ``load_archive_index()`` with a lifespan-scoped in-memory DuckDB
instance that loads data from:
- ``archive_index.json`` (entries + metadata)
- ``~/.claude/projects/*/`` JSONL session files (questions)
- ``sbs-oracle.md`` (concept index + file map)

Lifecycle:
- Created once in ``app_lifespan()`` and stored in ``AppContext``.
- ``ensure_loaded()`` is called at the start of every public method.
- ``refresh_if_stale()`` checks file mtimes and reloads if changed.
- ``invalidate()`` forces reload on next access (after archive writes).
- ``close()`` cleans up the DuckDB connection.
"""

from __future__ import annotations

import difflib
import json
import logging
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb

from .sbs_models import (
    AnalysisFinding,
    AnalysisSummary,
    ComparativeAnalysis,
    DiscriminatingFeature,
    GateFailureEntry,
    GateFailureReport,
    InterruptionAnalysisResult,
    InterruptionEvent,
    PhaseTransitionHealthResult,
    PhaseTransitionReport,
    QuestionAnalysisResult,
    QuestionInteraction,
    QuestionStatsResult,
    SelfImproveEntries,
    SelfImproveEntrySummary,
    SkillStatEntry,
    SkillStatsResult,
    SuccessPattern,
    SuccessPatterns,
    SystemHealthMetric,
    SystemHealthReport,
    TagEffectivenessEntry,
    TagEffectivenessResult,
    UserPatternAnalysis,
    AskOracleResult,
    OracleMatch,
    OracleConcept,
)

_log = logging.getLogger(__name__)

# Phase ordering used for backward-transition detection and override analysis
SKILL_PHASE_ORDERS: dict[str, list[str]] = {
    "task": ["alignment", "planning", "execution", "finalization"],
    "self-improve": ["discovery", "selection", "dialogue", "logging", "archive"],
}

CORRECTION_KEYWORDS = [
    "correction", "corrected", "redo", "retry", "revert",
    "wrong", "mistake", "back to", "restart", "redirected",
    "changed approach", "pivot", "scratch that",
]


class DuckDBLayer:
    """Lifespan-scoped DuckDB data layer for the SBS MCP server."""

    def __init__(
        self,
        archive_dir: Path,
        session_dir: Path,
        oracle_path: Path,
    ) -> None:
        self._archive_dir = archive_dir
        self._session_dir = session_dir
        self._oracle_path = oracle_path
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        self._loaded = False
        self._invalidated = False
        self._mtimes: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def ensure_loaded(self) -> None:
        """Lazy initialisation. Idempotent unless invalidated."""
        if self._loaded and not self._invalidated:
            self.refresh_if_stale()
            return
        self._full_load()

    def refresh_if_stale(self) -> None:
        """Compare file mtimes and reload if any source changed."""
        archive_path = self._archive_dir / "archive_index.json"
        if archive_path.exists():
            mtime = archive_path.stat().st_mtime
            if mtime != self._mtimes.get("archive_index"):
                self._full_load()
                return
        if self._oracle_path.exists():
            mtime = self._oracle_path.stat().st_mtime
            if mtime != self._mtimes.get("oracle"):
                self._full_load()
                return

    def invalidate(self) -> None:
        """Force a full reload on the next ``ensure_loaded()`` call."""
        self._invalidated = True

    def close(self) -> None:
        """Close the DuckDB connection."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
        self._loaded = False

    # ------------------------------------------------------------------
    # Internal: full load
    # ------------------------------------------------------------------

    def _full_load(self) -> None:
        """(Re-)create the in-memory database and load all sources."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass

        self._conn = duckdb.connect(":memory:")
        self._create_schema()
        self._load_archive_entries()
        self._load_oracle_data()
        # Session question loading is deferred: only loaded when analytics
        # methods actually need it (question_analysis / question_stats).
        self._create_derived_views()
        self._loaded = True
        self._invalidated = False

    def _create_schema(self) -> None:
        assert self._conn is not None
        self._conn.execute("""
            CREATE TABLE entries (
                entry_id VARCHAR PRIMARY KEY,
                created_at TIMESTAMP,
                project VARCHAR,
                build_run_id VARCHAR,
                notes TEXT,
                tags VARCHAR[],
                auto_tags VARCHAR[],
                screenshots VARCHAR[],
                trigger VARCHAR,
                quality_overall FLOAT,
                quality_scores JSON,
                quality_delta JSON,
                gs_skill VARCHAR,
                gs_substate VARCHAR,
                state_transition VARCHAR,
                epoch_summary JSON,
                gate_validation JSON,
                issue_refs VARCHAR[],
                pr_refs INTEGER[],
                repo_commits JSON,
                rubric_id VARCHAR,
                synced_to_icloud BOOLEAN,
                added_at TIMESTAMP
            )
        """)
        self._conn.execute("""
            CREATE TABLE index_metadata (
                global_state_skill VARCHAR,
                global_state_substate VARCHAR,
                last_epoch_entry VARCHAR,
                version VARCHAR
            )
        """)
        self._conn.execute("""
            CREATE TABLE questions (
                session_file VARCHAR,
                timestamp TIMESTAMP,
                question_text TEXT,
                header VARCHAR,
                options JSON,
                multi_select BOOLEAN,
                user_answer TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE oracle_concepts (
                concept VARCHAR,
                primary_location VARCHAR,
                notes TEXT,
                section VARCHAR
            )
        """)
        self._conn.execute("""
            CREATE TABLE oracle_files (
                file_path VARCHAR,
                section VARCHAR,
                concept VARCHAR,
                notes TEXT
            )
        """)

    def _create_derived_views(self) -> None:
        assert self._conn is not None
        # Two-CTE approach: DuckDB forbids nesting window functions.
        # CTE 1 computes LAG values; CTE 2 uses them in a running SUM.
        self._conn.execute("""
            CREATE OR REPLACE VIEW skill_sessions AS
            WITH lagged AS (
                SELECT *,
                    LAG(state_transition) OVER (ORDER BY created_at NULLS LAST) AS prev_transition,
                    LAG(gs_skill) OVER (ORDER BY created_at NULLS LAST) AS prev_skill
                FROM entries WHERE gs_skill IS NOT NULL
            ),
            boundaries AS (
                SELECT *,
                    SUM(CASE WHEN state_transition IN ('phase_start','skill_start')
                              AND gs_skill IS NOT NULL
                              AND (prev_transition IN ('phase_end','handoff','phase_fail')
                                   OR prev_skill IS NULL
                                   OR prev_skill != gs_skill)
                        THEN 1 ELSE 0 END) OVER (ORDER BY created_at NULLS LAST) AS session_id
                FROM lagged
            )
            SELECT * FROM boundaries
        """)
        self._conn.execute("""
            CREATE OR REPLACE VIEW skill_intervals AS
            SELECT
                MIN(created_at) AS start_ts,
                MAX(created_at) AS end_ts,
                gs_skill AS skill,
                gs_substate AS substate,
                session_id
            FROM skill_sessions
            GROUP BY session_id, gs_skill, gs_substate
        """)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_archive_entries(self) -> None:
        """Load ``archive_index.json`` into the entries + index_metadata tables."""
        assert self._conn is not None
        archive_path = self._archive_dir / "archive_index.json"
        if not archive_path.exists():
            # Insert empty metadata row
            self._conn.execute(
                "INSERT INTO index_metadata VALUES (NULL, NULL, NULL, '1.1')"
            )
            self._mtimes["archive_index"] = 0
            return

        self._mtimes["archive_index"] = archive_path.stat().st_mtime

        with open(archive_path) as f:
            data = json.load(f)

        # Metadata
        gs = data.get("global_state") or {}
        self._conn.execute(
            "INSERT INTO index_metadata VALUES (?, ?, ?, ?)",
            [
                gs.get("skill"),
                gs.get("substate"),
                data.get("last_epoch_entry"),
                data.get("version", "1.0"),
            ],
        )

        # Entries
        entries_raw = data.get("entries", {})
        for eid, e in entries_raw.items():
            entry_gs = e.get("global_state") or {}
            qs = e.get("quality_scores") or {}
            overall = None
            if qs and "overall" in qs:
                try:
                    overall = float(qs["overall"])
                except (ValueError, TypeError):
                    pass

            created_at = None
            if e.get("created_at"):
                try:
                    created_at = datetime.fromisoformat(
                        e["created_at"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            added_at = None
            if e.get("added_at"):
                try:
                    added_at = datetime.fromisoformat(
                        e["added_at"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            pr_refs = e.get("pr_refs", [])
            # pr_refs may be strings or ints; coerce to ints
            pr_refs_int = []
            for p in pr_refs:
                try:
                    pr_refs_int.append(int(p))
                except (ValueError, TypeError):
                    pass

            self._conn.execute(
                """
                INSERT INTO entries VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?
                )
                """,
                [
                    eid,
                    created_at,
                    e.get("project", ""),
                    e.get("build_run_id"),
                    e.get("notes", ""),
                    e.get("tags", []),
                    e.get("auto_tags", []),
                    e.get("screenshots", []),
                    e.get("trigger", "manual"),
                    overall,
                    json.dumps(qs) if qs else None,
                    json.dumps(e.get("quality_delta")) if e.get("quality_delta") else None,
                    entry_gs.get("skill"),
                    entry_gs.get("substate"),
                    e.get("state_transition"),
                    json.dumps(e.get("epoch_summary")) if e.get("epoch_summary") else None,
                    json.dumps(e.get("gate_validation")) if e.get("gate_validation") else None,
                    [str(x) for x in e.get("issue_refs", [])],
                    pr_refs_int,
                    json.dumps(e.get("repo_commits", {})),
                    e.get("rubric_id"),
                    e.get("synced_to_icloud", False),
                    added_at,
                ],
            )

    def _load_oracle_data(self) -> None:
        """Parse ``sbs-oracle.md`` into concept + file tables."""
        assert self._conn is not None
        if not self._oracle_path.exists():
            self._mtimes["oracle"] = 0
            return

        self._mtimes["oracle"] = self._oracle_path.stat().st_mtime
        content = self._oracle_path.read_text()

        current_section: Optional[str] = None
        in_table = False

        for line in content.split("\n"):
            if line.startswith("## "):
                current_section = line[3:].strip()
                in_table = False
                continue

            if not current_section:
                continue

            # Parse markdown table rows
            if line.startswith("|"):
                if "---" in line:
                    in_table = True
                    continue
                if not in_table and ("Concept" in line or "Primary Location" in line):
                    in_table = True
                    continue

                parts = [p.strip() for p in line.split("|")]
                parts = [p for p in parts if p]

                if len(parts) >= 2:
                    concept_name = parts[0].strip("`").strip()
                    location = parts[1].strip("`").strip() if len(parts) > 1 else ""
                    notes = parts[2].strip() if len(parts) > 2 else ""

                    is_file = (
                        "/" in location
                        or location.endswith(".lean")
                        or location.endswith(".py")
                        or location.endswith(".md")
                    )

                    if is_file:
                        self._conn.execute(
                            "INSERT INTO oracle_files VALUES (?, ?, ?, ?)",
                            [location, current_section, concept_name, notes],
                        )

                    self._conn.execute(
                        "INSERT INTO oracle_concepts VALUES (?, ?, ?, ?)",
                        [concept_name, location, notes, current_section],
                    )

            elif line.startswith("- ") and current_section:
                item = line[2:].strip()
                is_file = (
                    "/" in item
                    or item.endswith(".lean")
                    or item.endswith(".py")
                )
                if is_file:
                    path = item.split(" - ")[0].strip().strip("`")
                    self._conn.execute(
                        "INSERT INTO oracle_files VALUES (?, ?, ?, ?)",
                        [path, current_section, "", ""],
                    )
                else:
                    self._conn.execute(
                        "INSERT INTO oracle_concepts VALUES (?, ?, ?, ?)",
                        [item, "", "", current_section],
                    )

    def _ensure_questions_loaded(self) -> None:
        """Load JSONL session questions if not yet loaded.

        This is called lazily by question_analysis / question_stats to
        avoid scanning ``~/.claude/`` on every MCP call.
        """
        assert self._conn is not None
        # Check if already loaded
        count = self._conn.execute("SELECT COUNT(*) FROM questions").fetchone()
        # We use a sentinel: if the table has rows, skip. If it has been loaded
        # and was empty, we still mark it loaded via a flag.
        if hasattr(self, "_questions_loaded") and self._questions_loaded:
            return
        self._load_session_questions()
        self._questions_loaded = True

    def _load_session_questions(self) -> None:
        """Scan JSONL session files and extract AskUserQuestion interactions."""
        assert self._conn is not None

        # Add dev/scripts to path so we can import sbs modules
        sbs_root = self._archive_dir.parent  # archive_dir = dev/storage, parent = dev, grandparent = SBS root
        # Actually archive_dir IS dev/storage, so parent is dev, and dev/scripts is the scripts dir
        scripts_dir = sbs_root.parent / "scripts" if sbs_root.name == "storage" else sbs_root / "dev" / "scripts"
        if scripts_dir.exists() and str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))

        try:
            from sbs.archive.extractor import get_sbs_project_dirs, extract_ask_user_questions
        except ImportError:
            _log.debug("Cannot import sbs.archive.extractor - question loading skipped")
            return

        session_files = []
        for project_dir in get_sbs_project_dirs():
            for session_file in project_dir.glob("*.jsonl"):
                session_files.append((session_file.stem, session_file))

        for session_id, session_path in session_files:
            try:
                raw_interactions = extract_ask_user_questions(session_path)
            except Exception:
                continue

            for raw in raw_interactions:
                ts = raw.get("timestamp")
                ts_parsed = None
                if ts:
                    try:
                        ts_parsed = datetime.fromisoformat(
                            ts.replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass

                for q in raw.get("questions", []):
                    q_text = q.get("question", "")
                    header = q.get("header", "")
                    options = q.get("options")
                    multi_select = q.get("multiSelect", False)
                    answer = raw.get("answers", {}).get(q_text, "")

                    self._conn.execute(
                        "INSERT INTO questions VALUES (?, ?, ?, ?, ?, ?, ?)",
                        [
                            session_id,
                            ts_parsed,
                            q_text,
                            header,
                            json.dumps(options) if options else None,
                            multi_select,
                            answer,
                        ],
                    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_entry_dict(self, row: tuple, columns: list[str]) -> dict:
        """Convert a DuckDB result row to an entry dict matching the old format."""
        d: dict[str, Any] = {}
        for i, col in enumerate(columns):
            val = row[i]
            # DuckDB returns datetime objects; convert to ISO strings
            if isinstance(val, datetime):
                d[col] = val.isoformat()
            else:
                d[col] = val
        # Reconstruct global_state dict from flattened columns
        gs_skill = d.pop("gs_skill", None)
        gs_substate = d.pop("gs_substate", None)
        if gs_skill:
            d["global_state"] = {"skill": gs_skill, "substate": gs_substate}
        else:
            d["global_state"] = None
        # Parse JSON columns back to dicts
        for json_col in ("quality_scores", "quality_delta", "epoch_summary", "gate_validation", "repo_commits"):
            if json_col in d and isinstance(d[json_col], str):
                try:
                    d[json_col] = json.loads(d[json_col])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d

    def _fetch_entries(self, query: str, params: list | None = None) -> list[dict]:
        """Execute a query and return list of entry dicts."""
        assert self._conn is not None
        result = self._conn.execute(query, params or [])
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [self._row_to_entry_dict(row, columns) for row in rows]

    @staticmethod
    def _resolve_since_to_datetime(since: str) -> Optional[datetime]:
        """Convert a ``since`` value to a datetime for ``created_at`` comparison.

        Accepts:
        - ISO 8601 timestamps (``2026-02-01T00:00:00``, with optional ``Z``/offset)
        - Old-format entry IDs (``YYYYMMDDHHMMSS``, 14 digits)
        - Unix-timestamp entry IDs (10-digit strings)

        Returns ``None`` if the value cannot be parsed.
        """
        if not since:
            return None

        # Try ISO format first (contains '-')
        if "-" in since:
            try:
                return datetime.fromisoformat(since.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Pure digits: old entry_id (14 chars) or unix timestamp (10 chars)
        if since.isdigit():
            if len(since) == 14:
                # YYYYMMDDHHMMSS
                try:
                    return datetime.strptime(since, "%Y%m%d%H%M%S").replace(
                        tzinfo=timezone.utc
                    )
                except ValueError:
                    pass
            elif len(since) <= 12:
                # Unix timestamp (seconds since epoch)
                try:
                    return datetime.fromtimestamp(int(since), tz=timezone.utc)
                except (ValueError, OSError, OverflowError):
                    pass

        return None

    # ------------------------------------------------------------------
    # Core access methods
    # ------------------------------------------------------------------

    def get_global_state(self) -> tuple[Optional[str], Optional[str]]:
        """Return (skill, substate) from index_metadata."""
        self.ensure_loaded()
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT global_state_skill, global_state_substate FROM index_metadata LIMIT 1"
        ).fetchone()
        if row is None:
            return None, None
        return row[0], row[1]

    def get_metadata(self) -> dict:
        """Return global_state, last_epoch_entry, projects list, entry count."""
        self.ensure_loaded()
        assert self._conn is not None
        meta = self._conn.execute(
            "SELECT global_state_skill, global_state_substate, last_epoch_entry, version "
            "FROM index_metadata LIMIT 1"
        ).fetchone()

        projects = [
            r[0] for r in self._conn.execute(
                "SELECT DISTINCT project FROM entries WHERE project != '' ORDER BY project"
            ).fetchall()
        ]

        total = self._conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]

        gs = None
        if meta and meta[0]:
            gs = {"skill": meta[0], "substate": meta[1]}

        return {
            "global_state": gs,
            "last_epoch_entry": meta[2] if meta else None,
            "version": meta[3] if meta else None,
            "projects": projects,
            "total_entries": total,
        }

    def get_entry(self, entry_id: str) -> Optional[dict]:
        """Single entry lookup by ID."""
        self.ensure_loaded()
        entries = self._fetch_entries(
            "SELECT * FROM entries WHERE entry_id = ?", [entry_id]
        )
        return entries[0] if entries else None

    def get_entries(
        self,
        project: Optional[str] = None,
        tags: Optional[list[str]] = None,
        since: Optional[str] = None,
        trigger: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        """Filter entries. Tags use ANY match. ORDER BY created_at DESC."""
        self.ensure_loaded()
        assert self._conn is not None
        conditions: list[str] = []
        params: list[Any] = []

        if project:
            conditions.append("project = ?")
            params.append(project)
        if tags:
            # ANY match: entry has at least one tag in common
            tag_clauses = []
            for tag in tags:
                tag_clauses.append("list_contains(tags, ?) OR list_contains(auto_tags, ?)")
                params.extend([tag, tag])
            conditions.append(f"({' OR '.join(tag_clauses)})")
        if since:
            since_dt = self._resolve_since_to_datetime(since)
            if since_dt is not None:
                conditions.append("created_at > ?")
                params.append(since_dt)
            else:
                # Fallback: treat as entry_id for backwards compat
                conditions.append("entry_id > ?")
                params.append(since)
        if trigger:
            conditions.append("trigger = ?")
            params.append(trigger)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        query = f"SELECT * FROM entries {where} ORDER BY created_at DESC NULLS LAST LIMIT ?"
        params.append(limit)
        return self._fetch_entries(query, params)

    def _entry_id_to_created_at(self, entry_id: str) -> Optional[datetime]:
        """Look up the ``created_at`` timestamp for a given entry_id."""
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT created_at FROM entries WHERE entry_id = ? LIMIT 1",
            [entry_id],
        ).fetchone()
        return row[0] if row and row[0] else None

    def get_epoch_entries(self, epoch_entry_id: Optional[str] = None) -> list[dict]:
        """Get entries in an epoch.

        If epoch_entry_id is None, returns entries in the current (open) epoch.
        """
        self.ensure_loaded()
        assert self._conn is not None

        if epoch_entry_id is None:
            meta = self._conn.execute(
                "SELECT last_epoch_entry FROM index_metadata LIMIT 1"
            ).fetchone()
            start_id = (meta[0] if meta and meta[0] else None)
            if start_id:
                start_ts = self._entry_id_to_created_at(start_id)
                if start_ts:
                    return self._fetch_entries(
                        "SELECT * FROM entries WHERE created_at > ? "
                        "ORDER BY created_at ASC",
                        [start_ts],
                    )
            # Fallback: no epoch boundary found, return all entries
            return self._fetch_entries(
                "SELECT * FROM entries ORDER BY created_at ASC"
            )
        else:
            # Look up the created_at of the target epoch entry
            epoch_ts = self._entry_id_to_created_at(epoch_entry_id)
            if epoch_ts is None:
                return []

            # Find the previous epoch boundary (skill-triggered entry before this one)
            rows = self._conn.execute(
                "SELECT created_at FROM entries WHERE trigger = 'skill' "
                "AND created_at < ? AND created_at IS NOT NULL "
                "ORDER BY created_at DESC LIMIT 1",
                [epoch_ts],
            ).fetchall()
            if rows and rows[0][0]:
                start_ts = rows[0][0]
                return self._fetch_entries(
                    "SELECT * FROM entries WHERE created_at > ? AND created_at <= ? "
                    "ORDER BY created_at ASC",
                    [start_ts, epoch_ts],
                )
            else:
                return self._fetch_entries(
                    "SELECT * FROM entries WHERE created_at <= ? "
                    "ORDER BY created_at ASC",
                    [epoch_ts],
                )

    def get_entries_by_project(self, project: str) -> list[dict]:
        """All entries for a project, ordered by created_at DESC."""
        self.ensure_loaded()
        return self._fetch_entries(
            "SELECT * FROM entries WHERE project = ? ORDER BY created_at DESC NULLS LAST",
            [project],
        )

    def list_projects(self) -> list[str]:
        """Distinct project names."""
        self.ensure_loaded()
        assert self._conn is not None
        return [
            r[0]
            for r in self._conn.execute(
                "SELECT DISTINCT project FROM entries WHERE project != '' ORDER BY project"
            ).fetchall()
        ]

    # ------------------------------------------------------------------
    # Analytics methods — replicate sbs_self_improve.py logic
    # ------------------------------------------------------------------

    def _get_all_entries_sorted(self) -> list[dict]:
        """Get all entries sorted by created_at ASC (for session grouping etc)."""
        return self._fetch_entries(
            "SELECT * FROM entries ORDER BY created_at ASC NULLS LAST"
        )

    def analysis_summary(self) -> AnalysisSummary:
        """Replaces ``sbs_analysis_summary_impl``."""
        self.ensure_loaded()
        assert self._conn is not None

        total = self._conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        if total == 0:
            return AnalysisSummary(
                total_entries=0,
                date_range="",
                entries_by_trigger={},
                quality_metrics=None,
                most_common_tags=[],
                projects_summary={},
                findings=[],
            )

        # Date range
        date_range_row = self._conn.execute(
            "SELECT MIN(created_at), MAX(created_at) FROM entries"
        ).fetchone()
        first_ts = date_range_row[0].isoformat() if date_range_row[0] else ""
        last_ts = date_range_row[1].isoformat() if date_range_row[1] else ""
        date_range = f"{first_ts} to {last_ts}"

        # Entries by trigger
        trigger_rows = self._conn.execute(
            "SELECT trigger, COUNT(*) FROM entries GROUP BY trigger"
        ).fetchall()
        entries_by_trigger = {r[0]: r[1] for r in trigger_rows}

        # Tag frequency (combine tags + auto_tags using UNNEST)
        tag_rows = self._conn.execute("""
            SELECT tag, COUNT(*) as cnt FROM (
                SELECT UNNEST(tags) AS tag FROM entries
                UNION ALL
                SELECT UNNEST(auto_tags) AS tag FROM entries
            ) GROUP BY tag ORDER BY cnt DESC LIMIT 10
        """).fetchall()
        most_common_tags = [r[0] for r in tag_rows]

        # Projects summary
        proj_rows = self._conn.execute(
            "SELECT project, COUNT(*) FROM entries GROUP BY project"
        ).fetchall()
        projects_summary = {r[0]: r[1] for r in proj_rows}

        # Quality metrics
        quality_rows = self._conn.execute(
            "SELECT AVG(quality_overall), MIN(quality_overall), MAX(quality_overall), COUNT(quality_overall) "
            "FROM entries WHERE quality_overall IS NOT NULL"
        ).fetchone()
        quality_metrics = None
        if quality_rows and quality_rows[3] > 0:
            quality_metrics = {
                "average": quality_rows[0],
                "min": quality_rows[1],
                "max": quality_rows[2],
                "count": float(quality_rows[3]),
            }

        # Findings
        findings: list[AnalysisFinding] = []
        build_count = entries_by_trigger.get("build", 0)
        error_count = self._conn.execute("""
            SELECT COUNT(*) FROM entries WHERE
                list_contains(tags, 'error') OR list_contains(auto_tags, 'error')
                OR EXISTS (
                    SELECT 1 FROM (
                        SELECT UNNEST(tags) AS t FROM entries e2 WHERE e2.entry_id = entries.entry_id
                        UNION ALL
                        SELECT UNNEST(auto_tags) FROM entries e2 WHERE e2.entry_id = entries.entry_id
                    ) sub WHERE LOWER(sub.t) LIKE '%error%'
                )
        """).fetchone()[0]
        if build_count > 0 and error_count > build_count * 0.2:
            findings.append(AnalysisFinding(
                pillar="system_engineering",
                category="error_pattern",
                severity="medium",
                description=f"High error rate: {error_count} error entries out of {build_count} builds",
                recommendation="Investigate common error patterns and add safeguards",
                evidence=[],
            ))

        # Staleness finding
        if date_range_row[1]:
            last_dt = date_range_row[1]
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            now = datetime.now(last_dt.tzinfo)
            days_since = (now - last_dt).days
            if days_since > 7:
                findings.append(AnalysisFinding(
                    pillar="user_effectiveness",
                    category="workflow",
                    severity="low",
                    description=f"No archive entries in {days_since} days",
                    recommendation="Consider running a build to capture current state",
                    evidence=[],
                ))

        return AnalysisSummary(
            total_entries=total,
            date_range=date_range,
            entries_by_trigger=entries_by_trigger,
            quality_metrics=quality_metrics,
            most_common_tags=most_common_tags,
            projects_summary=projects_summary,
            findings=findings,
        )

    def entries_since_self_improve(self) -> SelfImproveEntries:
        """Replaces ``sbs_entries_since_self_improve_impl``."""
        self.ensure_loaded()
        assert self._conn is not None

        total = self._conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        if total == 0:
            return SelfImproveEntries(
                last_self_improve_entry=None,
                last_self_improve_timestamp=None,
                entries_since=[],
                count_by_trigger={},
                count=0,
            )

        # Use Python session grouping for correctness (matches original exactly)
        all_entries = self._get_all_entries_sorted()
        sessions = _group_dicts_by_skill_session(all_entries)

        last_si_entry: Optional[str] = None
        last_si_ts: Optional[str] = None
        for session in reversed(sessions):
            if session["skill"] == "self-improve" and session["completed"]:
                last_si_entry = session["last_entry_id"]
                last_si_ts = session["end_time"]
                break

        # Get entries since
        if last_si_entry:
            si_ts = self._entry_id_to_created_at(last_si_entry)
            if si_ts:
                since_entries = self._fetch_entries(
                    "SELECT * FROM entries WHERE created_at > ? "
                    "ORDER BY created_at DESC NULLS LAST",
                    [si_ts],
                )
            else:
                since_entries = self._fetch_entries(
                    "SELECT * FROM entries ORDER BY created_at DESC NULLS LAST"
                )
        else:
            since_entries = self._fetch_entries(
                "SELECT * FROM entries ORDER BY created_at DESC NULLS LAST"
            )

        # Filter out retroactive
        entries_since: list[SelfImproveEntrySummary] = []
        trigger_counts: Counter = Counter()
        for e in since_entries:
            all_tags = (e.get("tags") or []) + (e.get("auto_tags") or [])
            if "retroactive" in all_tags:
                continue
            quality_score = e.get("quality_overall")
            entries_since.append(SelfImproveEntrySummary(
                entry_id=e["entry_id"],
                created_at=e.get("created_at", ""),
                project=e.get("project", ""),
                trigger=e.get("trigger", ""),
                notes=e.get("notes", ""),
                tags=all_tags,
                quality_score=quality_score,
            ))
            trigger_counts[e.get("trigger", "")] += 1

        return SelfImproveEntries(
            last_self_improve_entry=last_si_entry,
            last_self_improve_timestamp=last_si_ts,
            entries_since=entries_since,
            count_by_trigger=dict(trigger_counts),
            count=len(entries_since),
        )

    def compute_self_improve_level(self, multiplier: int = 4) -> int:
        """Compute the introspection level based on geometric 4x decay.

        Counts entries tagged with level:L0, level:L1, etc.
        If there are >= multiplier L0 entries since the last L1, level is at least 1.
        If there are >= multiplier L1 entries since the last L2, level is at least 2.
        And so on.

        Returns the highest level where the entry count >= multiplier.
        Level 0 is always the minimum (every task gets at least L0).
        """
        self.ensure_loaded()
        assert self._conn is not None

        level = 0
        current_level = 0

        while True:
            level_tag = f"level:L{current_level}"
            next_level_tag = f"level:L{current_level + 1}"

            # Find the most recent L(N+1) entry
            last_higher = self._conn.execute(
                """
                SELECT MAX(created_at) FROM entries
                WHERE list_contains(tags, ?) OR list_contains(auto_tags, ?)
                """,
                [next_level_tag, next_level_tag],
            ).fetchone()[0]

            # Count L(N) entries since that timestamp
            if last_higher:
                count = self._conn.execute(
                    """
                    SELECT COUNT(*) FROM entries
                    WHERE (list_contains(tags, ?) OR list_contains(auto_tags, ?))
                    AND created_at > ?
                    """,
                    [level_tag, level_tag, last_higher],
                ).fetchone()[0]
            else:
                # No higher-level entry exists yet -- count all entries at this level
                count = self._conn.execute(
                    """
                    SELECT COUNT(*) FROM entries
                    WHERE list_contains(tags, ?) OR list_contains(auto_tags, ?)
                    """,
                    [level_tag, level_tag],
                ).fetchone()[0]

            if count >= multiplier:
                level = current_level + 1
                current_level += 1
            else:
                break

        return level

    def get_self_improve_findings(self, level: int) -> list[str]:
        """Get paths to finding documents at a given level.

        Looks for files matching dev/storage/archive/self-improve/L{level}-*.md
        """
        findings_dir = self._archive_dir.parent / "archive" / "self-improve"
        if not findings_dir.exists():
            return []

        pattern = f"L{level}-*.md"
        return sorted(str(p) for p in findings_dir.glob(pattern))

    def get_improvement_captures(self, since_entry_id: Optional[str] = None) -> list[dict]:
        """Get improvement observations (IO captures) since a given entry.

        IO captures are entries with trigger='improvement' or tags containing 'improvement'.
        """
        self.ensure_loaded()
        assert self._conn is not None

        improvement_filter = (
            "(trigger = 'improvement' "
            "OR list_contains(tags, 'improvement') "
            "OR list_contains(auto_tags, 'improvement'))"
        )

        if since_entry_id:
            since_dt = self._resolve_since_to_datetime(since_entry_id)
            if since_dt:
                return self._fetch_entries(
                    f"SELECT * FROM entries WHERE {improvement_filter} "
                    "AND created_at > ? ORDER BY created_at DESC",
                    [since_dt],
                )

        return self._fetch_entries(
            f"SELECT * FROM entries WHERE {improvement_filter} "
            "ORDER BY created_at DESC",
        )

    def successful_sessions(self) -> SuccessPatterns:
        """Replaces ``sbs_successful_sessions_impl``."""
        self.ensure_loaded()
        assert self._conn is not None

        total = self._conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        if total == 0:
            return SuccessPatterns()

        patterns: list[SuccessPattern] = []

        # Pattern 1: Completed tasks
        completed = self._conn.execute(
            "SELECT entry_id FROM entries WHERE gs_skill = 'task' AND state_transition = 'phase_end'"
        ).fetchall()
        if completed:
            patterns.append(SuccessPattern(
                pattern_type="completed_task",
                description=f"{len(completed)} task(s) completed full lifecycle (alignment->finalization)",
                evidence=[r[0] for r in completed[:10]],
                frequency=len(completed),
            ))

        # Pattern 2: Clean execution (skill entries with <=3 auto_tags)
        clean = self._conn.execute(
            "SELECT entry_id FROM entries WHERE trigger = 'skill' AND len(auto_tags) <= 3"
        ).fetchall()
        if clean:
            patterns.append(SuccessPattern(
                pattern_type="clean_execution",
                description=f"{len(clean)} session(s) with minimal auto-tags (<=3), indicating clean execution",
                evidence=[r[0] for r in clean[:10]],
                frequency=len(clean),
            ))

        # Pattern 3: High quality scores
        high_q = self._conn.execute(
            "SELECT entry_id FROM entries WHERE quality_overall >= 0.9"
        ).fetchall()
        if high_q:
            patterns.append(SuccessPattern(
                pattern_type="high_quality",
                description=f"{len(high_q)} entry/entries with quality score >= 0.9",
                evidence=[r[0] for r in high_q[:10]],
                frequency=len(high_q),
            ))

        return SuccessPatterns(
            patterns=patterns,
            total_sessions_analyzed=total,
            summary=f"Analyzed {total} entries, found {len(patterns)} success pattern types",
        )

    def comparative_analysis(self) -> ComparativeAnalysis:
        """Replaces ``sbs_comparative_analysis_impl``."""
        self.ensure_loaded()
        assert self._conn is not None

        total = self._conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        if total == 0:
            return ComparativeAnalysis()

        planning_count = self._conn.execute(
            "SELECT COUNT(*) FROM entries WHERE gs_skill = 'task' AND state_transition = 'phase_start' AND gs_substate = 'planning'"
        ).fetchone()[0]

        execution_count = self._conn.execute(
            "SELECT COUNT(*) FROM entries WHERE gs_skill = 'task' AND state_transition = 'phase_start' AND gs_substate = 'execution'"
        ).fetchone()[0]

        approved_count = execution_count
        rejected_count = max(0, planning_count - approved_count)

        features: list[DiscriminatingFeature] = []
        if planning_count > 0:
            features.append(DiscriminatingFeature(
                feature="plan_approval_rate",
                approved_value=f"{approved_count}/{planning_count} ({100 * approved_count // max(planning_count, 1)}%)",
                rejected_value=f"{rejected_count}/{planning_count}",
                confidence="medium",
            ))

        # Tag patterns in successful entries
        all_entries = self._get_all_entries_sorted()
        successful_tags: dict[str, int] = {}
        all_tags_count: dict[str, int] = {}
        for e in all_entries:
            tags = (e.get("tags") or []) + (e.get("auto_tags") or [])
            gs = e.get("global_state") or {}
            is_successful = (
                gs.get("skill") == "task"
                and (e.get("state_transition") or "") == "phase_end"
            )
            for tag in tags:
                all_tags_count[tag] = all_tags_count.get(tag, 0) + 1
                if is_successful:
                    successful_tags[tag] = successful_tags.get(tag, 0) + 1

        for tag, count in successful_tags.items():
            tag_total = all_tags_count.get(tag, 1)
            if count > 1 and count / tag_total > 0.3:
                features.append(DiscriminatingFeature(
                    feature=f"tag:{tag}",
                    approved_value=f"present in {count} successful entries",
                    rejected_value=f"present in {tag_total} total entries",
                    confidence="low",
                ))

        return ComparativeAnalysis(
            approved_count=approved_count,
            rejected_count=rejected_count,
            features=features[:10],
            summary=f"Analyzed {planning_count} planning phases: {approved_count} reached execution, {rejected_count} did not",
        )

    def system_health(self) -> SystemHealthReport:
        """Replaces ``sbs_system_health_impl``."""
        self.ensure_loaded()
        assert self._conn is not None

        total = self._conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        if total == 0:
            return SystemHealthReport()

        build_metrics: list[SystemHealthMetric] = []
        findings: list[AnalysisFinding] = []

        # Build count
        build_count = self._conn.execute(
            "SELECT COUNT(*) FROM entries WHERE trigger = 'build'"
        ).fetchone()[0]
        if build_count:
            build_metrics.append(SystemHealthMetric(
                metric="total_builds",
                value=float(build_count),
                trend="stable",
                details=f"{build_count} build entries in archive",
            ))

        # Quality score coverage
        with_scores = self._conn.execute(
            "SELECT COUNT(*) FROM entries WHERE quality_scores IS NOT NULL"
        ).fetchone()[0]
        score_coverage = with_scores / max(total, 1)
        build_metrics.append(SystemHealthMetric(
            metric="quality_score_coverage",
            value=round(score_coverage, 3),
            trend="degrading" if score_coverage < 0.1 else "stable",
            details=f"{with_scores}/{total} entries have quality scores",
        ))

        if score_coverage < 0.1:
            findings.append(AnalysisFinding(
                pillar="system_engineering",
                category="data_quality",
                severity="high",
                description=f"Only {score_coverage * 100:.1f}% of entries have quality scores",
                recommendation="Ensure validators run automatically after builds (Issue #15)",
                evidence=[],
            ))

        # Noisy tags
        skill_count = self._conn.execute(
            "SELECT COUNT(*) FROM entries WHERE trigger = 'skill'"
        ).fetchone()[0]
        if skill_count > 0:
            noisy_rows = self._conn.execute("""
                SELECT tag, COUNT(*) as cnt FROM (
                    SELECT UNNEST(auto_tags) AS tag FROM entries WHERE trigger = 'skill'
                ) GROUP BY tag HAVING cnt > ? * 0.8
            """, [skill_count]).fetchall()
            noisy_tags = [r[0] for r in noisy_rows]
            if noisy_tags:
                findings.append(AnalysisFinding(
                    pillar="system_engineering",
                    category="tagging",
                    severity="medium",
                    description=f"Tags firing on >80% of skill entries (low signal): {', '.join(noisy_tags)}",
                    recommendation="Review tag thresholds to ensure they flag anomalies, not normal behavior",
                    evidence=[],
                ))
        else:
            noisy_tags = []

        archive_friction = {
            "total_entries": total,
            "skill_entries": skill_count,
            "build_entries": build_count,
            "noisy_tags": noisy_tags,
        }

        overall = "healthy"
        if len(findings) >= 2:
            overall = "warning"
        if len(findings) >= 4:
            overall = "degraded"

        return SystemHealthReport(
            build_metrics=build_metrics,
            tool_error_rates={},
            archive_friction=archive_friction,
            findings=findings,
            overall_health=overall,
        )

    def user_patterns(self) -> UserPatternAnalysis:
        """Replaces ``sbs_user_patterns_impl``."""
        self.ensure_loaded()
        assert self._conn is not None

        total = self._conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        if total == 0:
            return UserPatternAnalysis()

        all_entries = self._get_all_entries_sorted()
        effective_patterns: list[str] = []
        findings: list[AnalysisFinding] = []

        # Task phase tracking
        task_phases: dict[str, list[str]] = {}
        current_task_id: Optional[str] = None
        for e in all_entries:
            gs = e.get("global_state") or {}
            if gs.get("skill") == "task":
                st = e.get("state_transition") or ""
                substate = gs.get("substate", "")
                if substate == "alignment" and st == "phase_start":
                    current_task_id = e["entry_id"]
                    task_phases[current_task_id] = []
                if current_task_id:
                    task_phases[current_task_id].append(substate)

        efficient_tasks = 0
        total_tasks = len(task_phases)
        for phases in task_phases.values():
            if phases.count("alignment") <= 2:
                efficient_tasks += 1

        if total_tasks > 0:
            rate = efficient_tasks / total_tasks
            effective_patterns.append(
                f"Quick alignment (<=2 alignment entries): {efficient_tasks}/{total_tasks} tasks ({rate * 100:.0f}%)"
            )
            if rate > 0.7:
                findings.append(AnalysisFinding(
                    pillar="user_effectiveness",
                    category="alignment_efficiency",
                    severity="low",
                    description=f"Most tasks ({rate * 100:.0f}%) achieve alignment quickly",
                    recommendation="Current communication pattern is effective; maintain clear upfront context",
                    evidence=list(task_phases.keys())[:5],
                ))

        # Issue-driven vs freeform
        task_entries = [e for e in all_entries if (e.get("global_state") or {}).get("skill") == "task"]
        issue_driven = [e for e in task_entries if e.get("issue_refs")]
        freeform = [e for e in task_entries if not e.get("issue_refs")]
        if issue_driven or freeform:
            effective_patterns.append(
                f"Issue-driven tasks: {len(issue_driven)}, Freeform tasks: {len(freeform)}"
            )

        return UserPatternAnalysis(
            total_sessions_analyzed=total,
            effective_patterns=effective_patterns,
            findings=findings,
            summary=f"Analyzed {total_tasks} task sessions across {total} archive entries",
        )

    def skill_stats(self, as_findings: bool = False) -> SkillStatsResult:
        """Replaces ``sbs_skill_stats_impl``."""
        self.ensure_loaded()
        all_entries = self._get_all_entries_sorted()
        if not all_entries:
            return SkillStatsResult(summary="No archive entries found.")

        sessions = _group_dicts_by_skill_session(all_entries)
        if not sessions:
            return SkillStatsResult(total_sessions=0, summary="No skill sessions found in archive.")

        by_skill: dict[str, list[dict]] = {}
        for s in sessions:
            by_skill.setdefault(s["skill"], []).append(s)

        skills: dict[str, SkillStatEntry] = {}
        for skill_name, skill_sessions in by_skill.items():
            invocations = len(skill_sessions)
            completions = sum(1 for s in skill_sessions if s["completed"])
            rate = completions / invocations if invocations > 0 else 0.0

            durations = [_compute_dict_session_duration(s) for s in skill_sessions]
            valid_durations = [d for d in durations if d is not None]
            avg_duration = sum(valid_durations) / len(valid_durations) if valid_durations else None

            total_entry_count = sum(len(s["entries"]) for s in skill_sessions)
            avg_entries = total_entry_count / invocations if invocations > 0 else 0.0

            failure_substates: Counter = Counter()
            failure_tags: Counter = Counter()
            for s in skill_sessions:
                if not s["completed"] and s["entries"]:
                    sub = s["last_substate"]
                    if sub:
                        failure_substates[sub] += 1
                    last_e = s["entries"][-1]
                    for tag in (last_e.get("tags") or []) + (last_e.get("auto_tags") or []):
                        failure_tags[tag] += 1

            skills[skill_name] = SkillStatEntry(
                skill=skill_name,
                invocation_count=invocations,
                completion_count=completions,
                completion_rate=round(rate, 3),
                avg_duration_seconds=round(avg_duration, 1) if avg_duration is not None else None,
                avg_entries_per_session=round(avg_entries, 1),
                common_failure_substates=[s for s, _ in failure_substates.most_common(3)],
                common_failure_tags=[t for t, _ in failure_tags.most_common(5)],
            )

        findings_list: list[AnalysisFinding] = []
        if as_findings:
            for sn, stat in skills.items():
                if stat.completion_rate < 0.5 and stat.invocation_count >= 2:
                    findings_list.append(AnalysisFinding(
                        pillar="claude_execution",
                        category="skill_lifecycle",
                        severity="medium",
                        description=f"Skill '{sn}' has low completion rate: {stat.completion_rate:.0%} ({stat.completion_count}/{stat.invocation_count})",
                        recommendation=f"Investigate common failure substates: {stat.common_failure_substates}",
                        evidence=[],
                    ))

        return SkillStatsResult(
            skills=skills,
            total_sessions=len(sessions),
            findings=findings_list,
            summary=f"Analyzed {len(sessions)} sessions across {len(skills)} skill types.",
        )

    def phase_transition_health(self, as_findings: bool = False) -> PhaseTransitionHealthResult:
        """Replaces ``sbs_phase_transition_health_impl``."""
        self.ensure_loaded()
        all_entries = self._get_all_entries_sorted()
        if not all_entries:
            return PhaseTransitionHealthResult(summary="No archive entries found.")

        sessions = _group_dicts_by_skill_session(all_entries)
        if not sessions:
            return PhaseTransitionHealthResult(summary="No skill sessions found in archive.")

        by_skill: dict[str, list[dict]] = {}
        for s in sessions:
            by_skill.setdefault(s["skill"], []).append(s)

        reports: list[PhaseTransitionReport] = []
        for skill_name, skill_sessions in by_skill.items():
            expected = SKILL_PHASE_ORDERS.get(skill_name, [])
            total_backward = 0
            all_backward_details: list[dict[str, str]] = []
            all_skipped: dict[str, int] = {}
            phase_times: dict[str, list[float]] = {}

            for session in skill_sessions:
                backward = _detect_backward_transitions_dict(session, expected)
                total_backward += len(backward)
                for eid, from_p, to_p in backward:
                    all_backward_details.append({"entry_id": eid, "from": from_p, "to": to_p})

                skipped = _detect_skipped_phases_dict(session, expected)
                for phase in skipped:
                    all_skipped[phase] = all_skipped.get(phase, 0) + 1

                # Time-in-phase
                prev_phase = None
                prev_time = None
                for entry in session["entries"]:
                    gs = entry.get("global_state") or {}
                    substate = gs.get("substate", "")
                    if not substate:
                        continue
                    try:
                        ca = entry.get("created_at", "")
                        if isinstance(ca, datetime):
                            entry_time = ca
                        else:
                            entry_time = datetime.fromisoformat(ca.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        continue
                    if prev_phase and prev_phase != substate and prev_time:
                        delta = (entry_time - prev_time).total_seconds()
                        phase_times.setdefault(prev_phase, []).append(delta)
                    if substate != prev_phase:
                        prev_time = entry_time
                    prev_phase = substate

            avg_time: dict[str, float] = {}
            for phase, times in phase_times.items():
                if times:
                    avg_time[phase] = round(sum(times) / len(times), 1)

            reports.append(PhaseTransitionReport(
                skill=skill_name,
                expected_sequence=expected,
                total_sessions=len(skill_sessions),
                backward_transitions=total_backward,
                backward_details=all_backward_details[:20],
                skipped_phases=all_skipped,
                time_in_phase=avg_time,
            ))

        findings_list: list[AnalysisFinding] = []
        if as_findings:
            for report in reports:
                if report.total_sessions > 0 and report.backward_transitions > 0:
                    rate = report.backward_transitions / report.total_sessions
                    if rate > 0.3:
                        findings_list.append(AnalysisFinding(
                            pillar="alignment_patterns",
                            category="phase_transition",
                            severity="medium",
                            description=f"Skill '{report.skill}' has high backward transition rate: {rate:.0%}",
                            recommendation="Investigate causes of phase regressions",
                            evidence=[d["entry_id"] for d in report.backward_details[:5]],
                        ))

        return PhaseTransitionHealthResult(
            reports=reports,
            findings=findings_list,
            summary=f"Analyzed {len(sessions)} sessions across {len(reports)} skill types.",
        )

    def interruption_analysis(self, as_findings: bool = False) -> InterruptionAnalysisResult:
        """Replaces ``sbs_interruption_analysis_impl``."""
        self.ensure_loaded()
        all_entries = self._get_all_entries_sorted()
        if not all_entries:
            return InterruptionAnalysisResult(summary="No archive entries found.")

        sessions = _group_dicts_by_skill_session(all_entries)
        if not sessions:
            return InterruptionAnalysisResult(summary="No skill sessions found in archive.")

        events: list[InterruptionEvent] = []
        sessions_with_interruptions = 0

        for session in sessions:
            session_had_interruption = False
            expected = SKILL_PHASE_ORDERS.get(session["skill"], [])

            # 1. Backward transitions
            backward = _detect_backward_transitions_dict(session, expected)
            for eid, from_p, to_p in backward:
                events.append(InterruptionEvent(
                    entry_id=eid,
                    skill=session["skill"],
                    event_type="backward_transition",
                    from_phase=from_p,
                    to_phase=to_p,
                    context=f"Phase went backward from '{from_p}' to '{to_p}'",
                ))
                session_had_interruption = True

            # 2. Retries
            substate_counts: Counter = Counter()
            for entry in session["entries"]:
                gs = entry.get("global_state") or {}
                sub = gs.get("substate", "")
                if sub:
                    substate_counts[sub] += 1
            for sub, count in substate_counts.items():
                if count > 2:
                    events.append(InterruptionEvent(
                        entry_id=session["first_entry_id"],
                        skill=session["skill"],
                        event_type="retry",
                        from_phase=sub,
                        to_phase=sub,
                        context=f"Substate '{sub}' appeared {count} times (possible retry pattern)",
                    ))
                    session_had_interruption = True

            # 3. Correction keywords
            for entry in session["entries"]:
                notes = (entry.get("notes") or "").lower()
                if notes:
                    for keyword in CORRECTION_KEYWORDS:
                        if keyword in notes:
                            events.append(InterruptionEvent(
                                entry_id=entry["entry_id"],
                                skill=session["skill"],
                                event_type="correction_keyword",
                                context=f"Correction keyword '{keyword}' found in notes",
                            ))
                            session_had_interruption = True
                            break

            # 4. High churn
            num_phases = max(len(session["phases_visited"]), 1)
            n_entries = len(session["entries"])
            if n_entries > 2 * num_phases and n_entries > 4:
                events.append(InterruptionEvent(
                    entry_id=session["first_entry_id"],
                    skill=session["skill"],
                    event_type="high_entry_count",
                    context=f"{n_entries} entries for {num_phases} phases (ratio: {n_entries / num_phases:.1f}x)",
                ))
                session_had_interruption = True

            if session_had_interruption:
                sessions_with_interruptions += 1

        findings_list: list[AnalysisFinding] = []
        if as_findings and sessions:
            interrupt_rate = sessions_with_interruptions / len(sessions)
            if interrupt_rate > 0.3:
                findings_list.append(AnalysisFinding(
                    pillar="user_effectiveness",
                    category="interruption",
                    severity="medium",
                    description=f"{sessions_with_interruptions}/{len(sessions)} sessions had interruptions ({interrupt_rate:.0%})",
                    recommendation="Review common interruption types and address root causes",
                    evidence=[e.entry_id for e in events[:5]],
                ))

        return InterruptionAnalysisResult(
            events=events,
            total_sessions_analyzed=len(sessions),
            sessions_with_interruptions=sessions_with_interruptions,
            findings=findings_list,
            summary=f"Found {len(events)} interruption events across {len(sessions)} sessions ({sessions_with_interruptions} had interruptions).",
        )

    def gate_failures(self, as_findings: bool = False) -> GateFailureReport:
        """Replaces ``sbs_gate_failures_impl``."""
        self.ensure_loaded()
        assert self._conn is not None

        total = self._conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        if total == 0:
            return GateFailureReport(summary="No archive entries found.")

        # Get all entries and sessions for override detection
        all_entries = self._get_all_entries_sorted()
        sessions = _group_dicts_by_skill_session(all_entries)

        gate_entries = [e for e in all_entries if e.get("gate_validation") is not None]
        if not gate_entries:
            return GateFailureReport(
                total_gate_checks=0,
                summary="No gate validation entries found in archive.",
            )

        total_checks = len(gate_entries)
        failures: list[GateFailureEntry] = []
        override_count = 0

        # Map entry_ids to sessions
        session_map: dict[str, dict] = {}
        for s in sessions:
            for e in s["entries"]:
                session_map[e["entry_id"]] = s

        finding_counts: Counter = Counter()

        for entry in gate_entries:
            gv = entry.get("gate_validation") or {}
            if isinstance(gv, str):
                try:
                    gv = json.loads(gv)
                except (json.JSONDecodeError, TypeError):
                    continue
            passed = gv.get("passed", True)
            if not passed:
                gs = entry.get("global_state") or {}
                gate_findings_list = gv.get("findings", [])
                for f in gate_findings_list:
                    finding_counts[f] += 1

                # Override detection
                continued = False
                session = session_map.get(entry["entry_id"])
                if session:
                    current_substate = gs.get("substate", "")
                    expected = SKILL_PHASE_ORDERS.get(gs.get("skill", ""), [])
                    found_entry = False
                    for se in session["entries"]:
                        if se["entry_id"] == entry["entry_id"]:
                            found_entry = True
                            continue
                        if found_entry:
                            se_gs = se.get("global_state") or {}
                            se_sub = se_gs.get("substate", "")
                            if se_sub and se_sub != current_substate:
                                try:
                                    if expected.index(se_sub) > expected.index(current_substate):
                                        continued = True
                                        break
                                except ValueError:
                                    pass

                if continued:
                    override_count += 1

                failures.append(GateFailureEntry(
                    entry_id=entry["entry_id"],
                    skill=gs.get("skill"),
                    substate=gs.get("substate"),
                    gate_findings=gate_findings_list,
                    continued=continued,
                ))

        failure_rate = len(failures) / total_checks if total_checks > 0 else 0.0
        common_findings_list = [f for f, _ in finding_counts.most_common(10)]

        findings_list: list[AnalysisFinding] = []
        if as_findings:
            if failure_rate > 0.3:
                findings_list.append(AnalysisFinding(
                    pillar="claude_execution",
                    category="gate_validation",
                    severity="high",
                    description=f"High gate failure rate: {failure_rate:.0%} ({len(failures)}/{total_checks})",
                    recommendation="Review common gate findings and address recurring issues",
                    evidence=[f.entry_id for f in failures[:5]],
                ))
            if override_count > 0:
                findings_list.append(AnalysisFinding(
                    pillar="alignment_patterns",
                    category="gate_override",
                    severity="medium",
                    description=f"{override_count} gate failures were overridden (task continued despite failure)",
                    recommendation="Evaluate whether gate checks are too strict or if overrides indicate quality risks",
                    evidence=[f.entry_id for f in failures if f.continued][:5],
                ))

        return GateFailureReport(
            total_gate_checks=total_checks,
            total_failures=len(failures),
            failure_rate=round(failure_rate, 3),
            failures=failures,
            override_count=override_count,
            common_findings=common_findings_list,
            findings=findings_list,
            summary=f"{len(failures)} gate failures out of {total_checks} checks ({failure_rate:.0%}). {override_count} overrides.",
        )

    def tag_effectiveness(self, as_findings: bool = False) -> TagEffectivenessResult:
        """Replaces ``sbs_tag_effectiveness_impl``."""
        self.ensure_loaded()
        all_entries = self._get_all_entries_sorted()
        if not all_entries:
            return TagEffectivenessResult(summary="No archive entries found.")

        total_entries = len(all_entries)
        if total_entries == 0:
            return TagEffectivenessResult(summary="No entries to analyze.")

        sessions = _group_dicts_by_skill_session(all_entries)

        # Tag frequency
        tag_freq: Counter = Counter()
        for e in all_entries:
            for tag in e.get("auto_tags") or []:
                tag_freq[tag] += 1

        if not tag_freq:
            return TagEffectivenessResult(summary="No auto-tags found in archive entries.")

        # Problem entry sets
        gate_failure_ids: set[str] = set()
        for e in all_entries:
            gv = e.get("gate_validation") or {}
            if isinstance(gv, str):
                try:
                    gv = json.loads(gv)
                except (json.JSONDecodeError, TypeError):
                    continue
            if gv and not gv.get("passed", True):
                gate_failure_ids.add(e["entry_id"])

        backward_ids: set[str] = set()
        for session in sessions:
            expected = SKILL_PHASE_ORDERS.get(session["skill"], [])
            backward = _detect_backward_transitions_dict(session, expected)
            for eid, _, _ in backward:
                backward_ids.add(eid)

        error_note_ids: set[str] = set()
        error_keywords = ["error", "fail", "bug", "broken", "crash", "exception"]
        for e in all_entries:
            notes = (e.get("notes") or "").lower()
            if any(kw in notes for kw in error_keywords):
                error_note_ids.add(e["entry_id"])

        # Per-tag analysis
        tag_entries: list[TagEffectivenessEntry] = []
        noisy_tags: list[str] = []
        signal_tags: list[str] = []
        legacy_count = 0

        for tag, freq in tag_freq.most_common():
            freq_pct = freq / total_entries
            era = "v2" if ":" in tag else "legacy"
            if era == "legacy":
                legacy_count += 1

            co_gate = co_backward = co_error = 0
            for e in all_entries:
                if tag in (e.get("auto_tags") or []):
                    if e["entry_id"] in gate_failure_ids:
                        co_gate += 1
                    if e["entry_id"] in backward_ids:
                        co_backward += 1
                    if e["entry_id"] in error_note_ids:
                        co_error += 1

            signal_score = (co_gate + co_backward + co_error) / (freq * 3) if freq > 0 else 0.0
            signal_score = min(signal_score, 1.0)

            if era == "legacy":
                classification = "legacy"
            elif freq_pct > 0.8:
                classification = "noise"
                noisy_tags.append(tag)
            elif signal_score > 0.3:
                classification = "signal"
                signal_tags.append(tag)
            else:
                classification = "neutral"

            tag_entries.append(TagEffectivenessEntry(
                tag=tag,
                tag_era=era,
                frequency=freq,
                frequency_pct=round(freq_pct, 3),
                co_occurs_with_gate_failure=co_gate,
                co_occurs_with_backward_transition=co_backward,
                co_occurs_with_error_notes=co_error,
                signal_score=round(signal_score, 3),
                classification=classification,
            ))

        findings_list: list[AnalysisFinding] = []
        if as_findings:
            if noisy_tags:
                findings_list.append(AnalysisFinding(
                    pillar="system_engineering",
                    category="tagging",
                    severity="medium",
                    description=f"Noisy v2.0 tags (>80% frequency, low signal): {', '.join(noisy_tags)}",
                    recommendation="Consider raising thresholds or removing these auto-tags",
                    evidence=[],
                ))
            if signal_tags:
                findings_list.append(AnalysisFinding(
                    pillar="system_engineering",
                    category="tagging",
                    severity="low",
                    description=f"Signal v2.0 tags (correlated with problems): {', '.join(signal_tags)}",
                    recommendation="These tags are effective problem indicators; preserve and leverage them",
                    evidence=[],
                ))
            if legacy_count > 0:
                findings_list.append(AnalysisFinding(
                    pillar="system_engineering",
                    category="tagging",
                    severity="info",
                    description=f"{legacy_count} legacy (pre-v2.0) tags found in historical entries",
                    recommendation="Legacy tags are from pre-v2.0 entries and cannot be changed; they are excluded from noise/signal analysis",
                    evidence=[],
                ))

        return TagEffectivenessResult(
            tags=tag_entries,
            noisy_tags=noisy_tags,
            signal_tags=signal_tags,
            findings=findings_list,
            summary=f"Analyzed {len(tag_freq)} auto-tags ({legacy_count} legacy, {len(tag_freq) - legacy_count} v2.0): {len(noisy_tags)} noisy, {len(signal_tags)} signal.",
        )

    def question_analysis(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        skill: Optional[str] = None,
        limit: int = 50,
    ) -> QuestionAnalysisResult:
        """Replaces ``sbs_question_analysis_impl``.

        Delegates to the same extractor functions for JSONL parsing, but
        correlates with skill intervals from DuckDB.
        """
        self.ensure_loaded()
        self._ensure_questions_loaded()

        # For question analysis, we still need the original extractor approach
        # because the questions table stores denormalized rows per question,
        # but the original API returns grouped interactions.
        # Delegate to the Python extractor for now; correlation uses DuckDB intervals.
        try:
            from sbs.archive.extractor import get_sbs_project_dirs, extract_ask_user_questions
        except ImportError:
            return QuestionAnalysisResult(interactions=[], total_found=0, sessions_searched=0)

        session_files = []
        for project_dir in get_sbs_project_dirs():
            for session_file in project_dir.glob("*.jsonl"):
                session_files.append((session_file.stem, session_file))

        since_dt = _parse_ts(since) if since else None
        until_dt = _parse_ts(until) if until else None

        all_interactions: list[QuestionInteraction] = []
        sessions_searched = 0

        for session_id, session_path in session_files:
            sessions_searched += 1
            raw_interactions = extract_ask_user_questions(session_path)

            for raw in raw_interactions:
                ts = raw.get("timestamp")
                if since_dt and ts:
                    try:
                        ts_dt = _parse_ts(ts)
                        if ts_dt and ts_dt < since_dt:
                            continue
                    except (ValueError, TypeError):
                        pass
                if until_dt and ts:
                    try:
                        ts_dt = _parse_ts(ts)
                        if ts_dt and ts_dt > until_dt:
                            continue
                    except (ValueError, TypeError):
                        pass

                active_skill, active_substate = self._correlate_question_with_skill(ts)
                if skill and active_skill != skill:
                    continue

                interaction = QuestionInteraction(
                    session_id=session_id,
                    timestamp=ts,
                    questions=raw.get("questions", []),
                    answers=raw.get("answers", {}),
                    context_before=raw.get("context_before"),
                    skill=active_skill,
                    substate=active_substate,
                )
                all_interactions.append(interaction)

        all_interactions.sort(key=lambda i: i.timestamp or "", reverse=True)
        limited = all_interactions[:limit]

        return QuestionAnalysisResult(
            interactions=limited,
            total_found=len(all_interactions),
            sessions_searched=sessions_searched,
        )

    def question_stats(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> QuestionStatsResult:
        """Replaces ``sbs_question_stats_impl``."""
        self.ensure_loaded()

        try:
            from sbs.archive.extractor import get_sbs_project_dirs, extract_ask_user_questions
        except ImportError:
            return QuestionStatsResult()

        session_files = []
        for project_dir in get_sbs_project_dirs():
            for session_file in project_dir.glob("*.jsonl"):
                session_files.append((session_file.stem, session_file))

        since_dt = _parse_ts(since) if since else None
        until_dt = _parse_ts(until) if until else None

        total_questions = 0
        skill_counts: Counter = Counter()
        header_counts: Counter = Counter()
        option_counts: Counter = Counter()
        multi_select_count = 0
        sessions_with = 0
        sessions_without = 0

        for session_id, session_path in session_files:
            raw_interactions = extract_ask_user_questions(session_path)
            if raw_interactions:
                sessions_with += 1
            else:
                sessions_without += 1

            for raw in raw_interactions:
                ts = raw.get("timestamp")
                if since_dt and ts:
                    try:
                        ts_dt = _parse_ts(ts)
                        if ts_dt and ts_dt < since_dt:
                            continue
                    except (ValueError, TypeError):
                        pass
                if until_dt and ts:
                    try:
                        ts_dt = _parse_ts(ts)
                        if ts_dt and ts_dt > until_dt:
                            continue
                    except (ValueError, TypeError):
                        pass

                total_questions += 1
                active_skill, _ = self._correlate_question_with_skill(ts)
                if active_skill:
                    skill_counts[active_skill] += 1
                else:
                    skill_counts["none"] += 1

                for q in raw.get("questions", []):
                    header = q.get("header", "")
                    if header:
                        header_counts[header] += 1
                    if q.get("multiSelect", False):
                        multi_select_count += 1

                for question_text, answer in raw.get("answers", {}).items():
                    option_counts[answer] += 1

        most_common = [
            {"option": opt, "count": cnt}
            for opt, cnt in option_counts.most_common(15)
        ]

        return QuestionStatsResult(
            total_questions=total_questions,
            questions_by_skill=dict(skill_counts),
            questions_by_header=dict(header_counts),
            most_common_options_selected=most_common,
            multi_select_usage=multi_select_count,
            sessions_with_questions=sessions_with,
            sessions_without_questions=sessions_without,
        )

    def _correlate_question_with_skill(self, timestamp: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """Find active skill/substate at a given timestamp.

        Uses the most recent archive entry with a skill before or at the given
        timestamp. This approach handles gaps between substates correctly,
        unlike the skill_intervals view which only covers exact entry times.
        """
        if not timestamp:
            return None, None
        assert self._conn is not None
        try:
            ts = _parse_ts(timestamp)
            if ts is None:
                return None, None
        except (ValueError, TypeError):
            return None, None

        # Archive entries are stored as naive UTC timestamps. Strip timezone
        # from the question timestamp to ensure correct comparison in DuckDB.
        # Without this, DuckDB treats naive timestamps as local time, causing
        # a timezone offset mismatch.
        if ts.tzinfo is not None:
            ts = ts.replace(tzinfo=None)

        # Find the most recent entry with a skill that was recorded before or
        # at this timestamp. This gives us the skill/substate that was active.
        row = self._conn.execute("""
            SELECT gs_skill, gs_substate FROM entries
            WHERE gs_skill IS NOT NULL AND created_at <= ?
            ORDER BY created_at DESC LIMIT 1
        """, [ts]).fetchone()

        if row:
            return row[0], row[1]
        return None, None

    # ------------------------------------------------------------------
    # Oracle query
    # ------------------------------------------------------------------

    def oracle_query(
        self,
        query: str,
        max_results: int = 10,
        result_type: str = "all",
        scope: Optional[str] = None,
        min_relevance: float = 0.0,
        fuzzy: bool = False,
        include_archive: bool = False,
        include_quality: bool = False,
    ) -> AskOracleResult:
        """Search oracle tables with relevance scoring.

        If ``include_archive`` is True, recent entries touching matched
        projects/files are appended. ``include_issues`` is handled by the
        calling tool in sbs_tools.py.
        """
        self.ensure_loaded()
        assert self._conn is not None

        query_lower = query.lower()
        query_words = query_lower.split()
        file_matches: list[OracleMatch] = []
        concepts: list[OracleConcept] = []
        seen_files: set[str] = set()

        # --- File matches ---
        if result_type in ("all", "files"):
            rows = self._conn.execute(
                "SELECT file_path, section, concept, notes FROM oracle_files"
            ).fetchall()
            for fpath, section, concept, notes in rows:
                if scope and scope.lower() not in fpath.lower() and scope.lower() not in section.lower():
                    continue
                is_match = query_lower in fpath.lower()
                is_fuzzy = False
                if not is_match and fuzzy:
                    words = fpath.lower().replace("/", " ").replace(".", " ").split()
                    is_fuzzy = bool(difflib.get_close_matches(query_lower, words, n=1, cutoff=0.6))
                if is_match or is_fuzzy:
                    if fpath not in seen_files:
                        seen_files.add(fpath)
                        ctx_str = f"Found in section: {section}"
                        if concept:
                            ctx_str = f"{concept} -> {ctx_str}"
                        if notes:
                            ctx_str += f" ({notes})"
                        relevance = 1.0 if query_lower == fpath.lower() else (0.5 if is_fuzzy else 0.7)
                        file_matches.append(OracleMatch(
                            file=fpath, lines=None, context=ctx_str, relevance=relevance,
                        ))

        # --- Concept matches ---
        if result_type in ("all", "concepts"):
            rows = self._conn.execute(
                "SELECT concept, primary_location, notes, section FROM oracle_concepts"
            ).fetchall()
            for name, location, notes_val, section in rows:
                if scope and scope.lower() not in (location or "").lower() and scope.lower() not in section.lower():
                    continue
                name_lower = name.lower()
                notes_lower = (notes_val or "").lower()
                relevance = 0.0
                if query_lower in name_lower:
                    relevance = 0.9 if query_lower == name_lower else 0.8
                elif any(w in name_lower for w in query_words):
                    relevance = 0.7
                elif query_lower in notes_lower:
                    relevance = 0.6
                elif any(w in notes_lower for w in query_words):
                    relevance = 0.5
                elif fuzzy and difflib.get_close_matches(
                    query_lower,
                    (name_lower + " " + notes_lower).split(),
                    n=1,
                    cutoff=0.6,
                ):
                    relevance = 0.4

                if relevance > 0:
                    is_file = location and ("/" in location or location.endswith((".lean", ".py", ".md")))
                    if is_file:
                        if location not in seen_files:
                            seen_files.add(location)
                            ctx_str = f"Concept '{name}' in {section}"
                            if notes_lower:
                                ctx_str += f" ({notes_val})"
                            file_matches.append(OracleMatch(
                                file=location, lines=None, context=ctx_str, relevance=relevance,
                            ))
                    else:
                        concepts.append(OracleConcept(name=name, section=section))

        # Filter by min_relevance and sort
        if min_relevance > 0:
            file_matches = [m for m in file_matches if m.relevance >= min_relevance]
        file_matches.sort(key=lambda m: m.relevance, reverse=True)
        file_matches = file_matches[:max_results]

        # Archive context
        archive_context = None
        if include_archive:
            recent = self._fetch_entries(
                "SELECT * FROM entries ORDER BY created_at DESC NULLS LAST LIMIT 5"
            )
            if recent:
                archive_context = {
                    "recent_entries": [
                        {"entry_id": e["entry_id"], "project": e["project"], "trigger": e["trigger"]}
                        for e in recent
                    ]
                }

        # Quality snapshot
        quality_snapshot = None
        if include_quality:
            row = self._conn.execute(
                "SELECT quality_overall, quality_scores FROM entries "
                "WHERE quality_overall IS NOT NULL ORDER BY created_at DESC NULLS LAST LIMIT 1"
            ).fetchone()
            if row:
                scores = row[1]
                if isinstance(scores, str):
                    try:
                        scores = json.loads(scores)
                    except (json.JSONDecodeError, TypeError):
                        pass
                quality_snapshot = {"overall": row[0], "scores": scores}

        return AskOracleResult(
            file_matches=file_matches,
            concepts=concepts,
            archive_context=archive_context,
            quality_snapshot=quality_snapshot,
        )

    # ------------------------------------------------------------------
    # Context generation
    # ------------------------------------------------------------------

    def build_context_block(self, include: Optional[list[str]] = None) -> str:
        """Generate markdown context block (replaces generate_context_block)."""
        self.ensure_loaded()
        assert self._conn is not None

        sections_to_include = include or ["state", "epoch", "quality", "recent"]
        lines: list[str] = []

        if "state" in sections_to_include:
            skill, substate = self.get_global_state()
            lines.append("## Current State")
            if skill:
                lines.append(f"- Skill: {skill}")
                lines.append(f"- Substate: {substate}")
            else:
                lines.append("- Idle (no active skill)")
            lines.append("")

        if "epoch" in sections_to_include:
            meta = self.get_metadata()
            lines.append("## Current Epoch")
            epoch_entries = self.get_epoch_entries()
            lines.append(f"- Last epoch entry: {meta.get('last_epoch_entry', 'N/A')}")
            lines.append(f"- Entries in current epoch: {len(epoch_entries)}")
            lines.append("")

        if "quality" in sections_to_include:
            row = self._conn.execute(
                "SELECT quality_overall, entry_id FROM entries "
                "WHERE quality_overall IS NOT NULL ORDER BY created_at DESC NULLS LAST LIMIT 1"
            ).fetchone()
            if row:
                lines.append("## Quality")
                lines.append(f"- Latest score: {row[0]} (entry {row[1]})")
                lines.append("")

        if "recent" in sections_to_include:
            recent = self._fetch_entries(
                "SELECT * FROM entries ORDER BY created_at DESC NULLS LAST LIMIT 10"
            )
            lines.append("## Recent Archive Activity")
            lines.append("")
            for entry in recent:
                all_tags = (entry.get("tags") or []) + (entry.get("auto_tags") or [])
                tags_str = ", ".join(all_tags) or "none"
                lines.append(f"- **{entry['entry_id']}** ({entry.get('trigger', '')}): {entry.get('project', '')}")
                if entry.get("notes"):
                    lines.append(f"  Notes: {entry['notes'][:80]}...")
                lines.append(f"  Tags: {tags_str}")
                lines.append("")

        return "\n".join(lines)


# ======================================================================
# Module-level helpers for session grouping on dict-based entries
# ======================================================================


def _parse_ts(s: Optional[str]) -> Optional[datetime]:
    """Parse an ISO timestamp string into a timezone-aware datetime."""
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _group_dicts_by_skill_session(entries: list[dict]) -> list[dict]:
    """Group dict-based entries into skill sessions.

    Returns list of session dicts with keys:
    skill, entries, first_entry_id, last_entry_id, phases_visited,
    completed, start_time, end_time, last_substate.
    """
    sorted_entries = sorted(entries, key=lambda e: e["entry_id"])
    sessions: list[dict] = []
    current: Optional[dict] = None

    def _close(s: dict) -> None:
        if s["entries"]:
            s["last_entry_id"] = s["entries"][-1]["entry_id"]
            s["end_time"] = s["entries"][-1].get("created_at")
        sessions.append(s)

    def _new_session(skill: str, entry: dict, substate: str) -> dict:
        return {
            "skill": skill,
            "entries": [entry],
            "first_entry_id": entry["entry_id"],
            "last_entry_id": entry["entry_id"],
            "phases_visited": [substate] if substate else [],
            "completed": False,
            "start_time": entry.get("created_at"),
            "end_time": entry.get("created_at"),
            "last_substate": substate,
        }

    for entry in sorted_entries:
        st = entry.get("state_transition") or ""

        # phase_end closes current session (or creates+closes if none active)
        if st == "phase_end":
            gs = entry.get("global_state") or {}
            skill = gs.get("skill")
            substate = gs.get("substate", "")
            if current is not None:
                current["entries"].append(entry)
                current["completed"] = True
                current["last_entry_id"] = entry["entry_id"]
                current["end_time"] = entry.get("created_at")
                sessions.append(current)
                current = None
            elif skill:
                # Tail of a session that started before our data window
                s = _new_session(skill, entry, substate)
                s["completed"] = True
                sessions.append(s)
            continue

        # handoff: close outgoing, start incoming
        if st == "handoff" and current is not None:
            current["entries"].append(entry)
            current["completed"] = True
            current["last_entry_id"] = entry["entry_id"]
            current["end_time"] = entry.get("created_at")
            sessions.append(current)
            gs = entry.get("global_state") or {}
            new_skill = gs.get("skill", "")
            new_sub = gs.get("substate", "")
            current = _new_session(new_skill, entry, new_sub)
            continue

        gs = entry.get("global_state") or {}
        skill = gs.get("skill")
        substate = gs.get("substate", "")

        if not skill:
            continue

        if st == "phase_start":
            if current is not None and current["skill"] == skill:
                current["entries"].append(entry)
                if substate and (not current["phases_visited"] or current["phases_visited"][-1] != substate):
                    current["phases_visited"].append(substate)
                if substate:
                    current["last_substate"] = substate
            else:
                if current is not None:
                    _close(current)
                current = _new_session(skill, entry, substate)
            continue

        if current is not None and current["skill"] == skill:
            current["entries"].append(entry)
            if substate and (not current["phases_visited"] or current["phases_visited"][-1] != substate):
                current["phases_visited"].append(substate)
            if substate:
                current["last_substate"] = substate
            continue

        if current is not None:
            _close(current)
        current = _new_session(skill, entry, substate)

    if current is not None:
        _close(current)

    return sessions


def _compute_dict_session_duration(session: dict) -> Optional[float]:
    """Compute session duration from ISO timestamps."""
    start = session.get("start_time")
    end = session.get("end_time")
    if not start or not end:
        return None
    try:
        if isinstance(start, datetime):
            s = start
        else:
            s = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        if isinstance(end, datetime):
            e = end
        else:
            e = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
        return (e - s).total_seconds()
    except (ValueError, TypeError):
        return None


def _detect_backward_transitions_dict(session: dict, expected_order: list[str]) -> list[tuple[str, str, str]]:
    """Detect backward phase transitions within a dict-based session."""
    backward = []
    prev_phase: Optional[str] = None
    for entry in session["entries"]:
        gs = entry.get("global_state") or {}
        substate = gs.get("substate", "")
        if not substate:
            continue
        if prev_phase and substate != prev_phase:
            try:
                prev_idx = expected_order.index(prev_phase)
                curr_idx = expected_order.index(substate)
                if curr_idx < prev_idx:
                    backward.append((entry["entry_id"], prev_phase, substate))
            except ValueError:
                pass
        prev_phase = substate
    return backward


def _detect_skipped_phases_dict(session: dict, expected_order: list[str]) -> list[str]:
    """Detect skipped phases in a dict-based session."""
    visited = set(session.get("phases_visited", []))
    if not visited:
        return []
    visited_indices = []
    for phase in session["phases_visited"]:
        try:
            visited_indices.append(expected_order.index(phase))
        except ValueError:
            continue
    if len(visited_indices) < 2:
        return []
    min_idx = min(visited_indices)
    max_idx = max(visited_indices)
    return [
        expected_order[i]
        for i in range(min_idx, max_idx + 1)
        if i < len(expected_order) and expected_order[i] not in visited
    ]
