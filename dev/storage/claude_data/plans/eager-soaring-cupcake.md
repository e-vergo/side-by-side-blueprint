# Plan: Archive System Expansion

## Status: ✅ COMPLETE

All planned work has been implemented and verified.

## Purpose

Expand the SBS archival system with comprehensive data capture, visualization, and iCloud sync:
- Archive Claude session data (transcripts, plans, summaries)
- Generate matplotlib visualizations (LOC trends, timing trends, activity heatmaps)
- Sync all data to iCloud on every build
- Tag/notes system with unique IDs for each archive entry
- Retroactive analysis of existing archived data
- **Consolidate local storage into single `archive/` directory**

---

## Storage Architecture

**Local Ground Truth:**
```
/Users/eric/GitHub/Side-By-Side-Blueprint/archive/
```

**Cloud Backup:**
```
/Users/eric/Library/Mobile Documents/com~apple~CloudDocs/SBS_archive/
```

**Tooling (separate):**
```
/Users/eric/GitHub/Side-By-Side-Blueprint/scripts/
```

**Claude System (external, read-only):**
```
~/.claude/projects/.../*.jsonl  # Session transcripts
~/.claude/plans/*.md            # Plan files
```

### Migration

| Current Location | New Location |
|------------------|--------------|
| `images/{project}/` | `archive/{project}/` |
| `scripts/stats/unified_ledger.json` | `archive/unified_ledger.json` |
| `scripts/stats/lifetime_stats.json` | `archive/lifetime_stats.json` |
| `scripts/stats/chart_output/` | `archive/charts/` |
| `scripts/compliance_ledger.json` | `archive/compliance_ledger.json` |
| (new) | `archive/archive_index.json` |
| (new) | `archive/chat_summaries/` |

---

## Scope

**Include:**
- Session transcripts (`~/.claude/projects/**/*.jsonl`) - copied to archive
- Plan files (`~/.claude/plans/*.md`) - copied to archive
- Auto-generated session summaries
- Screenshots (`archive/{project}/`)
- Build metrics (unified ledger)
- Code stats visualizations

**Exclude:**
- Telemetry (`~/.claude/telemetry/`)
- Debug logs (`~/.claude/debug/`)

---

## Phase 1: Archive Entry System

Create `scripts/sbs/archive/` module with entry data structures.

### Files to Create

| File | Purpose |
|------|---------|
| `archive/__init__.py` | Module exports |
| `archive/entry.py` | ArchiveEntry, ArchiveIndex dataclasses |

### Data Structures (entry.py)

```python
@dataclass
class ArchiveEntry:
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

@dataclass
class ArchiveIndex:
    version: str = "1.0"
    entries: dict[str, ArchiveEntry] = field(default_factory=dict)
    by_tag: dict[str, list[str]] = field(default_factory=dict)
    by_project: dict[str, list[str]] = field(default_factory=dict)
    latest_by_project: dict[str, str] = field(default_factory=dict)
```

---

## Phase 2: Directory Migration

Consolidate existing data into `archive/` directory.

### Migration Steps

1. Create `archive/` directory structure
2. Move `images/` contents to `archive/`
3. Move `scripts/stats/` contents to `archive/`
4. Move `scripts/compliance_ledger.json` to `archive/`
5. Update all path references in:
   - `scripts/build.py`
   - `scripts/sbs/ledger.py`
   - `scripts/sbs/capture.py`
   - `scripts/sbs/cli.py`
6. Delete empty `images/` and `scripts/stats/` directories

### Local Archive Structure

```
archive/
  unified_ledger.json     # Single source of truth
  lifetime_stats.json     # Cross-run aggregates
  archive_index.json      # Entry index with tags
  compliance_ledger.json  # Legacy (backwards compat)
  charts/                 # Generated visualizations
    loc_trends.png
    timing_trends.png
    activity_heatmap.png
  chat_summaries/         # Session summaries
    {entry_id}.md
  SBSTest/                # Per-project
    latest/
      capture.json
      *.png
    archive/
      {timestamp}/
  GCR/
    ...
```

---

## Phase 3: iCloud Sync

Create non-blocking iCloud sync that mirrors local archive.

### File to Create

| File | Purpose |
|------|---------|
| `scripts/sbs/archive/icloud_sync.py` | Sync logic to iCloud |

### iCloud Directory Structure (mirrors local)

```
SBS_archive/
  unified_ledger.json
  archive_index.json
  charts/
  chat_summaries/
  entries/
    {unix_timestamp}/     # Per-entry snapshots
      metadata.json
      screenshots/
  SBSTest/
    latest/
    archive/
  GCR/
    ...
```

### Sync Logic

```python
def sync_to_icloud(entry: ArchiveEntry, local_base: Path) -> bool:
    """
    Non-blocking sync. Steps:
    1. Create entry dir: SBS_archive/entries/{entry_id}/
    2. Copy: metadata.json, screenshots/, stats/, chat_summary.md, charts/
    3. Update index.json
    4. Mark entry.synced_to_icloud = True

    On error: log warning, set sync_error, never fail build.
    """
```

