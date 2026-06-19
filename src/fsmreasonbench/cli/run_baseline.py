"""Run a C2 reference baseline against a benchmark item."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from fsmreasonbench.baselines.c2 import (
    run_invalid_baseline,
    run_oracle_baseline,
    run_random_baseline,
)
from fsmreasonbench.evaluator.io import load_item
from fsmreasonbench.evaluator.scorer import score_c2_item

_BASELINES = frozenset({"oracle", "random", "invalid"})


def run_baseline(
    baseline: str,
    item_path: str,
    *,
    seed: int = 0,
) -> Any:
    item = load_item(item_path)
    if item.family != "C2":
        raise ValueError(f"expected C2 item, got family={item.family!r}")
    if baseline == "oracle":
        return run_oracle_baseline(item)
    if baseline == "random":
        return run_random_baseline(item, seed=seed)
    if baseline == "invalid":
        return run_invalid_baseline(item)
    raise ValueError(f"unknown baseline {baseline!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a C2 reference baseline")
    parser.add_argument(
        "--baseline",
        required=True,
        choices=sorted(_BASELINES),
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
        raw_response = run_baseline(args.baseline, args.item, seed=args.seed)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if isinstance(raw_response, dict):
        print(json.dumps(raw_response, indent=2, sort_keys=True))
    else:
        print(raw_response)

    if args.score:
        item = load_item(args.item)
        record = score_c2_item(item, raw_response)
        print(json.dumps(record.to_dict(), indent=2, sort_keys=True), file=sys.stderr)
        return 0 if record.fully_correct else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
