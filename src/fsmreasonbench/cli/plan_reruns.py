"""CLI to plan local matrix reruns from integrity audit rules."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fsmreasonbench.runners.rerun_planner import (
    build_rerun_plan,
    render_rerun_plan_summary,
    write_rerun_plan_artifacts,
)
from fsmreasonbench.runners.track_pilot_models import parse_temperatures


def _parse_csv(raw: str) -> tuple[str, ...]:
    values = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not values:
        raise ValueError("expected at least one value")
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Plan reruns for a local matrix experiment from integrity audit rules",
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
        "--max-items",
        type=int,
        default=20,
        help="Expected items per cell (default: 20)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=900.0,
        help="Timeout passed to generated rerun commands (default: 900)",
    )
    parser.add_argument(
        "--incremental-safe",
        action="store_true",
        help="Add --incremental-safe to generated rerun commands",
    )
    parser.add_argument(
        "--write-scripts",
        action="store_true",
        help="Write mandatory_rerun.sh and recommended_rerun.sh under rerun_plans/",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON summary to stdout",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        parser.error(f"--root is not a directory: {root}")

    if args.max_items < 1:
        parser.error("--max-items must be >= 1")

    try:
        models = _parse_csv(args.models) if args.models else None
        families = _parse_csv(args.families)
        tracks = _parse_csv(args.tracks)
        temperatures = parse_temperatures(args.temperatures)
    except ValueError as exc:
        parser.error(str(exc))

    plan = build_rerun_plan(
        root,
        models=models,
        families=families,
        tracks=tracks,
        temperatures=temperatures,
        max_items=args.max_items,
        timeout=args.timeout,
        incremental_safe=args.incremental_safe,
    )

    artifact_paths: dict[str, str] = {}
    if args.write_scripts:
        artifact_paths = write_rerun_plan_artifacts(
            plan,
            root / "rerun_plans",
            timeout=args.timeout,
            incremental_safe=args.incremental_safe,
        )

    if args.json:
        payload = {
            "root": str(plan.root),
            "tier_counts": plan.tier_counts(),
            "mandatory_group_count": len(plan.mandatory_groups),
            "recommended_group_count": len(plan.recommended_groups),
            "mandatory_cell_count": sum(len(group.cells) for group in plan.mandatory_groups),
            "recommended_cell_count": sum(len(group.cells) for group in plan.recommended_groups),
            "artifacts": artifact_paths,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_rerun_plan_summary(plan))
        if artifact_paths:
            print("## Generated artifacts", "")
            for label, path in artifact_paths.items():
                print(f"- **{label}:** `{path}`")
            print("")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
