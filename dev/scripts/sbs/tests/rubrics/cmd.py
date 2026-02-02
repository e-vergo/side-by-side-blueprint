"""Rubric management CLI commands."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from sbs.tests.rubrics.rubric import Rubric, RubricIndex, RubricEvaluation
from sbs.tests.validators.base import ValidationContext
from sbs.core.utils import ARCHIVE_DIR, log


# Rubrics are stored in archive/rubrics/
RUBRICS_DIR = ARCHIVE_DIR / "rubrics"
INDEX_PATH = RUBRICS_DIR / "index.json"

# Project roots for known projects
PROJECT_ROOTS = {
    "SBSTest": "toolchain/SBS-Test",
    "GCR": "showcase/General_Crystallographic_Restriction",
    "PNT": "showcase/PrimeNumberTheoremAnd",
}


def cmd_rubric(args: argparse.Namespace) -> int:
    """Dispatch to rubric subcommands."""
    if not hasattr(args, "rubric_command") or args.rubric_command is None:
        log.error("No rubric subcommand specified. Use 'sbs rubric --help' for usage.")
        return 1

    if args.rubric_command == "create":
        return cmd_rubric_create(args)
    elif args.rubric_command == "show":
        return cmd_rubric_show(args)
    elif args.rubric_command == "list":
        return cmd_rubric_list(args)
    elif args.rubric_command == "evaluate":
        return cmd_rubric_evaluate(args)
    elif args.rubric_command == "delete":
        return cmd_rubric_delete(args)
    else:
        log.error(f"Unknown rubric subcommand: {args.rubric_command}")
        return 1


def cmd_rubric_create(args: argparse.Namespace) -> int:
    """Create a new rubric from JSON or interactively."""
    # Ensure directory exists
    RUBRICS_DIR.mkdir(parents=True, exist_ok=True)

    if args.from_json:
        # Load from JSON file
        json_path = Path(args.from_json)
        if not json_path.exists():
            log.error(f"File not found: {json_path}")
            return 1

        with open(json_path) as f:
            data = json.load(f)

        # Generate ID if not provided
        if "id" not in data:
            import uuid
            data["id"] = str(uuid.uuid4())

        rubric = Rubric.from_dict(data)
    elif args.name:
        # Create minimal rubric with name
        rubric = Rubric.create(name=args.name, categories=[])
    else:
        log.error("Must specify --from-json or --name")
        return 1

    # Save rubric
    rubric_path = RUBRICS_DIR / f"{rubric.id}.json"
    with open(rubric_path, "w") as f:
        json.dump(rubric.to_dict(), f, indent=2)

    # Generate markdown
    md_path = RUBRICS_DIR / f"{rubric.id}.md"
    with open(md_path, "w") as f:
        f.write(rubric.to_markdown())

    # Update index
    index = RubricIndex.load(INDEX_PATH) if INDEX_PATH.exists() else RubricIndex()
    index.add_rubric(rubric, str(rubric_path))
    index.save(INDEX_PATH)

    log.success(f"Created rubric: {rubric.id}")
    log.info(f"  Name: {rubric.name}")
    log.info(f"  JSON: {rubric_path}")
    log.info(f"  Markdown: {md_path}")
    return 0


def cmd_rubric_show(args: argparse.Namespace) -> int:
    """Display a rubric."""
    rubric_path = RUBRICS_DIR / f"{args.rubric_id}.json"
    if not rubric_path.exists():
        log.error(f"Rubric not found: {args.rubric_id}")
        return 1

    with open(rubric_path) as f:
        data = json.load(f)

    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        rubric = Rubric.from_dict(data)
        print(rubric.to_markdown())

    return 0


def cmd_rubric_list(args: argparse.Namespace) -> int:
    """List all rubrics."""
    if not INDEX_PATH.exists():
        log.info("No rubrics found.")
        return 0

    index = RubricIndex.load(INDEX_PATH)
    rubrics = index.list_rubrics()

    if not rubrics:
        log.info("No rubrics found.")
        return 0

    # Category filtering would require loading each rubric
    # For now, just list all
    if hasattr(args, "category") and args.category:
        log.warning("Category filtering requires loading rubrics (not yet implemented)")

    log.header("Rubrics")
    print(f"{'ID':<40} {'Name':<25} {'Version':<10} {'Created':<12}")
    print("-" * 90)
    for r in rubrics:
        rubric_id = r["id"][:38] + ".." if len(r["id"]) > 40 else r["id"]
        name = r["name"][:23] + ".." if len(r["name"]) > 25 else r["name"]
        version = r.get("version", "1.0.0")
        created = r.get("created_at", "")[:10]
        print(f"{rubric_id:<40} {name:<25} {version:<10} {created:<12}")

    return 0


def _get_repo_root() -> Path:
    """Get the SBS monorepo root directory."""
    # This file is at dev/scripts/sbs/tests/rubrics/cmd.py
    return Path(__file__).resolve().parent.parent.parent.parent.parent.parent


def _get_project_root(project: str, repo_root: Path) -> Optional[Path]:
    """Get the project root directory for a known project."""
    if project in PROJECT_ROOTS:
        project_path = repo_root / PROJECT_ROOTS[project]
        if project_path.exists():
            return project_path
    return None


def _get_git_commit(directory: Path) -> str:
    """Get the current git commit hash for a directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=directory,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()[:12]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def cmd_rubric_evaluate(args: argparse.Namespace) -> int:
    """Evaluate a rubric against current state using real validators."""
    from sbs.tests.validators.rubric_validator import RubricValidator

    rubric_path = RUBRICS_DIR / f"{args.rubric_id}.json"
    if not rubric_path.exists():
        log.error(f"Rubric not found: {args.rubric_id}")
        return 1

    with open(rubric_path) as f:
        rubric = Rubric.from_dict(json.load(f))

    log.header(f"Evaluating: {rubric.name}")
    log.info(f"Project: {args.project}")
    log.info(f"Metrics: {len(rubric.metrics)}")

    # Build validation context
    repo_root = _get_repo_root()
    project_root = _get_project_root(args.project, repo_root)

    if not project_root:
        log.warning(f"Unknown project '{args.project}', using repo root")
        project_root = repo_root

    commit = _get_git_commit(project_root)

    # Check for screenshots directory
    screenshots_dir = repo_root / "dev" / "storage" / args.project / "latest"
    if not screenshots_dir.exists():
        log.warning(f"Screenshots directory not found: {screenshots_dir}")
        log.info("AI-based validators will require screenshots. Run 'sbs capture' first.")
        screenshots_dir = None

    # Build site directory path
    site_dir = project_root / ".lake" / "build" / "runway"
    if not site_dir.exists():
        site_dir = None

    context = ValidationContext(
        project=args.project,
        project_root=project_root,
        commit=commit,
        screenshots_dir=screenshots_dir,
        site_dir=site_dir,
        extra={},
    )

    # Create and configure the rubric validator
    validator = RubricValidator()
    validator.set_rubric(rubric)

    # Run evaluation
    log.info("Running validators...")
    print()

    result = validator.validate(context)
    evaluation = validator.get_evaluation()

    if not evaluation:
        log.error("Evaluation failed - no results produced")
        return 1

    # Display results
    print(evaluation.to_markdown(rubric))

    # Summary
    print()
    if result.passed:
        log.success(f"Overall: PASSED ({evaluation.overall_score:.1%})")
    else:
        log.error(f"Overall: FAILED ({evaluation.overall_score:.1%})")

    # Show per-metric summary
    print()
    log.header("Metric Summary")
    for metric in rubric.metrics:
        metric_result = evaluation.results.get(metric.id)
        if metric_result:
            status = "PASS" if metric_result.passed else "FAIL"
            status_color = "\033[32m" if metric_result.passed else "\033[31m"
            print(f"  {status_color}{status}\033[0m  {metric.name}: {metric_result.value:.2f}")
        else:
            print(f"  \033[33mSKIP\033[0m  {metric.name}: not evaluated")

    if args.save:
        RUBRICS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        eval_path = RUBRICS_DIR / f"{rubric.id}_eval_{timestamp}.json"
        with open(eval_path, "w") as f:
            json.dump(evaluation.to_dict(), f, indent=2)
        log.success(f"Saved evaluation to: {eval_path}")

    return 0 if result.passed else 1


def cmd_rubric_delete(args: argparse.Namespace) -> int:
    """Delete a rubric."""
    rubric_path = RUBRICS_DIR / f"{args.rubric_id}.json"
    md_path = RUBRICS_DIR / f"{args.rubric_id}.md"

    if not rubric_path.exists():
        log.error(f"Rubric not found: {args.rubric_id}")
        return 1

    if not args.force:
        confirm = input(f"Delete rubric '{args.rubric_id}'? [y/N]: ")
        if confirm.lower() != "y":
            log.info("Cancelled.")
            return 0

    # Delete files
    rubric_path.unlink()
    if md_path.exists():
        md_path.unlink()

    # Update index
    if INDEX_PATH.exists():
        index = RubricIndex.load(INDEX_PATH)
        index.remove_rubric(args.rubric_id)
        index.save(INDEX_PATH)

    log.success(f"Deleted rubric: {args.rubric_id}")
    return 0
