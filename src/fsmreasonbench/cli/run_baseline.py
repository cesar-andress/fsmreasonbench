"""Run a reference baseline against a benchmark item."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from fsmreasonbench.baselines.runner import run_baseline as dispatch_baseline
from fsmreasonbench.evaluator.io import load_item
from fsmreasonbench.evaluator.scorer import score_item


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a reference baseline")
    parser.add_argument(
        "--baseline",
        required=True,
        choices=["oracle", "random", "invalid"],
        help="Baseline system: oracle (ceiling), random, or invalid",
    )
    parser.add_argument("--item", required=True, help="Path to full benchmark item JSON")
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="RNG seed for random baseline (default: 0)",
    )
    parser.add_argument(
        "--score",
        action="store_true",
        help="Score the baseline output and print scoring record",
    )
    args = parser.parse_args(argv)

    try:
        item = load_item(args.item)
        raw_response = dispatch_baseline(args.baseline, item, seed=args.seed)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if isinstance(raw_response, dict):
        print(json.dumps(raw_response, indent=2, sort_keys=True))
    else:
        print(raw_response)

    if args.score:
        record = score_item(item, raw_response)
        print(json.dumps(record.to_dict(), indent=2, sort_keys=True), file=sys.stderr)
        return 0 if record.fully_correct else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