---

## Phase 4: Visualizations (matplotlib)

Generate charts from unified ledger data.

### File to Create

| File | Purpose |
|------|---------|
| `scripts/sbs/archive/visualizations.py` | matplotlib chart generation |

### Charts

1. **LOC Trends** (line chart)
   - X: Build timestamps (last 20)
   - Y: LOC count
   - Lines: Per-language (Lean, Python, CSS, JS)

2. **Build Timing Trends** (stacked area)
   - X: Build timestamps
   - Y: Duration (seconds)
   - Areas: sync_repos, build_toolchain, build_project, generate_site

3. **Diff Activity Heatmap** (grid)
   - Rows: Repos
   - Columns: Recent builds
   - Color: Files changed intensity

### Output

- Location: `archive/charts/`
- Files: `loc_trends.png`, `timing_trends.png`, `activity_heatmap.png`
- Synced to iCloud: `SBS_archive/charts/`

### Dependency

```bash
scripts/.venv/bin/pip install matplotlib
```

---

## Phase 5: Chat Archiving

Archive Claude session data with auto-generated summaries.

### File to Create

| File | Purpose |
|------|---------|
| `scripts/sbs/archive/chat_archive.py` | Session parsing and summary generation |

### Source Data

- `~/.claude/projects/-Users-eric-GitHub-Side-By-Side-Blueprint/*.jsonl`
- `~/.claude/plans/*.md`

### Logic

```python
def archive_chat_sessions(entry_id: str, output_dir: Path) -> dict:
    """
    1. Scan relevant .jsonl files (SBS workspace sessions)
    2. Parse: session ID, timestamps, messages, tool calls
    3. Generate summary (key decisions, files modified, commits)
    4. Save to output_dir/chat_summary.md
    """
```

---

## Phase 6: Build.py Integration

Integrate archive system into build pipeline.

### Modify: `scripts/build.py`

Add to end of `BuildOrchestrator.run()`:

```python
def _create_archive_entry(self) -> ArchiveEntry:
    return ArchiveEntry(
        entry_id=str(int(time.time())),
        created_at=datetime.now().isoformat(),
        project=self.config.project_name,
        build_run_id=self._run_id,
        repo_commits=self._commits_after,
    )

def _finalize_archive(self, entry: ArchiveEntry) -> None:
    # Copy screenshots to entry
    # Generate charts
    # Archive recent chat sessions
    # Sync to iCloud (non-blocking)
    # Save entry to index
```

### Extended Build Flow

1-8. (existing steps)
9. Create ArchiveEntry
10. Generate charts
11. Archive recent chat sessions
12. Sync to iCloud (non-blocking)
13. Save entry to index

---

## Phase 7: CLI Commands

Add archive management commands to sbs CLI.

### Modify: `scripts/sbs/cli.py`

```
sbs archive tag <entry_id> <tag> [<tag>...]
sbs archive note <entry_id> "Your note here"
sbs archive list [--project NAME] [--tag TAG]
sbs archive show <entry_id>
sbs archive retroactive
```

---

## Phase 8: Retroactive Migration

Apply entry system to existing archived data.

### File to Create

| File | Purpose |
|------|---------|
| `scripts/sbs/archive/retroactive.py` | Historical data migration |

### Logic

```python
def retroactive_migration() -> list[ArchiveEntry]:
    """
    1. Scan images/{project}/archive/{timestamp}/ directories
    2. Parse capture.json for metadata
    3. Cross-reference with unified_ledger by timestamp
    4. Cross-reference with Claude sessions by timestamp
    5. Create ArchiveEntry with best-effort linkage
    6. DO NOT sync to iCloud (user triggers manually)
    """
```

---

## Phase 9: Final README Update

Update `archive/README.md` to reflect the new archive system structure.

### Current State (outdated)

The README still references:
- Old `images/` directory structure
- Old `capture.py` script path
- Only 3 captured pages (dashboard, dep_graph, chapter)

### New Content

Update to document:

1. **New directory structure:**
```
archive/
  unified_ledger.json     # Build metrics and timing
  lifetime_stats.json     # Cross-run aggregates
  archive_index.json      # Entry index with tags/notes
  compliance_ledger.json  # Compliance tracking
  charts/                 # Generated visualizations
    loc_trends.png
    timing_trends.png
    activity_heatmap.png
  chat_summaries/         # Session summaries
  {project}/              # Per-project screenshots
    latest/
    archive/{timestamp}/
```

2. **New CLI commands:**
```bash
sbs capture --project NAME [--interactive]
sbs archive list [--project NAME] [--tag TAG]
sbs archive show <entry_id>
sbs archive tag <entry_id> <tag>...
sbs archive note <entry_id> "note"
sbs archive charts
sbs archive sync
sbs archive retroactive [--dry-run]
```

3. **All 8 captured pages:**
   - dashboard, dep_graph, chapter
   - paper_tex, pdf_tex, paper_verso, pdf_verso, blueprint_verso

4. **iCloud sync location:**
   - `~/Library/Mobile Documents/com~apple~CloudDocs/SBS_archive/`

