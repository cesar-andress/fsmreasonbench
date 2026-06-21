"""CLI to repair misplaced local-matrix cell output directories."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fsmreasonbench.runners.local_matrix_paths import (
    apply_repair_actions,
    plan_repair_actions,
    scan_misplaced_cells,
    write_repair_log,
)
from fsmreasonbench.runners.track_pilot_models import infer_matrix_layout


def _load_models(root: Path) -> tuple[str, ...]:
    summary_path = root / "combined_summary.json"
    if summary_path.exists():
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        models = payload.get("models")
        if isinstance(models, list) and models:
            return tuple(str(model) for model in models)
    return tuple()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Repair misplaced local-matrix cell directories missing temp_* segments",
    )
    parser.add_argument("--root", required=True, help="Experiment root (e.g. runs/local_matrix_v1)")
    parser.add_argument(
        "--models",
        help="Comma-separated models (default: read from combined_summary.json)",
    )
    parser.add_argument("--families", default="C2,F1")
    parser.add_argument("--tracks", default="R0,R1,R2")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply repairs (default: dry-run only)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned repairs without moving files (default unless --apply)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        parser.error(f"--root is not a directory: {root}")
    if not infer_matrix_layout(root):
        parser.error(f"--root does not look like a local matrix experiment: {root}")

    models = (
        tuple(part.strip() for part in args.models.split(",") if part.strip())
        if args.models
        else _load_models(root)
    )
    families = tuple(part.strip() for part in args.families.split(",") if part.strip())
    tracks = tuple(part.strip() for part in args.tracks.split(",") if part.strip())
    dry_run = not args.apply

    misplaced = scan_misplaced_cells(
        root,
        models=models or None,
        families=families,
        tracks=tracks,
    )
    actions = plan_repair_actions(
        root,
        models=models or None,
        families=families,
        tracks=tracks,
    )
    result_actions = apply_repair_actions(actions, dry_run=dry_run)
    log_path = write_repair_log(root, result_actions, dry_run=dry_run)

    payload = {
        "root": str(root),
        "dry_run": dry_run,
        "misplaced_cells": misplaced,
        "actions": [
            {
                "source_dir": str(action.source_dir),
                "target_dir": str(action.target_dir),
                "model": action.model,
                "family": action.family,
                "track": action.track,
                "temperature": action.temperature,
                "status": action.status,
                "message": action.message,
            }
            for action in result_actions
        ],
        "repair_log": str(log_path),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if any(action.status == "conflict" for action in result_actions):
        return 2
    if any(action.status == "ambiguous" for action in result_actions):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
