"""Evaluate a baseline on a JSONL batch of benchmark items."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.evaluator.batch import evaluate_baseline_on_items
from fsmreasonbench.evaluator.jsonl import load_items_jsonl, write_jsonl


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate a baseline on item JSONL")
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

    family = items[0].family
    if family not in {"C2", "F1", "F2"}:
        print(f"ERROR: unsupported family={family!r}", file=sys.stderr)
        return 2
    if any(item.family != family for item in items):
        print("ERROR: mixed families in items JSONL", file=sys.stderr)
        return 2

    try:
        records = evaluate_baseline_on_items(args.baseline, items, seed=args.seed)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    write_jsonl(args.out, (record.to_dict() for record in records))
    print(
        json.dumps(
            {
                "baseline": args.baseline,
                "family": family,
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
