"""
README staleness detection based on git state.

Checks all repos in the SBS workspace and reports which have uncommitted
or unpushed changes, indicating their READMEs may need updating.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import subprocess

# All repos to check (main + 10 submodules)
REPOS = [
    ("Main", ".", "README.md"),
    ("subverso", "forks/subverso", "forks/subverso/README.md"),
    ("verso", "forks/verso", "forks/verso/README.md"),
    ("LeanArchitect", "forks/LeanArchitect", "forks/LeanArchitect/README.md"),
    ("Dress", "toolchain/Dress", "toolchain/Dress/README.md"),
    ("Runway", "toolchain/Runway", "toolchain/Runway/README.md"),
    ("SBS-Test", "toolchain/SBS-Test", "toolchain/SBS-Test/README.md"),
    ("dress-blueprint-action", "toolchain/dress-blueprint-action", "toolchain/dress-blueprint-action/README.md"),
    ("GCR", "showcase/General_Crystallographic_Restriction", "showcase/General_Crystallographic_Restriction/README.md"),
    ("PNT", "showcase/PrimeNumberTheoremAnd", "showcase/PrimeNumberTheoremAnd/README.md"),
    ("storage", "dev/storage", "dev/storage/README.md"),
]


@dataclass
class RepoStatus:
    """Status of a single repository."""

    name: str
    path: str
    readme_path: str
    has_uncommitted: bool = False
    has_unpushed: bool = False
    changed_files: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return self.has_uncommitted or self.has_unpushed


def check_repo_status(repo_root: Path, name: str, rel_path: str, readme_path: str) -> RepoStatus:
    """
    Check git status for a single repo.

    Uses:
    - git status --porcelain for uncommitted changes
    - git log origin/main..HEAD --oneline for unpushed commits
    - git diff --name-only for changed file list
    """
    repo_path = repo_root / rel_path
    status = RepoStatus(name=name, path=rel_path, readme_path=readme_path)

    if not repo_path.exists():
        return status

    try:
        # Check for uncommitted changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            status.has_uncommitted = True
            # Parse changed files from porcelain output
            for line in result.stdout.strip().split("\n"):
                if line:
                    # Format: XY filename (XY is 2-char status)
                    status.changed_files.append(line[3:].strip())

        # Check for unpushed commits (try main, then master)
        for branch in ["main", "master"]:
            result = subprocess.run(
                ["git", "log", f"origin/{branch}..HEAD", "--oneline"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                if result.stdout.strip():
                    status.has_unpushed = True
                break
    except Exception:
        pass  # Gracefully handle git errors

    return status


def check_all_repos(repo_root: Path) -> list[RepoStatus]:
    """Check all repos and return statuses."""
    return [check_repo_status(repo_root, name, path, readme) for name, path, readme in REPOS]


def format_report(statuses: list[RepoStatus]) -> str:
    """Format human-readable report."""
    lines = ["README Staleness Report", "=" * 23, ""]

    changed = [s for s in statuses if s.has_changes]
    clean = [s for s in statuses if not s.has_changes]

    if changed:
        lines.append("Repos with changes (READMEs may need updating):")
        lines.append("")
        for i, s in enumerate(changed, 1):
            status_parts = []
            if s.has_uncommitted:
                status_parts.append("uncommitted changes")
            if s.has_unpushed:
                status_parts.append("unpushed commits")

            lines.append(f"{i}. {s.name} ({s.path})")
            lines.append(f"   README: {s.readme_path}")
            lines.append(f"   Status: {', '.join(status_parts)}")
            if s.changed_files:
                lines.append("   Changed files:")
                for f in s.changed_files[:10]:  # Limit to 10
                    lines.append(f"     - {f}")
                if len(s.changed_files) > 10:
                    lines.append(f"     ... and {len(s.changed_files) - 10} more")
            lines.append("")
    else:
        lines.append("No repos have changes. All READMEs are up to date.")
        lines.append("")

    if clean:
        lines.append("Clean repos (no README updates needed):")
        lines.append(f"  {', '.join(s.name for s in clean)}")
        lines.append("")

    lines.append(f"Summary: {len(changed)} repos need README review, {len(clean)} repos clean")

    return "\n".join(lines)


def format_json(statuses: list[RepoStatus]) -> str:
    """Format as JSON for programmatic use."""
    changed = [s for s in statuses if s.has_changes]
    clean = [s for s in statuses if not s.has_changes]

    data = {
        "repos_with_changes": [
            {
                "name": s.name,
                "path": s.path,
                "readme_path": s.readme_path,
                "has_uncommitted": s.has_uncommitted,
                "has_unpushed": s.has_unpushed,
                "changed_files": s.changed_files,
            }
            for s in changed
        ],
        "clean_repos": [s.name for s in clean],
        "summary": {"needs_review": len(changed), "clean": len(clean)},
    }

    return json.dumps(data, indent=2)
