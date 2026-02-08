"""
Matplotlib-based visualizations for archive data.
"""

from pathlib import Path
from typing import Optional
import json
import logging

log = logging.getLogger(__name__)

# Try to import matplotlib (optional dependency)
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def generate_loc_chart(ledger_path: Path, output_path: Path, last_n: int = 20) -> bool:
    """
    Generate LOC trends line chart.

    X: Build timestamps (last N)
    Y: LOC count
    Lines: Per-language (Lean, Python, CSS, JS)

    Returns True if chart generated, False otherwise.
    """
    if not HAS_MATPLOTLIB:
        log.warning("matplotlib not installed, skipping LOC chart")
        return False

    # Load unified ledger
    if not ledger_path.exists():
        log.warning(f"Ledger not found: {ledger_path}")
        return False

    with open(ledger_path) as f:
        ledger = json.load(f)

    builds = ledger.get("build_history", [])[-last_n:]
    if not builds:
        log.warning("No builds in ledger")
        return False

    # Extract data
    timestamps = []
    loc_by_lang = {"Lean": [], "Python": [], "CSS": [], "JavaScript": []}

    for build in builds:
        timestamps.append(build.get("started_at", ""))
        loc_data = build.get("loc_by_language", {})
        for lang in loc_by_lang:
            loc_by_lang[lang].append(loc_data.get(lang, 0))

    # Create chart
    fig, ax = plt.subplots(figsize=(12, 6))
    for lang, values in loc_by_lang.items():
        if any(v > 0 for v in values):  # Only plot if has data
            ax.plot(range(len(timestamps)), values, marker='o', label=lang)

    ax.set_xlabel("Build")
    ax.set_ylabel("Lines of Code")
    ax.set_title("LOC Trends by Language")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Rotate x labels if too many
    if len(timestamps) > 10:
        plt.xticks(rotation=45, ha='right')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close(fig)

    log.info(f"Generated LOC chart: {output_path}")
    return True


def generate_timing_chart(ledger_path: Path, output_path: Path, last_n: int = 20) -> bool:
    """
    Generate build timing trends stacked area chart.

    X: Build timestamps
    Y: Duration (seconds)
    Areas: sync_repos, build_toolchain, build_project, generate_site

    Returns True if chart generated, False otherwise.
    """
    if not HAS_MATPLOTLIB:
        log.warning("matplotlib not installed, skipping timing chart")
        return False

    # Load unified ledger
    if not ledger_path.exists():
        return False

    with open(ledger_path) as f:
        ledger = json.load(f)

    builds = ledger.get("build_history", [])[-last_n:]
    if not builds:
        return False

    # Extract timing phases
    phases = ["sync_repos", "build_toolchain", "build_project", "generate_site"]
    phase_data = {p: [] for p in phases}

    for build in builds:
        phase_timings = build.get("phase_timings", {})
        for phase in phases:
            phase_data[phase].append(phase_timings.get(phase, 0))

    # Create stacked area chart
    fig, ax = plt.subplots(figsize=(12, 6))

    x = range(len(builds))
    bottom = [0] * len(builds)

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    for i, phase in enumerate(phases):
        values = phase_data[phase]
        ax.fill_between(x, bottom, [b + v for b, v in zip(bottom, values)],
                       label=phase.replace('_', ' ').title(), alpha=0.7, color=colors[i])
        bottom = [b + v for b, v in zip(bottom, values)]

    ax.set_xlabel("Build")
    ax.set_ylabel("Duration (seconds)")
    ax.set_title("Build Timing Breakdown")
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close(fig)

    log.info(f"Generated timing chart: {output_path}")
    return True


def generate_activity_heatmap(ledger_path: Path, output_path: Path, last_n: int = 20) -> bool:
    """
    Generate diff activity heatmap.

    Rows: Repos
    Columns: Recent builds
    Color: Files changed intensity

    Returns True if chart generated, False otherwise.
    """
    if not HAS_MATPLOTLIB:
        log.warning("matplotlib not installed, skipping heatmap")
        return False

    # Load unified ledger
    if not ledger_path.exists():
        return False

    with open(ledger_path) as f:
        ledger = json.load(f)

    builds = ledger.get("build_history", [])[-last_n:]
    if not builds:
        return False

    # Collect all repos from commits_before/after
    all_repos = set()
    for build in builds:
        all_repos.update(build.get("commits_before", {}).keys())
        all_repos.update(build.get("commits_after", {}).keys())

    if not all_repos:
        log.warning("No repo data for heatmap")
        return False

    repos = sorted(all_repos)

    # Build heatmap data based on repos_changed
    data = []
    for repo in repos:
        row = []
        for build in builds:
            repos_changed = build.get("repos_changed", [])
            # 1 if repo was changed, 0 otherwise
            changed = 1 if repo in repos_changed else 0
            row.append(changed)
        data.append(row)

    # Create heatmap
    fig, ax = plt.subplots(figsize=(max(8, len(builds) * 0.5), max(4, len(repos) * 0.4)))

    import numpy as np
    data_array = np.array(data)

    im = ax.imshow(data_array, cmap='YlOrRd', aspect='auto')

    ax.set_xticks(range(len(builds)))
    ax.set_xticklabels([f"B{i+1}" for i in range(len(builds))])
    ax.set_yticks(range(len(repos)))
    ax.set_yticklabels(repos)

    ax.set_xlabel("Build")
    ax.set_ylabel("Repository")
    ax.set_title("Files Changed Heatmap")

    fig.colorbar(im, ax=ax, label="Files Changed")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close(fig)

    log.info(f"Generated activity heatmap: {output_path}")
    return True


