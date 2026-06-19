"""Run oracle, random, and invalid C2 baselines on one generated batch."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.evaluator.batch import run_c2_smoke_baselines
from fsmreasonbench.generator.reachability import ReachabilityGeneratorConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-run all C2 baselines on one generated batch",
    )
    parser.add_argument("--n", type=int, default=100, help="Number of items (default: 100)")
    parser.add_argument("--seed", type=int, default=1, help="Batch generator seed (default: 1)")
    parser.add_argument(
        "--out-dir",
        default="runs/c2_smoke",
        help="Output directory (default: runs/c2_smoke)",
    )
    parser.add_argument(
        "--baseline-seed",
        type=int,
        default=0,
        help="Base RNG seed for random baseline (default: 0)",
    )
    parser.add_argument("--state-count", type=int, default=5)
    args = parser.parse_args(argv)

    if args.n < 1:
        parser.error("--n must be >= 1")

    config = ReachabilityGeneratorConfig(state_count=args.state_count)
    try:
        combined = run_c2_smoke_baselines(
            args.n,
            args.seed,
            args.out_dir,
            config=config,
            baseline_seed=args.baseline_seed,
        )
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "n": args.n,
                "seed": args.seed,
                "out_dir": args.out_dir,
                "baselines": [row["baseline"] for row in combined],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
