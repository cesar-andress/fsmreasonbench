"""Run exploratory C2/F1 capability-surface baseline sweeps."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.evaluator.capability_surface import (
    CapabilitySurfaceConfig,
    run_capability_surface,
)


def _parse_families(raw: str) -> tuple[str, ...]:
    families = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not families:
        raise ValueError("at least one family is required")
    for family in families:
        if family not in {"C2", "F1"}:
            raise ValueError(f"unsupported family: {family!r}")
    return families


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run exploratory C2/F1 baseline capability-surface sweeps",
    )
    parser.add_argument(
        "--families",
        default="C2,F1",
        help="Comma-separated families to sweep (default: C2,F1)",
    )
    parser.add_argument(
        "--n-per-level",
        type=int,
        default=50,
        help="Items to generate per family/level (default: 50)",
    )
    parser.add_argument("--seed", type=int, default=1, help="Base generator seed (default: 1)")
    parser.add_argument(
        "--out-dir",
        default="runs/capability_surface",
        help="Output directory (default: runs/capability_surface)",
    )
    parser.add_argument(
        "--baseline-seed",
        type=int,
        default=0,
        help="Base RNG seed for random baseline (default: 0)",
    )
    parser.add_argument(
        "--skip-failed-levels",
        action="store_true",
        help="Record levels that fail generation instead of aborting",
    )
    args = parser.parse_args(argv)

    if args.n_per_level < 1:
        parser.error("--n-per-level must be >= 1")

    try:
        families = _parse_families(args.families)
    except ValueError as exc:
        parser.error(str(exc))

    config = CapabilitySurfaceConfig(
        families=families,
        n_per_level=args.n_per_level,
        seed=args.seed,
        baseline_seed=args.baseline_seed,
        skip_failed_levels=args.skip_failed_levels,
    )
    try:
        payload = run_capability_surface(args.out_dir, config)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "out_dir": args.out_dir,
                "families": payload["families"],
                "n_per_level": payload["n_per_level"],
                "rows": len(payload["rows"]),
                "skipped_levels": len(payload["skipped_levels"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