def generate_archive_timing_chart(entries: list, output_dir: Path, max_entries: int = 20) -> Optional[Path]:
    """Generate stacked bar chart of archive upload phase timings.

    Shows per-phase timing breakdown for recent archive entries that have
    archive_timings data.

    Args:
        entries: List of ArchiveEntry objects (or dicts with archive_timings)
        output_dir: Directory to save the chart
        max_entries: Maximum number of entries to include

    Returns:
        Path to generated chart, or None if no data available.
    """
    if not HAS_MATPLOTLIB:
        log.warning("matplotlib not installed, skipping archive timing chart")
        return None

    # Filter entries to those with non-empty archive_timings
    timed_entries = []
    for entry in entries:
        timings = entry.get("archive_timings") if isinstance(entry, dict) else getattr(entry, "archive_timings", None)
        if timings:
            timed_entries.append(entry)

    if not timed_entries:
        log.warning("No entries with archive_timings data")
        return None

    # Take the most recent max_entries
    timed_entries = timed_entries[-max_entries:]

    # Define phases and colors
    phases = [
        "extraction", "quality_scores", "repo_commits", "tagging",
        "gate_validation", "index_save", "icloud_sync_launch", "porcelain",
    ]
    phase_colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
        '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
    ]

    # Extract timing data
    labels = []
    phase_data = {p: [] for p in phases}

    for entry in timed_entries:
        timings = entry.get("archive_timings") if isinstance(entry, dict) else getattr(entry, "archive_timings", None)
        entry_id = entry.get("entry_id") if isinstance(entry, dict) else getattr(entry, "entry_id", "?")
        # Use short entry_id or timestamp for x-axis label
        label = str(entry_id)[-6:] if len(str(entry_id)) > 6 else str(entry_id)
        labels.append(label)

        for phase in phases:
            phase_data[phase].append(timings.get(phase, 0) if isinstance(timings, dict) else 0)

    # Create stacked bar chart
    fig, ax = plt.subplots(figsize=(max(10, len(labels) * 0.6), 6))

    x = range(len(labels))
    bottom = [0.0] * len(labels)

    for i, phase in enumerate(phases):
        values = phase_data[phase]
        if any(v > 0 for v in values):
            ax.bar(x, values, bottom=bottom, label=phase.replace('_', ' ').title(),
                   color=phase_colors[i], alpha=0.85, width=0.7)
            bottom = [b + v for b, v in zip(bottom, values)]

    ax.set_xlabel("Archive Entry")
    ax.set_ylabel("Duration (seconds)")
    ax.set_title("Archive Upload Phase Timings")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.legend(loc='upper left', fontsize='small')
    ax.grid(True, alpha=0.3, axis='y')

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "archive_timing_trends.png"
    fig.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close(fig)

    log.info(f"Generated archive timing chart: {output_path}")
    return output_path


def generate_all_charts(archive_root: Path) -> dict:
    """
    Generate all charts from unified ledger.

    Args:
        archive_root: Path to archive/ directory

    Returns:
        Dict with generated chart paths and any errors
    """
    ledger_path = archive_root / "unified_ledger.json"
    charts_dir = archive_root / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "generated": [],
        "failed": [],
        "skipped": []
    }

    if not HAS_MATPLOTLIB:
        results["skipped"] = ["matplotlib not installed"]
        return results

    charts = [
        ("loc_trends.png", generate_loc_chart),
        ("timing_trends.png", generate_timing_chart),
        ("activity_heatmap.png", generate_activity_heatmap),
    ]

    for filename, func in charts:
        output_path = charts_dir / filename
        try:
            if func(ledger_path, output_path):
                results["generated"].append(str(output_path))
            else:
                results["failed"].append(filename)
        except Exception as e:
            log.error(f"Error generating {filename}: {e}")
            results["failed"].append(f"{filename}: {e}")

    # Archive timing chart (uses archive_index.json entries, not ledger)
    try:
        index_path = archive_root / "archive_index.json"
        if index_path.exists():
            with open(index_path) as f:
                index_data = json.load(f)
            entries = index_data.get("entries", [])
            chart_path = generate_archive_timing_chart(entries, charts_dir)
            if chart_path:
                results["generated"].append(str(chart_path))
            else:
                results["failed"].append("archive_timing_trends.png")
        else:
            results["failed"].append("archive_timing_trends.png: no archive_index.json")
    except Exception as e:
        log.error(f"Error generating archive_timing_trends.png: {e}")
        results["failed"].append(f"archive_timing_trends.png: {e}")

    return results
