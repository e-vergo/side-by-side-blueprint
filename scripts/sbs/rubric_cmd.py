"""Rubric management CLI commands."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from .rubric import Rubric, RubricIndex, RubricEvaluation
from .utils import ARCHIVE_DIR, log


# Rubrics are stored in archive/rubrics/
RUBRICS_DIR = ARCHIVE_DIR / "rubrics"
INDEX_PATH = RUBRICS_DIR / "index.json"


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


def cmd_rubric_evaluate(args: argparse.Namespace) -> int:
    """Evaluate a rubric against current state."""
    rubric_path = RUBRICS_DIR / f"{args.rubric_id}.json"
    if not rubric_path.exists():
        log.error(f"Rubric not found: {args.rubric_id}")
        return 1

    with open(rubric_path) as f:
        rubric = Rubric.from_dict(json.load(f))

    log.header(f"Evaluating: {rubric.name}")
    log.info(f"Project: {args.project}")
    log.info(f"Metrics: {len(rubric.metrics)}")

    # Create empty evaluation (actual evaluation would use validators)
    evaluation = RubricEvaluation(
        rubric_id=rubric.id,
        evaluated_at=datetime.now().isoformat(),
        evaluator="manual",
        results={},
        overall_score=0.0,
        passed=False,
        findings=["Evaluation not yet implemented - run validators manually"],
    )

    print()
    print(evaluation.to_markdown(rubric))

    if args.save:
        RUBRICS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        eval_path = RUBRICS_DIR / f"{rubric.id}_eval_{timestamp}.json"
        with open(eval_path, "w") as f:
            json.dump(evaluation.to_dict(), f, indent=2)
        log.success(f"Saved evaluation to: {eval_path}")

    return 0


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
