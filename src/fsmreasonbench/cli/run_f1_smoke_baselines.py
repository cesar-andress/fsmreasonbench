"""Run oracle, random, and invalid F1 baselines on one generated batch."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.evaluator.batch import run_f1_smoke_baselines
from fsmreasonbench.generator.separation import SeparationGeneratorConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-run all F1 baselines on one generated batch",
    )
    parser.add_argument("--n", type=int, default=100, help="Number of items (default: 100)")
    parser.add_argument("--seed", type=int, default=1, help="Batch generator seed (default: 1)")
    parser.add_argument(
        "--out-dir",
        default="runs/f1_smoke",
        help="Output directory (default: runs/f1_smoke)",
    )
    parser.add_argument(
        "--baseline-seed",
        type=int,
        default=0,
        help="Base RNG seed for random baseline (default: 0)",
    )
    parser.add_argument("--state-count-a", type=int, default=4)
    parser.add_argument("--state-count-b", type=int, default=4)
    parser.add_argument("--alphabet-size", type=int, default=3)
    parser.add_argument("--min-distinguishing-trace-length", type=int, default=2)
    parser.add_argument("--max-distinguishing-trace-length", type=int, default=12)
    parser.add_argument("--max-retries", type=int, default=64)
    args = parser.parse_args(argv)

    if args.n < 1:
        parser.error("--n must be >= 1")

    config = SeparationGeneratorConfig(
        state_count_a=args.state_count_a,
        state_count_b=args.state_count_b,
        alphabet_size=args.alphabet_size,
        min_distinguishing_trace_length=args.min_distinguishing_trace_length,
        max_distinguishing_trace_length=args.max_distinguishing_trace_length,
        max_retries=args.max_retries,
    )
    try:
        combined = run_f1_smoke_baselines(
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
                "family": "F1",
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
