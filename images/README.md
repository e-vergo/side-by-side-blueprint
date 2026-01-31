# Screenshots

Visual verification screenshots for Side-by-Side Blueprint projects.

## Structure

```
images/
  {project}/
    latest/           # Most recent capture
      capture.json    # Metadata (timestamp, commit, pages)
      dashboard.png
      dep_graph.png
      chapter.png
    archive/          # Historical captures
      YYYY-MM-DD_HH-MM-SS/
        capture.json
        *.png
```

## Usage

From a project directory with `runway.json`:

```bash
# Capture with server running at localhost:8000
python /Users/eric/GitHub/Side-By-Side-Blueprint/scripts/capture.py

# Capture from custom URL
python /Users/eric/GitHub/Side-By-Side-Blueprint/scripts/capture.py --url http://localhost:3000
```

## Captured Pages

- **dashboard**: Main homepage with stats, key theorems, messages
- **dep_graph**: Dependency graph with pan/zoom and modals
- **chapter**: First detected chapter page with side-by-side displays
