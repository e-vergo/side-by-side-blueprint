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

    return results
