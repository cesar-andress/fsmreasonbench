"""Evaluate a baseline on a JSONL batch of C2 items."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.evaluator.batch import evaluate_baseline_on_items
from fsmreasonbench.evaluator.jsonl import load_items_jsonl, write_jsonl


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate a baseline on C2 item JSONL")
    parser.add_argument(
        "--baseline",
        required=True,
        choices=["oracle", "random", "invalid"],
        help="Baseline system to evaluate",
    )
    parser.add_argument("--items", required=True, help="Input items JSONL (with answer_key)")
    parser.add_argument("--out", required=True, help="Output scoring records JSONL")
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Base RNG seed for random baseline (default: 0)",
    )
    args = parser.parse_args(argv)

    try:
        items = load_items_jsonl(args.items)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not items:
        print("ERROR: items JSONL is empty", file=sys.stderr)
        return 2

    for item in items:
        if item.family != "C2":
            print(f"ERROR: expected C2 items, got family={item.family!r}", file=sys.stderr)
            return 2

    records = evaluate_baseline_on_items(args.baseline, items, seed=args.seed)
    write_jsonl(args.out, (record.to_dict() for record in records))
    print(
        json.dumps(
            {
                "baseline": args.baseline,
                "n": len(records),
                "out": args.out,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