5. **Archive entry system:**
   - Unique IDs (unix timestamps)
   - Tags and notes support
   - Automatic sync on build

---

## Implementation Order

1. ✅ **Entry dataclasses** - `scripts/sbs/archive/entry.py`
2. ✅ **Directory migration** - Move `images/` and `scripts/stats/` to `archive/`
3. ✅ **Update path references** - All scripts use new `archive/` location
4. ✅ **iCloud sync** - `scripts/sbs/archive/icloud_sync.py`
5. ✅ **Build.py integration** - Entry creation + sync on each build
6. ✅ **Chart generation** - `scripts/sbs/archive/visualizations.py` (install matplotlib)
7. ✅ **CLI commands** - Tag, note, list, show
8. ✅ **Chat archival** - `scripts/sbs/archive/chat_archive.py`
9. ✅ **Retroactive entry creation** - `scripts/sbs/archive/retroactive.py`
10. ✅ **Documentation** - Update CLAUDE.md
11. ⏳ **Final README** - Update `archive/README.md` to reflect new structure

---

## Critical Files

| File | Action | Status |
|------|--------|--------|
| `archive/` | CREATE (new directory) | ✅ |
| `scripts/sbs/archive/__init__.py` | CREATE | ✅ |
| `scripts/sbs/archive/entry.py` | CREATE | ✅ |
| `scripts/sbs/archive/icloud_sync.py` | CREATE | ✅ |
| `scripts/sbs/archive/visualizations.py` | CREATE | ✅ |
| `scripts/sbs/archive/chat_archive.py` | CREATE | ✅ |
| `scripts/sbs/archive/retroactive.py` | CREATE | ✅ |
| `scripts/build.py` | MODIFY (paths + archive finalization) | ✅ |
| `scripts/sbs/ledger.py` | MODIFY (paths to `archive/`) | ✅ |
| `scripts/sbs/capture.py` | MODIFY (paths to `archive/`) | ✅ |
| `scripts/sbs/cli.py` | MODIFY (paths + archive subcommands) | ✅ |
| `scripts/sbs/compare.py` | MODIFY (paths to `archive/`) | ✅ |
| `scripts/sbs/validate.py` | MODIFY (paths to `archive/`) | ✅ |
| `CLAUDE.md` | MODIFY (document archive system) | ✅ |
| `images/` | DELETE (after migration) | ✅ |
| `scripts/stats/` | DELETE (after migration) | ✅ |
| `archive/README.md` | UPDATE (reflect new structure) | ⏳ |

---

## Verification

### Unit Tests

```bash
cd scripts
python -c "from sbs.archive import ArchiveEntry, ArchiveIndex; print('OK')"
python -c "from sbs.archive.visualizations import generate_loc_chart; print('OK')"
```

### Migration Verification

```bash
# Verify new structure
ls -la /Users/eric/GitHub/Side-By-Side-Blueprint/archive/
ls -la /Users/eric/GitHub/Side-By-Side-Blueprint/archive/SBSTest/

# Verify old directories removed
test ! -d /Users/eric/GitHub/Side-By-Side-Blueprint/images && echo "images/ removed"
test ! -d /Users/eric/GitHub/Side-By-Side-Blueprint/scripts/stats && echo "scripts/stats/ removed"
```

### Integration Test

1. Run `python build.py` on SBS-Test
2. Verify `archive/archive_index.json` created
3. Verify `archive/charts/` contains PNGs
4. Verify `archive/unified_ledger.json` updated
5. Verify iCloud: `ls ~/Library/Mobile\ Documents/com~apple~CloudDocs/SBS_archive/`

### End-to-End Test

1. Run build with `--capture`
2. Add tag: `sbs archive tag <entry_id> release`
3. Add note: `sbs archive note <entry_id> "First release candidate"`
4. List: `sbs archive list --tag release`
5. Run retroactive: `sbs archive retroactive`
6. Verify all historical entries created

---

## Validators

For this implementation, use:
- `git-metrics`: Track commits across all repos
- `code-stats`: Track LOC changes
- `timing`: Track build performance
- `visual-compliance`: Verify no UI regressions

---

## Success Criteria

1. ✅ Archive entries created on every build
2. ✅ Charts generated with matplotlib (LOC, timing, activity)
3. ✅ iCloud sync works (non-blocking on failure)
4. ✅ CLI commands functional (tag, note, list, show)
5. ✅ Chat sessions archived with summaries
6. ✅ Retroactive migration populates historical entries
7. ✅ All data trackable through unified ledger
8. ⏳ `archive/README.md` updated to reflect new structure

## Verification Results

**Build completed:** 2026-01-31T19:26:14
- 208 files committed, 4,283 insertions
- 188.3s build duration across 12 phases
- 7 repos changed (Runway, verso, SBS-Test, GCR, PNT, Side-By-Side-Blueprint)
- Archive entry 1769905574 created with build_run_id
- 30 entries synced to iCloud
- Charts regenerated: timing_trends.png (44KB), activity_heatmap.png (32KB), loc_trends.png (15KB)
