# Archive

Central archive for Side-by-Side Blueprint build data, screenshots, metrics, and visualizations.

## Directory Structure

```
archive/
  unified_ledger.json     # Build metrics and timing (single source of truth)
  lifetime_stats.json     # Cross-run aggregates
  archive_index.json      # Entry index with tags/notes
  compliance_ledger.json  # Compliance tracking
  charts/                 # Generated visualizations
    loc_trends.png        # Lines of code by language
    timing_trends.png     # Build phase durations
    activity_heatmap.png  # Repo activity per build
  chat_summaries/         # Session summaries
    {entry_id}.md
  {project}/              # Per-project screenshots
    latest/               # Most recent capture
      capture.json
      *.png
    archive/              # Historical captures
      {timestamp}/
        capture.json
        *.png
```

## iCloud Sync

Archive data is automatically synced to iCloud on every build:

```
~/Library/Mobile Documents/com~apple~CloudDocs/SBS_archive/
```

Sync is non-blocking - failures are logged but don't break builds.

## CLI Commands

### Screenshot Capture

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/scripts

# Capture static pages
python3 -m sbs capture --project SBSTest

# Capture with interactive states (hover, click, theme toggle)
python3 -m sbs capture --project SBSTest --interactive
```

### Archive Management

```bash
# List all entries
python3 -m sbs archive list

# List entries for a project
python3 -m sbs archive list --project SBSTest

# List entries with a specific tag
python3 -m sbs archive list --tag release

# Show entry details
python3 -m sbs archive show <entry_id>

# Add tags to an entry
python3 -m sbs archive tag <entry_id> release v1.0

# Add note to an entry
python3 -m sbs archive note <entry_id> "First stable release"

# Generate charts from build data
python3 -m sbs archive charts

# Sync archive to iCloud
python3 -m sbs archive sync

# Migrate historical captures to entry system
python3 -m sbs archive retroactive --dry-run
python3 -m sbs archive retroactive
```

## Captured Pages

8 pages are captured per project:

| Page | Description |
|------|-------------|
| `dashboard` | Main homepage with stats, key theorems, messages |
| `dep_graph` | Dependency graph with pan/zoom and modals |
| `chapter` | First detected chapter page with side-by-side displays |
| `paper_tex` | Paper from TeX source |
| `pdf_tex` | PDF viewer from TeX source |
| `paper_verso` | Paper from Verso source |
| `pdf_verso` | PDF viewer from Verso source |
| `blueprint_verso` | Blueprint from Verso source |

Pages returning HTTP 404 are skipped without error.

### Interactive States

With `--interactive`, additional screenshots are captured:

- `*_theme_toggle.png` - Dark mode variant
- `*_proof_toggle.png` - Proof expanded state
- `*_hover_token.png` - Token hover popup
- `dep_graph_zoom_*.png` - Zoom in/out/fit states
- `dep_graph_node_click_*.png` - Node modal views

## Archive Entries

Each build creates an `ArchiveEntry` with:

| Field | Description |
|-------|-------------|
| `entry_id` | Unique ID (unix timestamp) |
| `created_at` | ISO timestamp |
| `project` | Project name |
| `build_run_id` | Build run ID (links to unified ledger) |
| `tags` | User-defined tags |
| `notes` | User notes |
| `screenshots` | List of captured screenshots |
| `repo_commits` | Git commits at build time (all 11 repos) |
| `synced_to_icloud` | Sync status |

## Visualizations

Charts are generated from `unified_ledger.json`:

| Chart | Description |
|-------|-------------|
| `loc_trends.png` | Lines of code by language over last 20 builds |
| `timing_trends.png` | Build phase durations (stacked area) |
| `activity_heatmap.png` | Files changed per repo per build |

Regenerate manually: `python3 -m sbs archive charts`

## Build Integration

The archive system is integrated into `build.py`:

1. Build completes
2. Metrics saved to `unified_ledger.json`
3. Archive entry created with build_run_id
4. Charts regenerated
5. Entry synced to iCloud
6. Entry saved to `archive_index.json`
