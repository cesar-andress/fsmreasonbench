"""CLI for inspecting on-disk matrix experiment cell status."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fsmreasonbench.runners.experiment_cells import DEFAULT_STALE_RUNNING_SECONDS
from fsmreasonbench.runners.experiment_status import (
    format_experiment_status_report,
    scan_experiment_status,
)
from fsmreasonbench.runners.track_pilot_models import parse_temperatures


def _parse_csv(raw: str) -> tuple[str, ...]:
    values = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not values:
        raise ValueError("expected at least one value")
    return values


def _discover_models(root: Path) -> tuple[str, ...]:
    summary_path = root / "combined_summary.json"
    if summary_path.exists():
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        models = payload.get("models")
        if isinstance(models, list) and models:
            return tuple(str(model) for model in models)
    return tuple()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize cell status for a local matrix experiment directory",
    )
    parser.add_argument(
        "--root",
        required=True,
        help="Experiment root directory (e.g. runs/local_matrix_v1)",
    )
    parser.add_argument(
        "--models",
        help="Comma-separated models (default: infer from --root subdirectories)",
    )
    parser.add_argument("--families", default="C2,F1")
    parser.add_argument("--tracks", default="R0,R1,R2")
    parser.add_argument("--temperatures", default="0,0.2,0.7")
    parser.add_argument(
        "--stale-running-seconds",
        type=float,
        default=DEFAULT_STALE_RUNNING_SECONDS,
        help=f"Mark running cells stale after N seconds (default: {DEFAULT_STALE_RUNNING_SECONDS:g})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of markdown",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        parser.error(f"--root is not a directory: {root}")

    try:
        models = _parse_csv(args.models) if args.models else _discover_models(root)
        if not models:
            raise ValueError("could not infer models; pass --models explicitly")
        families = _parse_csv(args.families)
        tracks = _parse_csv(args.tracks)
        temperatures = parse_temperatures(args.temperatures)
    except ValueError as exc:
        parser.error(str(exc))

    result = scan_experiment_status(
        root,
        models=models,
        families=families,
        tracks=tracks,
        temperatures=temperatures,
        stale_running_seconds=args.stale_running_seconds,
    )

    if args.json:
        payload = {
            "root": str(result.root),
            "status_counts": result.status_counts,
            "incomplete_cells": result.incomplete_cells,
            "suggested_retry": result.suggested_retry,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(format_experiment_status_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
